"""
用户认证上下文管理器
用于Agent系统与外部认证系统集成
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class UserAuthContext:
    """用户认证上下文"""
    user_id: str
    username: Optional[str] = None
    roles: Optional[list] = None
    permissions: Optional[list] = None
    tenant_id: Optional[str] = None
    organization_id: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

    def has_permission(self, permission: str) -> bool:
        """检查用户是否有指定权限"""
        if not self.permissions:
            return False
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        """检查用户是否有指定角色"""
        if not self.roles:
            return False
        return role in self.roles


class AuthContextManager:
    """认证上下文管理器"""

    def __init__(self):
        self._current_context: Optional[UserAuthContext] = None

    def set_context(self, auth_context: UserAuthContext) -> None:
        """设置当前认证上下文"""
        self._current_context = auth_context

    def get_context(self) -> Optional[UserAuthContext]:
        """获取当前认证上下文"""
        return self._current_context

    def clear_context(self) -> None:
        """清除认证上下文"""
        self._current_context = None

    def get_current_user_id(self) -> Optional[str]:
        """获取当前用户ID"""
        if self._current_context:
            return self._current_context.user_id
        return None

    def require_authentication(self) -> UserAuthContext:
        """要求认证，如果未认证则抛出异常"""
        if not self._current_context:
            raise ValueError("用户未认证，请先设置认证上下文")
        return self._current_context


# 全局认证上下文管理器实例
auth_manager = AuthContextManager()