import time
import os
import schedule
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from app.models.task import Task
from app.services.etl_service import ETLService
from app.services.report_composition_service import report_composition_service
from app.services.word_generator_service import word_generator_service
from app.services.email_service import email_service
from app.services.template_parser_service import template_parser_service
from app.models.template import Template
from app import crud
import requests # For calling the analysis endpoint

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://autoreport:autoreport@db:5432/autoreport")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

# Database session management
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db_session():
    """Provide a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def run_task_flow(task_id: int):
    """
    The main job function that orchestrates the ETL and report generation.
    """
    print(f"SCHEDULER: Starting task flow for task_id: {task_id}")
    
    db = next(get_db_session())
    task = None
    report_path = None
    try:
        task = db.query(Task).get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found.")

        # Step 1: Run ETL
        if not task.data_source_id:
            raise ValueError(f"Task {task_id} has no data source configured.")
        
        print(f"SCHEDULER: Running ETL for data_source_id: {task.data_source_id}")
        etl_service = ETLService(db)
        etl_service.run_etl(data_source_id=task.data_source_id)
        print(f"SCHEDULER: ETL completed for data_source_id: {task.data_source_id}")

        # Step 2: Fetch and Parse Template
        if not task.template_id:
             raise ValueError(f"Task {task.id} has no template configured.")
        template = db.query(Template).get(task.template_id)
        if not template:
            raise ValueError(f"Template for task {task_id} not found.")
        
        placeholders = template_parser_service.parse(template.content)
        
        # Step 3: Execute Analysis for each placeholder
        analysis_results = {}
        for placeholder in placeholders:
            print(f"SCHEDULER: Analyzing placeholder: {placeholder}")
            # This requires the backend to be running and accessible
            analysis_endpoint = f"{BACKEND_URL}/api/experimental-analysis"
            try:
                # We need a token for this endpoint, this is a placeholder
                # In a real scenario, the scheduler would need a service account token
                headers = {"Authorization": "Bearer FAKETOKEN"}
                response = requests.post(analysis_endpoint, json={"placeholder": placeholder}, headers=headers)
                response.raise_for_status()
                result_data = response.json()
                analysis_results[placeholder] = result_data.get("result")
            except requests.RequestException as e:
                print(f"SCHEDULER: Failed to analyze placeholder {placeholder}. Error: {e}")
                analysis_results[placeholder] = f"[Analysis failed: {e}]"

        # Step 4: Compose report
        composed_content = report_composition_service.compose_report(
            template_content=template.content,
            results=analysis_results
        )
        
        # Step 5: Generate Word document
        output_dir = "generated_reports"
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, f"report_{task.name}_{int(time.time())}.docx")
        
        word_generator_service.generate_report_from_content(
            composed_content=composed_content,
            output_path=report_path
        )
        print(f"SCHEDULER: Report generated at {report_path}")

        # Step 6: Send email
        recipients = [email.strip() for email in (task.recipients or "").split(",") if email.strip()]
        if recipients:
            email_service.send_report_email(
                recipients=recipients,
                subject=f"Scheduled Report: {task.name}",
                body=f"Please find the attached report for {task.name}.",
                attachment_path=report_path
            )
            print(f"SCHEDULER: Email sent to {recipients}")

        crud.report_history.create(db, obj_in={
            "task_id": task.id,
            "status": "success",
            "file_path": report_path
        })
        print(f"SCHEDULER: Successfully logged history for task {task.id}")

    except Exception as e:
        print(f"SCHEDULER: Task flow for {task_id} failed with error: {e}")
        if task:
            crud.report_history.create(db, obj_in={
                "task_id": task.id,
                "status": "failure",
                "file_path": report_path, # May be null if generation failed early
                "error_message": str(e)
            })
            print(f"SCHEDULER: Logged failure for task {task.id}")
    finally:
        if db:
            db.close()
        print(f"SCHEDULER: Task flow finished for task_id: {task_id}")


def sync_tasks_from_db(scheduler):
    """
    Syncs the jobs in the scheduler with the tasks in the database.
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
    
    # Schedule the sync function to run periodically
    scheduler.add_job(sync_tasks_from_db, 'interval', seconds=30, args=[scheduler])
    
    print("SCHEDULER: Starting scheduler...")
    # Initial sync on startup
    sync_tasks_from_db(scheduler)
    scheduler.start()
