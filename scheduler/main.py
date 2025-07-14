import time
import os
import sys
import schedule
import logging
import structlog
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from app.db.session import get_db_session
from app.models.task import Task
from app.models.template import Template
from app import crud
import requests # For calling the analysis endpoint
from datetime import datetime
from app.models.report_history import ReportHistoryCreate
from app.models.etl_job import ETLJob
from dependencies import create_service_container


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/app")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

# Configure logging
def setup_logging(log_level: str = "INFO"):
    """
    Configures structured logging for the scheduler.
    """
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        stream=sys.stdout,
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

# Setup logging and get logger
setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = structlog.get_logger("scheduler")

# Database session management is now handled by get_db_session from app.db.session
# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# @contextmanager
# def get_db_session():
#     """Provide a transactional scope around a series of operations."""
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

def run_task_flow(task_id: int, services: 'ServiceContainer' = None):
    """
    完整的任务执行流程，由调度器触发。
    """
    logger.info("Starting task flow", task_id=task_id)
    with get_db_session() as db:
        task = crud.task.get(db, id=task_id)
        if not task:
            logger.error("Task not found", task_id=task_id)
            return

        # 如果没有传入服务容器，创建一个新的
        if services is None:
            services = create_service_container(db)

        history_entry = None
        try:
            # 获取服务实例
            report_generation_service = services.get_report_generation_service()
            email_service = services.get_email_service()
            
            # 创建进行中的历史记录
            history_entry = crud.report_history.create(
                db, obj_in=ReportHistoryCreate(task_id=task_id, status="in_progress")
            )

            # --- 步骤 1: 生成报告 ---
            logger.info("Starting report generation", task_id=task_id, task_name=task.name)
            generation_result = report_generation_service.generate_report(
                task_id=task_id,
                template_id=task.template_id,
                data_source_id=task.data_source_id
            )
            logger.info("Report generation completed", 
                       task_id=task_id, 
                       status=generation_result['status'])
            
            if generation_result['status'] != "completed":
                raise Exception(f"Report generation failed: {generation_result.get('error_message', 'Unknown error')}")
                
            output_path = generation_result['output_path']
            logger.info("Report saved", task_id=task_id, output_path=output_path)

            # --- 步骤 2: 发送邮件 ---
            if task.recipients:
                logger.info("Starting email send", 
                           task_id=task_id, 
                           recipients=task.recipients)
                subject = f"自动化报告: {task.name}"
                body = "您好，附件是您订阅的最新报告，请查收。"
                email_service.send_email(
                    recipients=task.recipients.split(','),
                    subject=subject,
                    body=body,
                    attachment_path=output_path
                )
                logger.info("Email sent successfully", task_id=task_id)
            
            # 更新历史记录为成功
            crud.report_history.update(
                db, db_obj=history_entry, obj_in={"status": "success", "report_path": output_path}
            )
            logger.info("Task completed successfully", task_id=task_id)

        except Exception as e:
            logger.error("Task execution failed", task_id=task_id, error=str(e), exc_info=True)
            # 如果出错，更新历史记录为失败
            if history_entry:
                error_message = str(e)
                crud.report_history.update(
                    db, db_obj=history_entry, obj_in={"status": "failure", "error_message": error_message}
                )


def sync_all_jobs(scheduler):
    """Syncs all types of jobs (tasks, ETL, etc.) from the database."""
    logger.info("Starting full job sync")
    sync_tasks_from_db(scheduler)
    sync_etl_jobs_from_db(scheduler)


