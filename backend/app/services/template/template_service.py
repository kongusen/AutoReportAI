"""
Template Service

Central service for template management, integrating with placeholder configuration
and cache management for optimized performance.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.template import Template
from app.models.user import User
from .placeholder_config_service import PlaceholderConfigService
from .template_parser import EnhancedTemplateParser
from .template_cache_service import TemplateCacheService

logger = logging.getLogger(__name__)


class TemplateService:
    """模板管理核心服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.placeholder_service = PlaceholderConfigService(db)
        self.parser = EnhancedTemplateParser()
        self.cache_service = TemplateCacheService(db)
        
    async def create_template(
        self,
        user_id: UUID,
        name: str,
        content: str,
        description: str = None,
        is_public: bool = False,
        auto_generate_placeholders: bool = True
    ) -> Tuple[Template, Dict[str, Any]]:
        """
        创建新模板并自动配置占位符
        
        Returns:
            Tuple[Template, Dict]: (模板对象, 占位符分析结果)
        """
        try:
            logger.info(f"创建模板: {name}, 用户: {user_id}")
            
            # 1. 创建模板记录
            template = Template(
                id=uuid4(),
                user_id=user_id,
                name=name,
                content=content,
                description=description,
                is_public=is_public,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.db.add(template)
            self.db.flush()  # 获取模板ID，但不提交事务
            
            # 2. 解析模板内容，提取占位符
            placeholder_analysis = {}
            if auto_generate_placeholders and content:
                placeholder_analysis = await self._analyze_and_create_placeholders(
                    template.id, content
                )
            
            # 3. 提交事务
            self.db.commit()
            
            logger.info(f"模板创建成功: {template.id}, 占位符数量: {placeholder_analysis.get('total_placeholders', 0)}")
            
            return template, placeholder_analysis
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"模板创建失败: {str(e)}")
            raise
    
    async def update_template(
        self,
        template_id: UUID,
        user_id: UUID,
        updates: Dict[str, Any],
        reanalyze_placeholders: bool = True
    ) -> Tuple[Template, Dict[str, Any]]:
        """
        更新模板并重新分析占位符（如果内容发生变化）
        """
        try:
            # 1. 获取并验证模板
            template = self.db.query(Template).filter(
                Template.id == template_id,
                Template.user_id == user_id
            ).first()
            
            if not template:
                raise ValueError(f"模板不存在或无权限: {template_id}")
            
            # 2. 检查内容是否变化
            content_changed = 'content' in updates and updates['content'] != template.content
            
            # 3. 更新模板字段
            for key, value in updates.items():
                if hasattr(template, key):
                    setattr(template, key, value)
            
            template.updated_at = datetime.now()
            
            # 4. 如果内容变化且需要重新分析占位符
            placeholder_analysis = {}
            if content_changed and reanalyze_placeholders:
                # 先失效现有占位符配置
                await self.placeholder_service.deactivate_template_placeholders(template_id)
                
                # 重新分析并创建占位符配置
                placeholder_analysis = await self._analyze_and_create_placeholders(
                    template_id, updates['content']
                )
                
                # 清除相关缓存
                await self.cache_service.invalidate_template_cache(template_id)
            
            self.db.commit()
            
            logger.info(f"模板更新成功: {template_id}")
            
            return template, placeholder_analysis
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"模板更新失败: {str(e)}")
            raise
    
    async def get_template_with_placeholders(
        self,
        template_id: UUID,
        user_id: UUID = None,
        include_inactive: bool = False
    ) -> Dict[str, Any]:
        """
        获取模板及其占位符配置
        """
        # 1. 获取模板
        query = self.db.query(Template).filter(Template.id == template_id)
        
        if user_id:
            query = query.filter(
                or_(
                    Template.user_id == user_id,
                    Template.is_public == True
                )
            )
        
        template = query.first()
        if not template:
            raise ValueError(f"模板不存在或无权限: {template_id}")
        
        # 2. 获取占位符配置
        placeholders = await self.placeholder_service.get_template_placeholders_config(
            template_id, include_inactive
        )
        
        # 3. 获取模板统计信息
        stats = await self._get_template_statistics(template_id)
        
        return {
            "template": {
                "id": str(template.id),
                "name": template.name,
                "description": template.description,
                "content": template.content,
                "is_public": template.is_public,
                "created_at": template.created_at.isoformat(),
                "updated_at": template.updated_at.isoformat()
            },
            "placeholders": [
                {
                    "id": str(p.id),
                    "name": p.placeholder_name,
                    "text": p.placeholder_text,
                    "type": p.placeholder_type,
                    "content_type": p.content_type,
                    "workflow_id": p.agent_workflow_id,
                    "etl_template": p.etl_command_template,
                    "cache_ttl_hours": p.cache_ttl_hours,
                    "execution_order": p.execution_order,
                    "description": p.description,
                    "is_required": p.is_required,
                    "is_active": p.is_active
                }
                for p in placeholders
            ],
            "statistics": stats
        }
    
    async def list_user_templates(
        self,
        user_id: UUID,
        include_public: bool = True,
        page: int = 1,
        page_size: int = 20,
        search_query: str = None
    ) -> Dict[str, Any]:
        """
        获取用户模板列表
        """
        query = self.db.query(Template)
        
        # 构建查询条件
        if include_public:
            query = query.filter(
                or_(
                    Template.user_id == user_id,
                    Template.is_public == True
                )
            )
        else:
            query = query.filter(Template.user_id == user_id)
        
        # 搜索条件
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                or_(
                    Template.name.ilike(search_pattern),
                    Template.description.ilike(search_pattern)
                )
            )
        
        # 总数
        total_count = query.count()
        
        # 分页
        offset = (page - 1) * page_size
        templates = query.order_by(Template.updated_at.desc())\
                        .offset(offset)\
                        .limit(page_size)\
                        .all()
        
        # 构建结果
        template_list = []
        for template in templates:
            # 获取占位符数量
            placeholder_count = await self.placeholder_service.count_template_placeholders(template.id)
            
            template_list.append({
                "id": str(template.id),
                "name": template.name,
                "description": template.description,
                "is_public": template.is_public,
                "placeholder_count": placeholder_count,
                "created_at": template.created_at.isoformat(),
                "updated_at": template.updated_at.isoformat()
            })
        
        return {
            "templates": template_list,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        }
    
    async def delete_template(
        self,
        template_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        删除模板及其相关配置
        """
        try:
            # 1. 验证权限
            template = self.db.query(Template).filter(
                Template.id == template_id,
                Template.user_id == user_id
            ).first()
            
            if not template:
                raise ValueError(f"模板不存在或无权限: {template_id}")
            
            # 2. 删除占位符配置（级联删除）
            await self.placeholder_service.delete_template_placeholders(template_id)
            
            # 3. 清除缓存
            await self.cache_service.invalidate_template_cache(template_id)
            
            # 4. 删除模板
            self.db.delete(template)
            self.db.commit()
            
            logger.info(f"模板删除成功: {template_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"模板删除失败: {str(e)}")
            raise
    
    async def _analyze_and_create_placeholders(
        self,
        template_id: UUID,
        content: str
    ) -> Dict[str, Any]:
        """
        分析模板内容并创建占位符配置
        """
        try:
            # 1. 解析占位符
            placeholders = self.parser.extract_placeholders(content)
            
            if not placeholders:
                return {
                    "total_placeholders": 0,
                    "created_placeholders": 0,
                    "analysis_errors": ["未发现有效占位符"]
                }
            
            # 2. 创建占位符配置
            created_placeholders = await self.placeholder_service.create_template_placeholders_config(
                template_id, placeholders
            )
            
            # 3. 分析结果统计
            type_distribution = {}
            for placeholder in placeholders:
                ptype = placeholder.get("type", "unknown")
                type_distribution[ptype] = type_distribution.get(ptype, 0) + 1
            
            return {
                "total_placeholders": len(placeholders),
                "created_placeholders": len(created_placeholders),
                "type_distribution": type_distribution,
                "placeholder_details": [
                    {
                        "name": p["name"],
                        "type": p["type"],
                        "content_type": p["content_type"],
                        "description": p.get("description", "")
                    }
                    for p in placeholders
                ],
                "analysis_errors": []
            }
            
        except Exception as e:
            logger.error(f"占位符分析失败: {str(e)}")
            return {
                "total_placeholders": 0,
                "created_placeholders": 0,
                "analysis_errors": [str(e)]
            }
    
    async def _get_template_statistics(self, template_id: UUID) -> Dict[str, Any]:
        """
        获取模板统计信息
        """
        try:
            # 占位符统计
            placeholder_stats = await self.placeholder_service.get_placeholder_statistics(template_id)
            
            # 使用统计（从执行历史获取）
            # 这里先返回基础统计，后续会在实现执行历史后完善
            usage_stats = {
                "total_generations": 0,
                "last_generation": None,
                "average_generation_time_ms": 0,
                "success_rate": 0.0
            }
            
            return {
                "placeholder_stats": placeholder_stats,
                "usage_stats": usage_stats,
                "cache_stats": {
                    "cache_hit_rate": 0.0,
                    "cached_placeholders": 0
                }
            }
            
        except Exception as e:
            logger.error(f"获取模板统计失败: {str(e)}")
            return {
                "placeholder_stats": {},
                "usage_stats": {},
                "cache_stats": {}
            }
    
    async def duplicate_template(
        self,
        template_id: UUID,
        user_id: UUID,
        new_name: str,
        copy_placeholders: bool = True
    ) -> Tuple[Template, Dict[str, Any]]:
        """
        复制模板
        """
        try:
            # 1. 获取原模板
            original_template = self.db.query(Template).filter(
                Template.id == template_id
            ).filter(
                or_(
                    Template.user_id == user_id,
                    Template.is_public == True
                )
            ).first()
            
            if not original_template:
                raise ValueError(f"模板不存在或无权限: {template_id}")
            
            # 2. 创建新模板
            new_template = Template(
                id=uuid4(),
                user_id=user_id,
                name=new_name,
                content=original_template.content,
                description=f"复制自: {original_template.name}",
                is_public=False,  # 复制的模板默认为私有
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.db.add(new_template)
            self.db.flush()
            
            # 3. 复制占位符配置
            placeholder_analysis = {}
            if copy_placeholders:
                placeholder_analysis = await self.placeholder_service.copy_template_placeholders(
                    original_template.id, new_template.id
                )
            
            self.db.commit()
            
            logger.info(f"模板复制成功: {original_template.id} -> {new_template.id}")
            
            return new_template, placeholder_analysis
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"模板复制失败: {str(e)}")
            raise


# 全局服务实例工厂
def get_template_service(db: Session) -> TemplateService:
    """获取模板服务实例"""
    return TemplateService(db)