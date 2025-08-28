"""
LLM服务器CRUD操作
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.crud.base import CRUDBase
from app.models.llm_server import LLMServer, LLMModel
from app.schemas.llm_server import LLMServerCreate, LLMServerUpdate


class CRUDLLMServer(CRUDBase[LLMServer, LLMServerCreate, LLMServerUpdate]):
    """LLM服务器CRUD操作"""
    
    def get_by_server_id(self, db: Session, server_id: str) -> Optional[LLMServer]:
        """通过server_id获取服务器"""
        return db.query(self.model).filter(self.model.server_id == server_id).first()
    
    def get_active_servers(self, db: Session) -> List[LLMServer]:
        """获取所有活跃的服务器"""
        return db.query(self.model).filter(self.model.is_active == True).all()
    
    def get_healthy_servers(self, db: Session) -> List[LLMServer]:
        """获取所有健康的服务器"""
        return db.query(self.model).filter(
            and_(
                self.model.is_active == True,
                self.model.is_healthy == True
            )
        ).all()
    
    def get_by_base_url(self, db: Session, base_url: str) -> Optional[LLMServer]:
        """通过base_url获取服务器"""
        return db.query(self.model).filter(self.model.base_url == base_url).first()
    
    def get_servers_with_provider(self, db: Session, provider_name: str) -> List[LLMServer]:
        """获取支持特定提供商的服务器"""
        return db.query(self.model).join(LLMModel).filter(
            and_(
                self.model.is_active == True,
                LLMModel.provider_name == provider_name,
                LLMModel.is_active == True
            )
        ).distinct().all()
    
    def get_multi_by_filter(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100, 
        **filters
    ) -> List[LLMServer]:
        """根据过滤条件获取服务器列表"""
        query = db.query(self.model)
        
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def get_server_stats(self, db: Session, server_id: int) -> Dict[str, Any]:
        """获取服务器统计信息"""
        # 获取模型数量和健康状态
        from sqlalchemy import Integer
        models_stats = db.query(
            func.count(LLMModel.id).label("total_models"),
            func.sum(func.cast(LLMModel.is_healthy, Integer)).label("healthy_models")
        ).filter(
            LLMModel.server_id == server_id
        ).first()
        
        total_models = models_stats.total_models or 0
        healthy_models = models_stats.healthy_models or 0
        health_rate = (healthy_models / total_models * 100.0) if total_models > 0 else 0.0
        
        return {
            "models_count": total_models,
            "healthy_models_count": healthy_models,
            "health_rate": health_rate
        }

    def update_health_status(
        self, 
        db: Session, 
        server_id: int, 
        is_healthy: bool, 
        version: Optional[str] = None
    ) -> Optional[LLMServer]:
        """更新服务器健康状态"""
        server = self.get(db, id=server_id)
        if server:
            server.is_healthy = is_healthy
            server.last_health_check = datetime.utcnow()
            if version:
                server.server_version = version
            db.commit()
            db.refresh(server)
        return server
    
    def count(self, db: Session) -> int:
        """获取服务器总数"""
        return db.query(func.count(self.model.id)).scalar() or 0
    
    def activate_servers(self, db: Session, *, server_ids: List[int]) -> int:
        """批量激活服务器"""
        result = db.query(self.model).filter(
            self.model.id.in_(server_ids)
        ).update({"is_active": True}, synchronize_session=False)
        
        db.commit()
        return result
    
    def deactivate_servers(self, db: Session, *, server_ids: List[int]) -> int:
        """批量停用服务器"""
        result = db.query(self.model).filter(
            self.model.id.in_(server_ids)
        ).update({"is_active": False}, synchronize_session=False)
        
        db.commit()
        return result


# 创建CRUD实例
crud_llm_server = CRUDLLMServer(LLMServer)