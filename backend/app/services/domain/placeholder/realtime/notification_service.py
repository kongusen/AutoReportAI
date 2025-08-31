"""
通知服务

处理实时数据的通知和告警
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)

class NotificationSeverity(Enum):
    """通知严重程度"""
    INFO = "info"
    WARNING = "warning"  
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Notification:
    """通知"""
    notification_id: str
    title: str
    message: str
    severity: NotificationSeverity
    placeholder_id: Optional[str]
    data: Dict[str, Any]
    created_at: datetime
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

@dataclass
class NotificationRule:
    """通知规则"""
    rule_id: str
    name: str
    description: str
    placeholder_ids: List[str]  # 空列表表示所有占位符
    condition: Dict[str, Any]
    notification_template: Dict[str, Any]
    severity: NotificationSeverity
    enabled: bool = True
    cooldown_minutes: int = 5  # 冷却时间，防止重复通知

class NotificationService:
    """通知服务"""
    
    def __init__(self,
                 max_notifications: int = 1000,
                 cleanup_hours: int = 24):
        """
        初始化通知服务
        
        Args:
            max_notifications: 最大通知数量
            cleanup_hours: 通知保留时间（小时）
        """
        self.max_notifications = max_notifications
        self.cleanup_hours = cleanup_hours
        
        # 通知存储
        self._notifications: deque = deque(maxlen=max_notifications)
        self._notifications_by_id: Dict[str, Notification] = {}
        
        # 通知规则
        self._notification_rules: Dict[str, NotificationRule] = {}
        
        # 通知处理器
        self._notification_handlers: Dict[str, Callable] = {}
        
        # 冷却时间管理
        self._rule_cooldowns: Dict[str, datetime] = {}
        
        # 统计信息
        self._stats = {
            'total_notifications': 0,
            'notifications_by_severity': {
                severity.value: 0 for severity in NotificationSeverity
            },
            'acknowledged_notifications': 0,
            'suppressed_notifications': 0  # 因冷却时间被抑制的通知
        }
        
        self._lock = asyncio.Lock()
        
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        logger.info("通知服务初始化完成")
    
    async def add_notification_rule(self, rule: NotificationRule) -> bool:
        """添加通知规则"""
        async with self._lock:
            try:
                self._notification_rules[rule.rule_id] = rule
                logger.info(f"添加通知规则: {rule.rule_id} - {rule.name}")
                return True
            except Exception as e:
                logger.error(f"添加通知规则失败: {e}")
                return False
    
    async def remove_notification_rule(self, rule_id: str) -> bool:
        """移除通知规则"""
        async with self._lock:
            try:
                if rule_id in self._notification_rules:
                    del self._notification_rules[rule_id]
                    # 清理相关的冷却时间
                    if rule_id in self._rule_cooldowns:
                        del self._rule_cooldowns[rule_id]
                    logger.info(f"移除通知规则: {rule_id}")
                    return True
                return False
            except Exception as e:
                logger.error(f"移除通知规则失败: {e}")
                return False
    
    async def register_notification_handler(self, 
                                           handler_name: str, 
                                           handler_func: Callable[[Notification], None]) -> bool:
        """注册通知处理器"""
        try:
            self._notification_handlers[handler_name] = handler_func
            logger.info(f"注册通知处理器: {handler_name}")
            return True
        except Exception as e:
            logger.error(f"注册通知处理器失败: {e}")
            return False
    
    async def create_notification(self,
                                title: str,
                                message: str,
                                severity: NotificationSeverity,
                                placeholder_id: Optional[str] = None,
                                data: Dict[str, Any] = None) -> str:
        """创建通知"""
        async with self._lock:
            try:
                notification_id = f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                
                notification = Notification(
                    notification_id=notification_id,
                    title=title,
                    message=message,
                    severity=severity,
                    placeholder_id=placeholder_id,
                    data=data or {},
                    created_at=datetime.now()
                )
                
                # 存储通知
                self._notifications.append(notification)
                self._notifications_by_id[notification_id] = notification
                
                # 更新统计
                self._stats['total_notifications'] += 1
                self._stats['notifications_by_severity'][severity.value] += 1
                
                # 异步处理通知
                asyncio.create_task(self._process_notification(notification))
                
                logger.info(f"创建通知: {notification_id} - {title} ({severity.value})")
                return notification_id
                
            except Exception as e:
                logger.error(f"创建通知失败: {e}")
                raise
    
    async def process_data_point_notifications(self, data_point) -> List[str]:
        """处理数据点相关的通知"""
        triggered_notifications = []
        
        async with self._lock:
            for rule in self._notification_rules.values():
                if not rule.enabled:
                    continue
                
                # 检查冷却时间
                if await self._is_rule_in_cooldown(rule.rule_id):
                    self._stats['suppressed_notifications'] += 1
                    continue
                
                # 检查规则条件
                if await self._check_notification_condition(data_point, rule):
                    notification_id = await self._create_rule_notification(data_point, rule)
                    if notification_id:
                        triggered_notifications.append(notification_id)
                        # 设置冷却时间
                        self._rule_cooldowns[rule.rule_id] = datetime.now()
        
        return triggered_notifications
    
    async def _check_notification_condition(self, data_point, rule: NotificationRule) -> bool:
        """检查通知条件"""
        try:
            # 检查占位符ID
            if rule.placeholder_ids and data_point.placeholder_id not in rule.placeholder_ids:
                return False
            
            condition = rule.condition
            
            # 检查数据类型
            if 'data_types' in condition:
                if data_point.data_type not in condition['data_types']:
                    return False
            
            # 检查数值条件
            if 'value_conditions' in condition:
                value_conditions = condition['value_conditions']
                
                if isinstance(data_point.value, dict):
                    for field, field_condition in value_conditions.items():
                        if field not in data_point.value:
                            continue
                        
                        field_value = data_point.value[field]
                        if not self._check_value_condition(field_value, field_condition):
                            return False
                
                elif isinstance(data_point.value, (int, float)):
                    if not self._check_value_condition(data_point.value, value_conditions):
                        return False
            
            # 检查元数据条件
            if 'metadata_conditions' in condition:
                metadata_conditions = condition['metadata_conditions']
                for key, expected_value in metadata_conditions.items():
                    if key not in data_point.metadata:
                        return False
                    if data_point.metadata[key] != expected_value:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查通知条件失败: {e}")
            return False
    
    def _check_value_condition(self, value, condition: Dict[str, Any]) -> bool:
        """检查数值条件"""
        try:
            if 'gt' in condition and value <= condition['gt']:
                return False
            if 'gte' in condition and value < condition['gte']:
                return False
            if 'lt' in condition and value >= condition['lt']:
                return False
            if 'lte' in condition and value > condition['lte']:
                return False
            if 'eq' in condition and value != condition['eq']:
                return False
            
            return True
        except Exception:
            return False
    
    async def _create_rule_notification(self, data_point, rule: NotificationRule) -> Optional[str]:
        """根据规则创建通知"""
        try:
            template = rule.notification_template
            
            # 构建通知标题和消息
            title = template.get('title', f'通知规则触发: {rule.name}')
            message = template.get('message', f'占位符 {data_point.placeholder_id} 触发了通知规则')
            
            # 支持模板变量替换
            title = title.format(
                placeholder_id=data_point.placeholder_id,
                rule_name=rule.name,
                timestamp=data_point.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                value=data_point.value
            )
            
            message = message.format(
                placeholder_id=data_point.placeholder_id,
                rule_name=rule.name,
                timestamp=data_point.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                value=data_point.value,
                data_type=data_point.data_type
            )
            
            # 创建通知数据
            notification_data = {
                'rule_id': rule.rule_id,
                'data_point': {
                    'placeholder_id': data_point.placeholder_id,
                    'timestamp': data_point.timestamp.isoformat(),
                    'value': data_point.value,
                    'data_type': data_point.data_type,
                    'metadata': data_point.metadata
                }
            }
            
            return await self.create_notification(
                title=title,
                message=message,
                severity=rule.severity,
                placeholder_id=data_point.placeholder_id,
                data=notification_data
            )
            
        except Exception as e:
            logger.error(f"创建规则通知失败: {e}")
            return None
    
    async def _is_rule_in_cooldown(self, rule_id: str) -> bool:
        """检查规则是否在冷却时间内"""
        if rule_id not in self._rule_cooldowns:
            return False
        
        rule = self._notification_rules.get(rule_id)
        if not rule:
            return False
        
        last_notification = self._rule_cooldowns[rule_id]
        cooldown_end = last_notification + timedelta(minutes=rule.cooldown_minutes)
        
        return datetime.now() < cooldown_end
    
    async def _process_notification(self, notification: Notification):
        """处理通知"""
        try:
            # 调用所有已注册的通知处理器
            for handler_name, handler_func in self._notification_handlers.items():
                try:
                    if asyncio.iscoroutinefunction(handler_func):
                        await handler_func(notification)
                    else:
                        handler_func(notification)
                except Exception as e:
                    logger.error(f"通知处理器执行失败 {handler_name}: {e}")
            
            logger.debug(f"处理通知完成: {notification.notification_id}")
            
        except Exception as e:
            logger.error(f"处理通知失败: {e}")
    
    async def acknowledge_notification(self, 
                                     notification_id: str, 
                                     acknowledged_by: str) -> bool:
        """确认通知"""
        async with self._lock:
            try:
                if notification_id not in self._notifications_by_id:
                    return False
                
                notification = self._notifications_by_id[notification_id]
                if notification.acknowledged:
                    return False
                
                notification.acknowledged = True
                notification.acknowledged_at = datetime.now()
                notification.acknowledged_by = acknowledged_by
                
                self._stats['acknowledged_notifications'] += 1
                
                logger.info(f"确认通知: {notification_id} by {acknowledged_by}")
                return True
                
            except Exception as e:
                logger.error(f"确认通知失败: {e}")
                return False
    
    async def get_notifications(self,
                              severity: Optional[NotificationSeverity] = None,
                              placeholder_id: Optional[str] = None,
                              acknowledged: Optional[bool] = None,
                              limit: int = 50,
                              offset: int = 0) -> List[Dict[str, Any]]:
        """获取通知列表"""
        async with self._lock:
            notifications = list(self._notifications)
            
            # 应用过滤器
            if severity:
                notifications = [n for n in notifications if n.severity == severity]
            
            if placeholder_id:
                notifications = [n for n in notifications if n.placeholder_id == placeholder_id]
            
            if acknowledged is not None:
                notifications = [n for n in notifications if n.acknowledged == acknowledged]
            
            # 按创建时间倒序排列
            notifications.sort(key=lambda n: n.created_at, reverse=True)
            
            # 分页
            start = offset
            end = offset + limit
            page_notifications = notifications[start:end]
            
            # 转换为字典格式
            result = []
            for notification in page_notifications:
                result.append({
                    'notification_id': notification.notification_id,
                    'title': notification.title,
                    'message': notification.message,
                    'severity': notification.severity.value,
                    'placeholder_id': notification.placeholder_id,
                    'data': notification.data,
                    'created_at': notification.created_at.isoformat(),
                    'acknowledged': notification.acknowledged,
                    'acknowledged_at': notification.acknowledged_at.isoformat() if notification.acknowledged_at else None,
                    'acknowledged_by': notification.acknowledged_by
                })
            
            return result
    
    async def get_notification_stats(self) -> Dict[str, Any]:
        """获取通知统计"""
        async with self._lock:
            unacknowledged_count = sum(
                1 for n in self._notifications if not n.acknowledged
            )
            
            # 按严重程度统计未确认通知
            unacknowledged_by_severity = {}
            for severity in NotificationSeverity:
                count = sum(
                    1 for n in self._notifications 
                    if not n.acknowledged and n.severity == severity
                )
                unacknowledged_by_severity[severity.value] = count
            
            return {
                'total_notifications': self._stats['total_notifications'],
                'current_notifications': len(self._notifications),
                'acknowledged_notifications': self._stats['acknowledged_notifications'],
                'unacknowledged_notifications': unacknowledged_count,
                'suppressed_notifications': self._stats['suppressed_notifications'],
                'notifications_by_severity': self._stats['notifications_by_severity'].copy(),
                'unacknowledged_by_severity': unacknowledged_by_severity,
                'active_rules': len([r for r in self._notification_rules.values() if r.enabled]),
                'total_rules': len(self._notification_rules),
                'registered_handlers': len(self._notification_handlers)
            }
    
    async def get_notification_rules(self) -> List[Dict[str, Any]]:
        """获取通知规则"""
        async with self._lock:
            rules = []
            for rule in self._notification_rules.values():
                rule_info = {
                    'rule_id': rule.rule_id,
                    'name': rule.name,
                    'description': rule.description,
                    'placeholder_ids': rule.placeholder_ids,
                    'condition': rule.condition,
                    'notification_template': rule.notification_template,
                    'severity': rule.severity.value,
                    'enabled': rule.enabled,
                    'cooldown_minutes': rule.cooldown_minutes
                }
                
                # 添加冷却状态
                if await self._is_rule_in_cooldown(rule.rule_id):
                    last_notification = self._rule_cooldowns[rule.rule_id]
                    cooldown_end = last_notification + timedelta(minutes=rule.cooldown_minutes)
                    rule_info['in_cooldown'] = True
                    rule_info['cooldown_ends_at'] = cooldown_end.isoformat()
                else:
                    rule_info['in_cooldown'] = False
                
                rules.append(rule_info)
            
            return rules
    
    async def _periodic_cleanup(self):
        """定期清理过期通知"""
        while True:
            try:
                await asyncio.sleep(3600)  # 每小时清理一次
                await self._cleanup_old_notifications()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"通知清理任务出错: {e}")
    
    async def _cleanup_old_notifications(self):
        """清理旧通知"""
        async with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=self.cleanup_hours)
            
            # 清理内存中的通知
            notifications_to_remove = []
            for notification in self._notifications:
                if notification.created_at < cutoff_time:
                    notifications_to_remove.append(notification)
            
            for notification in notifications_to_remove:
                self._notifications.remove(notification)
                if notification.notification_id in self._notifications_by_id:
                    del self._notifications_by_id[notification.notification_id]
            
            if notifications_to_remove:
                logger.info(f"清理了 {len(notifications_to_remove)} 个过期通知")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            stats = await self.get_notification_stats()
            
            health_status = "healthy"
            issues = []
            
            # 检查未确认通知数量
            unacknowledged = stats['unacknowledged_notifications']
            if unacknowledged > 100:
                issues.append(f"未确认通知过多: {unacknowledged}")
                health_status = "warning"
            
            # 检查关键和错误级别的未确认通知
            critical_unacknowledged = stats['unacknowledged_by_severity'].get('critical', 0)
            error_unacknowledged = stats['unacknowledged_by_severity'].get('error', 0)
            
            if critical_unacknowledged > 0:
                issues.append(f"有 {critical_unacknowledged} 个未确认的关键通知")
                health_status = "warning"
            
            if error_unacknowledged > 5:
                issues.append(f"有 {error_unacknowledged} 个未确认的错误通知")
                health_status = "warning"
            
            # 检查通知处理器
            if len(self._notification_handlers) == 0:
                issues.append("没有注册的通知处理器")
                health_status = "warning"
            
            return {
                'status': health_status,
                'issues': issues,
                'stats': stats
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'issues': [f"健康检查失败: {str(e)}"],
                'stats': {}
            }
    
    async def shutdown(self):
        """关闭通知服务"""
        if hasattr(self, '_cleanup_task'):
            self._cleanup_task.cancel()
        
        logger.info("通知服务已关闭")

# 全局通知服务实例
_notification_service: Optional[NotificationService] = None

def get_notification_service() -> NotificationService:
    """获取全局通知服务实例"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service

def initialize_notification_service(**kwargs) -> NotificationService:
    """初始化全局通知服务"""
    global _notification_service
    _notification_service = NotificationService(**kwargs)
    return _notification_service