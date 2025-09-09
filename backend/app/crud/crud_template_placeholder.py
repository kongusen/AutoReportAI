"""
Template Placeholder CRUD操作
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.crud.base import CRUDBase
from app.models.template_placeholder import TemplatePlaceholder
from app.schemas.template_placeholder import TemplatePlaceholderCreate, TemplatePlaceholderUpdate


class CRUDTemplatePlaceholder(
    CRUDBase[TemplatePlaceholder, TemplatePlaceholderCreate, TemplatePlaceholderUpdate]
):
    """模板占位符CRUD操作类"""
    
    def get_by_template(
        self, 
        db: Session, 
        template_id: str,
        include_inactive: bool = False
    ) -> List[TemplatePlaceholder]:
        """根据模板ID获取所有占位符"""
        query = db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.template_id == template_id
        )
        
        if not include_inactive:
            query = query.filter(TemplatePlaceholder.is_active == True)
        
        return query.order_by(TemplatePlaceholder.execution_order).all()
    
    def get_by_template_and_name(
        self,
        db: Session,
        template_id: str,
        name: str
    ) -> Optional[TemplatePlaceholder]:
        """根据模板ID和占位符名称获取占位符"""
        return db.query(TemplatePlaceholder).filter(
            and_(
                TemplatePlaceholder.template_id == template_id,
                TemplatePlaceholder.placeholder_name == name
            )
        ).first()
    
    def get_by_content_hash(
        self,
        db: Session,
        template_id: str,
        content_hash: str
    ) -> Optional[TemplatePlaceholder]:
        """根据内容hash获取占位符（用于去重）"""
        return db.query(TemplatePlaceholder).filter(
            and_(
                TemplatePlaceholder.template_id == template_id,
                TemplatePlaceholder.content_hash == content_hash
            )
        ).first()
    
    def delete_by_template(
        self,
        db: Session,
        template_id: str
    ) -> int:
        """删除模板的所有占位符"""
        count = db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.template_id == template_id
        ).count()
        
        db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.template_id == template_id
        ).delete()
        
        db.commit()
        return count
    
    def get_analyzed_placeholders(
        self,
        db: Session,
        template_id: str
    ) -> List[TemplatePlaceholder]:
        """获取已分析的占位符"""
        return db.query(TemplatePlaceholder).filter(
            and_(
                TemplatePlaceholder.template_id == template_id,
                TemplatePlaceholder.agent_analyzed == True,
                TemplatePlaceholder.is_active == True
            )
        ).order_by(TemplatePlaceholder.execution_order).all()
    
    def get_pending_analysis(
        self,
        db: Session,
        template_id: str
    ) -> List[TemplatePlaceholder]:
        """获取待分析的占位符"""
        return db.query(TemplatePlaceholder).filter(
            and_(
                TemplatePlaceholder.template_id == template_id,
                TemplatePlaceholder.agent_analyzed == False,
                TemplatePlaceholder.is_active == True
            )
        ).order_by(TemplatePlaceholder.execution_order).all()
    
    def get_sql_validated(
        self,
        db: Session,
        template_id: str
    ) -> List[TemplatePlaceholder]:
        """获取SQL已验证的占位符"""
        return db.query(TemplatePlaceholder).filter(
            and_(
                TemplatePlaceholder.template_id == template_id,
                TemplatePlaceholder.sql_validated == True,
                TemplatePlaceholder.is_active == True
            )
        ).order_by(TemplatePlaceholder.execution_order).all()
    
    def bulk_update_analysis_status(
        self,
        db: Session,
        placeholder_ids: List[str],
        analyzed: bool = True
    ) -> int:
        """批量更新分析状态"""
        from sqlalchemy.sql import func
        
        count = db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.id.in_(placeholder_ids)
        ).update(
            {
                TemplatePlaceholder.agent_analyzed: analyzed,
                TemplatePlaceholder.analyzed_at: func.now() if analyzed else None
            },
            synchronize_session=False
        )
        
        db.commit()
        return count
    
    def get_execution_ready(
        self,
        db: Session,
        template_id: str
    ) -> List[TemplatePlaceholder]:
        """获取可执行的占位符（已分析且SQL已验证）"""
        return db.query(TemplatePlaceholder).filter(
            and_(
                TemplatePlaceholder.template_id == template_id,
                TemplatePlaceholder.agent_analyzed == True,
                TemplatePlaceholder.sql_validated == True,
                TemplatePlaceholder.is_active == True,
                TemplatePlaceholder.generated_sql.isnot(None)
            )
        ).order_by(TemplatePlaceholder.execution_order).all()


# 创建实例
template_placeholder = CRUDTemplatePlaceholder(TemplatePlaceholder)