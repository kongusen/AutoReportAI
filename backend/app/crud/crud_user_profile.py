from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user_profile import UserProfile
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate


class CRUDUserProfile:
    def get_by_user_id(self, db: Session, user_id: UUID) -> UserProfile | None:
        """根据用户ID获取用户配置"""
        return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    def create(
        self, db: Session, obj_in: UserProfileCreate, user_id: UUID
    ) -> UserProfile:
        """创建用户配置"""
        db_obj = UserProfile(**obj_in.model_dump(), user_id=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, db_obj: UserProfile, obj_in: UserProfileUpdate
    ) -> UserProfile:
        """更新用户配置"""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_or_create(self, db: Session, user_id: UUID) -> UserProfile:
        """获取或创建用户配置"""
        profile = self.get_by_user_id(db, user_id)
        if not profile:
            profile = self.create(db, UserProfileCreate(), user_id)
        return profile


user_profile = CRUDUserProfile()
