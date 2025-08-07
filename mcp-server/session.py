"""
Session Management for AutoReportAI MCP Server
处理用户会话、认证状态和token管理
"""

import asyncio
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from config import config

@dataclass
class UserSession:
    """用户会话数据"""
    user_id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    access_token: str
    refresh_token: Optional[str] = None
    created_at: float = None
    last_activity: float = None
    permissions: list = None
    
    def __post_init__(self):
        current_time = time.time()
        if self.created_at is None:
            self.created_at = current_time
        if self.last_activity is None:
            self.last_activity = current_time
        if self.permissions is None:
            self.permissions = []
    
    def is_expired(self) -> bool:
        """检查会话是否过期"""
        return (time.time() - self.last_activity) > config.SESSION_TIMEOUT
    
    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "permissions": self.permissions,
            "is_expired": self.is_expired()
        }

class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        self._sessions: Dict[str, UserSession] = {}
        self._current_session_id: Optional[str] = None
        self._cleanup_task = None
    
    async def start_cleanup_task(self):
        """启动清理过期会话的后台任务"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
    
    async def stop_cleanup_task(self):
        """停止清理任务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def _cleanup_expired_sessions(self):
        """定期清理过期会话"""
        while True:
            try:
                expired_sessions = [
                    session_id for session_id, session in self._sessions.items()
                    if session.is_expired()
                ]
                
                for session_id in expired_sessions:
                    del self._sessions[session_id]
                    if self._current_session_id == session_id:
                        self._current_session_id = None
                
                # 每分钟清理一次
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"清理会话时出错: {e}")
                await asyncio.sleep(60)
    
    def create_session(self, user_data: Dict[str, Any], access_token: str) -> str:
        """创建新会话"""
        # 检查会话数量限制
        if len(self._sessions) >= config.MAX_SESSIONS:
            # 删除最旧的会话
            oldest_session_id = min(
                self._sessions.keys(),
                key=lambda sid: self._sessions[sid].created_at
            )
            del self._sessions[oldest_session_id]
        
        # 创建会话ID
        session_id = f"session_{user_data.get('id', 'unknown')}_{int(time.time())}"
        
        # 创建会话对象
        session = UserSession(
            user_id=str(user_data.get("id", "")),
            username=user_data.get("username", ""),
            email=user_data.get("email"),
            full_name=user_data.get("full_name"),
            access_token=access_token,
            permissions=user_data.get("permissions", [])
        )
        
        self._sessions[session_id] = session
        self._current_session_id = session_id
        
        return session_id
    
    def get_session(self, session_id: str = None) -> Optional[UserSession]:
        """获取会话"""
        if session_id is None:
            session_id = self._current_session_id
        
        if not session_id or session_id not in self._sessions:
            return None
        
        session = self._sessions[session_id]
        
        # 检查是否过期
        if session.is_expired():
            del self._sessions[session_id]
            if self._current_session_id == session_id:
                self._current_session_id = None
            return None
        
        # 更新活动时间
        session.update_activity()
        return session
    
    def get_current_session(self) -> Optional[UserSession]:
        """获取当前活跃会话"""
        return self.get_session()
    
    def switch_session(self, session_id: str) -> bool:
        """切换到指定会话"""
        if session_id in self._sessions and not self._sessions[session_id].is_expired():
            self._current_session_id = session_id
            self._sessions[session_id].update_activity()
            return True
        return False
    
    def remove_session(self, session_id: str = None) -> bool:
        """删除会话"""
        if session_id is None:
            session_id = self._current_session_id
        
        if session_id and session_id in self._sessions:
            del self._sessions[session_id]
            if self._current_session_id == session_id:
                self._current_session_id = None
            return True
        return False
    
    def list_sessions(self) -> Dict[str, Dict[str, Any]]:
        """列出所有活跃会话"""
        active_sessions = {}
        for session_id, session in self._sessions.items():
            if not session.is_expired():
                active_sessions[session_id] = session.to_dict()
        return active_sessions
    
    def get_session_count(self) -> int:
        """获取活跃会话数量"""
        return len([s for s in self._sessions.values() if not s.is_expired()])
    
    def clear_all_sessions(self):
        """清空所有会话"""
        self._sessions.clear()
        self._current_session_id = None
    
    def has_permission(self, permission: str, session_id: str = None) -> bool:
        """检查用户权限"""
        session = self.get_session(session_id)
        if not session:
            return False
        return permission in session.permissions
    
    def is_admin(self, session_id: str = None) -> bool:
        """检查是否为管理员"""
        return self.has_permission("admin", session_id)

# 全局会话管理器实例
session_manager = SessionManager()