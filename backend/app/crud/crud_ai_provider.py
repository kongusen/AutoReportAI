from typing import Any, Dict, Union

from sqlalchemy.orm import Session

from app.core.security_utils import encrypt_data
from app.crud.base import CRUDBase
from app.models.ai_provider import AIProvider
from app.schemas.ai_provider import AIProviderCreate, AIProviderUpdate


class CRUDAIProvider(CRUDBase[AIProvider, AIProviderCreate, AIProviderUpdate]):
    def create(self, db: Session, *, obj_in: AIProviderCreate) -> AIProvider:
        # Convert the Pydantic model to a dictionary
        obj_in_data = obj_in.model_dump()

        # Convert HttpUrl to string if present
        if "api_base_url" in obj_in_data and obj_in_data["api_base_url"]:
            obj_in_data["api_base_url"] = str(obj_in_data["api_base_url"])

        # Encrypt the api_key if it is provided
        if obj_in_data.get("api_key"):
            obj_in_data["api_key"] = encrypt_data(obj_in_data["api_key"])

        # Create the database model instance
        db_obj = self.model(**obj_in_data)

        # Add to session, commit, and refresh
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: AIProvider,
        obj_in: Union[AIProviderUpdate, Dict[str, Any]],
    ) -> AIProvider:
        # Determine if the input is a Pydantic model or a dict
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # Encrypt the api_key if it is being updated
        if update_data.get("api_key"):
            update_data["api_key"] = encrypt_data(update_data["api_key"])

        # Call the parent update method with the modified data
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def get_active(self, db: Session) -> AIProvider | None:
        return db.query(self.model).filter(self.model.is_active == 1).first()

    def get_by_provider_name(self, db: Session, *, name: str) -> AIProvider | None:
        return db.query(self.model).filter(self.model.provider_name == name).first()


ai_provider = CRUDAIProvider(AIProvider)
