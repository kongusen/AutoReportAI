import time
import os
import schedule
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from app.db.session import get_db_session
from app.models.task import Task
from app.services.report_composition_service import report_composition_service
from app.services.word_generator_service import word_generator_service
from app.services.email_service import email_service
from app.services.template_parser_service import template_parser_service
from app.models.template import Template
from app import crud
import requests # For calling the analysis endpoint
from datetime import datetime
from app.models.report_history import ReportHistoryCreate
from app.models.etl_job import ETLJob
from app.services.etl_service import etl_service


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/app")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

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

def run_task_flow(task_id: int):
    """
    完整的任务执行流程，由调度器触发。
    """
    print(f"[{datetime.now()}] Running task flow for task_id: {task_id}")
    with get_db_session() as db:
        task = crud.task.get(db, id=task_id)
        if not task:
            print(f"Task with id {task_id} not found.")
            return

        history_entry = None
        try:
            # 初始化所有服务
            # etl_service = ETLService(db)
            tool_dispatcher_service = ToolDispatcherService(db)
            report_composition_service = ReportCompositionService(db, tool_dispatcher_service)
            word_generator_service = WordGeneratorService()
            email_service = EmailService()
            
            # 创建进行中的历史记录
            history_entry = crud.report_history.create(
                db, obj_in=ReportHistoryCreate(task_id=task_id, status="in_progress")
            )

            # --- 步骤 1: ETL (暂时禁用，直接进入报告生成) ---
            # print("Step 1: Running ETL...")
            # etl_service.run_etl(task.data_source_id)
            # print("ETL completed.")

            # --- 步骤 2: 报告合成 ---
            # ToolDispatcherService将直接在内部处理数据检索
            print("Step 2: Composing report...")
            composed_html = report_composition_service.process_template(
                template_id=task.template_id,
                data_source_id=task.data_source_id, # 传递 data_source_id 以便工具分发器使用
            )
            print("Report composition completed.")
            
            # --- 步骤 3: 生成Word文档 ---
            print("Step 3: Generating Word document...")
            output_path = word_generator_service.generate_word_from_html(
                html_content=composed_html,
                task_name=task.name
            )
            print(f"Word document generated at: {output_path}")

            # --- 步骤 4: 发送邮件 ---
            if task.recipients:
                print(f"Step 4: Sending email to {task.recipients}...")
                subject = f"自动化报告: {task.name}"
                body = "您好，附件是您订阅的最新报告，请查收。"
                email_service.send_email(
                    recipients=task.recipients.split(','),
                    subject=subject,
                    body=body,
                    attachment_path=output_path
                )
                print("Email sent.")
            
            # 更新历史记录为成功
            crud.report_history.update(
                db, db_obj=history_entry, obj_in={"status": "success", "report_path": output_path}
            )
            print(f"Task {task_id} completed successfully.")

        except Exception as e:
            print(f"An error occurred during task {task_id}: {e}")
            # 如果出错，更新历史记录为失败
            if history_entry:
                error_message = str(e)
                crud.report_history.update(
                    db, db_obj=history_entry, obj_in={"status": "failure", "error_message": error_message}
                )


def sync_all_jobs(scheduler):
    """Syncs all types of jobs (tasks, ETL, etc.) from the database."""
    print(f"[{datetime.now()}] Running full job sync...")
    sync_tasks_from_db(scheduler)
    sync_etl_jobs_from_db(scheduler)


def sync_etl_jobs_from_db(scheduler):
    """
    Syncs the ETL jobs in the scheduler with the ETLJob models in the database.
    """
    print("SCHEDULER: Syncing ETL jobs from database...")
    with get_db_session() as db:
        try:
            db_etl_jobs = db.query(ETLJob).filter_by(enabled=True).all()
            
            scheduler_job_ids = {job.id for job in scheduler.get_jobs()}
            
            for job_model in db_etl_jobs:
                job_id = f"etl_{job_model.id}"
                
                if not job_model.schedule:
                    if job_id in scheduler_job_ids:
                        scheduler.remove_job(job_id)
                        print(f"SCHEDULER: Removed ETL job '{job_id}' for '{job_model.name}' as it has no schedule.")
                    continue

                if job_id in scheduler_job_ids:
                    existing_job = scheduler.get_job(job_id)
                    if existing_job.trigger.cron_expression != job_model.schedule:
                        scheduler.reschedule_job(
                            job_id, 
                            trigger='cron', 
                            **_cron_to_dict(job_model.schedule)
                        )
                        print(f"SCHEDULER: Rescheduled ETL job '{job_id}' for '{job_model.name}'.")
                else:
                    scheduler.add_job(
                        etl_service.run_job,
                        'cron',
                        id=job_id,
                        name=job_model.name,
                        args=[job_model.id], # Pass only job_id
                        **_cron_to_dict(job_model.schedule)
                    )
                    print(f"SCHEDULER: Added new ETL job '{job_id}' for '{job_model.name}'.")

            db_job_ids = {f"etl_{job.id}" for job in db_etl_jobs if job.schedule}
            for job_id in scheduler_job_ids:
                if job_id.startswith("etl_") and job_id not in db_job_ids:
                    scheduler.remove_job(job_id)
                    print(f"SCHEDULER: Removed orphaned ETL job '{job_id}'.")
        except Exception as e:
            print(f"SCHEDULER: Error during ETL job sync: {e}")


def sync_tasks_from_db(scheduler):
    """
    Syncs the report generation tasks in the scheduler with the Task models in the database.
    """
    print("SCHEDULER: Syncing tasks from database...")
    with get_db_session() as db:
        db_tasks = db.query(Task).filter_by(is_active=True).all()
        
        scheduler_job_ids = {job.id for job in scheduler.get_jobs()}
        
        for task in db_tasks:
            job_id = f"task_{task.id}"
            
            if not task.schedule:
                if job_id in scheduler_job_ids:
                    scheduler.remove_job(job_id)
                    print(f"SCHEDULER: Removed job '{job_id}' for task '{task.name}' as it has no schedule.")
                continue

            if job_id in scheduler_job_ids:
                existing_job = scheduler.get_job(job_id)
                if existing_job.trigger.cron_expression != task.schedule:
                    scheduler.reschedule_job(
                        job_id, 
                        trigger='cron', 
                        **_cron_to_dict(task.schedule)
                    )
                    print(f"SCHEDULER: Rescheduled job '{job_id}' for task '{task.name}'.")
            else:
                scheduler.add_job(
                    run_task_flow,
                    'cron',
                    id=job_id,
                    name=task.name,
                    args=[task.id],
                    **_cron_to_dict(task.schedule)
                )
                print(f"SCHEDULER: Added new job '{job_id}' for task '{task.name}'.")

        db_task_ids = {f"task_{task.id}" for task in db_tasks if task.schedule}
        for job_id in scheduler_job_ids:
            if job_id.startswith("task_") and job_id not in db_task_ids:
                scheduler.remove_job(job_id)
                print(f"SCHEDULER: Removed job '{job_id}'.")

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
    
    print("SCHEDULER: Starting scheduler...")
    # Initial sync on startup
    sync_all_jobs(scheduler)
    scheduler.start()
