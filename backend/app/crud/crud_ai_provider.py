from app.crud.base import CRUDBase
from app.models.ai_provider import AIProvider
from app.schemas.ai_provider import AIProviderCreate, AIProviderUpdate
from sqlalchemy.orm import Session

class CRUDAIProvider(CRUDBase[AIProvider, AIProviderCreate, AIProviderUpdate]):
    def get_active(self, db: Session) -> AIProvider | None:
        return db.query(self.model).filter(self.model.is_active == 1).first()

    def get_by_provider_name(self, db: Session, *, name: str) -> AIProvider | None:
        return db.query(self.model).filter(self.model.provider_name == name).first()

ai_provider = CRUDAIProvider(AIProvider) 