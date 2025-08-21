"""
Placeholder Extractor

整合并重构原placeholder_extraction_service.py的功能
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from sqlalchemy.orm import Session
from uuid import UUID, uuid4

from app.models.template_placeholder import TemplatePlaceholder
# 延迟导入避免循环依赖
# from app.services.report_generation.document_pipeline import TemplateParser
from ..core.exceptions import PlaceholderExtractionError
from ..core.constants import SUPPORTED_PLACEHOLDER_TYPES, ContentType
from .parser import PlaceholderParser
from app.services.application.interfaces.extraction_interfaces import PlaceholderExtractorInterface

logger = logging.getLogger(__name__)


class PlaceholderExtractor(PlaceholderExtractorInterface):
    """
    统一的占位符提取器
    
    整合原有的提取逻辑，提供更完善的占位符识别和分析功能
    """
    
    def __init__(self, db: Session, template_parser: Any = None):
        self.db = db
        self.template_parser = template_parser  # 可注入，避免循环依赖
        self.placeholder_parser = PlaceholderParser()
    
    async def extract_and_store_placeholders(
        self, 
        template_id: str, 
        template_content: str,
        force_update: bool = False
    ) -> Dict[str, Any]:
        """
        从模板中提取占位符并存储到数据库
        
        Args:
            template_id: 模板ID
            template_content: 模板内容
            force_update: 是否强制更新现有占位符
            
        Returns:
            提取结果统计
        """
        try:
            logger.info(f"开始提取模板占位符: {template_id}")
            
            # 1. 提取原始占位符
            raw_placeholders = self._extract_raw_placeholders(template_content)
            
            if not raw_placeholders:
                return {
                    "success": True,
                    "total_placeholders": 0,
                    "new_placeholders": 0,
                    "updated_placeholders": 0,
                    "message": "模板中未发现占位符"
                }
            
            # 2. 解析和分析占位符
            analyzed_placeholders = await self._analyze_placeholders(raw_placeholders)
            
            # 3. 存储或更新占位符
            storage_result = await self._store_placeholders(
                template_id, analyzed_placeholders, force_update
            )
            
            logger.info(f"占位符提取完成: {template_id}, 处理了 {len(analyzed_placeholders)} 个占位符")
            
            return {
                "success": True,
                "total_placeholders": len(raw_placeholders),
                "analyzed_placeholders": len(analyzed_placeholders),
                **storage_result
            }
            
        except Exception as e:
            logger.error(f"占位符提取失败: {template_id}, 错误: {e}", exc_info=True)
            raise PlaceholderExtractionError(
                f"提取占位符失败: {str(e)}", 
                template_id=template_id
            )
    
    async def extract_placeholders(self, template_content: str) -> List[Dict[str, Any]]:
        """仅提取占位符（不持久化），满足接口抽象需求"""
        raw_placeholders = self._extract_raw_placeholders(template_content)
        if not raw_placeholders:
            return []
        analyzed_placeholders = await self._analyze_placeholders(raw_placeholders)
        return analyzed_placeholders
    
    def _extract_raw_placeholders(self, template_content: str) -> List[Dict[str, Any]]:
        """提取原始占位符"""
        try:
            # 如未注入，则延迟初始化模板解析器（向后兼容）
            if self.template_parser is None:
                from app.services.report_generation.document_pipeline import TemplateParser
                self.template_parser = TemplateParser()
            
            # 使用现有的模板解析器
            raw_placeholders = self.template_parser.extract_placeholders(template_content)
            
            # 增强提取逻辑，支持更多格式
            enhanced_placeholders = self._enhance_placeholder_extraction(template_content)
            
            # 合并结果并去重
            all_placeholders = raw_placeholders + enhanced_placeholders
            unique_placeholders = self._deduplicate_placeholders(all_placeholders)
            
            return unique_placeholders
            
        except Exception as e:
            raise PlaceholderExtractionError(f"原始占位符提取失败: {str(e)}")
    
    def _enhance_placeholder_extraction(self, content: str) -> List[Dict[str, Any]]:
        """增强的占位符提取，支持更多格式"""
        placeholders = []
        
        # 支持的占位符模式
        patterns = [
            # {{placeholder_name | description}}
            r'\\{\\{\\s*([\\w_]+)\\s*\\|\\s*([^}]+)\\s*\\}\\}',
            # {{placeholder_name:type}}  
            r'\\{\\{\\s*([\\w_]+)\\s*:\\s*([\\w_]+)\\s*\\}\\}',
            # ${placeholder_name}
            r'\\$\\{([\\w_]+)\\}',
            # {placeholder_name}
            r'\\{([\\w_]+)\\}',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                placeholder_name = groups[0]
                
                placeholder_info = {
                    "name": placeholder_name,
                    "full_text": match.group(0),
                    "position": match.span(),
                    "extraction_method": "enhanced_regex"
                }
                
                # 如果有额外信息（描述或类型）
                if len(groups) > 1:
                    extra_info = groups[1]
                    if extra_info in SUPPORTED_PLACEHOLDER_TYPES:
                        placeholder_info["suggested_type"] = extra_info
                    else:
                        placeholder_info["description"] = extra_info
                
                placeholders.append(placeholder_info)
        
        return placeholders
    
    def _deduplicate_placeholders(self, placeholders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重占位符"""
        seen_names = set()
        unique_placeholders = []
        
        for placeholder in placeholders:
            name = placeholder.get("name", placeholder.get("placeholder_name", ""))
            if name and name not in seen_names:
                seen_names.add(name)
                unique_placeholders.append(placeholder)
        
        return unique_placeholders
    
    async def _analyze_placeholders(self, raw_placeholders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分析占位符，提取元信息"""
        analyzed = []
        
        for placeholder in raw_placeholders:
            try:
                analysis = await self.placeholder_parser.parse_placeholder(placeholder)
                analyzed.append(analysis)
            except Exception as e:
                logger.warning(f"占位符分析失败: {placeholder.get('name', 'unknown')}, 错误: {e}")
                # 保留原始信息，标记为未分析
                placeholder["analysis_failed"] = True
                placeholder["analysis_error"] = str(e)
                analyzed.append(placeholder)
        
        return analyzed
    
    async def _store_placeholders(
        self, 
        template_id: str, 
        placeholders: List[Dict[str, Any]], 
        force_update: bool
    ) -> Dict[str, Any]:
        """存储占位符到数据库"""
        new_count = 0
        updated_count = 0
        skipped_count = 0
        
        try:
            for i, placeholder in enumerate(placeholders):
                placeholder_name = placeholder.get("name", placeholder.get("placeholder_name"))
                if not placeholder_name:
                    logger.warning(f"跳过无名称占位符: {placeholder}")
                    skipped_count += 1
                    continue
                
                # 检查是否已存在
                existing = self.db.query(TemplatePlaceholder).filter(
                    TemplatePlaceholder.template_id == template_id,
                    TemplatePlaceholder.placeholder_name == placeholder_name
                ).first()
                
                if existing and not force_update:
                    skipped_count += 1
                    continue
                
                if existing:
                    # 更新现有占位符
                    self._update_placeholder_from_analysis(existing, placeholder)
                    updated_count += 1
                else:
                    # 创建新占位符
                    new_placeholder = self._create_placeholder_from_analysis(
                        template_id, placeholder, i
                    )
                    self.db.add(new_placeholder)
                    new_count += 1
            
            self.db.commit()
            
            return {
                "new_placeholders": new_count,
                "updated_placeholders": updated_count,
                "skipped_placeholders": skipped_count
            }
            
        except Exception as e:
            self.db.rollback()
            raise PlaceholderExtractionError(f"存储占位符失败: {str(e)}")
    
    def _create_placeholder_from_analysis(
        self, 
        template_id: str, 
        analysis: Dict[str, Any], 
        order: int
    ) -> TemplatePlaceholder:
        """从分析结果创建占位符对象"""
        return TemplatePlaceholder(
            id=uuid4(),
            template_id=UUID(template_id),
            placeholder_name=analysis.get("name", analysis.get("placeholder_name")),
            placeholder_text=analysis.get("full_text", ""),
            placeholder_type=analysis.get("suggested_type", "text"),
            content_type=analysis.get("content_type", ContentType.TEXT.value),
            execution_order=order,
            is_active=True,
            description=analysis.get("description", ""),
            agent_analyzed=False,
            # 从分析结果中提取的建议配置
            generated_sql=analysis.get("suggested_sql"),
            confidence_score=analysis.get("confidence", 0.0),
            agent_config=analysis,
            created_at=datetime.utcnow()
        )
    
    def _update_placeholder_from_analysis(
        self, 
        placeholder: TemplatePlaceholder, 
        analysis: Dict[str, Any]
    ):
        """根据分析结果更新占位符"""
        # 更新基础信息
        placeholder.placeholder_text = analysis.get("full_text", placeholder.placeholder_text)
        placeholder.description = analysis.get("description", placeholder.description)
        
        # 更新分析结果
        if analysis.get("suggested_type"):
            placeholder.placeholder_type = analysis["suggested_type"]
        if analysis.get("content_type"):
            placeholder.content_type = analysis["content_type"]
        if analysis.get("suggested_sql"):
            placeholder.generated_sql = analysis["suggested_sql"]
        
        placeholder.confidence_score = analysis.get("confidence", placeholder.confidence_score)
        placeholder.agent_config = analysis
        placeholder.updated_at = datetime.utcnow()
    
    async def get_template_placeholders(
        self, 
        template_id: str, 
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """获取模板的所有占位符"""
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
                    "template_id": str(p.template_id),
                    "placeholder_name": p.placeholder_name,
                    "placeholder_text": p.placeholder_text,
                    "placeholder_type": p.placeholder_type,
                    "content_type": p.content_type,
                    "description": p.description,
                    "execution_order": p.execution_order,
                    "is_active": p.is_active,
                    "agent_analyzed": p.agent_analyzed,
                    "analysis_confidence": p.confidence_score,
                    "extraction_metadata": p.agent_config or {},
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                }
                for p in placeholders
            ]
            
        except Exception as e:
            raise PlaceholderExtractionError(f"获取模板占位符失败: {str(e)}", template_id=template_id)