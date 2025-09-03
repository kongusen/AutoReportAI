from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app import crud
from app.api import deps
from app.core.config import settings
from app.models.user import User
from app.models.notification import NotificationType, NotificationStatus
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    NotificationCreate,
    NotificationUpdate,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationStatsResponse,
    BulkNotificationCreate,
    WebSocketNotificationMessage
)
from app.services.infrastructure.notification.notification_service import get_notification_service
from app.websocket.manager import websocket_manager

router = APIRouter()


@router.get("/", response_model=NotificationListResponse)
def get_notifications(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回的记录数"),
    status: Optional[NotificationStatus] = Query(None, description="状态过滤"),
    type: Optional[NotificationType] = Query(None, description="类型过滤"),
    include_read: bool = Query(True, description="是否包含已读通知")
):
    """
    获取当前用户的通知列表
    """
    notifications = crud.notification.get_by_user(
        db=db,
        user_id=str(current_user.id),
        skip=skip,
        limit=limit,
        status_filter=status,
        type_filter=type,
        include_read=include_read
    )
    
    # 获取总数和未读数
    total = crud.notification.get_by_user(
        db=db,
        user_id=str(current_user.id),
        skip=0,
        limit=10000,  # 大数量获取总数
        status_filter=status,
        type_filter=type,
        include_read=include_read
    )
    
    unread_count = crud.notification.get_unread_count(db, str(current_user.id))
    
    return NotificationListResponse(
        notifications=[NotificationResponse.from_orm(n) for n in notifications],
        total=len(total),
        unread_count=unread_count,
        page=skip // limit + 1,
        size=len(notifications),
        has_more=len(notifications) == limit
    )


@router.get("/stats", response_model=NotificationStatsResponse)
def get_notification_stats(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    获取当前用户的通知统计信息
    """
    stats = crud.notification.get_notifications_stats(db, str(current_user.id))
    return NotificationStatsResponse(**stats)


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    获取未读通知数量
    """
    count = crud.notification.get_unread_count(db, str(current_user.id))
    return {"unread_count": count}


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(
    notification_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    获取指定通知详情
    """
    notification = crud.notification.get(db=db, id=notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")
    
    if notification.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权限访问此通知")
    
    return NotificationResponse.from_orm(notification)


@router.post("/", response_model=NotificationResponse)
async def create_notification(
    notification_in: NotificationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_superuser)
):
    """
    创建新通知（仅超级用户）
    """
    notification = crud.notification.create(db=db, obj_in=notification_in)
    
    # 后台发送实时通知
    background_tasks.add_task(send_realtime_notification, notification.user_id, notification)
    
    return NotificationResponse.from_orm(notification)


@router.post("/bulk", response_model=List[NotificationResponse])
async def create_bulk_notifications(
    bulk_data: BulkNotificationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_superuser)
):
    """
    批量创建通知（仅超级用户）
    """
    notifications = crud.notification.create_bulk(
        db=db,
        user_ids=bulk_data.user_ids,
        notification_data=bulk_data.notification
    )
    
    # 后台发送实时通知
    for notification in notifications:
        background_tasks.add_task(send_realtime_notification, notification.user_id, notification)
    
    return [NotificationResponse.from_orm(n) for n in notifications]


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    标记通知为已读
    """
    notification = crud.notification.mark_as_read(
        db=db,
        notification_id=notification_id,
        user_id=str(current_user.id)
    )
    
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在或无权限访问")
    
    return NotificationResponse.from_orm(notification)


@router.patch("/{notification_id}/dismiss", response_model=NotificationResponse)
async def dismiss_notification(
    notification_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    忽略通知
    """
    notification = crud.notification.mark_as_dismissed(
        db=db,
        notification_id=notification_id,
        user_id=str(current_user.id)
    )
    
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在或无权限访问")
    
    return NotificationResponse.from_orm(notification)


@router.patch("/mark-all-read")
def mark_all_notifications_as_read(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    标记所有通知为已读
    """
    updated_count = crud.notification.mark_all_as_read(db, str(current_user.id))
    return {"updated_count": updated_count}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    删除通知
    """
    notification = crud.notification.get(db=db, id=notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")
    
    if notification.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权限删除此通知")
    
    crud.notification.remove(db=db, id=notification_id)
    return {"message": "通知已删除"}


@router.get("/preferences/", response_model=NotificationPreferenceResponse)
def get_notification_preferences(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    获取用户通知偏好设置
    """
    preferences = crud.notification_preference.get_by_user(db, str(current_user.id))
    
    if not preferences:
        # 创建默认偏好设置
        default_preferences = NotificationPreferenceUpdate()
        preferences = crud.notification_preference.create_or_update(
            db=db,
            user_id=str(current_user.id),
            preference_data=default_preferences
        )
    
    return NotificationPreferenceResponse.from_orm(preferences)


@router.patch("/preferences/", response_model=NotificationPreferenceResponse)
def update_notification_preferences(
    preferences_in: NotificationPreferenceUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    更新用户通知偏好设置
    """
    preferences = crud.notification_preference.create_or_update(
        db=db,
        user_id=str(current_user.id),
        preference_data=preferences_in
    )
    
    return NotificationPreferenceResponse.from_orm(preferences)


@router.post("/test")
async def send_test_notification(
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    message: str = Query("这是一条测试通知", description="测试消息内容")
):
    """
    发送测试通知
    """
    notification_data = NotificationCreate(
        user_id=str(current_user.id),
        type=NotificationType.INFO,
        title="测试通知",
        message=message,
        persistent=False,
        auto_dismiss_seconds=5
    )
    
    notification = crud.notification.create(db=db, obj_in=notification_data)
    
    # 发送实时通知
    background_tasks.add_task(send_realtime_notification, str(current_user.id), notification)
    
    return {"message": "测试通知已发送", "notification_id": notification.id}


async def send_realtime_notification(user_id: str, notification):
    """
    发送实时通知的后台任务
    """
    try:
        # 通过WebSocket发送
        # websocket_manager is already imported
        notification_message = WebSocketNotificationMessage(
            data=NotificationResponse.from_orm(notification)
        )
        
        await websocket_manager.send_personal_message(
            user_id,
            notification_message.dict()
        )
        
        # 通过通知服务发送
        notification_service = get_notification_service()
        await notification_service.send_direct_message(user_id, {
            "type": "notification",
            "data": NotificationResponse.from_orm(notification).dict(),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        # 记录错误但不影响主流程
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"发送实时通知失败: {str(e)}")


# 管理员相关接口
@router.get("/admin/stats")
def get_admin_notification_stats(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_superuser)
):
    """
    获取系统通知统计（仅管理员）
    """
    # 这里可以添加系统级别的通知统计
    return {"message": "管理员统计功能待实现"}


@router.delete("/admin/cleanup")
def cleanup_old_notifications(
    days: int = Query(30, ge=1, le=365, description="清理多少天前的通知"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_superuser)
):
    """
    清理过期通知（仅管理员）
    """
    deleted_count = crud.notification.delete_old_notifications(db, days)
    return {"deleted_count": deleted_count, "message": f"已清理 {days} 天前的通知"}