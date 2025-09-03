from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from app.crud.base import CRUDBase
from app.models.notification import Notification, NotificationPreference, NotificationStatus, NotificationType
from app.schemas.notification import (
    NotificationCreate, 
    NotificationUpdate, 
    NotificationPreferenceCreate, 
    NotificationPreferenceUpdate
)


class CRUDNotification(CRUDBase[Notification, NotificationCreate, NotificationUpdate]):
    """通知CRUD操作"""
    
    def get_by_user(
        self,
        db: Session,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        status_filter: Optional[NotificationStatus] = None,
        type_filter: Optional[NotificationType] = None,
        include_read: bool = True
    ) -> List[Notification]:
        """获取用户通知列表"""
        query = db.query(self.model).filter(self.model.user_id == user_id)
        
        # 状态过滤
        if status_filter:
            query = query.filter(self.model.status == status_filter)
        elif not include_read:
            query = query.filter(self.model.status != NotificationStatus.READ)
            
        # 类型过滤
        if type_filter:
            query = query.filter(self.model.type == type_filter)
            
        # 过滤过期通知
        query = query.filter(
            or_(
                self.model.expires_at.is_(None),
                self.model.expires_at > datetime.utcnow()
            )
        )
        
        return query.order_by(desc(self.model.created_at)).offset(skip).limit(limit).all()
    
    def get_unread_count(self, db: Session, user_id: str) -> int:
        """获取用户未读通知数量"""
        return db.query(self.model).filter(
            and_(
                self.model.user_id == user_id,
                self.model.status.in_([NotificationStatus.PENDING, NotificationStatus.SENT]),
                or_(
                    self.model.expires_at.is_(None),
                    self.model.expires_at > datetime.utcnow()
                )
            )
        ).count()
    
    def mark_as_read(self, db: Session, notification_id: int, user_id: str) -> Optional[Notification]:
        """标记通知为已读"""
        notification = db.query(self.model).filter(
            and_(
                self.model.id == notification_id,
                self.model.user_id == user_id
            )
        ).first()
        
        if notification:
            notification.mark_as_read()
            db.commit()
            db.refresh(notification)
            
        return notification
    
    def mark_as_dismissed(self, db: Session, notification_id: int, user_id: str) -> Optional[Notification]:
        """标记通知为已忽略"""
        notification = db.query(self.model).filter(
            and_(
                self.model.id == notification_id,
                self.model.user_id == user_id
            )
        ).first()
        
        if notification:
            notification.mark_as_dismissed()
            db.commit()
            db.refresh(notification)
            
        return notification
    
    def mark_all_as_read(self, db: Session, user_id: str) -> int:
        """标记用户所有通知为已读"""
        updated_count = db.query(self.model).filter(
            and_(
                self.model.user_id == user_id,
                self.model.status.in_([NotificationStatus.PENDING, NotificationStatus.SENT])
            )
        ).update({
            "status": NotificationStatus.READ,
            "read_at": datetime.utcnow()
        })
        
        db.commit()
        return updated_count
    
    def delete_old_notifications(self, db: Session, days: int = 30) -> int:
        """删除过期的通知"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted_count = db.query(self.model).filter(
            or_(
                self.model.created_at < cutoff_date,
                and_(
                    self.model.expires_at.is_not(None),
                    self.model.expires_at < datetime.utcnow()
                )
            )
        ).delete()
        
        db.commit()
        return deleted_count
    
    def get_notifications_stats(self, db: Session, user_id: str) -> Dict[str, Any]:
        """获取通知统计信息"""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        
        # 总数量
        total = db.query(self.model).filter(self.model.user_id == user_id).count()
        
        # 未读数量
        unread = self.get_unread_count(db, user_id)
        
        # 今日数量
        today = db.query(self.model).filter(
            and_(
                self.model.user_id == user_id,
                self.model.created_at >= today_start
            )
        ).count()
        
        # 本周数量
        this_week = db.query(self.model).filter(
            and_(
                self.model.user_id == user_id,
                self.model.created_at >= week_start
            )
        ).count()
        
        # 按类型统计
        by_type = {}
        type_stats = db.query(
            self.model.type,
            func.count(self.model.id)
        ).filter(self.model.user_id == user_id).group_by(self.model.type).all()
        
        for notification_type, count in type_stats:
            by_type[notification_type.value] = count
            
        # 按状态统计
        by_status = {}
        status_stats = db.query(
            self.model.status,
            func.count(self.model.id)
        ).filter(self.model.user_id == user_id).group_by(self.model.status).all()
        
        for status, count in status_stats:
            by_status[status.value] = count
        
        return {
            "total_notifications": total,
            "unread_count": unread,
            "today_count": today,
            "this_week_count": this_week,
            "by_type": by_type,
            "by_status": by_status
        }
    
    def create_bulk(
        self,
        db: Session,
        user_ids: List[str],
        notification_data: NotificationCreate
    ) -> List[Notification]:
        """批量创建通知"""
        notifications = []
        
        for user_id in user_ids:
            # 为每个用户创建通知副本
            user_notification_data = notification_data.dict()
            user_notification_data["user_id"] = user_id
            
            notification = self.model(**user_notification_data)
            notification.mark_as_sent()  # 标记为已发送
            
            db.add(notification)
            notifications.append(notification)
        
        db.commit()
        
        for notification in notifications:
            db.refresh(notification)
            
        return notifications


class CRUDNotificationPreference(CRUDBase[NotificationPreference, NotificationPreferenceCreate, NotificationPreferenceUpdate]):
    """通知偏好CRUD操作"""
    
    def get_by_user(self, db: Session, user_id: str) -> Optional[NotificationPreference]:
        """获取用户通知偏好"""
        return db.query(self.model).filter(self.model.user_id == user_id).first()
    
    def create_or_update(
        self,
        db: Session,
        user_id: str,
        preference_data: NotificationPreferenceUpdate
    ) -> NotificationPreference:
        """创建或更新用户通知偏好"""
        existing = self.get_by_user(db, user_id)
        
        if existing:
            # 更新现有偏好
            update_data = preference_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(existing, field, value)
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # 创建新偏好
            create_data = preference_data.dict()
            create_data["user_id"] = user_id
            new_preference = self.model(**create_data)
            db.add(new_preference)
            db.commit()
            db.refresh(new_preference)
            return new_preference
    
    def is_notification_allowed(
        self,
        db: Session,
        user_id: str,
        notification_type: NotificationType,
        channel: str = "websocket"
    ) -> bool:
        """检查是否允许发送通知"""
        preference = self.get_by_user(db, user_id)
        
        if not preference:
            return True  # 默认允许所有通知
        
        # 检查渠道是否启用
        channel_enabled = True
        if channel == "websocket" and not preference.enable_websocket:
            channel_enabled = False
        elif channel == "email" and not preference.enable_email:
            channel_enabled = False
        elif channel == "browser" and not preference.enable_browser:
            channel_enabled = False
            
        if not channel_enabled:
            return False
        
        # 检查通知类型是否启用
        if notification_type == NotificationType.TASK_UPDATE and not preference.enable_task_notifications:
            return False
        elif notification_type == NotificationType.REPORT_READY and not preference.enable_report_notifications:
            return False
        elif notification_type == NotificationType.SYSTEM and not preference.enable_system_notifications:
            return False
        elif notification_type == NotificationType.ERROR and not preference.enable_error_notifications:
            return False
        
        # 检查免打扰时间
        if preference.quiet_hours_start and preference.quiet_hours_end:
            now = datetime.now()
            current_time = now.time()
            
            try:
                start_time = datetime.strptime(preference.quiet_hours_start, "%H:%M").time()
                end_time = datetime.strptime(preference.quiet_hours_end, "%H:%M").time()
                
                if start_time <= end_time:
                    # 同一天内的时间段
                    if start_time <= current_time <= end_time:
                        return False
                else:
                    # 跨日的时间段
                    if current_time >= start_time or current_time <= end_time:
                        return False
            except ValueError:
                # 时间格式错误，忽略免打扰设置
                pass
        
        return True


# 实例化CRUD对象
notification = CRUDNotification(Notification)
notification_preference = CRUDNotificationPreference(NotificationPreference)