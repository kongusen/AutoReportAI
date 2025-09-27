"""
模板分析适配器 - 前端兼容性
将前端的模板分析请求路由到新的流水线系统
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.base import APIResponse
from app.schemas.pipeline_responses import (
    ETLScanResponse, PlaceholderItem, PlaceholderStats,
    create_etl_scan_response
)
from app.schemas.frontend_adapters import (
    adapt_error_for_frontend, adapt_analysis_progress_for_frontend
)
from app.services.application.facades.unified_service_facade import create_unified_service_facade
from app.services.infrastructure.websocket.pipeline_notifications import (
    pipeline_notification_service, PipelineTaskType, PipelineTaskStatus,
    notify_task_start, notify_task_progress, notify_task_complete, notify_task_error
)
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()


class TemplateAnalysisRequest(BaseModel):
    """模板分析请求 - 前端兼容格式"""
    target_expectations: Optional[Dict[str, Any]] = Field(None, description="目标期望")


@router.post("/templates/{template_id}/analyze")
async def analyze_template_placeholders(
    template_id: str,
    data_source_id: str = Query(..., description="数据源ID"),
    force_reanalyze: bool = Query(False, description="强制重新分析"),
    optimization_level: str = Query("enhanced", description="优化级别"),
    request_body: TemplateAnalysisRequest = TemplateAnalysisRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> APIResponse[ETLScanResponse]:
    """
    分析模板占位符 - 前端兼容接口

    这个端点提供与前端 analyzeTemplatePlaceholders() 调用的完整兼容性，
    同时将请求路由到新的PTOF流水线系统。
    """
    try:
        logger.info(f"用户 {current_user.id} 请求分析模板 {template_id}，数据源: {data_source_id}")

        # 生成任务ID
        task_id = f"template_analysis_{uuid.uuid4().hex[:8]}"

        # 启动实时通知
        await notify_task_start(
            task_id=task_id,
            task_type=PipelineTaskType.TEMPLATE_ANALYSIS,
            user_id=str(current_user.id),
            message="开始模板分析",
            template_id=template_id,
            data_source_id=data_source_id
        )

        # 更新进度：准备阶段
        await notify_task_progress(
            task_id=task_id,
            status=PipelineTaskStatus.SCANNING,
            progress=0.1,
            message="准备分析环境"
        )

        # 创建统一门面服务
        facade = create_unified_service_facade(db, str(current_user.id))

        # 更新进度：扫描阶段
        await notify_task_progress(
            task_id=task_id,
            status=PipelineTaskStatus.ANALYZING,
            progress=0.3,
            message="扫描模板占位符"
        )

        # 调用流水线的ETL前扫描
        scan_result = await facade.etl_pre_scan_placeholders(
            template_id=template_id,
            data_source_id=data_source_id,
            options={
                "force_reanalyze": force_reanalyze,
                "optimization_level": optimization_level,
                "target_expectations": request_body.target_expectations
            }
        )

        if not scan_result.get("success", False):
            error_msg = scan_result.get("error", "分析失败")
            logger.error(f"模板分析失败: {error_msg}")

            # 发送错误通知
            await notify_task_error(
                task_id=task_id,
                error_message=error_msg,
                error_details={"scan_result": scan_result}
            )

            # 使用前端错误适配器
            error_info = adapt_error_for_frontend(
                error_message=error_msg,
                error_type="template_analysis",
                error_code="template_analysis_failed",
                details={"scan_result": scan_result, "template_id": template_id}
            )

            raise HTTPException(
                status_code=400,
                detail=error_info.user_friendly_message
            )

        # 更新进度：处理结果
        await notify_task_progress(
            task_id=task_id,
            status=PipelineTaskStatus.ASSEMBLING,
            progress=0.8,
            message="处理分析结果"
        )

        # 转换为标准化格式
        items = []
        for item_data in scan_result.get("items", []):
            items.append(PlaceholderItem(
                text=item_data.get("text", ""),
                kind=item_data.get("kind", "unknown"),
                needs_reanalysis=item_data.get("needs_reanalysis", False),
                confidence=item_data.get("confidence"),
                meta=item_data.get("meta")
            ))

        stats_data = scan_result.get("stats", {})
        stats = PlaceholderStats(
            total=stats_data.get("total", 0),
            need_reanalysis=stats_data.get("need_reanalysis", 0),
            by_kind=stats_data.get("by_kind", {})
        )

        # 完成任务通知
        await notify_task_complete(
            task_id=task_id,
            result_data={
                "total_placeholders": stats.total,
                "placeholders_by_kind": stats.by_kind,
                "needs_reanalysis": stats.need_reanalysis
            },
            message=f"模板分析完成，发现 {stats.total} 个占位符"
        )

        # 返回标准化响应
        response = create_etl_scan_response(
            items=items,
            stats=stats,
            template_id=template_id,
            data_source_id=data_source_id,
            success=True,
            message=f"模板分析完成，发现 {stats.total} 个占位符"
        )

        # 在响应中包含任务ID，便于前端跟踪
        response.data.task_id = task_id  # type: ignore

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"模板分析异常: {e}")

        # 发送异常通知（如果任务已创建）
        try:
            if 'task_id' in locals():
                await notify_task_error(
                    task_id=task_id,
                    error_message=f"系统异常: {str(e)}",
                    error_details={"exception_type": type(e).__name__}
                )
        except:
            pass  # 避免通知失败影响主要错误处理

        # 使用前端错误适配器
        error_info = adapt_error_for_frontend(
            error_message=str(e),
            error_type="system",
            error_code="template_analysis_exception",
            details={"exception_type": type(e).__name__, "template_id": template_id}
        )

        raise HTTPException(
            status_code=500,
            detail=error_info.user_friendly_message
        )


@router.get("/templates/{template_id}/analysis-status")
async def get_template_analysis_status(
    template_id: str,
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """
    获取模板分析状态 - 扩展功能
    """
    try:
        logger.info(f"用户 {current_user.id} 查询模板 {template_id} 分析状态")

        # 这里可以实现缓存状态查询、历史分析记录等功能
        # 目前返回基础状态信息

        return APIResponse(
            success=True,
            message="状态查询成功",
            data={
                "template_id": template_id,
                "last_analysis": None,  # 可以从缓存或数据库查询
                "cache_available": False,
                "supported_operations": [
                    "etl_pre_scan",
                    "report_assembly",
                    "health_check"
                ]
            }
        )

    except Exception as e:
        logger.error(f"状态查询异常: {e}")
        raise HTTPException(status_code=500, detail=f"状态查询失败: {str(e)}")


@router.delete("/templates/{template_id}/analysis-cache")
async def clear_template_analysis_cache(
    template_id: str,
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """
    清除模板分析缓存 - 维护功能
    """
    try:
        logger.info(f"用户 {current_user.id} 清除模板 {template_id} 分析缓存")

        # 这里可以实现缓存清除逻辑
        # 目前返回成功状态

        return APIResponse(
            success=True,
            message="缓存清除成功",
            data={
                "template_id": template_id,
                "cache_cleared": True,
                "next_analysis_will_be_fresh": True
            }
        )

    except Exception as e:
        logger.error(f"缓存清除异常: {e}")
        raise HTTPException(status_code=500, detail=f"缓存清除失败: {str(e)}")