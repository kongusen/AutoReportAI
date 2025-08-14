from typing import List, Optional
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.ai_provider import AIProvider
from app.schemas.ai_provider import AIProviderCreate, AIProviderUpdate


class CRUDAIProvider(CRUDBase[AIProvider, AIProviderCreate, AIProviderUpdate]):
    def create_with_user(
        self, db: Session, *, obj_in: AIProviderCreate, user_id: str
    ) -> AIProvider:
        obj_in_data = obj_in.dict()
        db_obj = self.model(**obj_in_data, user_id=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_by_user_id(self, db: Session, *, user_id: str) -> List[AIProvider]:
        """获取特定用户的所有AI提供商"""
        return db.query(self.model).filter(self.model.user_id == user_id).all()
    
    def get_active_by_user_id(self, db: Session, *, user_id: str) -> Optional[AIProvider]:
        """获取特定用户的激活AI提供商"""
        return db.query(self.model).filter(
            self.model.user_id == user_id,
            self.model.is_active == True
        ).first()
    
    def get_active(self, db: Session) -> Optional[AIProvider]:
        """获取系统中任意一个激活的AI提供商（用于系统级别回退）"""
        return db.query(self.model).filter(self.model.is_active == True).first()
    
    def get_all_active(self, db: Session) -> List[AIProvider]:
        """获取所有激活的AI提供商"""
        return db.query(self.model).filter(self.model.is_active == True).all()
    
    def get_all(self, db: Session) -> List[AIProvider]:
        """获取所有AI提供商"""
        return db.query(self.model).all()
    
    def activate_provider(self, db: Session, *, provider_id: int, user_id: str) -> Optional[AIProvider]:
        """激活特定用户的AI提供商，同时停用该用户的其他提供商"""
        # 先停用该用户的所有提供商
        db.query(self.model).filter(self.model.user_id == user_id).update(
            {self.model.is_active: False}
        )
        
        # 激活指定的提供商
        provider = db.query(self.model).filter(
            self.model.id == provider_id,
            self.model.user_id == user_id
        ).first()
        
        if provider:
            provider.is_active = True
            db.commit()
            db.refresh(provider)
            
        return provider


crud_ai_provider = CRUDAIProvider(AIProvider)
