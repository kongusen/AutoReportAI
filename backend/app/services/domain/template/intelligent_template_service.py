"""
智能模板服务 - 集成新的占位符分析系统
替换原有的模板服务，使用DAG编排架构的占位符处理能力
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
# 导入新的占位符分析系统
from ..placeholder.intelligent_placeholder_service import IntelligentPlaceholderService
from ..placeholder.models import TimeContext, BusinessContext, DocumentContext

logger = logging.getLogger(__name__)


class IntelligentTemplateService:
    """智能模板服务 - 基于新的占位符分析系统"""
    
    def __init__(self, db: Session):
        self.db = db
        self.placeholder_service = IntelligentPlaceholderService()
        
    async def create_template_with_sql_generation(
        self,
        user_id: UUID,
        name: str,
        content: str,
        description: str = None,
        is_public: bool = False,
        auto_analyze: bool = True
    ) -> Tuple[Template, Dict[str, Any]]:
        """
        创建新模板并自动生成SQL
        
        Returns:
            Tuple[Template, Dict]: (模板对象, 占位符分析结果)
        """
        try:
            logger.info(f"创建模板并生成SQL: {name}, 用户: {user_id}")
            
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
            
            # 2. 使用新的占位符分析系统生成SQL
            placeholder_analysis = {}
            if auto_analyze and content:
                placeholder_analysis = await self._analyze_template_for_sql_generation(
                    template_id=str(template.id),
                    template_content=content,
                    user_id=str(user_id)
                )
            
            # 3. 提交事务
            self.db.commit()
            
            logger.info(f"模板创建成功: {template.id}, SQL生成数量: {placeholder_analysis.get('total_sqls_generated', 0)}")
            
            return template, placeholder_analysis
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"模板创建失败: {str(e)}")
            raise
    
    async def update_template_and_regenerate_sql(
        self,
        template_id: UUID,
        user_id: UUID,
        updates: Dict[str, Any],
        regenerate_sql: bool = True
    ) -> Tuple[Template, Dict[str, Any]]:
        """
        更新模板并重新生成SQL（如果内容发生变化）
        """
        try:
            # 1. 获取并验证模板
            template = self._get_template_with_permission(template_id, user_id)
            if not template:
                raise ValueError(f"模板未找到或无权限访问: {template_id}")
            
            # 2. 记录原始内容
            original_content = template.content
            content_changed = False
            
            # 3. 更新模板字段
            for field, value in updates.items():
                if hasattr(template, field):
                    if field == "content" and value != original_content:
                        content_changed = True
                    setattr(template, field, value)
            
            template.updated_at = datetime.now()
            
            # 4. 重新分析占位符（如果内容变化）
            placeholder_analysis = {}
            if regenerate_sql and content_changed:
                placeholder_analysis = await self._analyze_template_for_sql_generation(
                    template_id=str(template_id),
                    template_content=template.content,
                    user_id=str(user_id)
                )
            
            # 5. 提交更新
            self.db.commit()
            
            logger.info(f"模板更新成功: {template_id}, 内容变化: {content_changed}, SQL重新生成: {regenerate_sql and content_changed}")
            
            return template, placeholder_analysis
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"模板更新失败: {template_id}, 错误: {str(e)}")
            raise
    
    async def test_template_chart_generation(
        self,
        template_id: UUID,
        placeholder_text: str,
        stored_sql_id: str,
        test_data: Dict[str, Any],
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        测试模板中的图表生成（前端预览）
        """
        try:
            logger.info(f"测试模板图表: {template_id}, 占位符: {placeholder_text}")
            
            # 1. 获取模板
            template = self._get_template_with_permission(template_id, user_id)
            if not template:
                raise ValueError(f"模板未找到或无权限访问: {template_id}")
            
            # 2. 调用新的占位符分析系统进行图表测试
            result = await self.placeholder_service.analyze_template_for_chart_testing(
                placeholder_text=placeholder_text,
                template_content=template.content,
                stored_sql_id=stored_sql_id,
                test_data=test_data,
                template_id=str(template_id),
                user_id=str(user_id)
            )
            
            # 3. 转换结果格式
            return {
                "success": result.success,
                "template_id": str(template_id),
                "placeholder_text": placeholder_text,
                "chart_config": result.generated_chart_config if hasattr(result, 'generated_chart_config') else None,
                "chart_data": result.chart_data if hasattr(result, 'chart_data') else None,
                "frontend_ready": True,
                "processing_time_ms": result.processing_time_ms,
                "confidence_score": result.confidence_score
            }
            
        except Exception as e:
            logger.error(f"模板图表测试失败: {template_id}, 错误: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "template_id": str(template_id),
                "placeholder_text": placeholder_text
            }
    
    async def get_template_placeholder_analysis(
        self,
        template_id: UUID,
        user_id: UUID,
        force_reanalyze: bool = False
    ) -> Dict[str, Any]:
        """
        获取模板的占位符分析结果
        """
        try:
            # 1. 获取模板
            template = self._get_template_with_permission(template_id, user_id)
            if not template:
                raise ValueError(f"模板未找到或无权限访问: {template_id}")
            
            # 2. 分析占位符
            if force_reanalyze or not self._has_cached_analysis(template_id):
                analysis = await self._analyze_template_for_sql_generation(
                    template_id=str(template_id),
                    template_content=template.content,
                    user_id=str(user_id)
                )
            else:
                analysis = self._get_cached_analysis(template_id)
            
            return {
                "template_id": str(template_id),
                "template_name": template.name,
                "analysis": analysis,
                "last_analyzed": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取模板占位符分析失败: {template_id}, 错误: {str(e)}")
            raise
    
    async def _analyze_template_for_sql_generation(
        self,
        template_id: str,
        template_content: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        使用新的占位符分析系统生成SQL
        """
        try:
            # 构建默认的时间和业务上下文
            time_context = self._create_default_time_context()
            business_context = self._create_default_business_context()
            document_context = self._create_document_context(template_id, template_content)
            
            # 调用新的占位符分析系统
            result = await self.placeholder_service.analyze_template_for_sql_generation(
                template_content=template_content,
                template_id=template_id,
                user_id=user_id,
                time_context=time_context,
                business_context=business_context,
                document_context=document_context
            )
            
            # 转换结果格式
            return {
                "success": result.success,
                "template_id": template_id,
                "total_placeholders": result.total_placeholders,
                "total_sqls_generated": result.successfully_analyzed,
                "overall_confidence": result.overall_confidence,
                "processing_time_ms": result.processing_time_ms,
                "placeholders": [
                    {
                        "placeholder_text": analysis.placeholder_spec.raw_text,
                        "statistical_type": analysis.placeholder_spec.statistical_type.value,
                        "description": analysis.placeholder_spec.description,
                        "generated_sql": analysis.generated_sql,
                        "sql_quality_score": analysis.sql_quality_score,
                        "confidence_score": analysis.confidence_score,
                        "processing_time_ms": analysis.processing_time_ms,
                        "success": analysis.success,
                        "error_message": getattr(analysis, 'error_message', None)
                    }
                    for analysis in result.analysis_results
                ]
            }
            
        except Exception as e:
            logger.error(f"占位符SQL生成失败: {template_id}, 错误: {str(e)}")
            return {
                "success": False,
                "template_id": template_id,
                "error": str(e),
                "total_placeholders": 0,
                "total_sqls_generated": 0,
                "placeholders": []
            }
    
    def _get_template_with_permission(self, template_id: UUID, user_id: UUID) -> Optional[Template]:
        """获取有权限访问的模板"""
        return self.db.query(Template).filter(
            and_(
                Template.id == template_id,
                or_(
                    Template.user_id == user_id,
                    Template.is_public == True
                )
            )
        ).first()
    
    def _create_default_time_context(self) -> TimeContext:
        """创建默认时间上下文"""
        now = datetime.now()
        return TimeContext(
            report_period=now.strftime("%Y-%m"),
            period_type="monthly",
            start_date=now.replace(day=1),
            end_date=now,
            previous_period_start=now.replace(month=now.month-1, day=1) if now.month > 1 else now.replace(year=now.year-1, month=12, day=1),
            previous_period_end=now.replace(day=1),
            fiscal_year=str(now.year),
            quarter=f"Q{(now.month-1)//3 + 1}"
        )
    
    def _create_default_business_context(self) -> BusinessContext:
        """创建默认业务上下文"""
        return BusinessContext(
            task_type="template_analysis",
            department="general",
            report_level="standard",
            data_granularity="daily",
            include_comparisons=True,
            target_audience="analyst"
        )
    
    def _create_document_context(self, template_id: str, template_content: str) -> DocumentContext:
        """创建文档上下文"""
        return DocumentContext(
            document_id=template_id,
            paragraph_content=template_content,
            paragraph_index=0,
            section_title="Template Content",
            section_index=0,
            surrounding_text=template_content[:500],  # 前500字符作为周围文本
            document_structure={"type": "template", "length": len(template_content)}
        )
    
    def _has_cached_analysis(self, template_id: UUID) -> bool:
        """检查是否有缓存的分析结果"""
        # TODO: 实现缓存检查逻辑
        return False
    
    def _get_cached_analysis(self, template_id: UUID) -> Dict[str, Any]:
        """获取缓存的分析结果"""
        # TODO: 实现缓存获取逻辑
        return {}
    
    # 原有的模板管理方法保持不变
    async def get_template(self, template_id: UUID, user_id: UUID) -> Optional[Template]:
        """获取单个模板"""
        return self._get_template_with_permission(template_id, user_id)
    
    async def list_templates(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search_query: str = None,
        is_public: bool = None
    ) -> Tuple[List[Template], int]:
        """列出模板"""
        query = self.db.query(Template).filter(
            or_(
                Template.user_id == user_id,
                Template.is_public == True
            )
        )
        
        if search_query:
            query = query.filter(
                or_(
                    Template.name.ilike(f"%{search_query}%"),
                    Template.description.ilike(f"%{search_query}%"),
                    Template.content.ilike(f"%{search_query}%")
                )
            )
        
        if is_public is not None:
            query = query.filter(Template.is_public == is_public)
        
        total_count = query.count()
        
        templates = query.order_by(Template.updated_at.desc())\
                        .offset((page - 1) * page_size)\
                        .limit(page_size)\
                        .all()
        
        return templates, total_count
    
    async def delete_template(self, template_id: UUID, user_id: UUID) -> bool:
        """删除模板"""
        try:
            template = self.db.query(Template).filter(
                and_(
                    Template.id == template_id,
                    Template.user_id == user_id  # 只有模板所有者可以删除
                )
            ).first()
            
            if not template:
                return False
            
            self.db.delete(template)
            self.db.commit()
            
            logger.info(f"模板删除成功: {template_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"模板删除失败: {template_id}, 错误: {str(e)}")
            raise