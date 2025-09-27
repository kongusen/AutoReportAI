"""
流水线WebSocket相关API端点
提供任务状态查询、订阅管理等功能
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.base import APIResponse
from app.services.infrastructure.websocket.pipeline_notifications import (
    pipeline_notification_service, PipelineTaskType
)
from app.schemas.frontend_adapters import (
    adapt_error_for_frontend, adapt_analysis_progress_for_frontend
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/tasks/{task_id}/status")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """获取任务状态"""
    try:
        logger.info(f"用户 {current_user.id} 查询任务状态: {task_id}")

        task_status = await pipeline_notification_service.get_task_status(task_id)

        if not task_status:
            # 使用前端错误适配器
            error_info = adapt_error_for_frontend(
                error_message="任务不存在或已过期",
                error_type="validation",
                error_code="task_not_found",
                details={"task_id": task_id}
            )
            raise HTTPException(
                status_code=404,
                detail=error_info.user_friendly_message
            )

        # 检查权限 - 只有任务所有者可以查看状态
        task_user_id = task_status.get("details", {}).get("user_id")
        if task_user_id and task_user_id != str(current_user.id):
            # 使用前端错误适配器
            error_info = adapt_error_for_frontend(
                error_message="无权限查看该任务",
                error_type="permission",
                error_code="permission_denied",
                details={"task_id": task_id, "user_id": str(current_user.id)}
            )
            raise HTTPException(
                status_code=403,
                detail=error_info.user_friendly_message
            )

        return APIResponse(
            success=True,
            message="任务状态查询成功",
            data=task_status
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"任务状态查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/tasks/{task_id}/subscribe")
async def subscribe_to_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """订阅任务更新"""
    try:
        logger.info(f"用户 {current_user.id} 订阅任务: {task_id}")

        success = await pipeline_notification_service.subscribe_to_task(
            task_id, str(current_user.id)
        )

        if not success:
            raise HTTPException(status_code=400, detail="订阅失败")

        return APIResponse(
            success=True,
            message="订阅成功",
            data={
                "task_id": task_id,
                "user_id": str(current_user.id),
                "subscribed": True
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"任务订阅失败: {e}")
        raise HTTPException(status_code=500, detail=f"订阅失败: {str(e)}")


@router.post("/tasks/{task_id}/unsubscribe")
async def unsubscribe_from_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """取消订阅任务更新"""
    try:
        logger.info(f"用户 {current_user.id} 取消订阅任务: {task_id}")

        success = await pipeline_notification_service.unsubscribe_from_task(
            task_id, str(current_user.id)
        )

        return APIResponse(
            success=True,
            message="取消订阅成功" if success else "已经未订阅",
            data={
                "task_id": task_id,
                "user_id": str(current_user.id),
                "subscribed": False
            }
        )

    except Exception as e:
        logger.error(f"取消订阅失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消订阅失败: {str(e)}")


@router.get("/tasks/mine")
async def get_my_tasks(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> APIResponse[List[Dict[str, Any]]]:
    """获取我的任务列表"""
    try:
        logger.info(f"用户 {current_user.id} 查询任务列表")

        tasks = await pipeline_notification_service.list_user_tasks(str(current_user.id))

        # 按创建时间倒序排列并限制数量
        tasks.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        tasks = tasks[:limit]

        return APIResponse(
            success=True,
            message=f"查询成功，找到 {len(tasks)} 个任务",
            data=tasks
        )

    except Exception as e:
        logger.error(f"任务列表查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/websocket/stats")
async def get_websocket_stats(
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """获取WebSocket统计信息"""
    try:
        logger.info(f"用户 {current_user.id} 查询WebSocket统计")

        stats = pipeline_notification_service.get_service_stats()

        return APIResponse(
            success=True,
            message="统计信息查询成功",
            data=stats
        )

    except Exception as e:
        logger.error(f"WebSocket统计查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/broadcast/notification")
async def broadcast_system_notification(
    message: str = Query(..., description="通知消息"),
    notification_type: str = Query("info", description="通知类型"),
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """广播系统通知 - 管理员功能"""
    try:
        # 这里可以添加管理员权限检查
        # if not current_user.is_admin:
        #     raise HTTPException(status_code=403, detail="需要管理员权限")

        logger.info(f"用户 {current_user.id} 广播系统通知: {message}")

        sent_count = await pipeline_notification_service.broadcast_system_notification(
            message=message,
            notification_type=notification_type,
            data={
                "sender_id": str(current_user.id),
                "sender_name": getattr(current_user, 'username', '系统管理员')
            }
        )

        return APIResponse(
            success=True,
            message=f"系统通知已发送给 {sent_count} 个连接",
            data={
                "message": message,
                "notification_type": notification_type,
                "sent_count": sent_count
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"系统通知广播失败: {e}")
        raise HTTPException(status_code=500, detail=f"广播失败: {str(e)}")


@router.get("/task-types")
async def get_supported_task_types(
    current_user: User = Depends(get_current_user)
) -> APIResponse[List[Dict[str, str]]]:
    """获取支持的任务类型"""
    try:
        task_types = [
            {
                "value": task_type.value,
                "label": {
                    "etl_scan": "ETL前扫描",
                    "report_assembly": "报告组装",
                    "health_check": "健康检查",
                    "template_analysis": "模板分析"
                }.get(task_type.value, task_type.value)
            }
            for task_type in PipelineTaskType
        ]

        return APIResponse(
            success=True,
            message="任务类型查询成功",
            data=task_types
        )

    except Exception as e:
        logger.error(f"任务类型查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/connection/info")
async def get_websocket_connection_info(
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """获取用户的WebSocket连接信息"""
    try:
        from app.websocket.manager import websocket_manager

        user_connections = websocket_manager.get_user_connections(str(current_user.id))

        connection_info = {
            "user_id": str(current_user.id),
            "active_connections": len(user_connections),
            "connections": user_connections,
            "server_stats": websocket_manager.get_system_stats()
        }

        return APIResponse(
            success=True,
            message="连接信息查询成功",
            data=connection_info
        )

    except Exception as e:
        logger.error(f"连接信息查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")