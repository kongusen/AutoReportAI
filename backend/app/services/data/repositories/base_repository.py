from __future__ import annotations

import asyncio
import logging
from typing import Generic, TypeVar, Optional, List, Dict, Any, Union, Callable
from sqlalchemy.orm import Session, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, text, desc, asc
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RepositoryInterface(ABC, Generic[T]):
    """Repository接口定义"""
    
    @abstractmethod
    async def get_by_id(self, id_: Any) -> Optional[T]:
        """通过ID获取实体"""
        pass
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """创建实体"""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """更新实体"""
        pass
    
    @abstractmethod
    async def delete(self, id_: Any) -> bool:
        """删除实体"""
        pass
    
    @abstractmethod
    async def list(self, **filters) -> List[T]:
        """列出实体"""
        pass


class BaseRepository(RepositoryInterface[T]):
    """增强的基础Repository实现"""
    
    def __init__(self, session: Session, model_cls: type):
        self.session = session
        self.model_cls = model_cls
        self.logger = logging.getLogger(f"{__name__}.{model_cls.__name__}Repository")
    
    async def get_by_id(self, id_: Any) -> Optional[T]:
        """通过ID获取实体"""
        try:
            return self.session.query(self.model_cls).filter(self.model_cls.id == id_).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Error getting {self.model_cls.__name__} by id {id_}: {e}")
            return None
    
    async def create(self, entity: T) -> T:
        """创建实体"""
        try:
            self.session.add(entity)
            self.session.flush()  # 获取ID但不提交
            return entity
        except SQLAlchemyError as e:
            self.logger.error(f"Error creating {self.model_cls.__name__}: {e}")
            self.session.rollback()
            raise
    
    async def update(self, entity: T) -> T:
        """更新实体"""
        try:
            # 更新时间戳（如果实体有该字段）
            if hasattr(entity, 'updated_at'):
                entity.updated_at = datetime.utcnow()
            
            merged_entity = self.session.merge(entity)
            self.session.flush()
            return merged_entity
        except SQLAlchemyError as e:
            self.logger.error(f"Error updating {self.model_cls.__name__}: {e}")
            self.session.rollback()
            raise
    
    async def delete(self, id_: Any) -> bool:
        """删除实体"""
        try:
            entity = await self.get_by_id(id_)
            if entity:
                self.session.delete(entity)
                self.session.flush()
                return True
            return False
        except SQLAlchemyError as e:
            self.logger.error(f"Error deleting {self.model_cls.__name__} with id {id_}: {e}")
            self.session.rollback()
            raise
    
    async def soft_delete(self, id_: Any) -> bool:
        """软删除（如果实体支持）"""
        try:
            entity = await self.get_by_id(id_)
            if entity and hasattr(entity, 'is_deleted'):
                entity.is_deleted = True
                if hasattr(entity, 'deleted_at'):
                    entity.deleted_at = datetime.utcnow()
                await self.update(entity)
                return True
            return False
        except SQLAlchemyError as e:
            self.logger.error(f"Error soft deleting {self.model_cls.__name__} with id {id_}: {e}")
            raise
    
    async def list(self, 
                  limit: int = 100, 
                  offset: int = 0, 
                  order_by: str = None,
                  desc_order: bool = False,
                  filters: Dict[str, Any] = None,
                  include_deleted: bool = False) -> List[T]:
        """列出实体"""
        try:
            query = self.session.query(self.model_cls)
            
            # 应用过滤器
            if filters:
                query = self._apply_filters(query, filters)
            
            # 排除软删除的记录（如果支持）
            if not include_deleted and hasattr(self.model_cls, 'is_deleted'):
                query = query.filter(self.model_cls.is_deleted != True)
            
            # 应用排序
            if order_by:
                if hasattr(self.model_cls, order_by):
                    order_col = getattr(self.model_cls, order_by)
                    query = query.order_by(desc(order_col) if desc_order else asc(order_col))
            
            # 应用分页
            return query.offset(offset).limit(limit).all()
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error listing {self.model_cls.__name__}: {e}")
            raise
    
    async def count(self, filters: Dict[str, Any] = None, include_deleted: bool = False) -> int:
        """计数实体"""
        try:
            query = self.session.query(self.model_cls)
            
            if filters:
                query = self._apply_filters(query, filters)
            
            if not include_deleted and hasattr(self.model_cls, 'is_deleted'):
                query = query.filter(self.model_cls.is_deleted != True)
            
            return query.count()
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error counting {self.model_cls.__name__}: {e}")
            raise
    
    async def exists(self, **filters) -> bool:
        """检查实体是否存在"""
        try:
            query = self.session.query(self.model_cls)
            query = self._apply_filters(query, filters)
            return query.first() is not None
        except SQLAlchemyError as e:
            self.logger.error(f"Error checking existence of {self.model_cls.__name__}: {e}")
            return False
    
    async def find_one(self, **filters) -> Optional[T]:
        """查找单个实体"""
        try:
            query = self.session.query(self.model_cls)
            query = self._apply_filters(query, filters)
            return query.first()
        except SQLAlchemyError as e:
            self.logger.error(f"Error finding {self.model_cls.__name__}: {e}")
            return None
    
    async def find_many(self, **filters) -> List[T]:
        """查找多个实体"""
        return await self.list(filters=filters)
    
    async def bulk_create(self, entities: List[T]) -> List[T]:
        """批量创建实体"""
        try:
            self.session.add_all(entities)
            self.session.flush()
            return entities
        except SQLAlchemyError as e:
            self.logger.error(f"Error bulk creating {self.model_cls.__name__}: {e}")
            self.session.rollback()
            raise
    
    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """批量更新实体"""
        try:
            result = self.session.bulk_update_mappings(self.model_cls, updates)
            return result.rowcount
        except SQLAlchemyError as e:
            self.logger.error(f"Error bulk updating {self.model_cls.__name__}: {e}")
            self.session.rollback()
            raise
    
    def _apply_filters(self, query: Query, filters: Dict[str, Any]) -> Query:
        """应用查询过滤器"""
        for key, value in filters.items():
            if hasattr(self.model_cls, key):
                column = getattr(self.model_cls, key)
                
                if isinstance(value, dict):
                    # 支持复杂查询操作
                    for op, op_value in value.items():
                        if op == 'eq':
                            query = query.filter(column == op_value)
                        elif op == 'ne':
                            query = query.filter(column != op_value)
                        elif op == 'gt':
                            query = query.filter(column > op_value)
                        elif op == 'gte':
                            query = query.filter(column >= op_value)
                        elif op == 'lt':
                            query = query.filter(column < op_value)
                        elif op == 'lte':
                            query = query.filter(column <= op_value)
                        elif op == 'in':
                            query = query.filter(column.in_(op_value))
                        elif op == 'like':
                            query = query.filter(column.like(f"%{op_value}%"))
                        elif op == 'ilike':
                            query = query.filter(column.ilike(f"%{op_value}%"))
                elif isinstance(value, list):
                    # IN查询
                    query = query.filter(column.in_(value))
                else:
                    # 简单相等查询
                    query = query.filter(column == value)
        
        return query
    
    async def execute_raw_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """执行原生SQL查询"""
        try:
            result = self.session.execute(text(query), params or {})
            return [dict(row) for row in result]
        except SQLAlchemyError as e:
            self.logger.error(f"Error executing raw query: {e}")
            raise
    
    def get_query(self) -> Query:
        """获取基础查询对象，用于复杂查询"""
        return self.session.query(self.model_cls)


class TransactionalRepository(BaseRepository[T]):
    """支持事务的Repository"""
    
    async def with_transaction(self, func: Callable, *args, **kwargs):
        """在事务中执行操作"""
        try:
            result = await func(self, *args, **kwargs)
            self.session.commit()
            return result
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Transaction failed: {e}")
            raise
    
    async def create_and_commit(self, entity: T) -> T:
        """创建并提交事务"""
        return await self.with_transaction(self.create, entity)
    
    async def update_and_commit(self, entity: T) -> T:
        """更新并提交事务"""
        return await self.with_transaction(self.update, entity)
    
    async def delete_and_commit(self, id_: Any) -> bool:
        """删除并提交事务"""
        return await self.with_transaction(self.delete, id_)


