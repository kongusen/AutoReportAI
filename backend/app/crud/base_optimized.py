"""
优化的CRUD基础类
提供统一的数据库操作接口
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.base_class_optimized import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=PydanticBaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=PydanticBaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """基础CRUD类"""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    def get(self, db: Session, id: Union[UUID, str]) -> Optional[ModelType]:
        """根据ID获取单个对象"""
        if isinstance(id, str):
            id = UUID(id)
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[ModelType]:
        """获取多个对象"""
        query = db.query(self.model)
        
        # 软删除过滤
        if hasattr(self.model, 'is_deleted') and not include_deleted:
            query = query.filter(self.model.is_deleted == False)
        
        return query.offset(skip).limit(limit).all()
    
    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """创建对象"""
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"数据完整性错误: {str(e)}")
        except Exception as e:
            db.rollback()
            raise ValueError(f"创建失败: {str(e)}")
    
    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """更新对象"""
        obj_data = jsonable_encoder(db_obj)
        
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        # 版本控制
        if hasattr(db_obj, 'increment_version'):
            db_obj.increment_version()
        
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"数据完整性错误: {str(e)}")
        except Exception as e:
            db.rollback()
            raise ValueError(f"更新失败: {str(e)}")
    
    def remove(self, db: Session, *, id: Union[UUID, str], soft: bool = True) -> ModelType:
        """删除对象"""
        obj = self.get(db, id=id)
        if not obj:
            raise ValueError("对象不存在")
        
        if soft and hasattr(obj, 'soft_delete'):
            # 软删除
            obj.soft_delete()
            db.add(obj)
            db.commit()
            db.refresh(obj)
        else:
            # 硬删除
            db.delete(obj)
            db.commit()
        
        return obj
    
    def restore(self, db: Session, *, id: Union[UUID, str]) -> Optional[ModelType]:
        """恢复软删除的对象"""
        obj = db.query(self.model).filter(
            self.model.id == id,
            self.model.is_deleted == True
        ).first()
        
        if obj and hasattr(obj, 'restore'):
            obj.restore()
            db.add(obj)
            db.commit()
            db.refresh(obj)
            return obj
        
        return None
    
    def count(self, db: Session, *, include_deleted: bool = False) -> int:
        """计数"""
        query = db.query(self.model)
        
        if hasattr(self.model, 'is_deleted') and not include_deleted:
            query = query.filter(self.model.is_deleted == False)
        
        return query.count()
    
    def exists(self, db: Session, *, id: Union[UUID, str]) -> bool:
        """检查对象是否存在"""
        return self.get(db, id=id) is not None


class CRUDUserOwned(CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]):
    """用户拥有的资源CRUD类"""
    
    def get_by_user(
        self, 
        db: Session, 
        *, 
        user_id: Union[UUID, str],
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """获取用户的资源"""
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        query = db.query(self.model).filter(self.model.user_id == user_id)
        
        if hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        return query.offset(skip).limit(limit).all()
    
    def get_by_user_and_id(
        self, 
        db: Session, 
        *, 
        user_id: Union[UUID, str],
        id: Union[UUID, str]
    ) -> Optional[ModelType]:
        """获取用户的特定资源"""
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        if isinstance(id, str):
            id = UUID(id)
        
        query = db.query(self.model).filter(
            self.model.user_id == user_id,
            self.model.id == id
        )
        
        if hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        return query.first()
    
    def create_with_user(
        self, 
        db: Session, 
        *, 
        obj_in: CreateSchemaType, 
        user_id: Union[UUID, str]
    ) -> ModelType:
        """创建用户拥有的资源"""
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        obj_in_data = jsonable_encoder(obj_in)
        obj_in_data['user_id'] = user_id
        
        # 设置创建者
        if hasattr(self.model, 'created_by'):
            obj_in_data['created_by'] = user_id
        
        db_obj = self.model(**obj_in_data)
        
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"数据完整性错误: {str(e)}")
        except Exception as e:
            db.rollback()
            raise ValueError(f"创建失败: {str(e)}")
    
    def count_by_user(self, db: Session, *, user_id: Union[UUID, str]) -> int:
        """统计用户的资源数量"""
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        query = db.query(self.model).filter(self.model.user_id == user_id)
        
        if hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        return query.count()


class CRUDWithSearch(CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]):
    """支持搜索的CRUD类"""
    
    def __init__(self, model: Type[ModelType], search_fields: List[str] = None):
        super().__init__(model)
        self.search_fields = search_fields or []
    
    def search(
        self,
        db: Session,
        *,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """搜索对象"""
        db_query = db.query(self.model)
        
        if hasattr(self.model, 'is_deleted'):
            db_query = db_query.filter(self.model.is_deleted == False)
        
        if query and self.search_fields:
            from sqlalchemy import or_
            search_conditions = []
            
            for field in self.search_fields:
                if hasattr(self.model, field):
                    attr = getattr(self.model, field)
                    search_conditions.append(attr.ilike(f"%{query}%"))
            
            if search_conditions:
                db_query = db_query.filter(or_(*search_conditions))
        
        return db_query.offset(skip).limit(limit).all()


# 组合CRUD类
class CRUDComplete(CRUDUserOwned[ModelType, CreateSchemaType, UpdateSchemaType], CRUDWithSearch[ModelType, CreateSchemaType, UpdateSchemaType]):
    """完整功能的CRUD类"""
    
    def __init__(self, model: Type[ModelType], search_fields: List[str] = None):
        CRUDUserOwned.__init__(self, model)
        CRUDWithSearch.__init__(self, model, search_fields)