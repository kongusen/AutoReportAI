from typing import Any, Dict, Optional, Union

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        import uuid
        db_obj = User(
            id=uuid.uuid4(),
            username=obj_in.username,
            email=obj_in.email,
            full_name=obj_in.full_name,
            hashed_password=get_password_hash(obj_in.password),
            is_active=obj_in.is_active,
            is_superuser=obj_in.is_superuser,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        print(f"[DEBUG] Created user.id={db_obj.id}, type={type(db_obj.id)}")
        return db_obj

    def update(
        self, db: Session, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password

        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def authenticate(
        self, db: Session, *, username: str, password: str
    ) -> Optional[User]:
        # 支持用户名或邮箱登录
        user = self.get_by_username(db, username=username)
        if not user:
            user = self.get_by_email(db, email=username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        return user.is_active

    def is_superuser(self, user: User) -> bool:
        return user.is_superuser

    def update_password(self, db: Session, *, user_id: str, new_password: str) -> User:
        """更新用户密码"""
        import uuid
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        
        user_obj = db.query(User).filter(User.id == user_id).first()
        if not user_obj:
            raise ValueError("用户不存在")
        
        user_obj.hashed_password = get_password_hash(new_password)
        db.commit()
        db.refresh(user_obj)
        return user_obj
    
    def get_count(self, db: Session) -> int:
        """获取所有用户总数"""
        return db.query(User).count()


crud_user = CRUDUser(User)
