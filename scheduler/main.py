import time
import os
import schedule
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from app.models.task import Task  # We need to make the app module available to the scheduler
from scheduler.tasks import trigger_report_generation

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://autoreport:autoreport@db:5432/autoreport")

def sync_tasks_from_db(scheduler, db_session):
    """
    Syncs the jobs in the scheduler with the tasks in the database.
    """
    print("SCHEDULER: Syncing tasks from database...")
    db_tasks = db_session.query(Task).filter_by(enabled=True).all()
    
    # Get all job IDs currently in the scheduler
    scheduler_job_ids = {job.id for job in scheduler.get_jobs()}
    
    # Add/update tasks from DB
    for task in db_tasks:
        job_id = f"task_{task.id}"
        
        # This is a placeholder for recipients. In a real app, this should be stored in the Task model.
        mock_recipients = ["test@example.com"]
        
        if job_id in scheduler_job_ids:
            # Modify existing job if schedule differs
            existing_job = scheduler.get_job(job_id)
            if existing_job.trigger.cron_expression != task.schedule:
                scheduler.reschedule_job(
                    job_id, 
                    trigger='cron', 
                    **_cron_to_dict(task.schedule)
                )
                print(f"SCHEDULER: Rescheduled job '{job_id}' for task '{task.name}'.")
        else:
            # Add new job
            scheduler.add_job(
                trigger_report_generation,
                'cron',
                id=job_id,
                name=task.name,
                args=[task.id, f"{task.name} (Scheduled)", mock_recipients],
                **_cron_to_dict(task.schedule)
            )
            print(f"SCHEDULER: Added new job '{job_id}' for task '{task.name}'.")

    # Remove jobs that are no longer in the DB or are disabled
    db_task_ids = {f"task_{task.id}" for task in db_tasks}
    for job_id in scheduler_job_ids:
        if job_id not in db_task_ids:
            scheduler.remove_job(job_id)
            print(f"SCHEDULER: Removed job '{job_id}'.")

def _cron_to_dict(cron_str: str) -> dict:
    """Converts a cron string to a dictionary for APScheduler."""
    parts = cron_str.split()
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
    
    # Setup database connection for the sync function
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db_session = Session()

    # Schedule the sync function to run periodically
    # This ensures that changes to tasks in the UI are picked up by the scheduler
    scheduler.add_job(sync_tasks_from_db, 'interval', seconds=30, args=[scheduler, db_session])
    
    print("SCHEDULER: Starting scheduler...")
    # Initial sync on startup
    sync_tasks_from_db(scheduler, db_session)
    scheduler.start()
