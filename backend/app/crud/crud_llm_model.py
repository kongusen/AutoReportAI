"""
LLM模型CRUD操作
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.crud.base import CRUDBase
from app.models.llm_server import LLMModel, LLMServer, ModelType
from app.schemas.llm_server import LLMModelCreate, LLMModelUpdate


class CRUDLLMModel(CRUDBase[LLMModel, LLMModelCreate, LLMModelUpdate]):
    """LLM模型CRUD操作"""
    
    def get_by_server(self, db: Session, *, server_id: int) -> List[LLMModel]:
        """获取指定服务器的所有模型"""
        return db.query(self.model).filter(
            LLMModel.server_id == server_id
        ).order_by(LLMModel.priority.asc(), LLMModel.name.asc()).all()
    
    def get_active_by_server(self, db: Session, *, server_id: int) -> List[LLMModel]:
        """获取指定服务器的所有活跃模型"""
        return db.query(self.model).filter(
            and_(
                LLMModel.server_id == server_id,
                LLMModel.is_active == True
            )
        ).order_by(LLMModel.priority.asc(), LLMModel.name.asc()).all()

    def get_active_models(self, db: Session) -> List[LLMModel]:
        """获取所有活跃模型"""
        return db.query(self.model).filter(
            LLMModel.is_active == True
        ).order_by(LLMModel.priority.asc(), LLMModel.name.asc()).all()
    
    def get_by_name_and_server(
        self, 
        db: Session, 
        *, 
        server_id: int, 
        model_name: str
    ) -> Optional[LLMModel]:
        """根据服务器ID和模型名称获取模型"""
        return db.query(self.model).filter(
            and_(
                LLMModel.server_id == server_id,
                LLMModel.name == model_name
            )
        ).first()
    
    def get_by_type(
        self, 
        db: Session, 
        *, 
        model_type: ModelType,
        is_active: bool = True
    ) -> List[LLMModel]:
        """根据模型类型获取模型列表"""
        query = db.query(self.model).filter(LLMModel.model_type == model_type)
        
        if is_active:
            query = query.filter(LLMModel.is_active == True)
        
        return query.order_by(LLMModel.priority.asc(), LLMModel.name.asc()).all()
    
    def get_thinking_models(self, db: Session, *, is_active: bool = True) -> List[LLMModel]:
        """获取支持思考模式的模型"""
        query = db.query(self.model).filter(LLMModel.supports_thinking == True)
        
        if is_active:
            query = query.filter(LLMModel.is_active == True)
        
        return query.order_by(LLMModel.priority.asc(), LLMModel.name.asc()).all()
    
    def get_by_provider(
        self, 
        db: Session, 
        *, 
        provider_name: str,
        is_active: bool = True
    ) -> List[LLMModel]:
        """根据提供商获取模型列表"""
        query = db.query(self.model).filter(LLMModel.provider_name == provider_name)
        
        if is_active:
            query = query.filter(LLMModel.is_active == True)
        
        return query.order_by(LLMModel.priority.asc(), LLMModel.name.asc()).all()
    
    def get_healthy_models(self, db: Session, *, server_id: Optional[int] = None) -> List[LLMModel]:
        """获取健康的模型列表"""
        query = db.query(self.model).filter(
            and_(
                LLMModel.is_active == True,
                LLMModel.is_healthy == True
            )
        )
        
        if server_id:
            query = query.filter(LLMModel.server_id == server_id)
        
        return query.order_by(LLMModel.priority.asc(), LLMModel.name.asc()).all()
    
    def get_models_by_filter(
        self,
        db: Session,
        *,
        server_id: Optional[int] = None,
        model_type: Optional[ModelType] = None,
        provider_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_healthy: Optional[bool] = None,
        supports_thinking: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[LLMModel]:
        """根据多个条件筛选模型"""
        query = db.query(self.model)
        
        if server_id is not None:
            query = query.filter(LLMModel.server_id == server_id)
        
        if model_type is not None:
            query = query.filter(LLMModel.model_type == model_type)
        
        if provider_name is not None:
            query = query.filter(LLMModel.provider_name == provider_name)
        
        if is_active is not None:
            query = query.filter(LLMModel.is_active == is_active)
        
        if is_healthy is not None:
            query = query.filter(LLMModel.is_healthy == is_healthy)
        
        if supports_thinking is not None:
            query = query.filter(LLMModel.supports_thinking == supports_thinking)
        
        return query.order_by(
            LLMModel.priority.asc(), 
            LLMModel.name.asc()
        ).offset(skip).limit(limit).all()
    
    def update_health_status(
        self,
        db: Session,
        *,
        model_id: int,
        is_healthy: bool,
        health_message: Optional[str] = None
    ) -> Optional[LLMModel]:
        """更新模型健康状态"""
        model = self.get(db, id=model_id)
        if model:
            model.is_healthy = is_healthy
            model.last_health_check = datetime.utcnow()
            if health_message:
                model.health_check_message = health_message
            db.commit()
            db.refresh(model)
        return model
    
    def get_model_stats(self, db: Session, *, server_id: Optional[int] = None) -> Dict[str, Any]:
        """获取模型统计信息"""
        query = db.query(self.model)
        
        if server_id:
            query = query.filter(LLMModel.server_id == server_id)
        
        total_models = query.count()
        active_models = query.filter(LLMModel.is_active == True).count()
        healthy_models = query.filter(
            and_(LLMModel.is_active == True, LLMModel.is_healthy == True)
        ).count()
        
        # 按类型统计
        type_stats = db.query(
            LLMModel.model_type,
            func.count(LLMModel.id).label('count')
        ).group_by(LLMModel.model_type)
        
        if server_id:
            type_stats = type_stats.filter(LLMModel.server_id == server_id)
        
        type_distribution = {
            str(row.model_type): row.count 
            for row in type_stats.all()
        }
        
        # 按提供商统计
        provider_stats = db.query(
            LLMModel.provider_name,
            func.count(LLMModel.id).label('count')
        ).group_by(LLMModel.provider_name)
        
        if server_id:
            provider_stats = provider_stats.filter(LLMModel.server_id == server_id)
        
        provider_distribution = {
            row.provider_name: row.count 
            for row in provider_stats.all()
        }
        
        return {
            "total_models": total_models,
            "active_models": active_models,
            "healthy_models": healthy_models,
            "health_rate": healthy_models / active_models if active_models > 0 else 0.0,
            "type_distribution": type_distribution,
            "provider_distribution": provider_distribution
        }
    
    def batch_update_health(
        self,
        db: Session,
        *,
        model_ids: List[int],
        is_healthy: bool,
        health_message: Optional[str] = None
    ) -> int:
        """批量更新模型健康状态"""
        update_data = {
            "is_healthy": is_healthy,
            "last_health_check": datetime.utcnow()
        }
        
        if health_message:
            update_data["health_check_message"] = health_message
        
        result = db.query(self.model).filter(
            LLMModel.id.in_(model_ids)
        ).update(update_data, synchronize_session=False)
        
        db.commit()
        return result
    
    def activate_models(self, db: Session, *, model_ids: List[int]) -> int:
        """批量激活模型"""
        result = db.query(self.model).filter(
            LLMModel.id.in_(model_ids)
        ).update({"is_active": True}, synchronize_session=False)
        
        db.commit()
        return result
    
    def deactivate_models(self, db: Session, *, model_ids: List[int]) -> int:
        """批量停用模型"""
        result = db.query(self.model).filter(
            LLMModel.id.in_(model_ids)
        ).update({"is_active": False}, synchronize_session=False)
        
        db.commit()
        return result


crud_llm_model = CRUDLLMModel(LLMModel)