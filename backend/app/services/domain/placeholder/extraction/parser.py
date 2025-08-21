"""
Placeholder Parser

占位符解析器，负责分析占位符的语义和结构
"""

import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..core.constants import SUPPORTED_PLACEHOLDER_TYPES, ContentType
from ..core.exceptions import PlaceholderExtractionError

logger = logging.getLogger(__name__)


class PlaceholderParser:
    """占位符解析器"""
    
    def __init__(self):
        self.type_keywords = self._build_type_keywords()
        self.content_type_keywords = self._build_content_type_keywords()
    
    def _build_type_keywords(self) -> Dict[str, List[str]]:
        """构建类型关键词映射"""
        return {
            "metric": ["数量", "金额", "总数", "平均", "最大", "最小", "sum", "count", "avg", "max", "min", "total"],
            "text": ["名称", "描述", "内容", "标题", "name", "title", "description", "content"],
            "date": ["时间", "日期", "创建时间", "更新时间", "date", "time", "created", "updated"],
            "list": ["列表", "清单", "list", "items", "array"],
            "table": ["表格", "明细", "详情", "table", "details", "records"],
            "chart": ["图表", "统计图", "chart", "graph", "visualization"],
            "calculation": ["计算", "比率", "百分比", "增长率", "calculation", "ratio", "percentage", "growth"]
        }
    
    def _build_content_type_keywords(self) -> Dict[str, List[str]]:
        """构建内容类型关键词映射"""
        return {
            "number": ["数量", "个数", "次数", "count", "number", "quantity"],
            "percentage": ["百分比", "比率", "占比", "percent", "percentage", "ratio"],
            "currency": ["金额", "价格", "费用", "成本", "money", "price", "cost", "amount"],
            "date": ["日期", "时间", "date", "time"],
            "datetime": ["时间戳", "完整时间", "datetime", "timestamp"],
            "text": ["文本", "名称", "描述", "text", "name", "description"]
        }
    
    async def parse_placeholder(self, placeholder: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析占位符，提取语义信息
        
        Args:
            placeholder: 原始占位符信息
            
        Returns:
            包含分析结果的占位符信息
        """
        try:
            # 获取基础信息
            name = placeholder.get("name", placeholder.get("placeholder_name", ""))
            text = placeholder.get("full_text", placeholder.get("placeholder_text", ""))
            description = placeholder.get("description", "")
            
            # 语义分析
            semantic_analysis = self._analyze_semantics(name, text, description)
            
            # 类型推断
            suggested_type = self._infer_type(name, text, description, semantic_analysis)
            
            # 内容类型推断
            content_type = self._infer_content_type(name, text, description, suggested_type)
            
            # 置信度计算
            confidence = self._calculate_confidence(semantic_analysis, suggested_type, content_type)
            
            # 生成建议SQL模板
            suggested_sql = self._generate_sql_suggestion(name, suggested_type, content_type)
            
            # 构建完整分析结果
            analysis_result = {
                **placeholder,  # 保留原始信息
                "name": name,
                "suggested_type": suggested_type,
                "content_type": content_type,
                "confidence": confidence,
                "suggested_sql": suggested_sql,
                "semantic_analysis": semantic_analysis,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "parser_version": "v1.0"
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"占位符解析失败: {placeholder}, 错误: {e}")
            raise PlaceholderExtractionError(f"占位符解析失败: {str(e)}")
    
    def _analyze_semantics(self, name: str, text: str, description: str) -> Dict[str, Any]:
        """语义分析"""
        combined_text = f"{name} {text} {description}".lower()
        
        # 提取关键信息
        analysis = {
            "contains_aggregation": self._check_aggregation_keywords(combined_text),
            "contains_time_reference": self._check_time_keywords(combined_text),
            "contains_calculation": self._check_calculation_keywords(combined_text),
            "contains_filter": self._check_filter_keywords(combined_text),
            "language": self._detect_language(combined_text),
            "complexity_score": self._calculate_complexity(combined_text)
        }
        
        return analysis
    
    def _check_aggregation_keywords(self, text: str) -> bool:
        """检查聚合关键词"""
        agg_keywords = ["总", "平均", "最大", "最小", "数量", "sum", "avg", "count", "max", "min", "total"]
        return any(keyword in text for keyword in agg_keywords)
    
    def _check_time_keywords(self, text: str) -> bool:
        """检查时间关键词"""
        time_keywords = ["今天", "昨天", "本月", "上月", "本年", "去年", "today", "yesterday", "month", "year", "time", "date"]
        return any(keyword in text for keyword in time_keywords)
    
    def _check_calculation_keywords(self, text: str) -> bool:
        """检查计算关键词"""
        calc_keywords = ["增长", "下降", "比例", "百分比", "比率", "growth", "ratio", "percentage", "rate"]
        return any(keyword in text for keyword in calc_keywords)
    
    def _check_filter_keywords(self, text: str) -> bool:
        """检查过滤关键词"""
        filter_keywords = ["筛选", "过滤", "条件", "where", "filter", "condition", "status", "type"]
        return any(keyword in text for keyword in filter_keywords)
    
    def _detect_language(self, text: str) -> str:
        """检测语言"""
        # 简单的中英文检测
        chinese_chars = len(re.findall(r'[\\u4e00-\\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        
        if chinese_chars > english_chars:
            return "chinese"
        elif english_chars > 0:
            return "english"
        else:
            return "mixed"
    
    def _calculate_complexity(self, text: str) -> float:
        """计算复杂度分数"""
        score = 0.0
        
        # 基于长度
        score += min(len(text) / 100, 0.3)
        
        # 基于特殊字符
        special_chars = len(re.findall(r'[^\\w\\s\\u4e00-\\u9fff]', text))
        score += min(special_chars / 10, 0.2)
        
        # 基于数字
        numbers = len(re.findall(r'\\d+', text))
        score += min(numbers / 5, 0.1)
        
        return min(score, 1.0)
    
    def _infer_type(self, name: str, text: str, description: str, semantic_analysis: Dict[str, Any]) -> str:
        """推断占位符类型"""
        combined_text = f"{name} {text} {description}".lower()
        
        # 基于语义分析的类型推断
        if semantic_analysis.get("contains_aggregation") and semantic_analysis.get("contains_calculation"):
            return "calculation"
        elif semantic_analysis.get("contains_aggregation"):
            return "metric"
        elif semantic_analysis.get("contains_time_reference"):
            return "date"
        
        # 基于关键词匹配
        type_scores = {}
        for ptype, keywords in self.type_keywords.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                type_scores[ptype] = score
        
        if type_scores:
            return max(type_scores, key=type_scores.get)
        
        # 默认类型
        return "text"
    
    def _infer_content_type(self, name: str, text: str, description: str, placeholder_type: str) -> str:
        """推断内容类型"""
        combined_text = f"{name} {text} {description}".lower()
        
        # 基于占位符类型的映射
        type_content_mapping = {
            "metric": "number",
            "calculation": "percentage",
            "date": "date",
            "text": "text"
        }
        
        if placeholder_type in type_content_mapping:
            return type_content_mapping[placeholder_type]
        
        # 基于关键词匹配
        content_scores = {}
        for ctype, keywords in self.content_type_keywords.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                content_scores[ctype] = score
        
        if content_scores:
            return max(content_scores, key=content_scores.get)
        
        return "text"
    
    def _calculate_confidence(self, semantic_analysis: Dict[str, Any], suggested_type: str, content_type: str) -> float:
        """计算置信度"""
        confidence = 0.5  # 基础置信度
        
        # 基于语义分析的置信度提升
        if semantic_analysis.get("contains_aggregation") and suggested_type in ["metric", "calculation"]:
            confidence += 0.2
        
        if semantic_analysis.get("contains_time_reference") and suggested_type == "date":
            confidence += 0.2
        
        if semantic_analysis.get("contains_calculation") and suggested_type == "calculation":
            confidence += 0.2
        
        # 基于语言一致性
        if semantic_analysis.get("language") in ["chinese", "english"]:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _generate_sql_suggestion(self, name: str, placeholder_type: str, content_type: str) -> Optional[str]:
        """生成SQL建议"""
        # 基于类型生成SQL模板
        if placeholder_type == "metric" and content_type == "number":
            return f"SELECT COUNT(*) as {name} FROM {{table_name}}"
        elif placeholder_type == "metric" and content_type == "currency":
            return f"SELECT SUM(amount) as {name} FROM {{table_name}}"
        elif placeholder_type == "date":
            return f"SELECT MAX(created_at) as {name} FROM {{table_name}}"
        elif placeholder_type == "calculation" and content_type == "percentage":
            return f"SELECT (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {{table_name}})) as {name} FROM {{table_name}} WHERE condition = 1"
        elif placeholder_type == "text":
            return f"SELECT name as {name} FROM {{table_name}} LIMIT 1"
        
        return None