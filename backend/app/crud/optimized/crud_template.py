"""
优化的模板CRUD操作
"""

from typing import List, Optional, Union
from uuid import UUID
from sqlalchemy.orm import Session

from app.crud.base_optimized import CRUDComplete
from app.models.optimized.template import Template, TemplateType, TemplateStatus, TemplateCategory
from app.schemas.template import TemplateCreate, TemplateUpdate


class CRUDTemplate(CRUDComplete[Template, TemplateCreate, TemplateUpdate]):
    """模板CRUD操作类"""
    
    def __init__(self):
        super().__init__(Template, search_fields=["name", "description"])
    
    def get_by_type(
        self,
        db: Session,
        *,
        template_type: TemplateType,
        user_id: Union[UUID, str] = None,
        include_public: bool = True
    ) -> List[Template]:
        """根据类型获取模板"""
        query = db.query(self.model).filter(
            self.model.template_type == template_type,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            if include_public:
                # 包含用户自己的和公开的模板
                query = query.filter(
                    (self.model.user_id == user_id) | (self.model.is_public == True)
                )
            else:
                query = query.filter(self.model.user_id == user_id)
        elif not include_public:
            # 如果没有指定用户且不包含公开模板，返回空
            return []
        
        return query.all()
    
    def get_public_templates(
        self,
        db: Session,
        *,
        template_type: TemplateType = None,
        category: TemplateCategory = None
    ) -> List[Template]:
        """获取公开模板"""
        query = db.query(self.model).filter(
            self.model.is_public == True,
            self.model.status == TemplateStatus.ACTIVE,
            self.model.is_deleted == False
        )
        
        if template_type:
            query = query.filter(self.model.template_type == template_type)
        
        if category:
            query = query.filter(self.model.category == category)
        
        return query.all()
    
    def get_featured_templates(self, db: Session) -> List[Template]:
        """获取推荐模板"""
        return db.query(self.model).filter(
            self.model.is_featured == True,
            self.model.status == TemplateStatus.ACTIVE,
            self.model.is_deleted == False
        ).all()
    
    def get_validated_templates(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> List[Template]:
        """获取已验证的模板"""
        query = db.query(self.model).filter(
            self.model.is_validated == True,
            self.model.status == TemplateStatus.ACTIVE,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.all()
    
    def increment_usage(
        self,
        db: Session,
        *,
        template_id: Union[UUID, str]
    ) -> Optional[Template]:
        """增加模板使用次数"""
        template = self.get(db, id=template_id)
        if not template:
            return None
        
        template.increment_usage()
        
        db.add(template)
        db.commit()
        db.refresh(template)
        
        return template
    
    def validate_template(
        self,
        db: Session,
        *,
        template_id: Union[UUID, str]
    ) -> Optional[dict]:
        """验证模板"""
        template = self.get(db, id=template_id)
        if not template:
            return None
        
        validation_result = template.validate_template()
        
        db.add(template)
        db.commit()
        db.refresh(template)
        
        return validation_result
    
    def publish_template(
        self,
        db: Session,
        *,
        template_id: Union[UUID, str],
        make_public: bool = False
    ) -> Optional[Template]:
        """发布模板"""
        template = self.get(db, id=template_id)
        if not template:
            return None
        
        # 先验证模板
        validation_result = template.validate_template()
        if not validation_result["is_valid"]:
            raise ValueError(f"模板验证失败: {validation_result['errors']}")
        
        template.status = TemplateStatus.ACTIVE
        if make_public:
            template.is_public = True
        
        db.add(template)
        db.commit()
        db.refresh(template)
        
        return template
    
    def search_by_tags(
        self,
        db: Session,
        *,
        tags: List[str],
        user_id: Union[UUID, str] = None
    ) -> List[Template]:
        """根据标签搜索模板"""
        query = db.query(self.model).filter(self.model.is_deleted == False)
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(
                (self.model.user_id == user_id) | (self.model.is_public == True)
            )
        else:
            query = query.filter(self.model.is_public == True)
        
        # 使用JSON操作符查询包含指定标签的模板
        for tag in tags:
            query = query.filter(self.model.tags.contains([tag]))
        
        return query.all()
    
    def get_template_statistics(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> dict:
        """获取模板统计信息"""
        base_query = db.query(self.model).filter(self.model.is_deleted == False)
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            base_query = base_query.filter(self.model.user_id == user_id)
        
        stats = {
            "total": base_query.count(),
            "active": base_query.filter(self.model.status == TemplateStatus.ACTIVE).count(),
            "public": base_query.filter(self.model.is_public == True).count(),
            "validated": base_query.filter(self.model.is_validated == True).count(),
            "by_type": {},
            "by_category": {}
        }
        
        # 按类型统计
        for template_type in TemplateType:
            count = base_query.filter(self.model.template_type == template_type).count()
            if count > 0:
                stats["by_type"][template_type.value] = count
        
        # 按分类统计
        for category in TemplateCategory:
            count = base_query.filter(self.model.category == category).count()
            if count > 0:
                stats["by_category"][category.value] = count
        
        return stats


# 创建CRUD实例
crud_template = CRUDTemplate()