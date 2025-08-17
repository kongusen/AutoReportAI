"""
Placeholder Configuration Service

占位符配置管理服务，提供占位符的配置和管理功能
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.template_placeholder import TemplatePlaceholder

logger = logging.getLogger(__name__)


class PlaceholderConfigService:
    """占位符配置服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_placeholder_configs(
        self, 
        template_id: str,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """获取模板的占位符配置"""
        try:
            query = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.template_id == template_id
            )
            
            if not include_inactive:
                query = query.filter(TemplatePlaceholder.is_active == True)
            
            placeholders = query.order_by(TemplatePlaceholder.execution_order).all()
            
            return [
                {
                    "id": str(p.id),
                    "name": p.placeholder_name,
                    "text": p.placeholder_text,
                    "type": p.placeholder_type,
                    "content_type": p.content_type,
                    "agent_analyzed": p.agent_analyzed,
                    "target_database": p.target_database,
                    "target_table": p.target_table,
                    "required_fields": p.required_fields,
                    "generated_sql": p.generated_sql,
                    "sql_validated": p.sql_validated,
                    "confidence_score": p.confidence_score,
                    "execution_order": p.execution_order,
                    "cache_ttl_hours": p.cache_ttl_hours,
                    "agent_config": p.agent_config,
                    "is_active": p.is_active,
                    "analyzed_at": p.analyzed_at.isoformat() if p.analyzed_at else None,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                }
                for p in placeholders
            ]
            
        except Exception as e:
            logger.error(f"获取占位符配置失败: {template_id}, 错误: {str(e)}")
            return []
    
    async def update_placeholder_config(
        self,
        placeholder_id: str,
        config_updates: Dict[str, Any]
    ) -> bool:
        """更新占位符配置"""
        try:
            placeholder = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == placeholder_id
            ).first()
            
            if not placeholder:
                logger.error(f"占位符不存在: {placeholder_id}")
                return False
            
            # 更新允许的字段
            allowed_fields = [
                'placeholder_name', 'placeholder_text', 'placeholder_type',
                'content_type', 'execution_order', 'cache_ttl_hours',
                'agent_config', 'is_active'
            ]
            
            for field, value in config_updates.items():
                if field in allowed_fields and hasattr(placeholder, field):
                    setattr(placeholder, field, value)
            
            self.db.commit()
            logger.info(f"占位符配置更新成功: {placeholder_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新占位符配置失败: {placeholder_id}, 错误: {str(e)}")
            return False
    
    async def delete_placeholder_config(self, placeholder_id: str) -> bool:
        """删除占位符配置（软删除）"""
        try:
            placeholder = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == placeholder_id
            ).first()
            
            if not placeholder:
                logger.error(f"占位符不存在: {placeholder_id}")
                return False
            
            # 软删除：设置为非活跃
            placeholder.is_active = False
            self.db.commit()
            
            logger.info(f"占位符配置删除成功: {placeholder_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除占位符配置失败: {placeholder_id}, 错误: {str(e)}")
            return False