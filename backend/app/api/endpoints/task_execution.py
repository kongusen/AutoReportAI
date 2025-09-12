"""
任务执行API路由 - 增强架构v3.0

提供完整的报告生成任务执行API，集成增强架构v3.0：
1. 智能任务执行（使用工具链）
2. 实时状态查询（性能监控）
3. 流式进度反馈
4. 增强错误处理和重试
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
from app import crud

# 导入增强架构v3.0组件
# AI core components migrated to agents
from app.services.infrastructure.agents.core import *
# AI tools migrated to agents
from app.services.infrastructure.agents.tools import get_tool_registry
# AI core components migrated to agents
from app.services.infrastructure.agents.core import *

logger = logging.getLogger(__name__)
router = APIRouter()


class TaskExecutionRequestSchema(BaseModel):
    """增强任务执行请求模型"""
    template_id: str = Field(..., description="模板ID")
    data_source_ids: List[str] = Field(..., description="数据源ID列表")
    execution_context: Dict[str, Any] = Field(default_factory=dict, description="执行上下文")
    time_context: Optional[Dict[str, Any]] = Field(None, description="时间上下文")
    output_format: str = Field("docx", description="输出格式")
    delivery_config: Optional[Dict[str, Any]] = Field(None, description="投递配置")
    
    # 增强架构v3.0新增字段
    use_enhanced_execution: bool = Field(True, description="使用增强执行引擎")
    max_iterations: int = Field(5, ge=1, le=10, description="最大迭代次数")
    include_reasoning: bool = Field(True, description="包含推理过程")
    performance_optimization: bool = Field(True, description="性能优化")
    
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
    """增强任务状态响应模型"""
    task_id: str
    status: str
    current_step: str
    progress: float
    start_time: datetime
    updated_at: Optional[datetime] = None
    error: Optional[str] = None
    
    # 增强架构v3.0新增字段
    session_id: Optional[str] = None
    tools_used: List[str] = Field(default_factory=list, description="使用的工具列表")
    performance_metrics: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    reasoning_steps: Optional[List[str]] = None


@router.post("/execute", response_model=APIResponse[Dict[str, Any]])
async def execute_task(
    request: TaskExecutionRequestSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> APIResponse[Dict[str, Any]]:
    """启动增强任务执行 - 集成增强架构v3.0"""
    
    import uuid
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    
    try:
        logger.info(f"启动增强任务执行: user_id={current_user.id}, task_id={task_id}, template_id={request.template_id}")
        
        # 检查是否使用增强执行
        if not request.use_enhanced_execution:
            # 回退到原有实现（保持兼容性）
            from app.services.application.tasks.task_execution_service import (
                create_task_execution_service, TaskExecutionRequest
            )
            
            task_service = create_task_execution_service(str(current_user.id))
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
            
            import asyncio
            asyncio.create_task(task_service.execute_task(execution_request))
            
            return APIResponse(
                success=True,
                data={
                    "task_id": task_id,
                    "status": "started",
                    "message": "任务已启动（传统模式）",
                    "enhanced_execution": False,
                    "started_at": datetime.now().isoformat()
                },
                message="任务执行已启动"
            )
        
        # === 增强架构v3.0执行路径 ===
        
        # 1. 获取模板和占位符信息
        template = crud.template.get(db, id=request.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        placeholders = crud.template_placeholder.get_by_template(
            db, template_id=request.template_id
        )
        
        # 2. 获取数据源信息
        data_sources_info = []
        for ds_id in request.data_source_ids:
            ds = crud.data_source.get(db, id=ds_id)
            if ds:
                try:
                    from app.services.data.repositories.data_source_repository import DataSourceRepository
                    ds_repo = DataSourceRepository()
                    tables_info = await ds_repo.get_tables_info(ds_id)
                    data_sources_info.append({
                        "id": ds_id,
                        "name": ds.name,
                        "type": ds.source_type,
                        "tables": [t.get("name", "") for t in tables_info],
                        "table_details": tables_info
                    })
                except Exception as e:
                    logger.warning(f"获取数据源{ds_id}表信息失败: {e}")
                    data_sources_info.append({
                        "id": ds_id,
                        "name": ds.name,
                        "type": ds.source_type,
                        "tables": [],
                        "table_details": []
                    })
        
        # 3. 初始化增强工具链
        tool_chain = ToolChain()
        sql_generator = AdvancedSQLGenerator()
        tool_chain.register_tool(sql_generator)
        
        # 4. 创建执行上下文
        context = ToolContext(
            user_id=str(current_user.id),
            task_id=task_id,
            session_id=session_id,
            data_source_info={
                "tables": [t for ds in data_sources_info for t in ds.get("tables", [])],
                "table_details": [t for ds in data_sources_info for t in ds.get("table_details", [])],
                "data_sources": data_sources_info
            }
        )
        
        # 5. 准备输入数据
        placeholder_data = [
            {
                "name": p.placeholder_name,
                "text": p.description or p.placeholder_name,
                "type": "chart"
            }
            for p in placeholders
        ]
        
        input_data = {
            "placeholders": placeholder_data,
            "requirements": {
                "max_iterations": request.max_iterations,
                "include_reasoning": request.include_reasoning,
                "performance_optimization": request.performance_optimization
            }
        }
        
        # 6. 启动增强执行
        monitor = get_prompt_monitor()
        monitor.start_session(session_id)
        
        # 异步执行增强任务
        async def execute_enhanced_task():
            try:
                results = []
                async for result in sql_generator.execute(input_data, context):
                    results.append({
                        "type": result.type,
                        "content": result.content,
                        "data": result.data,
                        "timestamp": datetime.now().isoformat()
                    })
                return results
            except Exception as e:
                logger.error(f"增强任务执行失败: {e}")
                return [{"type": "error", "content": str(e)}]
        
        import asyncio
        asyncio.create_task(execute_enhanced_task())
        
        return APIResponse(
            success=True,
            data={
                "task_id": task_id,
                "session_id": session_id,
                "status": "started",
                "message": "增强任务已启动，支持智能执行",
                "template_id": request.template_id,
                "placeholders_count": len(placeholder_data),
                "tools_registered": tool_chain.list_tools(),
                "enhanced_features": {
                    "intelligent_retry": True,
                    "performance_monitoring": True,
                    "reasoning_included": request.include_reasoning,
                    "max_iterations": request.max_iterations
                },
                "started_at": datetime.now().isoformat()
            },
            message="增强任务执行已启动"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动增强任务执行失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"启动增强任务执行失败: {str(e)}"
        )


@router.get("/status/{task_id}", response_model=APIResponse[Optional[TaskStatusResponse]])
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> APIResponse[Optional[TaskStatusResponse]]:
    """获取任务状态"""
    try:
        from app.services.application.tasks.task_execution_service import create_task_execution_service
        
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
        from app.services.application.tasks.task_execution_service import create_task_execution_service
        
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
        from app.services.application.tasks.task_execution_service import create_task_execution_service
        
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
                from app.services.application.tasks.task_execution_service import (
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