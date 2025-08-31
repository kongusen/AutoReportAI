"""
基础占位符解析器

负责解析各种格式的占位符文本
"""

import logging
import re
from typing import Optional
from ..models import (
    PlaceholderSpec, ParameterizedPlaceholder, CompositePlaceholder, ConditionalPlaceholder,
    StatisticalType, SyntaxType, PlaceholderSyntaxError, PlaceholderParserInterface
)

logger = logging.getLogger(__name__)


class PlaceholderParser(PlaceholderParserInterface):
    """基础占位符解析器"""
    
    def __init__(self):
        # 定义各种语法模式
        self.syntax_patterns = {
            SyntaxType.BASIC: r'\{\{(\w+)：([^}|]+)\}\}',
            SyntaxType.PARAMETERIZED: r'\{\{(\w+)：([^|}]+)(\|([^}]+))?\}\}',
            SyntaxType.COMPOSITE: r'\{\{组合：(.+)\}\}',
            SyntaxType.CONDITIONAL: r'\{\{(\w+)：([^|}]+)\|条件=([^|}]+)(\|([^}]+))?\}\}'
        }
        
        # 统计类型映射
        self.statistical_type_mapping = {
            '统计': StatisticalType.STATISTICS,
            '趋势': StatisticalType.TREND,
            '极值': StatisticalType.EXTREME,
            '列表': StatisticalType.LIST,
            '统计图': StatisticalType.CHART,
            '对比': StatisticalType.COMPARISON,
            '预测': StatisticalType.FORECAST
        }
    
    async def parse(self, placeholder_text: str) -> PlaceholderSpec:
        """解析占位符文本"""
        try:
            # 1. 识别语法类型
            syntax_type = self._identify_syntax_type(placeholder_text)
            
            # 2. 基于语法类型进行解析
            if syntax_type == SyntaxType.BASIC:
                return await self._parse_basic(placeholder_text)
            elif syntax_type == SyntaxType.PARAMETERIZED:
                return await self._parse_parameterized(placeholder_text)
            elif syntax_type == SyntaxType.COMPOSITE:
                return await self._parse_composite(placeholder_text)
            elif syntax_type == SyntaxType.CONDITIONAL:
                return await self._parse_conditional(placeholder_text)
            else:
                raise PlaceholderSyntaxError(f"Unsupported syntax: {placeholder_text}")
                
        except Exception as e:
            logger.error(f"占位符解析失败: {placeholder_text}, 错误: {e}")
            raise PlaceholderSyntaxError(f"Failed to parse placeholder: {placeholder_text}") from e
    
    def supports_syntax(self, syntax_type: SyntaxType) -> bool:
        """是否支持指定语法类型"""
        return syntax_type in self.syntax_patterns
    
    def _identify_syntax_type(self, text: str) -> SyntaxType:
        """识别语法类型"""
        # 按复杂度从高到低检查
        for syntax_type, pattern in self.syntax_patterns.items():
            if re.match(pattern, text):
                return syntax_type
        
        raise PlaceholderSyntaxError(f"Unable to identify syntax type for: {text}")
    
    async def _parse_basic(self, text: str) -> PlaceholderSpec:
        """解析基础格式占位符"""
        match = re.match(self.syntax_patterns[SyntaxType.BASIC], text)
        if not match:
            raise PlaceholderSyntaxError(f"Invalid basic syntax: {text}")
        
        stat_type_str = match.group(1)
        description = match.group(2)
        
        # 获取统计类型
        statistical_type = self.statistical_type_mapping.get(
            stat_type_str,
            StatisticalType.STATISTICS  # 默认类型
        )
        
        return PlaceholderSpec(
            statistical_type=statistical_type,
            description=description.strip(),
            raw_text=text,
            syntax_type=SyntaxType.BASIC,
            confidence_score=0.9  # 基础语法置信度较高
        )
    
    async def _parse_parameterized(self, text: str) -> ParameterizedPlaceholder:
        """解析参数化格式占位符"""
        match = re.match(self.syntax_patterns[SyntaxType.PARAMETERIZED], text)
        if not match:
            raise PlaceholderSyntaxError(f"Invalid parameterized syntax: {text}")
        
        stat_type_str = match.group(1)
        description = match.group(2)
        params_str = match.group(4) if match.group(4) else ""
        
        # 获取统计类型
        statistical_type = self.statistical_type_mapping.get(
            stat_type_str,
            StatisticalType.STATISTICS
        )
        
        # 解析参数
        parameters = {}
        if params_str:
            for param in params_str.split('|'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    parameters[key.strip()] = value.strip()
        
        return ParameterizedPlaceholder(
            statistical_type=statistical_type,
            description=description.strip(),
            raw_text=text,
            syntax_type=SyntaxType.PARAMETERIZED,
            parameters=parameters,
            confidence_score=0.95  # 参数化语法置信度更高
        )
    
    async def _parse_composite(self, text: str) -> CompositePlaceholder:
        """解析组合格式占位符"""
        match = re.match(self.syntax_patterns[SyntaxType.COMPOSITE], text)
        if not match:
            raise PlaceholderSyntaxError(f"Invalid composite syntax: {text}")
        
        composition_logic = match.group(1)
        
        # 提取子占位符
        sub_placeholders = []
        sub_placeholder_pattern = r'\{[^}]+\}'
        sub_matches = re.findall(sub_placeholder_pattern, composition_logic)
        
        for sub_match in sub_matches:
            try:
                # 递归解析子占位符
                sub_placeholder = await self.parse(sub_match)
                sub_placeholders.append(sub_placeholder)
            except Exception as e:
                logger.warning(f"Failed to parse sub-placeholder {sub_match}: {e}")
        
        return CompositePlaceholder(
            statistical_type=StatisticalType.STATISTICS,  # 组合类型默认为统计
            description=f"组合占位符: {composition_logic}",
            raw_text=text,
            syntax_type=SyntaxType.COMPOSITE,
            sub_placeholders=sub_placeholders,
            composition_logic=composition_logic,
            confidence_score=0.8  # 组合语法相对复杂，置信度稍低
        )
    
    async def _parse_conditional(self, text: str) -> ConditionalPlaceholder:
        """解析条件格式占位符"""
        match = re.match(self.syntax_patterns[SyntaxType.CONDITIONAL], text)
        if not match:
            raise PlaceholderSyntaxError(f"Invalid conditional syntax: {text}")
        
        stat_type_str = match.group(1)
        description = match.group(2)
        condition_str = match.group(3)
        additional_params = match.group(5) if match.group(5) else ""
        
        # 获取统计类型
        statistical_type = self.statistical_type_mapping.get(
            stat_type_str,
            StatisticalType.STATISTICS
        )
        
        # 解析条件
        from ..models import FilterCondition
        conditions = []
        try:
            condition = FilterCondition.parse(condition_str)
            conditions.append(condition)
        except Exception as e:
            logger.warning(f"Failed to parse condition {condition_str}: {e}")
        
        # 处理额外参数
        fallback_logic = None
        if additional_params and "fallback=" in additional_params:
            for param in additional_params.split('|'):
                if param.startswith("fallback="):
                    fallback_logic = param.split('=', 1)[1]
        
        return ConditionalPlaceholder(
            statistical_type=statistical_type,
            description=description.strip(),
            raw_text=text,
            syntax_type=SyntaxType.CONDITIONAL,
            conditions=conditions,
            fallback_logic=fallback_logic,
            confidence_score=0.85  # 条件语法置信度中等
        )