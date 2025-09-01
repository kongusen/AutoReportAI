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
    
    def get_multi_with_total(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> tuple[List[ModelType], int]:
        """优化的分页查询：智能获取数据和总数"""
        items = db.query(self.model).offset(skip).limit(limit).all()
        
        # 智能计算总数：如果首页且返回数量少于limit，则无需查询count
        if len(items) < limit and skip == 0:
            total = len(items)
        else:
            total = db.query(self.model).count()
            
        return items, total
    
    def exists(self, db: Session, *, id: Union[int, str]) -> bool:
        """高效检查记录是否存在"""
        import uuid
        pk_type = self.model.id.type.python_type
        if pk_type is uuid.UUID and isinstance(id, str):
            try:
                id = uuid.UUID(id)
            except Exception:
                pass
        return db.query(db.query(self.model).filter(self.model.id == id).exists()).scalar()
    
    def bulk_create(self, db: Session, *, objs_in: List[CreateSchemaType]) -> List[ModelType]:
        """批量创建记录以提高性能"""
        db_objs = []
        for obj_in in objs_in:
            if isinstance(obj_in, dict):
                obj_in_data = obj_in
            else:
                obj_in_data = obj_in.model_dump()
            db_objs.append(self.model(**obj_in_data))
        
        db.add_all(db_objs)
        db.commit()
        for obj in db_objs:
            db.refresh(obj)
        return db_objs
