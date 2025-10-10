"""
生产级认证提供器
基于真实数据库的用户认证和权限管理
"""

from typing import Optional, List
from sqlalchemy.orm import Session
import logging

from .auth_context import UserAuthContext
from app.crud.crud_user import crud_user
from app.db.session import SessionLocal
from app.core.security import decode_access_token


logger = logging.getLogger(__name__)


class ProductionAuthProvider:
    """生产级认证提供器"""

    def __init__(self):
        """初始化认证提供器"""
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_auth_context_by_token(self, token: str) -> Optional[UserAuthContext]:
        """
        根据JWT令牌获取认证上下文

        Args:
            token: JWT令牌

        Returns:
            UserAuthContext或None
        """
        try:
            # 解析JWT令牌
            payload = decode_access_token(token)
            if not payload:
                return None

            user_id = payload.get("sub")  # JWT标准字段
            if not user_id:
                return None

            return self.get_auth_context_by_user_id(user_id)

        except Exception as e:
            self.logger.warning(f"JWT解析失败: {e}")
            return None

    def get_auth_context_by_user_id(self, user_id: str) -> Optional[UserAuthContext]:
        """
        根据用户ID获取认证上下文

        Args:
            user_id: 用户UUID

        Returns:
            UserAuthContext或None
        """
        db: Optional[Session] = None
        try:
            db = SessionLocal()

            # 从数据库获取用户信息
            user = crud_user.get(db, id=user_id)
            if not user or not user.is_active:
                return None

            # 构建用户权限列表
            permissions = self._build_user_permissions(user)

            # 构建用户角色列表
            roles = self._build_user_roles(user)

            return UserAuthContext(
                user_id=str(user.id),
                username=user.username,
                roles=roles,
                permissions=permissions,
                tenant_id=None,  # 如果有租户系统，可以从用户关联获取
                organization_id=None,  # 如果有组织系统，可以从用户关联获取
                preferences={
                    "full_name": user.full_name,
                    "email": user.email,
                    "is_superuser": user.is_superuser,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
            )

        except Exception as e:
            self.logger.error(f"获取用户认证上下文失败 (user_id: {user_id}): {e}")
            return None
        finally:
            if db is not None:
                db.close()

    def get_auth_context_by_session(self, session_id: str) -> Optional[UserAuthContext]:
        """
        根据会话ID获取认证上下文（如果使用会话认证）

        Args:
            session_id: 会话ID

        Returns:
            UserAuthContext或None
        """
        # 这里可以实现基于会话的认证
        # 如果您的系统使用Redis会话存储，可以在这里实现
        try:
            # 示例：从Redis或其他会话存储获取用户ID
            # user_id = get_user_id_from_session(session_id)
            # return self.get_auth_context_by_user_id(user_id)

            # 暂时返回None，由子类或具体实现处理
            return None
        except Exception as e:
            self.logger.error(f"会话认证失败 (session_id: {session_id}): {e}")
            return None

    def _build_user_permissions(self, user) -> List[str]:
        """
        构建用户权限列表

        Args:
            user: 用户对象

        Returns:
            权限列表
        """
        permissions = []

        # 基础权限
        if user.is_active:
            permissions.extend([
                "user.login",
                "agent.use",  # Agent使用权限
                "data.read"   # 数据读取权限
            ])

        # 超级用户权限
        if user.is_superuser:
            permissions.extend([
                "admin.access",
                "user.manage",
                "data.write",
                "data.delete",
                "system.configure",
                "agent.admin"
            ])

        # 根据用户数据源数量给予SQL执行权限
        if hasattr(user, 'data_sources') and user.data_sources:
            permissions.append("sql.execute")

        # 如果用户有LLM偏好配置，给予LLM使用权限
        if hasattr(user, 'llm_preference') and user.llm_preference:
            permissions.append("llm.use")

        return permissions

    def _build_user_roles(self, user) -> List[str]:
        """
        构建用户角色列表

        Args:
            user: 用户对象

        Returns:
            角色列表
        """
        roles = []

        # 基础角色
        if user.is_active:
            roles.append("user")

        # 管理员角色
        if user.is_superuser:
            roles.append("admin")
            roles.append("super_admin")

        # 根据用户资源判断角色
        if hasattr(user, 'data_sources') and user.data_sources:
            roles.append("data_analyst")

        if hasattr(user, 'templates') and user.templates:
            roles.append("template_creator")

        return roles

    def validate_permission(self, user_id: str, permission: str) -> bool:
        """
        验证用户是否有指定权限

        Args:
            user_id: 用户ID
            permission: 权限名

        Returns:
            是否有权限
        """
        auth_context = self.get_auth_context_by_user_id(user_id)
        if not auth_context:
            return False

        return auth_context.has_permission(permission)

    def validate_role(self, user_id: str, role: str) -> bool:
        """
        验证用户是否有指定角色

        Args:
            user_id: 用户ID
            role: 角色名

        Returns:
            是否有角色
        """
        auth_context = self.get_auth_context_by_user_id(user_id)
        if not auth_context:
            return False

        return auth_context.has_role(role)


# 创建全局实例
production_auth_provider = ProductionAuthProvider()