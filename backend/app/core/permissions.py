"""
权限管理系统
提供细粒度的权限控制和角色管理
"""

from typing import Dict, List, Optional, Set
from enum import Enum
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db_session
from app.models.user import User
from app.core.architecture import PermissionLevel, ResourceType, UserRole
from app.core.dependencies import get_current_user


class PermissionChecker:
    """权限检查器"""
    
    def __init__(self, resource_type: ResourceType, permission: PermissionLevel):
        self.resource_type = resource_type
        self.permission = permission
    
    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        """检查用户权限"""
        if current_user.is_superuser:
            return current_user
            
        # 检查用户是否有特定资源的权限
        user_permissions = self._get_user_permissions(current_user.id)
        resource_permission = user_permissions.get(self.resource_type.value, {})
        
        if not resource_permission.get(self.permission.value, False):
            raise HTTPException(
                status_code=403,
                detail=f"用户没有{self.permission.value}权限访问{self.resource_type.value}"
            )
        
        return current_user
    
    def _get_user_permissions(self, user_id: str) -> Dict[str, Dict[str, bool]]:
        """获取用户权限配置"""
        # 这里可以从数据库或缓存中获取用户权限
        # 暂时返回默认权限
        return {
            "user": {"read": True, "write": True, "delete": False},
            "template": {"read": True, "write": True, "delete": True},
            "datasource": {"read": True, "write": True, "delete": False},
            "report": {"read": True, "write": True, "delete": True},
            "task": {"read": True, "write": True, "delete": True},
            "etljob": {"read": True, "write": True, "delete": False},
        }


class ResourceOwnerChecker:
    """资源所有者检查器"""
    
    def __init__(self, resource_type: ResourceType):
        self.resource_type = resource_type
    
    def __call__(
        self,
        resource_id: str,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db_session)
    ) -> User:
        """检查用户是否为资源所有者"""
        if current_user.is_superuser:
            return current_user
            
        # 根据资源类型检查所有权
        is_owner = self._check_resource_ownership(
            db, resource_id, current_user.id, self.resource_type
        )
        
        if not is_owner:
            raise HTTPException(
                status_code=403,
                detail=f"用户不是{self.resource_type.value}的所有者"
            )
        
        return current_user
    
    def _check_resource_ownership(
        self, 
        db: Session, 
        resource_id: str, 
        user_id: str, 
        resource_type: ResourceType
    ) -> bool:
        """检查资源所有权"""
        # 根据资源类型查询数据库
        if resource_type == ResourceType.TEMPLATE:
            from app.models.template import Template
            template = db.query(Template).filter(
                Template.id == resource_id,
                Template.user_id == user_id
            ).first()
            return template is not None
            
        elif resource_type == ResourceType.DATASOURCE:
            from app.models.data_source import DataSource
            data_source = db.query(DataSource).filter(
                DataSource.id == resource_id,
                DataSource.user_id == user_id
            ).first()
            return data_source is not None
            
        elif resource_type == ResourceType.TASK:
            from app.models.task import Task
            task = db.query(Task).filter(
                Task.id == resource_id,
                Task.owner_id == user_id
            ).first()
            return task is not None
            
        elif resource_type == ResourceType.ETLJOB:
            from app.models.etl_job import ETLJob
            etl_job = db.query(ETLJob).filter(
                ETLJob.id == resource_id,
                ETLJob.user_id == user_id
            ).first()
            return etl_job is not None
            
        return False


class RoleBasedPermission:
    """基于角色的权限管理"""
    
    ROLE_PERMISSIONS = {
        UserRole.SUPERUSER: {
            ResourceType.USER: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE, PermissionLevel.ADMIN],
            ResourceType.TEMPLATE: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE, PermissionLevel.ADMIN],
            ResourceType.DATASOURCE: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE, PermissionLevel.ADMIN],
            ResourceType.REPORT: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE, PermissionLevel.ADMIN],
            ResourceType.TASK: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE, PermissionLevel.ADMIN],
            ResourceType.ETLJOB: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE, PermissionLevel.ADMIN],
        },
        UserRole.ADMIN: {
            ResourceType.USER: [PermissionLevel.READ, PermissionLevel.WRITE],
            ResourceType.TEMPLATE: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE],
            ResourceType.DATASOURCE: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE],
            ResourceType.REPORT: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE],
            ResourceType.TASK: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE],
            ResourceType.ETLJOB: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE],
        },
        UserRole.USER: {
            ResourceType.USER: [PermissionLevel.READ, PermissionLevel.WRITE],
            ResourceType.TEMPLATE: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE],
            ResourceType.DATASOURCE: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE],
            ResourceType.REPORT: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE],
            ResourceType.TASK: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE],
            ResourceType.ETLJOB: [PermissionLevel.READ, PermissionLevel.WRITE],
        },
        UserRole.GUEST: {
            ResourceType.USER: [PermissionLevel.READ],
            ResourceType.TEMPLATE: [PermissionLevel.READ],
            ResourceType.DATASOURCE: [PermissionLevel.READ],
            ResourceType.REPORT: [PermissionLevel.READ],
            ResourceType.TASK: [PermissionLevel.READ],
            ResourceType.ETLJOB: [PermissionLevel.READ],
        }
    }
    
    @classmethod
    def has_permission(
        cls, 
        user_role: UserRole, 
        resource_type: ResourceType, 
        permission: PermissionLevel
    ) -> bool:
        """检查角色是否有特定权限"""
        role_permissions = cls.ROLE_PERMISSIONS.get(user_role, {})
        resource_permissions = role_permissions.get(resource_type, [])
        return permission in resource_permissions
    
    @classmethod
    def get_user_permissions(cls, user_role: UserRole) -> Dict[str, List[str]]:
        """获取角色的所有权限"""
        role_permissions = cls.ROLE_PERMISSIONS.get(user_role, {})
        return {
            resource_type.value: [perm.value for perm in permissions]
            for resource_type, permissions in role_permissions.items()
        }


# 快捷权限检查函数
def require_permission(resource_type: ResourceType, permission: PermissionLevel):
    """要求特定权限的装饰器"""
    return PermissionChecker(resource_type, permission)


def require_owner(resource_type: ResourceType):
    """要求资源所有权的装饰器"""
    return ResourceOwnerChecker(resource_type)


def require_role(role: UserRole):
    """要求特定角色的装饰器"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.is_superuser and role != UserRole.USER:
            raise HTTPException(
                status_code=403,
                detail=f"需要{role.value}角色"
            )
        return current_user
    return role_checker


# 权限缓存
class PermissionCache:
    """权限缓存管理"""
    
    def __init__(self):
        self._cache = {}
        self._ttl = 300  # 5分钟缓存
    
    def get_user_permissions(self, user_id: str) -> Optional[Dict[str, List[str]]]:
        """获取用户权限缓存"""
        return self._cache.get(user_id)
    
    def set_user_permissions(self, user_id: str, permissions: Dict[str, List[str]]):
        """设置用户权限缓存"""
        self._cache[user_id] = permissions
    
    def invalidate_user_permissions(self, user_id: str):
        """使权限缓存失效"""
        self._cache.pop(user_id, None)


# 全局权限缓存实例
permission_cache = PermissionCache()
