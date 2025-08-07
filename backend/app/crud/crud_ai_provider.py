from app.crud.base import CRUDBase
from app.models.ai_provider import AIProvider
from app.schemas.ai_provider import AIProviderCreate, AIProviderUpdate
from sqlalchemy.orm import Session


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


crud_ai_provider = CRUDAIProvider(AIProvider)
