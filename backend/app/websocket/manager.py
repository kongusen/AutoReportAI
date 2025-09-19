"""
WebSocket连接管理器
基于DDD v2.0架构的实时通信管理器
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import uuid

from fastapi import WebSocket
from app.core.api_specification import (
    WebSocketMessage, WebSocketMessageType, NotificationMessage,
    TaskUpdateMessage, ReportUpdateMessage
)
from app.services.infrastructure.cache.unified_cache_system import (
    get_cache_manager, cache_get, cache_set, cache_delete, 
    CacheType, CacheLevel
)

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """连接状态"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


class ConnectionInfo:
    """连接信息"""
    
    def __init__(self, websocket: WebSocket, user_id: str, session_id: str):
        self.websocket = websocket
        self.user_id = user_id
        self.session_id = session_id
        self.state = ConnectionState.CONNECTED
        self.connected_at = datetime.utcnow()
        self.last_ping = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        
        # 连接统计
        self.messages_sent = 0
        self.messages_received = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        
        # 客户端信息
        self.client_info: Dict[str, Any] = {}
        self.subscriptions: Set[str] = set()  # 订阅的频道/主题
        
        # 消息队列（离线时暂存）
        self.message_queue: deque = deque(maxlen=100)
        
    @property
    def is_alive(self) -> bool:
        """检查连接是否活跃"""
        return (
            self.state == ConnectionState.AUTHENTICATED and
            datetime.utcnow() - self.last_ping < timedelta(minutes=2)
        )
    
    @property
    def connection_duration(self) -> timedelta:
        """连接持续时间"""
        return datetime.utcnow() - self.connected_at
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "state": self.state.value,
            "connected_at": self.connected_at.isoformat(),
            "last_ping": self.last_ping.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "connection_duration_seconds": self.connection_duration.total_seconds(),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "client_info": self.client_info,
            "subscriptions": list(self.subscriptions),
            "is_alive": self.is_alive
        }


