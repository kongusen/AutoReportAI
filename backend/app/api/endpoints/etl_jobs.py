import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.services.etl_service import etl_service

router = APIRouter()


@router.post("/", response_model=schemas.ETLJob)
def create_etl_job(
    *,
    db: Session = Depends(deps.get_db),
    etl_job_in: schemas.ETLJobCreate,
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Create new ETL job. (Superuser only)
    """
    etl_job = crud.etl_job.create(db=db, obj_in=etl_job_in)
    return etl_job


@router.get("/", response_model=List[schemas.ETLJob])
def read_etl_jobs(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve ETL jobs.
    """
    # TODO: check if user has permission
    etl_jobs = crud.etl_job.get_multi(db, skip=skip, limit=limit)
    return etl_jobs


@router.get("/{id}", response_model=schemas.ETLJob)
def read_etl_job(
    *,
    db: Session = Depends(deps.get_db),
    id: uuid.UUID,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get ETL job by ID.
    """
    etl_job = crud.etl_job.get(db=db, id=id)
    if not etl_job:
        raise HTTPException(status_code=404, detail="ETL Job not found")
    # TODO: check if user has permission
    return etl_job


@router.put("/{id}", response_model=schemas.ETLJob)
def update_etl_job(
    *,
    db: Session = Depends(deps.get_db),
    id: uuid.UUID,
    etl_job_in: schemas.ETLJobUpdate,
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Update an ETL job. (Superuser only)
    """
    etl_job = crud.etl_job.get(db=db, id=id)
    if not etl_job:
        raise HTTPException(status_code=404, detail="ETL Job not found")
    etl_job = crud.etl_job.update(db=db, db_obj=etl_job, obj_in=etl_job_in)
    return etl_job


@router.delete("/{id}", response_model=schemas.ETLJob)
def delete_etl_job(
    *,
    db: Session = Depends(deps.get_db),
    id: uuid.UUID,
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Delete an ETL job. (Superuser only)
    """
    etl_job = crud.etl_job.get(db=db, id=id)
    if not etl_job:
        raise HTTPException(status_code=404, detail="ETL Job not found")
    etl_job = crud.etl_job.remove(db=db, id=id)
    return etl_job


@router.post("/{id}/run", response_model=schemas.Msg)
def trigger_etl_job(
    *,
    db: Session = Depends(deps.get_db),
    id: uuid.UUID,
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Manually trigger an ETL job to run. (Superuser only)
    """
    # The service now manages its own DB session.
    # Note: This runs the job synchronously. For long-running jobs,
    # this should be offloaded to a background worker.
    try:
        etl_service.run_job(job_id=str(id))
    except ValueError as e:
        # Catch specific, expected errors like "Not Found"
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Catch all other unexpected errors
        raise HTTPException(status_code=500, detail=f"Failed to run ETL job: {str(e)}")

    return {"msg": "ETL job has been triggered successfully."}
