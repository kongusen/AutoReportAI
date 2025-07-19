from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.api import deps
from app.core.exceptions import (
    NotFoundError,
    ReportGenerationError,
    ValidationError
)
from app.services.report_generation import ReportGenerationService

def create_report_generation_service(db: Session) -> ReportGenerationService:
    """Create report generation service instance"""
    return ReportGenerationService(db)
from app.schemas.base import APIResponse, create_success_response, create_error_response

router = APIRouter()


@router.get("/", response_model=APIResponse[Dict[str, Any]])
def get_reports_root(
    db: Session = Depends(deps.get_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Get available report generation endpoints.
    """
    endpoints_data = {
        "endpoints": {
            "generate": "POST /api/v1/reports/generate",
            "test": "POST /api/v1/reports/test",
            "preview": "GET /api/v1/reports/preview",
            "validate": "POST /api/v1/reports/validate",
            "status": "GET /api/v1/reports/status/{task_id}",
        }
    }
    return APIResponse[Dict[str, Any]](
        success=True,
        message="报告生成API端点信息获取成功",
        data=endpoints_data
    )


@router.post("/generate", response_model=APIResponse[Dict[str, Any]])
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
            task_id=task_id, template_id=template_id, data_source_id=data_source_id
        )
        return APIResponse[Dict[str, Any]](
            success=True,
            message="报告生成任务已启动",
            data=result
        )
    except ValueError as e:
        raise NotFoundError(
            resource="报告生成资源",
            identifier=f"task_id={task_id}, template_id={template_id}",
            details={"error": str(e)}
        )
    except Exception as e:
        raise ReportGenerationError(
            message=f"报告生成失败: {str(e)}",
            template_id=str(template_id),
            details={"task_id": task_id, "data_source_id": data_source_id}
        )


@router.get("/preview", response_model=APIResponse[Dict[str, Any]])
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
            template_id=template_id, data_source_id=data_source_id, limit=limit
        )
        return APIResponse[Dict[str, Any]](
            success=True,
            message="报告数据预览获取成功",
            data=result
        )
    except ValueError as e:
        raise NotFoundError(
            resource="报告预览资源",
            identifier=f"template_id={template_id}, data_source_id={data_source_id}",
            details={"error": str(e)}
        )
    except Exception as e:
        raise ReportGenerationError(
            message=f"报告预览失败: {str(e)}",
            template_id=str(template_id),
            details={"data_source_id": data_source_id, "limit": limit}
        )


@router.post("/validate", response_model=APIResponse[Dict[str, Any]])
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
            template_id=template_id, data_source_id=data_source_id
        )
        return APIResponse[Dict[str, Any]](
            success=True,
            message="报告配置验证成功",
            data=result
        )
    except ValueError as e:
        raise NotFoundError(
            resource="报告配置验证资源",
            identifier=f"template_id={template_id}, data_source_id={data_source_id}",
            details={"error": str(e)}
        )
    except Exception as e:
        raise ValidationError(
            message=f"报告配置验证失败: {str(e)}",
            field="report_configuration",
            details={"template_id": template_id, "data_source_id": data_source_id}
        )


@router.get("/status/{task_id}", response_model=APIResponse[Dict[str, Any]])
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
    status_data = {
        "task_id": task_id,
        "status": "pending",
        "message": "Status tracking not yet implemented",
    }
    return APIResponse[Dict[str, Any]](
        success=True,
        message="任务状态获取成功",
        data=status_data
    )


@router.post("/test", response_model=APIResponse[Dict[str, Any]])
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
                "composition_service": "available",
            },
        }

        # Check AI service health
        try:
            ai_health = report_service.ai_service.health_check()
            result["components"]["ai_service"] = ai_health["status"]
        except Exception as e:
            result["components"]["ai_service"] = f"error: {str(e)}"

        return APIResponse[Dict[str, Any]](
            success=True,
            message="报告管道测试完成",
            data=result
        )

    except Exception as e:
        raise ReportGenerationError(
            message=f"报告管道测试失败: {str(e)}",
            template_id=None,
            details={"test_type": "pipeline_health_check"}
        )
