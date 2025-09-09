"""
任务执行API路由

提供完整的报告生成任务执行API，包括：
1. 启动任务执行
2. 查询任务状态
3. 取消任务
4. 获取任务历史
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.base import APIResponse

logger = logging.getLogger(__name__)
router = APIRouter()


class TaskExecutionRequestSchema(BaseModel):
    """任务执行请求模型"""
    template_id: str = Field(..., description="模板ID")
    data_source_ids: List[str] = Field(..., description="数据源ID列表")
    execution_context: Dict[str, Any] = Field(default_factory=dict, description="执行上下文")
    time_context: Optional[Dict[str, Any]] = Field(None, description="时间上下文")
    output_format: str = Field("docx", description="输出格式")
    delivery_config: Optional[Dict[str, Any]] = Field(None, description="投递配置")
    
    class Config:
        schema_extra = {
            "example": {
                "template_id": "template_123",
                "data_source_ids": ["datasource_456"],
                "execution_context": {
                    "force_repair": True,
                    "optimization_level": "enhanced"
                },
                "time_context": {
                    "cron_expression": "0 6 * * *",
                    "execution_time": "2024-12-01T06:00:00",
                    "task_type": "scheduled"
                },
                "output_format": "docx",
                "delivery_config": {
                    "send_email": True,
                    "email_recipients": ["user@example.com"],
                    "attach_files": True
                }
            }
        }


class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str
    status: str
    current_step: str
    progress: float
    start_time: datetime
    updated_at: Optional[datetime] = None
    error: Optional[str] = None


@router.post("/execute", response_model=APIResponse[Dict[str, Any]])
async def execute_task(
    request: TaskExecutionRequestSchema,
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """启动任务执行"""
    try:
        logger.info(f"启动任务执行: user_id={current_user.id}, template_id={request.template_id}")
        
        from app.services.application.task_execution_service import (
            create_task_execution_service, TaskExecutionRequest
        )
        
        # 创建任务执行服务
        task_service = create_task_execution_service(str(current_user.id))
        
        # 生成任务ID
        import uuid
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        # 构建任务执行请求
        execution_request = TaskExecutionRequest(
            task_id=task_id,
            template_id=request.template_id,
            data_source_ids=request.data_source_ids,
            user_id=str(current_user.id),
            execution_context=request.execution_context,
            time_context=request.time_context,
            output_format=request.output_format,
            delivery_config=request.delivery_config
        )
        
        # 异步执行任务
        import asyncio
        task_future = asyncio.create_task(task_service.execute_task(execution_request))
        
        # 立即返回任务ID，不等待执行完成
        return APIResponse(
            success=True,
            data={
                "task_id": task_id,
                "status": "started",
                "message": "任务已启动，正在后台执行",
                "template_id": request.template_id,
                "data_source_ids": request.data_source_ids,
                "started_at": datetime.now().isoformat()
            },
            message="任务执行已启动"
        )
        
    except Exception as e:
        logger.error(f"启动任务执行失败: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"启动任务执行失败: {str(e)}"
        )


@router.get("/status/{task_id}", response_model=APIResponse[Optional[TaskStatusResponse]])
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> APIResponse[Optional[TaskStatusResponse]]:
    """获取任务状态"""
    try:
        from app.services.application.task_execution_service import create_task_execution_service
        
        task_service = create_task_execution_service(str(current_user.id))
        task_status = task_service.get_task_status(task_id)
        
        if task_status is None:
            return APIResponse(
                success=True,
                data=None,
                message="任务不存在或已完成"
            )
        
        status_response = TaskStatusResponse(
            task_id=task_id,
            status=task_status["status"].value if hasattr(task_status["status"], "value") else str(task_status["status"]),
            current_step=task_status.get("current_step", ""),
            progress=task_status.get("progress", 0.0),
            start_time=task_status.get("start_time", datetime.now()),
            updated_at=task_status.get("updated_at"),
            error=task_status.get("error")
        )
        
        return APIResponse(
            success=True,
            data=status_response,
            message="获取任务状态成功"
        )
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"获取任务状态失败: {str(e)}"
        )


@router.get("/list", response_model=APIResponse[List[Dict[str, Any]]])
async def list_active_tasks(
    current_user: User = Depends(get_current_user)
) -> APIResponse[List[Dict[str, Any]]]:
    """列出活跃任务"""
    try:
        from app.services.application.task_execution_service import create_task_execution_service
        
        task_service = create_task_execution_service(str(current_user.id))
        active_tasks = task_service.list_active_tasks()
        
        # 转换任务状态格式
        formatted_tasks = []
        for task in active_tasks:
            formatted_task = {
                "task_id": task["task_id"],
                "status": task["status"].value if hasattr(task["status"], "value") else str(task["status"]),
                "current_step": task.get("current_step", ""),
                "progress": task.get("progress", 0.0),
                "start_time": task.get("start_time", datetime.now()).isoformat(),
                "updated_at": task.get("updated_at", datetime.now()).isoformat() if task.get("updated_at") else None
            }
            formatted_tasks.append(formatted_task)
        
        return APIResponse(
            success=True,
            data=formatted_tasks,
            message=f"获取到 {len(formatted_tasks)} 个活跃任务"
        )
        
    except Exception as e:
        logger.error(f"列出活跃任务失败: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"列出活跃任务失败: {str(e)}"
        )


@router.post("/cancel/{task_id}", response_model=APIResponse[bool])
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> APIResponse[bool]:
    """取消任务"""
    try:
        from app.services.application.task_execution_service import create_task_execution_service
        
        task_service = create_task_execution_service(str(current_user.id))
        success = await task_service.cancel_task(task_id)
        
        return APIResponse(
            success=success,
            data=success,
            message="任务已取消" if success else "任务未找到或无法取消"
        )
        
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"取消任务失败: {str(e)}"
        )


@router.post("/validate-placeholders", response_model=APIResponse[Dict[str, Any]])
async def validate_template_placeholders(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """验证模板占位符"""
    try:
        template_id = request.get("template_id")
        data_source_id = request.get("data_source_id")
        time_context = request.get("time_context")
        force_repair = request.get("force_repair", False)
        
        if not template_id:
            raise HTTPException(status_code=400, detail="缺少template_id参数")
        
        if not data_source_id:
            raise HTTPException(status_code=400, detail="缺少data_source_id参数")
        
        from app.services.domain.placeholder.placeholder_validation_service import (
            create_placeholder_validation_service
        )
        
        # 获取数据源信息
        from app.crud import data_source as crud_data_source
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        try:
            data_source = crud_data_source.get(db, id=data_source_id)
            if not data_source:
                raise HTTPException(status_code=404, detail="数据源不存在")
            
            data_source_info = {
                "type": data_source.source_type.value if hasattr(data_source.source_type, 'value') else str(data_source.source_type),
                "name": data_source.name,
                "database": getattr(data_source, 'doris_database', 'unknown'),
                "fe_hosts": getattr(data_source, 'doris_fe_hosts', ['localhost']),
                "username": getattr(data_source, 'doris_username', 'root'),
                "password": getattr(data_source, 'doris_password', ''),
                "query_port": getattr(data_source, 'doris_query_port', 9030)
            }
        finally:
            db.close()
        
        # 创建验证服务
        validation_service = create_placeholder_validation_service(str(current_user.id))
        
        # 执行批量验证和修复
        result = await validation_service.batch_repair_template_placeholders(
            template_id=template_id,
            data_source_info=data_source_info,
            time_context=time_context,
            force_repair=force_repair
        )
        
        return APIResponse(
            success=result["status"] != "error",
            data=result,
            message=result.get("message", "占位符验证完成")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证占位符失败: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"验证占位符失败: {str(e)}"
        )


@router.get("/placeholder-status/{template_id}", response_model=APIResponse[Dict[str, Any]])
async def get_placeholder_status(
    template_id: str,
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """获取模板占位符状态"""
    try:
        from app.services.domain.placeholder.placeholder_validation_service import (
            create_placeholder_validation_service
        )
        
        validation_service = create_placeholder_validation_service(str(current_user.id))
        status_info = await validation_service.get_placeholder_repair_status(template_id)
        
        return APIResponse(
            success=True,
            data=status_info,
            message="获取占位符状态成功"
        )
        
    except Exception as e:
        logger.error(f"获取占位符状态失败: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"获取占位符状态失败: {str(e)}"
        )


@router.post("/test-workflow", response_model=APIResponse[Dict[str, Any]])
async def test_workflow_components(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """测试工作流组件"""
    try:
        component = request.get("component", "all")  # all, validation, etl, chart, document, delivery
        test_data = request.get("test_data", {})
        
        results = {}
        
        if component in ["all", "validation"]:
            # 测试占位符验证服务
            try:
                from app.services.domain.placeholder.placeholder_validation_service import (
                    create_placeholder_validation_service
                )
                validation_service = create_placeholder_validation_service(str(current_user.id))
                results["validation"] = {"status": "available", "service": "PlaceholderValidationService"}
            except Exception as e:
                results["validation"] = {"status": "error", "error": str(e)}
        
        if component in ["all", "chart"]:
            # 测试图表生成服务
            try:
                from app.services.infrastructure.visualization.chart_generation_service import (
                    create_chart_generation_service
                )
                chart_service = create_chart_generation_service(str(current_user.id))
                results["chart"] = {"status": "available", "service": "ChartGenerationService"}
            except Exception as e:
                results["chart"] = {"status": "error", "error": str(e)}
        
        if component in ["all", "document"]:
            # 测试文档导出服务
            try:
                from app.services.infrastructure.document.word_export_service import (
                    create_word_export_service
                )
                word_service = create_word_export_service(str(current_user.id))
                results["document"] = {"status": "available", "service": "WordExportService"}
            except Exception as e:
                results["document"] = {"status": "error", "error": str(e)}
        
        if component in ["all", "delivery"]:
            # 测试投递服务
            try:
                from app.services.infrastructure.delivery.delivery_service import (
                    create_delivery_service
                )
                delivery_service = create_delivery_service(str(current_user.id))
                results["delivery"] = {"status": "available", "service": "DeliveryService"}
            except Exception as e:
                results["delivery"] = {"status": "error", "error": str(e)}
        
        if component in ["all", "task"]:
            # 测试任务执行服务
            try:
                from app.services.application.task_execution_service import (
                    create_task_execution_service
                )
                task_service = create_task_execution_service(str(current_user.id))
                results["task"] = {"status": "available", "service": "TaskExecutionService"}
            except Exception as e:
                results["task"] = {"status": "error", "error": str(e)}
        
        # 统计结果
        available_count = len([r for r in results.values() if r.get("status") == "available"])
        total_count = len(results)
        
        return APIResponse(
            success=True,
            data={
                "components": results,
                "summary": {
                    "total": total_count,
                    "available": available_count,
                    "errors": total_count - available_count,
                    "health": "good" if available_count == total_count else "partial" if available_count > 0 else "poor"
                }
            },
            message=f"工作流组件测试完成: {available_count}/{total_count} 可用"
        )
        
    except Exception as e:
        logger.error(f"测试工作流组件失败: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"测试工作流组件失败: {str(e)}"
        )