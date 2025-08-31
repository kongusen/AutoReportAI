"""
条件占位符解析器

专门处理条件格式的占位符，支持复杂的条件逻辑
"""

import logging
import re
from typing import List, Optional, Dict, Any
from ..models import (
    ConditionalPlaceholder, FilterCondition, StatisticalType, SyntaxType,
    PlaceholderSyntaxError, PlaceholderParserInterface
)

logger = logging.getLogger(__name__)


class ConditionalParser(PlaceholderParserInterface):
    """条件占位符解析器"""
    
    def __init__(self):
        # 条件语法模式
        self.conditional_patterns = {
            'basic': r'\{\{(\w+)：([^|}]+)\|条件=([^|}]+)((\|[^}]+)*)\}\}',
            'if_then': r'\{\{(\w+)：([^|}]+)\|如果=([^|}]+)((\|[^}]+)*)\}\}',
            'when': r'\{\{(\w+)：([^|}]+)\|当=([^|}]+)((\|[^}]+)*)\}\}',
            'filter': r'\{\{(\w+)：([^|}]+)\|筛选=([^|}]+)((\|[^}]+)*)\}\}'
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
        
        # 条件操作符映射
        self.condition_operators = {
            '=': 'equals',
            '==': 'equals',
            '!=': 'not_equals',
            '<>': 'not_equals',
            '>': 'greater_than',
            '<': 'less_than',
            '>=': 'greater_equal',
            '<=': 'less_equal',
            '包含': 'contains',
            '不包含': 'not_contains',
            '开始于': 'starts_with',
            '结束于': 'ends_with',
            '在...之间': 'between',
            '属于': 'in',
            '不属于': 'not_in'
        }
        
        # 逻辑连接符
        self.logical_operators = {
            '且': 'AND',
            '并且': 'AND',
            '和': 'AND',
            '或': 'OR',
            '或者': 'OR',
            '非': 'NOT',
            '不是': 'NOT'
        }
    
    async def parse(self, placeholder_text: str) -> ConditionalPlaceholder:
        """解析条件占位符"""
        try:
            # 尝试匹配不同的条件模式
            for pattern_name, pattern in self.conditional_patterns.items():
                match = re.match(pattern, placeholder_text)
                if match:
                    return await self._parse_with_pattern(placeholder_text, pattern_name, match)
            
            raise PlaceholderSyntaxError(f"Invalid conditional syntax: {placeholder_text}")
            
        except Exception as e:
            logger.error(f"条件占位符解析失败: {placeholder_text}, 错误: {e}")
            raise PlaceholderSyntaxError(f"Failed to parse conditional placeholder: {placeholder_text}") from e
    
    def supports_syntax(self, syntax_type: SyntaxType) -> bool:
        """是否支持指定语法类型"""
        return syntax_type == SyntaxType.CONDITIONAL
    
    async def _parse_with_pattern(self, placeholder_text: str, pattern_name: str, match: re.Match) -> ConditionalPlaceholder:
        """使用特定模式解析条件占位符"""
        stat_type_str = match.group(1)
        description = match.group(2)
        condition_str = match.group(3)
        additional_params = match.group(4) if match.group(4) else ""
        
        # 获取统计类型
        statistical_type = self.statistical_type_mapping.get(
            stat_type_str,
            StatisticalType.STATISTICS
        )
        
        # 解析条件
        conditions = await self._parse_conditions(condition_str)
        
        # 解析额外参数
        fallback_logic, else_clause = await self._parse_additional_params(additional_params)
        
        # 计算置信度
        confidence_score = self._calculate_confidence(conditions, fallback_logic)
        
        return ConditionalPlaceholder(
            statistical_type=statistical_type,
            description=description.strip(),
            raw_text=placeholder_text,
            syntax_type=SyntaxType.CONDITIONAL,
            conditions=conditions,
            fallback_logic=fallback_logic,
            confidence_score=confidence_score
        )
    
    async def _parse_conditions(self, condition_str: str) -> List[FilterCondition]:
        """解析条件字符串"""
        conditions = []
        
        # 处理复合条件（包含AND, OR等逻辑连接符）
        if any(op in condition_str for op in self.logical_operators.keys()):
            conditions = await self._parse_compound_conditions(condition_str)
        else:
            # 简单条件
            condition = await self._parse_single_condition(condition_str)
            if condition:
                conditions.append(condition)
        
        return conditions
    
    async def _parse_single_condition(self, condition_str: str) -> Optional[FilterCondition]:
        """解析单个条件"""
        condition_str = condition_str.strip()
        
        # 尝试匹配各种操作符
        for op_text, op_type in self.condition_operators.items():
            if op_text in condition_str:
                parts = condition_str.split(op_text, 1)
                if len(parts) == 2:
                    field = parts[0].strip()
                    value = parts[1].strip()
                    
                    return FilterCondition(
                        field=field,
                        operator=op_type,
                        value=value
                    )
        
        # 如果没有明确操作符，默认使用等于
        if '=' not in condition_str and '>' not in condition_str and '<' not in condition_str:
            # 可能是字段存在性检查或模糊匹配
            return FilterCondition(
                field=condition_str,
                operator='exists',
                value='true'
            )
        
        logger.warning(f"无法解析条件: {condition_str}")
        return None
    
    async def _parse_compound_conditions(self, condition_str: str) -> List[FilterCondition]:
        """解析复合条件"""
        conditions = []
        
        # 简化的复合条件解析
        # 按逻辑连接符分割
        parts = []
        current_part = ""
        
        i = 0
        while i < len(condition_str):
            found_operator = False
            for op_text in self.logical_operators.keys():
                if condition_str[i:].startswith(op_text):
                    if current_part.strip():
                        parts.append(current_part.strip())
                        parts.append(op_text)
                        current_part = ""
                    i += len(op_text)
                    found_operator = True
                    break
            
            if not found_operator:
                current_part += condition_str[i]
                i += 1
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        # 解析每个条件部分
        for part in parts:
            if part not in self.logical_operators.keys():
                condition = await self._parse_single_condition(part)
                if condition:
                    conditions.append(condition)
        
        return conditions
    
    async def _parse_additional_params(self, additional_params: str) -> tuple[Optional[str], Optional[str]]:
        """解析额外参数"""
        fallback_logic = None
        else_clause = None
        
        if not additional_params:
            return fallback_logic, else_clause
        
        # 按|分割参数
        param_parts = additional_params.split('|')
        
        for param in param_parts:
            param = param.strip()
            if not param:
                continue
                
            if param.startswith('否则=') or param.startswith('else='):
                else_clause = param.split('=', 1)[1]
            elif param.startswith('默认=') or param.startswith('default='):
                fallback_logic = param.split('=', 1)[1]
            elif param.startswith('失败时=') or param.startswith('fallback='):
                fallback_logic = param.split('=', 1)[1]
        
        return fallback_logic, else_clause
    
    def _calculate_confidence(self, conditions: List[FilterCondition], fallback_logic: Optional[str]) -> float:
        """计算条件占位符的置信度"""
        base_confidence = 0.8
        
        # 条件数量的影响
        condition_factor = min(len(conditions) * 0.05, 0.15)
        base_confidence += condition_factor
        
        # 有完整的条件解析
        if all(cond.field and cond.operator and cond.value for cond in conditions):
            base_confidence += 0.05
        
        # 有回退逻辑提高可靠性
        if fallback_logic:
            base_confidence += 0.05
        
        return min(base_confidence, 1.0)


class AdvancedConditionalParser(ConditionalParser):
    """高级条件占位符解析器 - 支持更复杂的条件逻辑"""
    
    def __init__(self):
        super().__init__()
        
        # 扩展条件模式
        self.advanced_patterns = {
            'case_when': r'\{\{(\w+)：([^|}]+)\|情况=(.+)\}\}',
            'switch': r'\{\{(\w+)：([^|}]+)\|选择=(.+)\}\}',
            'nested': r'\{\{(\w+)：([^|}]+)\|条件=\{(.+)\}((\|[^}]+)*)\}\}'
        }
        
        # 高级条件函数
        self.condition_functions = {
            'is_null': lambda x: x is None or x == '',
            'is_not_null': lambda x: x is not None and x != '',
            'is_empty': lambda x: len(str(x).strip()) == 0,
            'is_not_empty': lambda x: len(str(x).strip()) > 0,
            'matches_regex': lambda x, pattern: re.match(pattern, str(x)) is not None,
            'in_range': lambda x, min_val, max_val: min_val <= float(x) <= max_val
        }
    
    async def parse(self, placeholder_text: str) -> ConditionalPlaceholder:
        """解析高级条件占位符"""
        # 首先尝试基础条件解析
        try:
            return await super().parse(placeholder_text)
        except PlaceholderSyntaxError:
            pass
        
        # 尝试高级模式
        for pattern_name, pattern in self.advanced_patterns.items():
            match = re.match(pattern, placeholder_text)
            if match:
                return await self._parse_advanced_pattern(placeholder_text, pattern_name, match)
        
        raise PlaceholderSyntaxError(f"Unsupported advanced conditional syntax: {placeholder_text}")
    
    async def _parse_advanced_pattern(self, placeholder_text: str, pattern_name: str, match: re.Match) -> ConditionalPlaceholder:
        """解析高级模式的条件占位符"""
        stat_type_str = match.group(1)
        description = match.group(2)
        
        # 根据模式类型处理不同的条件逻辑
        if pattern_name == 'case_when':
            conditions = await self._parse_case_when(match.group(3))
        elif pattern_name == 'switch':
            conditions = await self._parse_switch_case(match.group(3))
        elif pattern_name == 'nested':
            conditions = await self._parse_nested_conditions(match.group(3))
        else:
            conditions = []
        
        statistical_type = self.statistical_type_mapping.get(
            stat_type_str,
            StatisticalType.STATISTICS
        )
        
        return ConditionalPlaceholder(
            statistical_type=statistical_type,
            description=description.strip(),
            raw_text=placeholder_text,
            syntax_type=SyntaxType.CONDITIONAL,
            conditions=conditions,
            fallback_logic=None,
            confidence_score=self._calculate_advanced_confidence(pattern_name, conditions)
        )
    
    async def _parse_case_when(self, case_str: str) -> List[FilterCondition]:
        """解析CASE WHEN模式的条件"""
        conditions = []
        
        # 解析CASE WHEN THEN结构
        cases = re.findall(r'当\s*([^那]+)\s*那么\s*([^;,]+)', case_str)
        
        for condition_text, then_value in cases:
            condition = await self._parse_single_condition(condition_text.strip())
            if condition:
                # 将结果值存储在条件的扩展属性中
                condition.then_value = then_value.strip()
                conditions.append(condition)
        
        return conditions
    
    async def _parse_switch_case(self, switch_str: str) -> List[FilterCondition]:
        """解析Switch Case模式的条件"""
        conditions = []
        
        # 解析switch case结构
        cases = re.findall(r'情况\s*([^:：]+)[:：]\s*([^;,]+)', switch_str)
        
        for case_value, result_value in cases:
            condition = FilterCondition(
                field='switch_field',  # 这需要从上下文中确定
                operator='equals',
                value=case_value.strip()
            )
            condition.then_value = result_value.strip()
            conditions.append(condition)
        
        return conditions
    
    async def _parse_nested_conditions(self, nested_str: str) -> List[FilterCondition]:
        """解析嵌套条件"""
        # 递归解析嵌套的条件结构
        return await self._parse_conditions(nested_str)
    
    def _calculate_advanced_confidence(self, pattern_name: str, conditions: List[FilterCondition]) -> float:
        """计算高级模式的置信度"""
        base_confidence = {
            'case_when': 0.85,
            'switch': 0.80,
            'nested': 0.75
        }.get(pattern_name, 0.70)
        
        # 条件完整性的影响
        if conditions and all(hasattr(cond, 'then_value') for cond in conditions):
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)