def sync_etl_jobs_from_db(scheduler):
    """
    Syncs the ETL jobs in the scheduler with the ETLJob models in the database.
    """
    logger.info("Syncing ETL jobs from database")
    with get_db_session() as db:
        try:
            db_etl_jobs = db.query(ETLJob).filter_by(enabled=True).all()
            
            scheduler_job_ids = {job.id for job in scheduler.get_jobs()}
            
            for job_model in db_etl_jobs:
                job_id = f"etl_{job_model.id}"
                
                if not job_model.schedule:
                    if job_id in scheduler_job_ids:
                        scheduler.remove_job(job_id)
                        logger.info("Removed ETL job with no schedule", 
                                   job_id=job_id, 
                                   job_name=job_model.name)
                    continue

                if job_id in scheduler_job_ids:
                    existing_job = scheduler.get_job(job_id)
                    if existing_job.trigger.cron_expression != job_model.schedule:
                        scheduler.reschedule_job(
                            job_id, 
                            trigger='cron', 
                            **_cron_to_dict(job_model.schedule)
                        )
                        logger.info("Rescheduled ETL job", 
                                   job_id=job_id, 
                                   job_name=job_model.name,
                                   schedule=job_model.schedule)
                else:
                    # 创建一个包装函数来处理ETL作业
                    def run_etl_job(job_id: int):
                        with get_db_session() as db:
                            services = create_service_container(db)
                            etl_service = services.get_etl_service()
                            etl_service.run_job(job_id)
                    
                    scheduler.add_job(
                        run_etl_job,
                        'cron',
                        id=job_id,
                        name=job_model.name,
                        args=[job_model.id], # Pass only job_id
                        **_cron_to_dict(job_model.schedule)
                    )
                    logger.info("Added new ETL job", 
                               job_id=job_id, 
                               job_name=job_model.name,
                               schedule=job_model.schedule)

            db_job_ids = {f"etl_{job.id}" for job in db_etl_jobs if job.schedule}
            for job_id in scheduler_job_ids:
                if job_id.startswith("etl_") and job_id not in db_job_ids:
                    scheduler.remove_job(job_id)
                    logger.info("Removed orphaned ETL job", job_id=job_id)
        except Exception as e:
            logger.error("Error during ETL job sync", error=str(e), exc_info=True)


def sync_tasks_from_db(scheduler):
    """
    Syncs the report generation tasks in the scheduler with the Task models in the database.
    """
    logger.info("Syncing tasks from database")
    with get_db_session() as db:
        db_tasks = db.query(Task).filter_by(is_active=True).all()
        
        scheduler_job_ids = {job.id for job in scheduler.get_jobs()}
        
        for task in db_tasks:
            job_id = f"task_{task.id}"
            
            if not task.schedule:
                if job_id in scheduler_job_ids:
                    scheduler.remove_job(job_id)
                    logger.info("Removed task with no schedule", 
                               job_id=job_id, 
                               task_name=task.name)
                continue

            if job_id in scheduler_job_ids:
                existing_job = scheduler.get_job(job_id)
                if existing_job.trigger.cron_expression != task.schedule:
                    scheduler.reschedule_job(
                        job_id, 
                        trigger='cron', 
                        **_cron_to_dict(task.schedule)
                    )
                    logger.info("Rescheduled task", 
                               job_id=job_id, 
                               task_name=task.name,
                               schedule=task.schedule)
            else:
                scheduler.add_job(
                    run_task_flow,
                    'cron',
                    id=job_id,
                    name=task.name,
                    args=[task.id],
                    **_cron_to_dict(task.schedule)
                )
                logger.info("Added new task", 
                           job_id=job_id, 
                           task_name=task.name,
                           schedule=task.schedule)

        db_task_ids = {f"task_{task.id}" for task in db_tasks if task.schedule}
        for job_id in scheduler_job_ids:
            if job_id.startswith("task_") and job_id not in db_task_ids:
                scheduler.remove_job(job_id)
                logger.info("Removed orphaned task", job_id=job_id)

def _cron_to_dict(cron_str: str) -> dict:
    """Converts a cron string to a dictionary for APScheduler."""
    parts = cron_str.split()
    if len(parts) != 5:
        raise ValueError("Cron string must have 5 parts.")
    return {
        'minute': parts[0],
        'hour': parts[1],
        'day': parts[2],
        'month': parts[3],
        'day_of_week': parts[4],
    }

if __name__ == "__main__":
    jobstores = {
        'default': SQLAlchemyJobStore(url=DATABASE_URL)
    }
    scheduler = BlockingScheduler(jobstores=jobstores)
    
    # Schedule the main sync function to run periodically
    scheduler.add_job(sync_all_jobs, 'interval', seconds=60, args=[scheduler])
    
    logger.info("Starting scheduler", database_url=DATABASE_URL)
    # Initial sync on startup
    sync_all_jobs(scheduler)
    scheduler.start()
