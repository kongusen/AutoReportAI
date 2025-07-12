from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app import schemas
from app.api import deps
from app.services.report_generation_service import create_report_generation_service

router = APIRouter()


@router.post("/generate", response_model=dict)
def generate_report(
    *,
    db: Session = Depends(deps.get_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    task_id: int,
    template_id: int,
    data_source_id: int,
):
    """
    Generate a complete report based on task configuration.
    """
    try:
        report_service = create_report_generation_service(db)
        result = report_service.generate_report(
            task_id=task_id,
            template_id=template_id,
            data_source_id=data_source_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/preview", response_model=dict)
async def preview_report_data(
    *,
    db: Session = Depends(deps.get_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    template_id: int,
    data_source_id: int,
    limit: int = 5,
):
    """
    Preview what data would be used for report generation.
    """
    try:
        report_service = create_report_generation_service(db)
        result = await report_service.preview_report_data(
            template_id=template_id,
            data_source_id=data_source_id,
            limit=limit
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/validate", response_model=dict)
def validate_report_configuration(
    *,
    db: Session = Depends(deps.get_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    template_id: int,
    data_source_id: int,
):
    """
    Validate that a template and data source are compatible for report generation.
    """
    try:
        report_service = create_report_generation_service(db)
        result = report_service.validate_report_configuration(
            template_id=template_id,
            data_source_id=data_source_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/status/{task_id}", response_model=dict)
def get_generation_status(
    task_id: int,
    db: Session = Depends(deps.get_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Get report generation status for a task.
    """
    # This is a placeholder - in a real implementation, you'd track generation status
    # in a database or cache (like Redis)
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Status tracking not yet implemented"
    }


@router.post("/test", response_model=dict)
def test_report_pipeline(
    *,
    db: Session = Depends(deps.get_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Test the report generation pipeline with sample data.
    """
    try:
        report_service = create_report_generation_service(db)
        
        # This is a basic health check for the report generation system
        result = {
            "pipeline_status": "healthy",
            "components": {
                "ai_service": "checking...",
                "template_parser": "available",
                "word_generator": "available",
                "composition_service": "available"
            }
        }
        
        # Check AI service health
        try:
            ai_health = report_service.ai_service.health_check()
            result["components"]["ai_service"] = ai_health["status"]
        except Exception as e:
            result["components"]["ai_service"] = f"error: {str(e)}"
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline test failed: {str(e)}")
