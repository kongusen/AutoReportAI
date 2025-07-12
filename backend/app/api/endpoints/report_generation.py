from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.api import deps

router = APIRouter()


@router.post("/generate", response_model=schemas.Msg)
def generate_report(
    db: Session = Depends(deps.get_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Generate a report.
    """
    return {"msg": "Report generation endpoint - to be implemented"}


@router.get("/status/{task_id}", response_model=schemas.Msg)
def get_generation_status(
    task_id: int,
    db: Session = Depends(deps.get_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Get report generation status.
    """
    return {"msg": f"Status for task {task_id} - to be implemented"}
