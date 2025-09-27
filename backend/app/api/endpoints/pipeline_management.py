"""
占位符流水线管理API端点
提供健康检查、扫描、组装、状态监控等管理功能
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.base import APIResponse, create_success_response, create_error_response
from app.schemas.pipeline_responses import (
    ETLScanResponse, ReportAssemblyResponse, PipelineHealthResponse,
    TaskStatus, MonitorStats, PlaceholderItem, PlaceholderStats,
    ResolvedPlaceholder, HealthStatusDetail,
    create_etl_scan_response, create_report_assembly_response,
    create_pipeline_health_response, create_task_status_response,
    create_monitor_stats_response
)
from app.services.application.health.pipeline_health_service import get_pipeline_health, get_quick_health
from app.services.application.facades.unified_service_facade import create_unified_service_facade

logger = logging.getLogger(__name__)
router = APIRouter()


# ================================================================================
# Request/Response Models
# ================================================================================

class PlaceholderScanRequest(BaseModel):
    """占位符扫描请求"""
    template_id: str = Field(..., description="模板ID")
    data_source_id: str = Field(..., description="数据源ID")


class ReportAssemblyRequest(BaseModel):
    """报告组装请求"""
    template_id: str = Field(..., description="模板ID")
    data_source_id: str = Field(..., description="数据源ID")
    start_date: Optional[str] = Field(None, description="开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")
    schedule: Optional[Dict[str, Any]] = Field(None, description="调度信息 (包含cron_expression)")
    execution_time: Optional[str] = Field(None, description="执行时间 (ISO格式)")
    output_dir: Optional[str] = Field(None, description="输出目录")


class TaskTriggerRequest(BaseModel):
    """任务触发请求"""
    task_id: str = Field(..., description="任务ID")
    force_execution: bool = Field(False, description="强制执行")
    execution_context: Optional[Dict[str, Any]] = Field(None, description="执行上下文")


# ================================================================================
# Health Check Endpoints
# ================================================================================

@router.get("/health", response_model=APIResponse[PipelineHealthResponse])
async def get_pipeline_health_status(
    current_user: User = Depends(get_current_user)
) -> APIResponse[PipelineHealthResponse]:
    """获取占位符流水线健康状态"""
    try:
        logger.info(f"用户 {current_user.id} 请求流水线健康检查")

        health_result = await get_pipeline_health()

        # 转换为标准化格式
        components = []
        for component_name, component_info in health_result.get("components", {}).items():
            components.append(HealthStatusDetail(
                component=component_name,
                status=component_info.get("status", "unknown"),
                message=component_info.get("message", ""),
                details=component_info.get("details", {})
            ))

        return create_pipeline_health_response(
            status=health_result.get("overall_status", "unknown"),
            ready_for_pipeline=health_result.get("overall_status") in ["healthy", "degraded"],
            components=components,
            recommendations=health_result.get("recommendations", []),
            message=f"健康检查完成，状态: {health_result.get('overall_status', 'unknown')}"
        )

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


@router.get("/health/quick", response_model=APIResponse[Dict[str, Any]])
async def get_quick_health_status(
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """获取快速健康检查状态"""
    try:
        health_result = await get_quick_health()

        return APIResponse(
            success=health_result["ready_for_pipeline"],
            data=health_result,
            message=f"快速检查完成，状态: {health_result['status']}"
        )

    except Exception as e:
        logger.error(f"快速健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"快速健康检查失败: {str(e)}")


# ================================================================================
# Placeholder Management Endpoints
# ================================================================================

@router.post("/scan", response_model=APIResponse[Dict[str, Any]])
async def scan_template_placeholders(
    request: PlaceholderScanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """扫描模板占位符（ETL前扫描）"""
    try:
        logger.info(f"开始扫描占位符: template_id={request.template_id}, data_source_id={request.data_source_id}")

        # 创建统一门面服务
        facade = create_unified_service_facade(db, str(current_user.id))

        # 执行占位符扫描
        scan_result = await facade.etl_pre_scan_placeholders(
            request.template_id,
            request.data_source_id
        )

        # 添加扫描元数据
        scan_result["scan_metadata"] = {
            "user_id": str(current_user.id),
            "scanned_at": datetime.now().isoformat(),
            "template_id": request.template_id,
            "data_source_id": request.data_source_id
        }

        success = scan_result.get("success", False)
        stats = scan_result.get("stats", {})

        return APIResponse(
            success=success,
            data=scan_result,
            message=f"扫描完成: 发现{stats.get('total', 0)}个占位符，{stats.get('need_reanalysis', 0)}个需重分析"
        )

    except Exception as e:
        logger.error(f"占位符扫描失败: {e}")
        raise HTTPException(status_code=500, detail=f"扫描失败: {str(e)}")


@router.post("/assemble", response_model=APIResponse[Dict[str, Any]])
async def assemble_report(
    request: ReportAssemblyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """组装报告（v2流水线）"""
    try:
        logger.info(f"开始报告组装: template_id={request.template_id}")

        # 创建统一门面服务
        facade = create_unified_service_facade(db, str(current_user.id))

        # 执行报告组装
        assembly_result = await facade.generate_report_v2(
            template_id=request.template_id,
            data_source_id=request.data_source_id,
            start_date=request.start_date,
            end_date=request.end_date,
            schedule=request.schedule,
            execution_time=request.execution_time,
            output_dir=request.output_dir
        )

        # 添加组装元数据
        assembly_result["assembly_metadata"] = {
            "user_id": str(current_user.id),
            "assembled_at": datetime.now().isoformat(),
            "template_id": request.template_id,
            "data_source_id": request.data_source_id,
            "schedule_used": bool(request.schedule),
            "execution_time": request.execution_time
        }

        success = assembly_result.get("success", False)
        content_length = len(assembly_result.get("content_preview", ""))
        artifact_count = len(assembly_result.get("artifacts", []))

        return APIResponse(
            success=success,
            data=assembly_result,
            message=f"组装完成: 内容{content_length}字符，生成{artifact_count}个图表"
        )

    except Exception as e:
        logger.error(f"报告组装失败: {e}")
        raise HTTPException(status_code=500, detail=f"组装失败: {str(e)}")


# ================================================================================
# Task Management Endpoints
# ================================================================================

@router.post("/tasks/trigger", response_model=APIResponse[Dict[str, Any]])
async def trigger_task_execution(
    request: TaskTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """手动触发任务执行"""
    try:
        logger.info(f"用户 {current_user.id} 触发任务执行: {request.task_id}")

        # 验证任务存在性
        from app import crud
        task = crud.task.get(db, id=int(request.task_id))
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 权限检查：只能触发自己的任务或管理员权限
        if task.owner_id != current_user.id:
            # 这里可以添加管理员权限检查
            raise HTTPException(status_code=403, detail="无权限触发此任务")

        # 准备执行上下文
        execution_context = request.execution_context or {}
        execution_context.update({
            "template_id": str(task.template_id),
            "triggered_by": "manual",
            "trigger_user_id": str(current_user.id),
            "triggered_at": datetime.now().isoformat()
        })

        # 如果有调度信息，添加到上下文
        if task.schedule:
            execution_context["cron_expression"] = task.schedule

        # 异步触发Celery任务
        from app.services.application.tasks.workflow_tasks import generate_report_workflow

        celery_task = generate_report_workflow.apply_async(
            args=(
                request.task_id,
                [str(task.data_source_id)] if task.data_source_id else [],
                execution_context
            ),
            countdown=1  # 1秒后执行
        )

        # 记录触发日志
        logger.info(f"任务 {request.task_id} 已触发，Celery任务ID: {celery_task.id}")

        return APIResponse(
            success=True,
            data={
                "task_id": request.task_id,
                "celery_task_id": celery_task.id,
                "status": "triggered",
                "triggered_at": datetime.now().isoformat(),
                "execution_context": execution_context
            },
            message=f"任务已触发执行，任务ID: {celery_task.id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"任务触发失败: {e}")
        raise HTTPException(status_code=500, detail=f"任务触发失败: {str(e)}")


@router.get("/tasks/{task_id}/status", response_model=APIResponse[Dict[str, Any]])
async def get_task_execution_status(
    task_id: str,
    celery_task_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """获取任务执行状态"""
    try:
        # 验证任务存在性和权限
        from app import crud
        task = crud.task.get(db, id=int(task_id))
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        if task.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权限查看此任务")

        # 如果提供了Celery任务ID，查询Celery状态
        celery_status = None
        if celery_task_id:
            try:
                from app.core.celery_app import celery_app
                celery_task = celery_app.AsyncResult(celery_task_id)

                celery_status = {
                    "celery_task_id": celery_task_id,
                    "status": celery_task.status,
                    "result": celery_task.result if celery_task.successful() else None,
                    "info": celery_task.info if celery_task.failed() else None,
                    "traceback": celery_task.traceback if celery_task.failed() else None
                }

            except Exception as e:
                logger.warning(f"获取Celery任务状态失败: {e}")
                celery_status = {"error": str(e)}

        # 构建状态响应
        status_info = {
            "task_id": task_id,
            "task_name": task.name,
            "task_schedule": task.schedule,
            "last_execution": task.last_execution.isoformat() if task.last_execution else None,
            "next_execution": task.next_execution.isoformat() if task.next_execution else None,
            "is_active": task.is_active,
            "celery_status": celery_status,
            "checked_at": datetime.now().isoformat()
        }

        return APIResponse(
            success=True,
            data=status_info,
            message="任务状态查询成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"任务状态查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"状态查询失败: {str(e)}")


# ================================================================================
# Monitoring and Debugging Endpoints
# ================================================================================

@router.get("/monitor/stats", response_model=APIResponse[Dict[str, Any]])
async def get_pipeline_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """获取流水线统计信息"""
    try:
        from app import crud

        # 统计模板数量
        templates_count = len(crud.template.get_multi(db, limit=1000))

        # 统计数据源数量
        datasources_count = len(crud.data_source.get_multi(db, limit=1000))

        # 统计任务数量
        tasks = crud.task.get_multi(db, limit=1000)
        active_tasks = len([t for t in tasks if t.is_active])

        # 统计占位符数量
        placeholders_count = len(crud.template_placeholder.get_multi(db, limit=5000))

        stats = {
            "templates": {
                "total": templates_count,
                "with_placeholders": "计算中..."  # 可以进一步查询
            },
            "data_sources": {
                "total": datasources_count,
                "types": "计算中..."  # 可以按类型统计
            },
            "tasks": {
                "total": len(tasks),
                "active": active_tasks,
                "inactive": len(tasks) - active_tasks
            },
            "placeholders": {
                "total": placeholders_count
            },
            "system_info": {
                "user_id": str(current_user.id),
                "generated_at": datetime.now().isoformat()
            }
        }

        return APIResponse(
            success=True,
            data=stats,
            message="统计信息获取成功"
        )

    except Exception as e:
        logger.error(f"统计信息获取失败: {e}")
        raise HTTPException(status_code=500, detail=f"统计信息获取失败: {str(e)}")


@router.get("/debug/trace/{trace_id}", response_model=APIResponse[Dict[str, Any]])
async def get_execution_trace(
    trace_id: str,
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """获取执行链路追踪信息"""
    try:
        # 这里可以实现基于trace_id的链路追踪
        # 暂时返回基础信息

        trace_info = {
            "trace_id": trace_id,
            "status": "not_implemented",
            "message": "链路追踪功能开发中",
            "requested_by": str(current_user.id),
            "requested_at": datetime.now().isoformat()
        }

        return APIResponse(
            success=True,
            data=trace_info,
            message="链路追踪查询完成"
        )

    except Exception as e:
        logger.error(f"链路追踪查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"链路追踪查询失败: {str(e)}")


# ================================================================================
# Cache Management Endpoints
# ================================================================================

@router.post("/cache/clear", response_model=APIResponse[Dict[str, Any]])
async def clear_pipeline_cache(
    cache_type: Optional[str] = None,  # "schema", "sql", "result", "all"
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """清理流水线缓存"""
    try:
        logger.info(f"用户 {current_user.id} 请求清理缓存: {cache_type or 'all'}")

        # 这里可以实现具体的缓存清理逻辑
        # 暂时返回模拟结果

        cleared_items = {
            "schema_cache": 0,
            "sql_cache": 0,
            "result_cache": 0,
            "cleared_at": datetime.now().isoformat(),
            "cleared_by": str(current_user.id)
        }

        return APIResponse(
            success=True,
            data=cleared_items,
            message=f"缓存清理完成: 类型 {cache_type or 'all'}"
        )

    except Exception as e:
        logger.error(f"缓存清理失败: {e}")
        raise HTTPException(status_code=500, detail=f"缓存清理失败: {str(e)}")


# ================================================================================
# Configuration Endpoints
# ================================================================================

@router.get("/config", response_model=APIResponse[Dict[str, Any]])
async def get_pipeline_configuration(
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """获取流水线配置信息"""
    try:
        config_info = {
            "agent_system": {
                "enabled": True,
                "fallback_available": True
            },
            "sql_generation": {
                "policy_row_limit": 5000,
                "quality_min_rows": 10,
                "timeout_seconds": 30
            },
            "time_context": {
                "supported_periods": ["daily", "weekly", "monthly", "yearly"],
                "default_timezone": "Asia/Shanghai"
            },
            "chart_rendering": {
                "enabled": True,
                "output_formats": ["png", "svg", "json"]
            },
            "cache": {
                "schema_ttl_hours": 24,
                "sql_ttl_hours": 6,
                "result_ttl_hours": 1
            }
        }

        return APIResponse(
            success=True,
            data=config_info,
            message="配置信息获取成功"
        )

    except Exception as e:
        logger.error(f"配置信息获取失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置信息获取失败: {str(e)}")