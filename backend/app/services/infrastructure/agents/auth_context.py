"""用户认证上下文管理器（沿用旧实现，供兼容层使用）。"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class UserAuthContext:
    user_id: str
    username: Optional[str] = None
    roles: Optional[list] = None
    permissions: Optional[list] = None
    tenant_id: Optional[str] = None
    organization_id: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

    def has_permission(self, permission: str) -> bool:
        if not self.permissions:
            return False
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        if not self.roles:
            return False
        return role in self.roles


class AuthContextManager:
    def __init__(self) -> None:
        self._current_context: Optional[UserAuthContext] = None

    def set_context(self, auth_context: UserAuthContext) -> None:
        self._current_context = auth_context

    def get_context(self) -> Optional[UserAuthContext]:
        return self._current_context

    def clear_context(self) -> None:
        self._current_context = None

    def get_current_user_id(self) -> Optional[str]:
        if self._current_context:
            return self._current_context.user_id
        return None

    def require_authentication(self) -> UserAuthContext:
        if not self._current_context:
            raise ValueError("用户未认证，请先设置认证上下文")
        return self._current_context


auth_manager = AuthContextManager()


__all__ = [
    "UserAuthContext",
    "AuthContextManager",
    "auth_manager",
]