class WebSocketManager:
    """DDD v2.0架构的WebSocket管理器"""
    
    def __init__(self):
        # 连接管理
        self.connections: Dict[str, ConnectionInfo] = {}  # session_id -> ConnectionInfo
        self.user_sessions: Dict[str, Set[str]] = defaultdict(set)  # user_id -> set(session_ids)
        
        # 频道/订阅管理
        self.channels: Dict[str, Set[str]] = defaultdict(set)  # channel -> set(session_ids)
        
        # 消息路由和处理
        self.message_handlers: Dict[WebSocketMessageType, Any] = {}
        self.global_handlers: List[Any] = []
        
        # 统计信息
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "total_messages": 0,
            "total_bytes": 0,
            "uptime": datetime.utcnow()
        }
        
        # 后台任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._started = False
        
        # 不在初始化时启动后台任务，延迟到实际使用时启动
    
    def _start_background_tasks(self):
        """启动后台任务"""
        if self._started:
            return
        try:
            self._cleanup_task = asyncio.create_task(self._cleanup_dead_connections())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
            self._started = True
        except RuntimeError:
            # 如果没有事件循环，暂时跳过
            pass
    
    async def _cleanup_dead_connections(self):
        """清理死连接"""
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒检查一次
                dead_sessions = []
                
                for session_id, conn in self.connections.items():
                    if not conn.is_alive:
                        dead_sessions.append(session_id)
                
                for session_id in dead_sessions:
                    await self._force_disconnect(session_id, "connection_timeout")
                    logger.info(f"Cleaned up dead connection: {session_id}")
                    
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)
    
    async def _heartbeat_monitor(self):
        """心跳监控"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟发送心跳
                
                # 发送心跳给所有活跃连接
                ping_message = WebSocketMessage(
                    type=WebSocketMessageType.PING,
                    data={"timestamp": datetime.utcnow().isoformat()}
                )
                
                await self.broadcast_to_all(ping_message)
                
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(60)
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        session_id: Optional[str] = None,
        client_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """建立WebSocket连接"""
        # 确保后台任务已启动
        self._start_background_tasks()
        
        session_id = session_id or str(uuid.uuid4())
        
        # 创建连接信息
        conn_info = ConnectionInfo(websocket, user_id, session_id)
        if client_info:
            conn_info.client_info = client_info
        
        # 存储连接
        self.connections[session_id] = conn_info
        self.user_sessions[user_id].add(session_id)
        
        # 更新统计
        self.stats["total_connections"] += 1
        self.stats["active_connections"] = len(self.connections)
        
        logger.info(f"WebSocket connected: user={user_id}, session={session_id}")
        
        # 发送连接确认
        welcome_message = NotificationMessage(
            title="Connected",
            message="WebSocket connection established successfully",
            notification_type="success",
            data={
                "session_id": session_id,
                "server_time": datetime.utcnow().isoformat(),
                "capabilities": [
                    "real_time_notifications",
                    "task_updates",
                    "report_status",
                    "system_alerts"
                ]
            }
        )
        
        await self.send_to_session(session_id, welcome_message)
        
        # 发送离线消息
        await self._deliver_offline_messages(session_id)
        
        return session_id
    
    async def authenticate(self, session_id: str, auth_data: Dict[str, Any]) -> bool:
        """认证连接"""
        if session_id not in self.connections:
            return False
        
        conn = self.connections[session_id]
        conn.state = ConnectionState.AUTHENTICATED
        conn.last_activity = datetime.utcnow()
        
        # 处理认证后的订阅
        if "subscriptions" in auth_data:
            for channel in auth_data["subscriptions"]:
                await self.subscribe(session_id, channel)
        
        logger.info(f"WebSocket authenticated: session={session_id}")
        return True
    
    async def disconnect(self, session_id: str, reason: str = "client_disconnect"):
        """断开连接"""
        if session_id not in self.connections:
            return
        
        conn = self.connections[session_id]
        conn.state = ConnectionState.DISCONNECTING
        
        # 清理订阅
        for channel in list(conn.subscriptions):
            await self.unsubscribe(session_id, channel)
        
        # 从用户会话中移除
        self.user_sessions[conn.user_id].discard(session_id)
        if not self.user_sessions[conn.user_id]:
            del self.user_sessions[conn.user_id]
        
        # 移除连接
        del self.connections[session_id]
        
        # 更新统计
        self.stats["active_connections"] = len(self.connections)
        
        logger.info(f"WebSocket disconnected: session={session_id}, reason={reason}")
    
    async def _force_disconnect(self, session_id: str, reason: str = "force_disconnect"):
        """强制断开连接"""
        if session_id in self.connections:
            conn = self.connections[session_id]
            try:
                await conn.websocket.close(code=1000, reason=reason)
            except Exception:
                pass
            await self.disconnect(session_id, reason)
    
    async def send_to_session(self, session_id: str, message: WebSocketMessage) -> bool:
        """发送消息到指定会话"""
        if session_id not in self.connections:
            # 会话不存在，缓存消息
            await self._cache_offline_message(session_id, message)
            return False
        
        conn = self.connections[session_id]
        
        try:
            message_data = json.dumps(message.model_dump(), ensure_ascii=False, default=str)
            await conn.websocket.send_text(message_data)
            
            # 更新统计
            conn.messages_sent += 1
            conn.bytes_sent += len(message_data.encode('utf-8'))
            conn.last_activity = datetime.utcnow()
            
            self.stats["total_messages"] += 1
            self.stats["total_bytes"] += len(message_data.encode('utf-8'))
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to session {session_id}: {e}")
            # 连接异常，标记清理
            conn.state = ConnectionState.DISCONNECTED
            return False
    
    async def send_to_user(self, user_id: str, message: WebSocketMessage) -> int:
        """发送消息到用户的所有会话"""
        if user_id not in self.user_sessions:
            # 用户不在线，缓存消息
            await self._cache_offline_message_for_user(user_id, message)
            return 0
        
        sent_count = 0
        sessions = list(self.user_sessions[user_id])  # 复制以避免并发修改
        
        for session_id in sessions:
            if await self.send_to_session(session_id, message):
                sent_count += 1
        
        return sent_count
    
    async def broadcast_to_channel(self, channel: str, message: WebSocketMessage) -> int:
        """广播消息到频道"""
        if channel not in self.channels:
            return 0
        
        sent_count = 0
        sessions = list(self.channels[channel])  # 复制以避免并发修改
        
        for session_id in sessions:
            if await self.send_to_session(session_id, message):
                sent_count += 1
        
        return sent_count
    
    async def broadcast_to_all(self, message: WebSocketMessage) -> int:
        """广播消息到所有连接"""
        sent_count = 0
        sessions = list(self.connections.keys())  # 复制以避免并发修改
        
        for session_id in sessions:
            if await self.send_to_session(session_id, message):
                sent_count += 1
        
        return sent_count
    
    async def subscribe(self, session_id: str, channel: str) -> bool:
        """订阅频道"""
        if session_id not in self.connections:
            return False
        
        conn = self.connections[session_id]
        conn.subscriptions.add(channel)
        self.channels[channel].add(session_id)
        
        logger.debug(f"Session {session_id} subscribed to channel {channel}")
        return True
    
    async def unsubscribe(self, session_id: str, channel: str) -> bool:
        """取消订阅"""
        if session_id not in self.connections:
            return False
        
        conn = self.connections[session_id]
        conn.subscriptions.discard(channel)
        self.channels[channel].discard(session_id)
        
        # 清理空频道
        if not self.channels[channel]:
            del self.channels[channel]
        
        logger.debug(f"Session {session_id} unsubscribed from channel {channel}")
        return True
    
    async def handle_message(self, session_id: str, message_data: str):
        """处理收到的消息"""
        if session_id not in self.connections:
            return
        
        conn = self.connections[session_id]
        
        try:
            # 解析消息
            raw_message = json.loads(message_data)
            message = WebSocketMessage(**raw_message)
            
            # 更新统计
            conn.messages_received += 1
            conn.bytes_received += len(message_data.encode('utf-8'))
            conn.last_activity = datetime.utcnow()
            
            # 处理特殊消息类型
            if message.type == WebSocketMessageType.PING:
                # 响应pong
                pong_message = WebSocketMessage(
                    type=WebSocketMessageType.PONG,
                    data={"original_id": message.id}
                )
                await self.send_to_session(session_id, pong_message)
                conn.last_ping = datetime.utcnow()
                
            elif message.type == WebSocketMessageType.PONG:
                # 更新ping时间
                conn.last_ping = datetime.utcnow()
            
            # 调用消息处理器
            if message.type in self.message_handlers:
                handler = self.message_handlers[message.type]
                await handler(session_id, message)
            
            # 调用全局处理器
            for handler in self.global_handlers:
                await handler(session_id, message)
                
        except Exception as e:
            logger.error(f"Error handling message from session {session_id}: {e}")
            # 发送错误响应
            error_message = WebSocketMessage(
                type=WebSocketMessageType.ERROR,
                message="Failed to process message",
                data={"error": str(e)}
            )
            await self.send_to_session(session_id, error_message)
    
    async def _cache_offline_message(self, session_id: str, message: WebSocketMessage):
        """缓存离线消息"""
        cache_key = f"offline_messages:session:{session_id}"
        messages = await cache_get(cache_key) or []
        messages.append(message.model_dump())
        await cache_set(
            cache_key, 
            messages, 
            cache_type=CacheType.SYSTEM_CONFIG,
            ttl_seconds=86400,  # 24小时
            cache_level=CacheLevel.REDIS
        )
    
    async def _cache_offline_message_for_user(self, user_id: str, message: WebSocketMessage):
        """为用户缓存离线消息"""
        cache_key = f"offline_messages:user:{user_id}"
        messages = await cache_get(cache_key) or []
        messages.append(message.model_dump())
        await cache_set(
            cache_key, 
            messages, 
            cache_type=CacheType.SYSTEM_CONFIG,
            ttl_seconds=86400,  # 24小时
            cache_level=CacheLevel.REDIS
        )
    
    async def _deliver_offline_messages(self, session_id: str):
        """发送离线消息"""
        if session_id not in self.connections:
            return
        
        conn = self.connections[session_id]
        
        # 发送会话特定的离线消息
        session_cache_key = f"offline_messages:session:{session_id}"
        session_messages = await cache_get(session_cache_key) or []
        
        # 发送用户的离线消息
        user_cache_key = f"offline_messages:user:{conn.user_id}"
        user_messages = await cache_get(user_cache_key) or []
        
        # 合并并排序消息
        all_messages = session_messages + user_messages
        all_messages.sort(key=lambda x: x.get("timestamp", ""))
        
        # 发送消息
        for msg_data in all_messages:
            try:
                offline_message = WebSocketMessage(**msg_data)
                await self.send_to_session(session_id, offline_message)
            except Exception as e:
                logger.error(f"Error delivering offline message: {e}")
        
        # 清理缓存
        await cache_delete(session_cache_key)
        # 用户消息只在第一个会话连接时清理
        if len(self.user_sessions[conn.user_id]) == 1:
            await cache_delete(user_cache_key)
    
    def register_message_handler(self, message_type: WebSocketMessageType, handler):
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
    
    def register_global_handler(self, handler):
        """注册全局消息处理器"""
        self.global_handlers.append(handler)
    
    def get_connection_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取连接信息"""
        if session_id in self.connections:
            return self.connections[session_id].to_dict()
        return None
    
    def get_user_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有连接"""
        if user_id not in self.user_sessions:
            return []
        
        connections = []
        for session_id in self.user_sessions[user_id]:
            if session_id in self.connections:
                connections.append(self.connections[session_id].to_dict())
        
        return connections
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        current_time = datetime.utcnow()
        uptime_seconds = (current_time - self.stats["uptime"]).total_seconds()
        
        # 计算活跃用户数
        active_users = len(self.user_sessions)
        
        # 计算频道统计
        channel_stats = {
            channel: len(sessions) 
            for channel, sessions in self.channels.items()
        }
        
        return {
            "uptime_seconds": uptime_seconds,
            "total_connections": self.stats["total_connections"],
            "active_connections": self.stats["active_connections"],
            "active_users": active_users,
            "total_messages": self.stats["total_messages"],
            "total_bytes": self.stats["total_bytes"],
            "channels": channel_stats,
            "avg_messages_per_connection": (
                self.stats["total_messages"] / max(self.stats["total_connections"], 1)
            )
        }
    
    async def shutdown(self):
        """关闭管理器"""
        logger.info("Shutting down WebSocket manager...")
        
        # 关闭所有连接
        sessions = list(self.connections.keys())
        for session_id in sessions:
            await self._force_disconnect(session_id, "server_shutdown")
        
        # 取消后台任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        logger.info("WebSocket manager shutdown complete")


# 全局管理器实例
websocket_manager = WebSocketManager()