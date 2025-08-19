"""
Placeholder Extraction Service

负责从模板中提取占位符并进行基础分析，为后续Agent分析做准备
"""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.template_placeholder import TemplatePlaceholder
from app.services.report_generation.document_pipeline import TemplateParser

logger = logging.getLogger(__name__)


class PlaceholderExtractionService:
    """占位符提取服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.template_parser = TemplateParser()
    
    async def extract_and_store_placeholders(
        self, 
        template_id: str, 
        template_content: str
    ) -> Dict[str, Any]:
        """
        从模板中提取占位符并存储到数据库
        
        Args:
            template_id: 模板ID
            template_content: 模板内容
            
        Returns:
            提取结果统计
        """
        try:
            logger.info(f"开始提取模板占位符: {template_id}")
            
            # 1. 使用现有解析器提取占位符
            raw_placeholders = self.template_parser.extract_placeholders(template_content)
            
            if not raw_placeholders:
                return {
                    "success": True,
                    "total_placeholders": 0,
                    "stored_placeholders": 0,
                    "message": "未发现占位符"
                }
            
            # 2. 增强分析占位符
            enhanced_placeholders = self._enhance_placeholder_analysis(raw_placeholders, template_content)
            
            # 3. 存储到数据库
            stored_placeholders = []
            for i, placeholder_info in enumerate(enhanced_placeholders):
                stored_placeholder = await self._store_placeholder(
                    template_id, placeholder_info, i + 1
                )
                stored_placeholders.append(stored_placeholder)
            
            self.db.commit()
            
            logger.info(f"占位符提取完成: {template_id}, 共提取 {len(stored_placeholders)} 个")
            
            return {
                "success": True,
                "total_placeholders": len(raw_placeholders),
                "stored_placeholders": len(stored_placeholders),
                "placeholders": [
                    {
                        "id": str(p.id),
                        "name": p.placeholder_name,
                        "type": p.placeholder_type,
                        "requires_analysis": not p.agent_analyzed
                    }
                    for p in stored_placeholders
                ],
                "type_distribution": self._get_type_distribution(enhanced_placeholders)
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"占位符提取失败: {template_id}, 错误: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "total_placeholders": 0,
                "stored_placeholders": 0
            }
    
    def _enhance_placeholder_analysis(
        self, 
        raw_placeholders: List[Dict], 
        template_content: str
    ) -> List[Dict[str, Any]]:
        """
        增强占位符分析，为Agent分析提供更多上下文
        """
        enhanced_placeholders = []
        
        for placeholder in raw_placeholders:
            placeholder_name = placeholder.get("name", "")
            placeholder_text = placeholder.get("placeholder_text", f"{{{placeholder_name}}}")
            
            # 分析占位符类型和意图
            analysis_result = self._analyze_placeholder_intent(placeholder_name, template_content)
            
            enhanced_placeholder = {
                "name": placeholder_name,
                "text": placeholder_text,
                "type": placeholder.get("type", "text"),
                "content_type": placeholder.get("content_type", "text"),
                "description": placeholder.get("description", ""),
                
                # 增强的分析信息
                "intent_analysis": analysis_result,
                "context_keywords": self._extract_context_keywords(placeholder_name, template_content),
                "priority": self._calculate_priority(placeholder_name),
                "complexity": self._estimate_complexity(placeholder_name),
                
                # Agent分析标记
                "requires_agent_analysis": self._requires_agent_analysis(placeholder.get("type", "text")),
                "suggested_workflow": self._suggest_workflow(placeholder.get("type", "text"))
            }
            
            enhanced_placeholders.append(enhanced_placeholder)
        
        return enhanced_placeholders
    
    def _analyze_placeholder_intent(self, placeholder_name: str, template_content: str) -> Dict[str, Any]:
        """分析占位符意图"""
        name_lower = placeholder_name.lower()
        
        intent = {
            "data_operation": "unknown",
            "aggregation_type": None,
            "time_dimension": False,
            "geographic_dimension": False,
            "requires_grouping": False,
            "estimated_complexity": "simple"
        }
        
        # 数据操作类型检测
        if any(keyword in name_lower for keyword in ['总数', '数量', 'count', '统计']):
            intent["data_operation"] = "count"
            intent["aggregation_type"] = "COUNT"
            
        elif any(keyword in name_lower for keyword in ['平均', 'avg', 'average']):
            intent["data_operation"] = "average"
            intent["aggregation_type"] = "AVG"
            
        elif any(keyword in name_lower for keyword in ['求和', 'sum', '总和', '合计']):
            intent["data_operation"] = "sum"
            intent["aggregation_type"] = "SUM"
            
        elif any(keyword in name_lower for keyword in ['最大', 'max', '最高']):
            intent["data_operation"] = "max"
            intent["aggregation_type"] = "MAX"
            
        elif any(keyword in name_lower for keyword in ['最小', 'min', '最低']):
            intent["data_operation"] = "min"
            intent["aggregation_type"] = "MIN"
            
        elif any(keyword in name_lower for keyword in ['列表', 'list', '清单', '明细']):
            intent["data_operation"] = "list"
            intent["estimated_complexity"] = "medium"
            
        # 维度检测
        if any(keyword in name_lower for keyword in ['按', '分组', '各', 'group', 'by']):
            intent["requires_grouping"] = True
            intent["estimated_complexity"] = "medium"
            
        if any(keyword in name_lower for keyword in ['年', '月', '日', '时间', 'year', 'month', 'date', 'time']):
            intent["time_dimension"] = True
            
        if any(keyword in name_lower for keyword in ['省', '市', '州', '县', '区', '地区', 'province', 'city']):
            intent["geographic_dimension"] = True
            
        # 复杂度评估
        complexity_factors = sum([
            intent["requires_grouping"],
            intent["time_dimension"], 
            intent["geographic_dimension"],
            intent["data_operation"] in ["list", "analysis"]
        ])
        
        if complexity_factors >= 2:
            intent["estimated_complexity"] = "complex"
        elif complexity_factors == 1:
            intent["estimated_complexity"] = "medium"
            
        return intent
    
    def _extract_context_keywords(self, placeholder_name: str, template_content: str) -> List[str]:
        """从模板内容中提取与占位符相关的上下文关键词"""
        # 找到占位符在模板中的位置
        placeholder_pattern = f"{{{{{placeholder_name}}}}}"
        
        # 提取占位符前后50个字符作为上下文
        match = re.search(re.escape(placeholder_pattern), template_content)
        if not match:
            return []
        
        start_pos = max(0, match.start() - 50)
        end_pos = min(len(template_content), match.end() + 50)
        context = template_content[start_pos:end_pos]
        
        # 提取关键词（中文词汇和英文单词）
        chinese_words = re.findall(r'[\u4e00-\u9fff]+', context)
        english_words = re.findall(r'[a-zA-Z]+', context)
        
        # 过滤常见停用词
        stopwords = {'的', '和', '在', '与', '等', '及', '是', '为', '有', '个', '中', 'the', 'and', 'or', 'in', 'of', 'to', 'a', 'an'}
        keywords = [word for word in chinese_words + english_words 
                   if len(word) > 1 and word.lower() not in stopwords]
        
        return list(set(keywords))[:10]  # 返回前10个唯一关键词
    
    def _calculate_priority(self, placeholder_name: str) -> int:
        """计算占位符优先级 (1-10, 10最高)"""
        name_lower = placeholder_name.lower()
        
        # 高优先级：总数、关键统计
        if any(keyword in name_lower for keyword in ['总数', '总计', 'total', 'count']):
            return 9
            
        # 中高优先级：百分比、占比
        if any(keyword in name_lower for keyword in ['占比', '百分比', 'percent', 'rate']):
            return 7
            
        # 中等优先级：各种统计
        if any(keyword in name_lower for keyword in ['平均', '最大', '最小', 'avg', 'max', 'min']):
            return 6
            
        # 中低优先级：列表、明细
        if any(keyword in name_lower for keyword in ['列表', '清单', 'list']):
            return 4
            
        # 低优先级：其他
        return 3
    
    def _estimate_complexity(self, placeholder_name: str) -> str:
        """估算占位符复杂度"""
        name_lower = placeholder_name.lower()
        
        # 简单：直接统计
        if any(keyword in name_lower for keyword in ['总数', 'count']) and not any(keyword in name_lower for keyword in ['按', '分组', '各']):
            return "simple"
            
        # 复杂：需要分组、关联、计算
        if any(keyword in name_lower for keyword in ['按', '分组', '各', '分布', '分析', 'group', 'analysis']):
            return "complex"
            
        # 中等：其他情况
        return "medium"
    
    def _requires_agent_analysis(self, placeholder_type: str) -> bool:
        """判断是否需要Agent分析"""
        # 除了简单的文本类型，其他都需要Agent分析
        return placeholder_type != "text" or placeholder_type in ["statistic", "analysis", "chart", "table"]
    
    def _suggest_workflow(self, placeholder_type: str) -> str:
        """建议使用的工作流"""
        workflow_mapping = {
            "statistic": "statistical_analysis_workflow",
            "analysis": "comprehensive_analysis_workflow",
            "chart": "chart_generation_workflow", 
            "table": "table_generation_workflow",
            "text": "simple_text_workflow"
        }
        return workflow_mapping.get(placeholder_type, "statistical_analysis_workflow")
    
    async def _store_placeholder(
        self, 
        template_id: str, 
        placeholder_info: Dict[str, Any], 
        execution_order: int
    ) -> TemplatePlaceholder:
        """存储单个占位符到数据库，避免重复插入"""
        
        # 先检查是否已存在相同的占位符
        existing_placeholder = self.db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.template_id == template_id,
            TemplatePlaceholder.placeholder_name == placeholder_info["name"]
        ).first()
        
        if existing_placeholder:
            # 如果已存在，更新现有记录
            logger.info(f"占位符已存在，更新现有记录: {placeholder_info['name']}")
            
            # 更新字段
            existing_placeholder.placeholder_text = placeholder_info["text"]
            existing_placeholder.placeholder_type = placeholder_info["type"]
            existing_placeholder.content_type = placeholder_info["content_type"]
            existing_placeholder.execution_order = execution_order
            existing_placeholder.cache_ttl_hours = self._calculate_cache_ttl(placeholder_info)
            existing_placeholder.is_active = True  # 重新激活
            existing_placeholder.agent_workflow_id = placeholder_info["suggested_workflow"]
            existing_placeholder.agent_config = {
                "intent_analysis": placeholder_info["intent_analysis"],
                "context_keywords": placeholder_info["context_keywords"],
                "priority": placeholder_info["priority"],
                "complexity": placeholder_info["complexity"]
            }
            existing_placeholder.description = placeholder_info.get("description", "")
            existing_placeholder.updated_at = datetime.now()
            
            self.db.flush()
            return existing_placeholder
        
        # 创建新的占位符
        placeholder = TemplatePlaceholder(
            template_id=template_id,
            placeholder_name=placeholder_info["name"],
            placeholder_text=placeholder_info["text"],
            placeholder_type=placeholder_info["type"],
            content_type=placeholder_info["content_type"],
            
            # Agent分析状态
            agent_analyzed=False,  # 初始状态：未分析
            sql_validated=False,
            
            # 配置信息
            execution_order=execution_order,
            cache_ttl_hours=self._calculate_cache_ttl(placeholder_info),
            is_required=True,
            is_active=True,
            
            # Agent配置
            agent_workflow_id=placeholder_info["suggested_workflow"],
            agent_config={
                "intent_analysis": placeholder_info["intent_analysis"],
                "context_keywords": placeholder_info["context_keywords"],
                "priority": placeholder_info["priority"],
                "complexity": placeholder_info["complexity"]
            },
            
            description=placeholder_info.get("description", ""),
            confidence_score=0.0,  # 待Agent分析后更新
            
            created_at=datetime.now()
        )
        
        self.db.add(placeholder)
        self.db.flush()  # 获取ID
        
        return placeholder
    
    def _calculate_cache_ttl(self, placeholder_info: Dict[str, Any]) -> int:
        """根据占位符特征计算缓存TTL"""
        complexity = placeholder_info.get("complexity", "medium")
        intent = placeholder_info.get("intent_analysis", {})
        
        # 基础TTL
        base_ttl = 24
        
        # 根据复杂度调整
        if complexity == "simple":
            base_ttl = 48  # 简单统计缓存更久
        elif complexity == "complex":
            base_ttl = 12  # 复杂分析缓存较短
            
        # 根据时间维度调整
        if intent.get("time_dimension", False):
            base_ttl = 6   # 时间相关数据缓存较短
            
        return base_ttl
    
    def _get_type_distribution(self, placeholders: List[Dict]) -> Dict[str, int]:
        """获取占位符类型分布"""
        distribution = {}
        for placeholder in placeholders:
            ptype = placeholder.get("type", "unknown")
            distribution[ptype] = distribution.get(ptype, 0) + 1
        return distribution
    
    async def get_template_placeholders(
        self, 
        template_id: str, 
        include_analysis_status: bool = True
    ) -> List[Dict[str, Any]]:
        """获取模板的所有占位符"""
        
        placeholders = self.db.query(TemplatePlaceholder)\
            .filter(TemplatePlaceholder.template_id == template_id)\
            .filter(TemplatePlaceholder.is_active == True)\
            .order_by(TemplatePlaceholder.execution_order)\
            .all()
        
        result = []
        for placeholder in placeholders:
            placeholder_data = {
                "id": str(placeholder.id),
                "name": placeholder.placeholder_name,
                "text": placeholder.placeholder_text,
                "type": placeholder.placeholder_type,
                "content_type": placeholder.content_type,
                "execution_order": placeholder.execution_order,
                "description": placeholder.description,
                "is_required": placeholder.is_required
            }
            
            if include_analysis_status:
                placeholder_data.update({
                    "agent_analyzed": placeholder.agent_analyzed,
                    "sql_validated": placeholder.sql_validated,
                    "target_database": placeholder.target_database,
                    "target_table": placeholder.target_table,
                    "generated_sql": placeholder.generated_sql,
                    "confidence_score": placeholder.confidence_score,
                    "analyzed_at": placeholder.analyzed_at.isoformat() if placeholder.analyzed_at else None
                })
            
            result.append(placeholder_data)
        
        return result
    
    async def count_unanalyzed_placeholders(self, template_id: str) -> int:
        """统计未分析的占位符数量"""
        return self.db.query(TemplatePlaceholder)\
            .filter(TemplatePlaceholder.template_id == template_id)\
            .filter(TemplatePlaceholder.is_active == True)\
            .filter(TemplatePlaceholder.agent_analyzed == False)\
            .count()