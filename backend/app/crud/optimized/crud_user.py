"""
优化的用户CRUD操作
"""

from typing import List, Optional, Union
from uuid import UUID
from sqlalchemy.orm import Session

from app.crud.base_optimized import CRUDWithSearch
from app.models.optimized.user import User, UserStatus, UserRole
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDWithSearch[User, UserCreate, UserUpdate]):
    """用户CRUD操作类"""
    
    def __init__(self):
        super().__init__(User, search_fields=["username", "email", "full_name"])
    
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return db.query(self.model).filter(
            self.model.email == email,
            self.model.is_deleted == False
        ).first()
    
    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return db.query(self.model).filter(
            self.model.username == username,
            self.model.is_deleted == False
        ).first()
    
    def get_by_role(
        self,
        db: Session,
        *,
        role: UserRole,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """根据角色获取用户"""
        return db.query(self.model).filter(
            self.model.role == role,
            self.model.is_deleted == False
        ).offset(skip).limit(limit).all()
    
    def get_by_status(
        self,
        db: Session,
        *,
        status: UserStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """根据状态获取用户"""
        return db.query(self.model).filter(
            self.model.status == status,
            self.model.is_deleted == False
        ).offset(skip).limit(limit).all()
    
    def get_active_users(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """获取活跃用户"""
        return db.query(self.model).filter(
            self.model.is_active == True,
            self.model.status == UserStatus.ACTIVE,
            self.model.is_deleted == False
        ).offset(skip).limit(limit).all()
    
    def get_admins(self, db: Session) -> List[User]:
        """获取管理员用户"""
        return db.query(self.model).filter(
            self.model.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN]),
            self.model.is_deleted == False
        ).all()
    
    def authenticate(
        self,
        db: Session,
        *,
        email: str,
        password: str
    ) -> Optional[User]:
        """用户认证"""
        from app.core.security import verify_password
        
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user
    
    def create_user(
        self,
        db: Session,
        *,
        user_create: UserCreate,
        created_by: Union[UUID, str] = None
    ) -> User:
        """创建用户"""
        from app.core.security import get_password_hash
        
        # 检查邮箱和用户名唯一性
        if self.get_by_email(db, email=user_create.email):
            raise ValueError(f"邮箱 {user_create.email} 已存在")
        
        if self.get_by_username(db, username=user_create.username):
            raise ValueError(f"用户名 {user_create.username} 已存在")
        
        # 创建用户对象
        user_data = user_create.dict()
        user_data["hashed_password"] = get_password_hash(user_create.password)
        del user_data["password"]  # 移除明文密码
        
        if created_by:
            if isinstance(created_by, str):
                created_by = UUID(created_by)
            user_data["created_by"] = created_by
        
        db_user = self.model(**user_data)
        
        try:
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            return db_user
        except Exception as e:
            db.rollback()
            raise ValueError(f"创建用户失败: {str(e)}")
    
    def update_password(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str],
        new_password: str
    ) -> Optional[User]:
        """更新用户密码"""
        from app.core.security import get_password_hash
        
        user = self.get(db, id=user_id)
        if not user:
            return None
        
        user.hashed_password = get_password_hash(new_password)
        user.password_reset_token = None  # 清除重置令牌
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    def verify_email(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str],
        verification_token: str = None
    ) -> Optional[User]:
        """验证用户邮箱"""
        user = self.get(db, id=user_id)
        if not user:
            return None
        
        # 如果提供了验证令牌，需要匹配
        if verification_token and user.email_verification_token != verification_token:
            return None
        
        user.is_verified = True
        user.email_verification_token = None
        
        # 如果用户状态是待验证，更新为活跃
        if user.status == UserStatus.PENDING_VERIFICATION:
            user.status = UserStatus.ACTIVE
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    def set_user_preference(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str],
        key: str,
        value
    ) -> Optional[User]:
        """设置用户偏好"""
        user = self.get(db, id=user_id)
        if not user:
            return None
        
        user.set_preference(key, value)
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    def deactivate_user(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str],
        reason: str = None
    ) -> Optional[User]:
        """停用用户"""
        user = self.get(db, id=user_id)
        if not user:
            return None
        
        user.is_active = False
        user.status = UserStatus.INACTIVE
        
        if reason and user.metadata:
            if not user.metadata:
                user.metadata = {}
            user.metadata["deactivation_reason"] = reason
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    def get_user_statistics(self, db: Session) -> dict:
        """获取用户统计信息"""
        base_query = db.query(self.model).filter(self.model.is_deleted == False)
        
        stats = {
            "total": base_query.count(),
            "active": base_query.filter(self.model.is_active == True).count(),
            "verified": base_query.filter(self.model.is_verified == True).count(),
            "by_role": {},
            "by_status": {}
        }
        
        # 按角色统计
        for role in UserRole:
            count = base_query.filter(self.model.role == role).count()
            if count > 0:
                stats["by_role"][role.value] = count
        
        # 按状态统计
        for status in UserStatus:
            count = base_query.filter(self.model.status == status).count()
            if count > 0:
                stats["by_status"][status.value] = count
        
        return stats


# 创建CRUD实例
crud_user = CRUDUser()