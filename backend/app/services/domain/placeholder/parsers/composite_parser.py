"""
组合占位符解析器

专门处理组合格式的占位符，支持嵌套占位符的解析
"""

import logging
import re
from typing import List, Optional
from ..models import (
    CompositePlaceholder, PlaceholderSpec, StatisticalType, SyntaxType,
    PlaceholderSyntaxError, PlaceholderParserInterface
)

logger = logging.getLogger(__name__)


class CompositeParser(PlaceholderParserInterface):
    """组合占位符解析器"""
    
    def __init__(self):
        # 组合语法模式
        self.composite_pattern = r'\{\{组合：(.+)\}\}'
        
        # 子占位符模式 - 匹配嵌套的占位符
        self.sub_placeholder_pattern = r'\{[^{}]*\{[^}]*\}[^{}]*\}|\{[^}]+\}'
        
        # 组合逻辑关键词
        self.composition_keywords = {
            '占': 'ratio',
            '比例': 'percentage',
            '差值': 'difference',
            '增长': 'growth',
            '总计': 'sum',
            '平均': 'average',
            '对比': 'compare'
        }
    
    async def parse(self, placeholder_text: str) -> CompositePlaceholder:
        """解析组合占位符"""
        try:
            match = re.match(self.composite_pattern, placeholder_text)
            if not match:
                raise PlaceholderSyntaxError(f"Invalid composite syntax: {placeholder_text}")
            
            composition_logic = match.group(1)
            
            # 提取子占位符
            sub_placeholders = await self._extract_sub_placeholders(composition_logic)
            
            # 分析组合逻辑
            composition_type = self._analyze_composition_type(composition_logic)
            
            # 计算置信度
            confidence_score = self._calculate_confidence(sub_placeholders, composition_logic)
            
            return CompositePlaceholder(
                statistical_type=self._infer_result_type(composition_type, sub_placeholders),
                description=f"组合分析: {composition_logic}",
                raw_text=placeholder_text,
                syntax_type=SyntaxType.COMPOSITE,
                sub_placeholders=sub_placeholders,
                composition_logic=composition_logic,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"组合占位符解析失败: {placeholder_text}, 错误: {e}")
            raise PlaceholderSyntaxError(f"Failed to parse composite placeholder: {placeholder_text}") from e
    
    def supports_syntax(self, syntax_type: SyntaxType) -> bool:
        """是否支持指定语法类型"""
        return syntax_type == SyntaxType.COMPOSITE
    
    async def _extract_sub_placeholders(self, composition_logic: str) -> List[PlaceholderSpec]:
        """提取子占位符"""
        sub_placeholders = []
        
        # 使用递归匹配找到所有嵌套占位符
        matches = self._find_nested_placeholders(composition_logic)
        
        for match in matches:
            try:
                # 创建基础解析器来解析子占位符
                from .placeholder_parser import PlaceholderParser
                parser = PlaceholderParser()
                sub_placeholder = await parser.parse(match)
                sub_placeholders.append(sub_placeholder)
            except Exception as e:
                logger.warning(f"子占位符解析失败 {match}: {e}")
                # 创建一个基础的占位符规格
                from ..models import PlaceholderSpec
                fallback_placeholder = PlaceholderSpec(
                    statistical_type=StatisticalType.STATISTICS,
                    description=f"未解析的子占位符: {match}",
                    raw_text=match,
                    syntax_type=SyntaxType.BASIC,
                    confidence_score=0.3
                )
                sub_placeholders.append(fallback_placeholder)
        
        return sub_placeholders
    
    def _find_nested_placeholders(self, text: str) -> List[str]:
        """递归查找嵌套占位符"""
        placeholders = []
        
        # 简化的嵌套匹配算法
        i = 0
        while i < len(text):
            if text[i:i+2] == '{{':
                # 找到开始位置，寻找匹配的结束位置
                start = i
                brace_count = 0
                j = i
                
                while j < len(text):
                    if text[j:j+2] == '{{':
                        brace_count += 1
                        j += 2
                    elif text[j:j+2] == '}}':
                        brace_count -= 1
                        if brace_count == 0:
                            # 找到匹配的结束位置
                            placeholder = text[start:j+2]
                            placeholders.append(placeholder)
                            i = j + 2
                            break
                        j += 2
                    else:
                        j += 1
                
                if brace_count > 0:
                    # 未找到匹配的结束括号，移动到下一个字符
                    i += 1
            else:
                i += 1
        
        return placeholders
    
    def _analyze_composition_type(self, composition_logic: str) -> str:
        """分析组合逻辑类型"""
        # 检查关键词确定组合类型
        for keyword, comp_type in self.composition_keywords.items():
            if keyword in composition_logic:
                return comp_type
        
        # 默认为比例计算
        return 'ratio'
    
    def _infer_result_type(self, composition_type: str, sub_placeholders: List[PlaceholderSpec]) -> StatisticalType:
        """推断结果的统计类型"""
        if composition_type in ['ratio', 'percentage']:
            return StatisticalType.STATISTICS
        elif composition_type in ['growth', 'difference']:
            return StatisticalType.TREND
        elif composition_type in ['compare']:
            return StatisticalType.COMPARISON
        elif composition_type in ['sum', 'average']:
            return StatisticalType.STATISTICS
        
        # 基于子占位符类型推断
        if sub_placeholders:
            # 如果所有子占位符都是同一类型，返回该类型
            types = [ph.statistical_type for ph in sub_placeholders]
            if len(set(types)) == 1:
                return types[0]
        
        # 默认返回统计类型
        return StatisticalType.STATISTICS
    
    def _calculate_confidence(self, sub_placeholders: List[PlaceholderSpec], composition_logic: str) -> float:
        """计算组合占位符的置信度"""
        base_confidence = 0.7
        
        # 子占位符数量因子
        if len(sub_placeholders) >= 2:
            base_confidence += 0.1
        
        # 子占位符置信度的影响
        if sub_placeholders:
            avg_sub_confidence = sum(ph.confidence_score for ph in sub_placeholders) / len(sub_placeholders)
            base_confidence = (base_confidence + avg_sub_confidence) / 2
        
        # 组合逻辑清晰度
        logic_clarity = self._assess_logic_clarity(composition_logic)
        base_confidence += logic_clarity * 0.1
        
        return min(base_confidence, 1.0)
    
    def _assess_logic_clarity(self, composition_logic: str) -> float:
        """评估组合逻辑的清晰度"""
        clarity_score = 0.0
        
        # 包含明确关键词的加分
        keyword_count = sum(1 for keyword in self.composition_keywords.keys() 
                          if keyword in composition_logic)
        clarity_score += min(keyword_count * 0.2, 0.8)
        
        # 逻辑长度适中的加分
        if 10 <= len(composition_logic) <= 50:
            clarity_score += 0.2
        
        return min(clarity_score, 1.0)


