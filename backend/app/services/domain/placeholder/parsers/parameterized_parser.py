"""
参数化占位符解析器

专门处理参数化格式的占位符
"""

import logging
import re
from typing import Dict, List, Optional
from ..models import (
    ParameterizedPlaceholder, StatisticalType, SyntaxType,
    PlaceholderSyntaxError, PlaceholderParserInterface,
    TimeRange, FilterCondition, SortSpec
)

logger = logging.getLogger(__name__)


class ParameterizedParser(PlaceholderParserInterface):
    """参数化占位符解析器"""
    
    def __init__(self):
        # 参数化语法模式
        self.parameterized_pattern = r'\{\{(\w+)：([^|}]+)(\|([^}]+))?\}\}'
        
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
        
        # 参数处理器映射
        self.parameter_processors = {
            '时间范围': self._process_time_range,
            '时间粒度': self._process_time_granularity,
            '部门': self._process_department,
            '条件': self._process_condition,
            '分组': self._process_grouping,
            '排序': self._process_sorting,
            '数量': self._process_limit,
            '类型': self._process_chart_type,
            '对比期': self._process_comparison_period
        }
    
    async def parse(self, placeholder_text: str) -> ParameterizedPlaceholder:
        """解析参数化占位符"""
        try:
            match = re.match(self.parameterized_pattern, placeholder_text)
            if not match:
                raise PlaceholderSyntaxError(f"Invalid parameterized syntax: {placeholder_text}")
            
            stat_type_str = match.group(1)
            description = match.group(2)
            params_str = match.group(4) if match.group(4) else ""
            
            # 获取统计类型
            statistical_type = self.statistical_type_mapping.get(
                stat_type_str,
                StatisticalType.STATISTICS
            )
            
            # 解析参数
            parameters = await self._parse_parameters(params_str)
            
            # 验证参数兼容性
            self._validate_parameters(statistical_type, parameters)
            
            return ParameterizedPlaceholder(
                statistical_type=statistical_type,
                description=description.strip(),
                raw_text=placeholder_text,
                syntax_type=SyntaxType.PARAMETERIZED,
                parameters=parameters,
                confidence_score=self._calculate_confidence(statistical_type, parameters)
            )
            
        except Exception as e:
            logger.error(f"参数化占位符解析失败: {placeholder_text}, 错误: {e}")
            raise PlaceholderSyntaxError(f"Failed to parse parameterized placeholder: {placeholder_text}") from e
    
    def supports_syntax(self, syntax_type: SyntaxType) -> bool:
        """是否支持指定语法类型"""
        return syntax_type == SyntaxType.PARAMETERIZED
    
    async def _parse_parameters(self, params_str: str) -> Dict[str, str]:
        """解析参数字符串"""
        parameters = {}
        
        if not params_str:
            return parameters
        
        # 按|分割参数
        param_parts = params_str.split('|')
        
        for param in param_parts:
            if '=' in param:
                key, value = param.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # 处理特殊参数
                if key in self.parameter_processors:
                    processed_value = await self.parameter_processors[key](value)
                    parameters[key] = processed_value
                else:
                    parameters[key] = value
            else:
                # 处理无值参数（如布尔标记）
                param = param.strip()
                if param:
                    parameters[param] = "true"
        
        return parameters
    
    def _validate_parameters(self, stat_type: StatisticalType, parameters: Dict[str, str]):
        """验证参数与统计类型的兼容性"""
        # 列表类型需要排序和数量参数
        if stat_type == StatisticalType.LIST:
            if '数量' not in parameters:
                logger.warning(f"列表类型建议指定数量参数")
        
        # 图表类型需要类型参数
        if stat_type == StatisticalType.CHART:
            if '类型' not in parameters:
                logger.warning(f"图表类型建议指定图表类型参数")
        
        # 对比类型需要对比期参数
        if stat_type == StatisticalType.COMPARISON:
            if '对比期' not in parameters:
                logger.warning(f"对比类型建议指定对比期参数")
    
    def _calculate_confidence(self, stat_type: StatisticalType, parameters: Dict[str, str]) -> float:
        """计算置信度分数"""
        base_confidence = 0.85
        
        # 参数完整性加分
        parameter_bonus = len(parameters) * 0.02
        
        # 特定类型参数匹配度
        type_bonus = 0.0
        if stat_type == StatisticalType.LIST and ('排序' in parameters and '数量' in parameters):
            type_bonus = 0.05
        elif stat_type == StatisticalType.CHART and '类型' in parameters:
            type_bonus = 0.05
        elif stat_type == StatisticalType.COMPARISON and '对比期' in parameters:
            type_bonus = 0.05
        
        return min(base_confidence + parameter_bonus + type_bonus, 1.0)
    
    # 参数处理器方法
    async def _process_time_range(self, value: str) -> str:
        """处理时间范围参数"""
        # 标准化时间格式
        if re.match(r'\d{4}-\d{2}', value):  # YYYY-MM格式
            return value
        elif re.match(r'\d{4}年\d{1,2}月', value):  # 中文格式转换
            # 转换为YYYY-MM格式
            year_month = re.findall(r'(\d{4})年(\d{1,2})月', value)[0]
            return f"{year_month[0]}-{year_month[1]:0>2}"
        
        return value
    
    async def _process_time_granularity(self, value: str) -> str:
        """处理时间粒度参数"""
        granularity_mapping = {
            '日': 'daily',
            '周': 'weekly', 
            '月': 'monthly',
            '季度': 'quarterly',
            '年': 'yearly'
        }
        return granularity_mapping.get(value, value)
    
    async def _process_department(self, value: str) -> str:
        """处理部门参数"""
        # 标准化部门名称
        department_mapping = {
            '华东': '华东区',
            '华南': '华南区',
            '华北': '华北区',
            '华中': '华中区',
            '西南': '西南区',
            '西北': '西北区'
        }
        return department_mapping.get(value, value)
    
    async def _process_condition(self, value: str) -> str:
        """处理条件参数"""
        # 标准化条件表达式
        return value.strip()
    
    async def _process_grouping(self, value: str) -> str:
        """处理分组参数"""
        # 标准化分组字段
        grouping_mapping = {
            '地区': 'region',
            '部门': 'department',
            '产品': 'product',
            '时间': 'time_period'
        }
        return grouping_mapping.get(value, value)
    
    async def _process_sorting(self, value: str) -> str:
        """处理排序参数"""
        # 标准化排序方向
        if value in ['降序', 'desc', '从高到低']:
            return 'desc'
        elif value in ['升序', 'asc', '从低到高']:
            return 'asc'
        return value
    
    async def _process_limit(self, value: str) -> str:
        """处理数量限制参数"""
        # 提取数字
        import re
        numbers = re.findall(r'\d+', value)
        if numbers:
            return numbers[0]
        return value
    
    async def _process_chart_type(self, value: str) -> str:
        """处理图表类型参数"""
        # 标准化图表类型
        chart_type_mapping = {
            '柱状图': 'bar_chart',
            '条形图': 'horizontal_bar_chart',
            '折线图': 'line_chart',
            '饼图': 'pie_chart',
            '散点图': 'scatter_plot',
            '面积图': 'area_chart'
        }
        return chart_type_mapping.get(value, value)
    
    async def _process_comparison_period(self, value: str) -> str:
        """处理对比期参数"""
        # 标准化对比期
        comparison_mapping = {
            '上月': 'last_month',
            '去年': 'last_year',
            '上季度': 'last_quarter',
            '同期': 'same_period_last_year'
        }
        return comparison_mapping.get(value, value)