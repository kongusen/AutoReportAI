from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: Union[int, str]) -> Optional[ModelType]:
        import uuid
        print(f"[DEBUG] CRUDBase.get: input id={id}, type={type(id)}")
        pk_type = self.model.id.type.python_type
        if pk_type is uuid.UUID and isinstance(id, str):
            try:
                id = uuid.UUID(id)
            except Exception:
                pass
        print(f"[DEBUG] CRUDBase.get: after convert id={id}, type={type(id)}")
        result = db.query(self.model).filter(self.model.id == id).first()
        print(f"[DEBUG] CRUDBase.get: result user.id={getattr(result, 'id', None)}, type={type(getattr(result, 'id', None))}")
        return result

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def count(self, db: Session) -> int:
        """Get total count of records."""
        return db.query(self.model).count()

    def create(
        self, db: Session, *, obj_in: CreateSchemaType, **extra_data
    ) -> ModelType:
        # 支持传入 Pydantic 模型或原始字典
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()
        obj_in_data.update(extra_data)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        for field in update_data:
            setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: Union[int, str]) -> ModelType:
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