class AdvancedCompositeParser(CompositeParser):
    """高级组合占位符解析器 - 支持更复杂的组合逻辑"""
    
    def __init__(self):
        super().__init__()
        
        # 扩展的组合模式
        self.advanced_patterns = {
            'calculation': r'\{\{计算：(.+)\}\}',  # 数学计算
            'aggregation': r'\{\{聚合：(.+)\}\}',  # 数据聚合
            'transformation': r'\{\{转换：(.+)\}\}',  # 数据转换
        }
        
        # 数学运算符支持
        self.math_operators = {
            '+': 'add',
            '-': 'subtract', 
            '*': 'multiply',
            '/': 'divide',
            '%': 'percentage'
        }
    
    async def parse(self, placeholder_text: str) -> CompositePlaceholder:
        """解析高级组合占位符"""
        # 首先尝试基础组合解析
        if re.match(self.composite_pattern, placeholder_text):
            return await super().parse(placeholder_text)
        
        # 尝试高级模式
        for pattern_name, pattern in self.advanced_patterns.items():
            match = re.match(pattern, placeholder_text)
            if match:
                return await self._parse_advanced_pattern(
                    placeholder_text, pattern_name, match.group(1)
                )
        
        raise PlaceholderSyntaxError(f"Unsupported advanced composite syntax: {placeholder_text}")
    
    async def _parse_advanced_pattern(self, placeholder_text: str, pattern_type: str, content: str) -> CompositePlaceholder:
        """解析高级模式的组合占位符"""
        sub_placeholders = await self._extract_sub_placeholders(content)
        
        return CompositePlaceholder(
            statistical_type=self._infer_advanced_result_type(pattern_type),
            description=f"高级组合({pattern_type}): {content}",
            raw_text=placeholder_text,
            syntax_type=SyntaxType.COMPOSITE,
            sub_placeholders=sub_placeholders,
            composition_logic=content,
            confidence_score=self._calculate_advanced_confidence(pattern_type, sub_placeholders)
        )
    
    def _infer_advanced_result_type(self, pattern_type: str) -> StatisticalType:
        """推断高级模式的结果类型"""
        type_mapping = {
            'calculation': StatisticalType.STATISTICS,
            'aggregation': StatisticalType.STATISTICS,
            'transformation': StatisticalType.STATISTICS
        }
        return type_mapping.get(pattern_type, StatisticalType.STATISTICS)
    
    def _calculate_advanced_confidence(self, pattern_type: str, sub_placeholders: List[PlaceholderSpec]) -> float:
        """计算高级模式的置信度"""
        base_confidence = {
            'calculation': 0.8,
            'aggregation': 0.85,
            'transformation': 0.75
        }.get(pattern_type, 0.7)
        
        # 子占位符质量的影响
        if sub_placeholders:
            avg_sub_confidence = sum(ph.confidence_score for ph in sub_placeholders) / len(sub_placeholders)
            base_confidence = (base_confidence + avg_sub_confidence) / 2
        
        return min(base_confidence, 1.0)