"""
WebSocket管理器

管理占位符实时数据的WebSocket连接
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import defaultdict
import weakref

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

@dataclass
class WebSocketConnection:
    """WebSocket连接信息"""
    connection_id: str
    websocket: WebSocket
    user_id: Optional[str]
    subscribed_placeholders: Set[str]
    subscribed_data_types: Set[str]
    connected_at: datetime
    last_activity: datetime

class WebSocketManager:
    """WebSocket管理器"""
    
    def __init__(self, max_connections: int = 100):
        """
        初始化WebSocket管理器
        
        Args:
            max_connections: 最大连接数
        """
        self.max_connections = max_connections
        
        # 连接管理
        self._connections: Dict[str, WebSocketConnection] = {}
        self._placeholder_subscribers: Dict[str, Set[str]] = defaultdict(set)
        self._user_connections: Dict[str, Set[str]] = defaultdict(set)
        
        # 消息队列
        self._message_queues: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # 统计信息
        self._stats = {
            'total_connections': 0,
            'current_connections': 0,
            'messages_sent': 0,
            'messages_failed': 0,
            'disconnections': 0
        }
        
        self._lock = asyncio.Lock()
        
        # 启动心跳检查任务
        self._heartbeat_task = asyncio.create_task(self._heartbeat_check())
        
        logger.info("WebSocket管理器初始化完成")
    
    async def connect(self,
                     websocket: WebSocket,
                     connection_id: str,
                     user_id: Optional[str] = None) -> bool:
        """建立WebSocket连接"""
        async with self._lock:
            try:
                # 检查连接数限制
                if len(self._connections) >= self.max_connections:
                    logger.warning("WebSocket连接数已达上限")
                    return False
                
                await websocket.accept()
                
                # 创建连接对象
                connection = WebSocketConnection(
                    connection_id=connection_id,
                    websocket=websocket,
                    user_id=user_id,
                    subscribed_placeholders=set(),
                    subscribed_data_types=set(),
                    connected_at=datetime.now(),
                    last_activity=datetime.now()
                )
                
                # 存储连接
                self._connections[connection_id] = connection
                
                if user_id:
                    self._user_connections[user_id].add(connection_id)
                
                # 更新统计
                self._stats['total_connections'] += 1
                self._stats['current_connections'] = len(self._connections)
                
                logger.info(f"WebSocket连接建立: {connection_id} (用户: {user_id})")
                
                # 发送欢迎消息
                await self._send_message(connection_id, {
                    'type': 'connection_established',
                    'connection_id': connection_id,
                    'timestamp': datetime.now().isoformat(),
                    'message': '连接建立成功'
                })
                
                return True
                
            except Exception as e:
                logger.error(f"建立WebSocket连接失败: {e}")
                return False
    
    async def disconnect(self, connection_id: str):
        """断开WebSocket连接"""
        async with self._lock:
            try:
                if connection_id not in self._connections:
                    return
                
                connection = self._connections[connection_id]
                
                # 清理订阅关系
                for placeholder_id in connection.subscribed_placeholders:
                    self._placeholder_subscribers[placeholder_id].discard(connection_id)
                    if not self._placeholder_subscribers[placeholder_id]:
                        del self._placeholder_subscribers[placeholder_id]
                
                # 清理用户连接映射
                if connection.user_id:
                    self._user_connections[connection.user_id].discard(connection_id)
                    if not self._user_connections[connection.user_id]:
                        del self._user_connections[connection.user_id]
                
                # 清理消息队列
                if connection_id in self._message_queues:
                    del self._message_queues[connection_id]
                
                # 删除连接
                del self._connections[connection_id]
                
                # 更新统计
                self._stats['current_connections'] = len(self._connections)
                self._stats['disconnections'] += 1
                
                logger.info(f"WebSocket连接断开: {connection_id}")
                
            except Exception as e:
                logger.error(f"断开WebSocket连接失败: {e}")
    
    async def subscribe_to_placeholder(self,
                                     connection_id: str,
                                     placeholder_ids: List[str],
                                     data_types: List[str] = None) -> bool:
        """订阅占位符数据"""
        async with self._lock:
            try:
                if connection_id not in self._connections:
                    return False
                
                connection = self._connections[connection_id]
                
                # 更新连接的订阅信息
                connection.subscribed_placeholders.update(placeholder_ids)
                if data_types:
                    connection.subscribed_data_types.update(data_types)
                else:
                    connection.subscribed_data_types.update(['result', 'metric', 'status'])
                
                connection.last_activity = datetime.now()
                
                # 更新占位符订阅者映射
                for placeholder_id in placeholder_ids:
                    self._placeholder_subscribers[placeholder_id].add(connection_id)
                
                logger.info(f"连接 {connection_id} 订阅占位符: {placeholder_ids}")
                
                # 发送订阅确认
                await self._send_message(connection_id, {
                    'type': 'subscription_confirmed',
                    'placeholder_ids': placeholder_ids,
                    'data_types': list(connection.subscribed_data_types),
                    'timestamp': datetime.now().isoformat()
                })
                
                return True
                
            except Exception as e:
                logger.error(f"订阅占位符失败: {e}")
                return False
    
    async def unsubscribe_from_placeholder(self,
                                         connection_id: str,
                                         placeholder_ids: List[str]) -> bool:
        """取消订阅占位符数据"""
        async with self._lock:
            try:
                if connection_id not in self._connections:
                    return False
                
                connection = self._connections[connection_id]
                
                # 更新连接的订阅信息
                connection.subscribed_placeholders.difference_update(placeholder_ids)
                connection.last_activity = datetime.now()
                
                # 更新占位符订阅者映射
                for placeholder_id in placeholder_ids:
                    if placeholder_id in self._placeholder_subscribers:
                        self._placeholder_subscribers[placeholder_id].discard(connection_id)
                        if not self._placeholder_subscribers[placeholder_id]:
                            del self._placeholder_subscribers[placeholder_id]
                
                logger.info(f"连接 {connection_id} 取消订阅占位符: {placeholder_ids}")
                
                # 发送取消订阅确认
                await self._send_message(connection_id, {
                    'type': 'unsubscription_confirmed',
                    'placeholder_ids': placeholder_ids,
                    'timestamp': datetime.now().isoformat()
                })
                
                return True
                
            except Exception as e:
                logger.error(f"取消订阅占位符失败: {e}")
                return False
    
    async def broadcast_data_point(self, data_point) -> int:
        """广播数据点给相关订阅者"""
        async with self._lock:
            if data_point.placeholder_id not in self._placeholder_subscribers:
                return 0
            
            subscriber_ids = self._placeholder_subscribers[data_point.placeholder_id].copy()
            sent_count = 0
            
            message = {
                'type': 'data_point',
                'placeholder_id': data_point.placeholder_id,
                'timestamp': data_point.timestamp.isoformat(),
                'value': data_point.value,
                'data_type': data_point.data_type,
                'metadata': data_point.metadata,
                'source': data_point.source
            }
            
            for connection_id in subscriber_ids:
                if connection_id not in self._connections:
                    continue
                
                connection = self._connections[connection_id]
                
                # 检查数据类型过滤
                if (connection.subscribed_data_types and 
                    data_point.data_type not in connection.subscribed_data_types):
                    continue
                
                # 发送消息
                if await self._send_message(connection_id, message):
                    sent_count += 1
            
            return sent_count
    
    async def broadcast_notification(self, notification) -> int:
        """广播通知"""
        async with self._lock:
            message = {
                'type': 'notification',
                'notification_id': notification.notification_id,
                'title': notification.title,
                'message': notification.message,
                'severity': notification.severity.value,
                'placeholder_id': notification.placeholder_id,
                'created_at': notification.created_at.isoformat(),
                'data': notification.data
            }
            
            sent_count = 0
            
            # 如果通知关联特定占位符，只发送给相关订阅者
            if notification.placeholder_id:
                if notification.placeholder_id in self._placeholder_subscribers:
                    subscriber_ids = self._placeholder_subscribers[notification.placeholder_id].copy()
                    for connection_id in subscriber_ids:
                        if await self._send_message(connection_id, message):
                            sent_count += 1
            else:
                # 广播给所有连接
                for connection_id in self._connections:
                    if await self._send_message(connection_id, message):
                        sent_count += 1
            
            return sent_count
    
    async def send_user_message(self, user_id: str, message: Dict[str, Any]) -> int:
        """发送消息给特定用户的所有连接"""
        async with self._lock:
            if user_id not in self._user_connections:
                return 0
            
            connection_ids = self._user_connections[user_id].copy()
            sent_count = 0
            
            for connection_id in connection_ids:
                if await self._send_message(connection_id, message):
                    sent_count += 1
            
            return sent_count
    
    async def _send_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """发送消息给特定连接"""
        try:
            if connection_id not in self._connections:
                return False
            
            connection = self._connections[connection_id]
            
            # 添加消息到队列
            self._message_queues[connection_id].append(message)
            
            # 发送消息
            await connection.websocket.send_text(json.dumps(message, ensure_ascii=False))
            
            # 更新连接活跃时间
            connection.last_activity = datetime.now()
            
            # 更新统计
            self._stats['messages_sent'] += 1
            
            return True
            
        except WebSocketDisconnect:
            # 连接已断开，清理连接
            await self.disconnect(connection_id)
            return False
        
        except Exception as e:
            logger.error(f"发送WebSocket消息失败 {connection_id}: {e}")
            self._stats['messages_failed'] += 1
            return False
    
    async def handle_client_message(self, connection_id: str, message: Dict[str, Any]):
        """处理客户端消息"""
        try:
            if connection_id not in self._connections:
                return
            
            connection = self._connections[connection_id]
            connection.last_activity = datetime.now()
            
            message_type = message.get('type')
            
            if message_type == 'ping':
                # 心跳响应
                await self._send_message(connection_id, {
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                })
            
            elif message_type == 'subscribe':
                # 订阅请求
                placeholder_ids = message.get('placeholder_ids', [])
                data_types = message.get('data_types')
                await self.subscribe_to_placeholder(connection_id, placeholder_ids, data_types)
            
            elif message_type == 'unsubscribe':
                # 取消订阅请求
                placeholder_ids = message.get('placeholder_ids', [])
                await self.unsubscribe_from_placeholder(connection_id, placeholder_ids)
            
            elif message_type == 'get_subscription_info':
                # 获取订阅信息
                subscription_info = {
                    'type': 'subscription_info',
                    'placeholder_ids': list(connection.subscribed_placeholders),
                    'data_types': list(connection.subscribed_data_types),
                    'connected_at': connection.connected_at.isoformat()
                }
                await self._send_message(connection_id, subscription_info)
            
            else:
                logger.warning(f"未知的客户端消息类型: {message_type}")
        
        except Exception as e:
            logger.error(f"处理客户端消息失败: {e}")
    
    async def _heartbeat_check(self):
        """心跳检查"""
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒检查一次
                await self._check_inactive_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳检查任务出错: {e}")
    
    async def _check_inactive_connections(self):
        """检查不活跃的连接"""
        async with self._lock:
            current_time = datetime.now()
            inactive_connections = []
            
            for connection_id, connection in self._connections.items():
                # 如果连接超过5分钟没有活动，发送ping
                time_since_activity = (current_time - connection.last_activity).total_seconds()
                
                if time_since_activity > 300:  # 5分钟
                    try:
                        await self._send_message(connection_id, {
                            'type': 'ping',
                            'timestamp': current_time.isoformat()
                        })
                    except:
                        # 发送失败，标记为不活跃
                        inactive_connections.append(connection_id)
                
                # 如果连接超过10分钟没有活动，断开连接
                elif time_since_activity > 600:  # 10分钟
                    inactive_connections.append(connection_id)
            
            # 断开不活跃的连接
            for connection_id in inactive_connections:
                await self.disconnect(connection_id)
            
            if inactive_connections:
                logger.info(f"断开了 {len(inactive_connections)} 个不活跃的连接")
    
    async def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """获取连接信息"""
        async with self._lock:
            if connection_id not in self._connections:
                return None
            
            connection = self._connections[connection_id]
            
            return {
                'connection_id': connection.connection_id,
                'user_id': connection.user_id,
                'subscribed_placeholders': list(connection.subscribed_placeholders),
                'subscribed_data_types': list(connection.subscribed_data_types),
                'connected_at': connection.connected_at.isoformat(),
                'last_activity': connection.last_activity.isoformat(),
                'message_queue_size': len(self._message_queues.get(connection_id, []))
            }
    
    async def get_websocket_stats(self) -> Dict[str, Any]:
        """获取WebSocket统计信息"""
        async with self._lock:
            # 按用户统计连接数
            connections_by_user = {}
            for connection in self._connections.values():
                if connection.user_id:
                    connections_by_user[connection.user_id] = connections_by_user.get(connection.user_id, 0) + 1
            
            # 统计订阅分布
            subscription_stats = {}
            for placeholder_id, subscribers in self._placeholder_subscribers.items():
                subscription_stats[placeholder_id] = len(subscribers)
            
            return {
                'total_connections': self._stats['total_connections'],
                'current_connections': self._stats['current_connections'],
                'messages_sent': self._stats['messages_sent'],
                'messages_failed': self._stats['messages_failed'],
                'disconnections': self._stats['disconnections'],
                'max_connections': self.max_connections,
                'connections_by_user': connections_by_user,
                'subscription_stats': subscription_stats,
                'total_message_queues': sum(len(queue) for queue in self._message_queues.values())
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            stats = await self.get_websocket_stats()
            
            health_status = "healthy"
            issues = []
            
            # 检查连接数
            current_connections = stats['current_connections']
            max_connections = stats['max_connections']
            
            if current_connections >= max_connections * 0.9:
                issues.append("连接数接近上限")
                health_status = "warning"
            
            # 检查消息失败率
            total_messages = stats['messages_sent'] + stats['messages_failed']
            if total_messages > 0:
                failure_rate = stats['messages_failed'] / total_messages
                if failure_rate > 0.1:  # 失败率超过10%
                    issues.append(f"消息发送失败率过高: {failure_rate:.2%}")
                    health_status = "warning"
            
            # 检查消息队列积压
            total_queued = stats['total_message_queues']
            if total_queued > 1000:
                issues.append(f"消息队列积压严重: {total_queued}")
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
        """关闭WebSocket管理器"""
        # 取消心跳任务
        if hasattr(self, '_heartbeat_task'):
            self._heartbeat_task.cancel()
        
        # 断开所有连接
        connection_ids = list(self._connections.keys())
        for connection_id in connection_ids:
            await self.disconnect(connection_id)
        
        logger.info("WebSocket管理器已关闭")

# 全局WebSocket管理器实例
_websocket_manager: Optional[WebSocketManager] = None

def get_websocket_manager() -> WebSocketManager:
    """获取全局WebSocket管理器实例"""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager

def initialize_websocket_manager(**kwargs) -> WebSocketManager:
    """初始化全局WebSocket管理器"""
    global _websocket_manager
    _websocket_manager = WebSocketManager(**kwargs)
    return _websocket_manager