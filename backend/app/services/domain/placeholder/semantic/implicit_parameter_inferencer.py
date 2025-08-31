"""
隐式参数推断器

根据语义分析结果推断隐含的参数
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from ..models import PlaceholderSpec, StatisticalType, DocumentContext

logger = logging.getLogger(__name__)


class ImplicitParameterInferencer:
    """隐式参数推断器"""
    
    def __init__(self):
        # 参数推断规则
        self.inference_rules = {
            # 统计类型相关的默认参数
            StatisticalType.STATISTICS: {
                'default_params': {
                    '聚合方式': 'sum'
                },
                'contextual_params': ['时间范围', '分组']
            },
            
            StatisticalType.TREND: {
                'default_params': {
                    '时间粒度': 'monthly',
                    '对比期': 'previous'
                },
                'contextual_params': ['时间范围']
            },
            
            StatisticalType.LIST: {
                'default_params': {
                    '数量': '10',
                    '排序': 'desc'
                },
                'contextual_params': ['分组', '条件']
            },
            
            StatisticalType.COMPARISON: {
                'default_params': {
                    '对比期': 'last_period'
                },
                'contextual_params': ['基准', '时间范围']
            },
            
            StatisticalType.EXTREME: {
                'default_params': {
                    '极值类型': 'max'
                },
                'contextual_params': ['条件', '分组']
            },
            
            StatisticalType.CHART: {
                'default_params': {
                    '图表类型': 'bar_chart'
                },
                'contextual_params': ['时间范围', '分组']
            },
            
            StatisticalType.FORECAST: {
                'default_params': {
                    '预测期间': '3_months',
                    '置信区间': '95%'
                },
                'contextual_params': ['历史数据范围']
            }
        }
        
        # 语义关键词到参数的映射
        self.semantic_param_mapping = {
            # 时间相关
            '本月': {'时间范围': 'current_month'},
            '上月': {'时间范围': 'last_month'},
            '今年': {'时间范围': 'current_year'},
            '去年': {'时间范围': 'last_year'},
            '本季度': {'时间范围': 'current_quarter'},
            
            # 排序相关
            '最好': {'排序': 'desc', '数量': '1'},
            '最差': {'排序': 'asc', '数量': '1'},
            '前十': {'排序': 'desc', '数量': '10'},
            '前五': {'排序': 'desc', '数量': '5'},
            'TOP': {'排序': 'desc'},
            
            # 对比相关
            '同比': {'对比期': 'same_period_last_year'},
            '环比': {'对比期': 'last_period'},
            '相比': {'对比期': 'comparison_base'},
            
            # 组织相关
            '华东区': {'部门': '华东区'},
            '华南区': {'部门': '华南区'},
            '华北区': {'部门': '华北区'},
            
            # 聚合相关
            '总': {'聚合方式': 'sum'},
            '平均': {'聚合方式': 'avg'},
            '数量': {'聚合方式': 'count'},
            
            # 图表相关
            '柱状图': {'图表类型': 'bar_chart'},
            '折线图': {'图表类型': 'line_chart'},
            '饼图': {'图表类型': 'pie_chart'},
        }
        
        # 业务领域参数映射
        self.domain_param_mapping = {
            'sales': {
                'default_grouping': '销售区域',
                'default_time_range': 'monthly',
                'common_conditions': ['销售额>0', '状态=已完成']
            },
            'finance': {
                'default_grouping': '科目',
                'default_time_range': 'quarterly',
                'common_conditions': ['金额!=0']
            },
            'marketing': {
                'default_grouping': '渠道',
                'default_time_range': 'weekly',
                'common_conditions': ['活跃=true']
            }
        }
        
        # 上下文线索到参数的映射
        self.context_clue_mapping = {
            '报告': {'报告类型': 'summary'},
            '明细': {'报告类型': 'detail'},
            '汇总': {'聚合方式': 'sum'},
            '分析': {'分析类型': 'analytical'},
            '监控': {'更新频率': 'daily'}
        }
    
    async def infer_parameters(
        self,
        placeholder_spec: PlaceholderSpec,
        semantic_info: Dict[str, Any],
        context: Optional[DocumentContext] = None
    ) -> Dict[str, str]:
        """推断隐式参数"""
        try:
            inferred_params = {}
            
            # 1. 基于统计类型的默认参数
            type_params = await self._infer_from_stat_type(placeholder_spec.statistical_type)
            inferred_params.update(type_params)
            
            # 2. 基于语义分析的参数
            semantic_params = await self._infer_from_semantics(
                placeholder_spec.description, semantic_info
            )
            inferred_params.update(semantic_params)
            
            # 3. 基于上下文的参数
            if context:
                context_params = await self._infer_from_context(context, semantic_info)
                inferred_params.update(context_params)
            
            # 4. 基于业务领域的参数
            domain_params = await self._infer_from_domain(semantic_info)
            inferred_params.update(domain_params)
            
            # 5. 智能参数优化
            optimized_params = await self._optimize_parameters(
                inferred_params, placeholder_spec, semantic_info
            )
            
            logger.debug(f"推断参数完成: {len(optimized_params)} 个参数")
            return optimized_params
            
        except Exception as e:
            logger.error(f"参数推断失败: {e}")
            return {}
    
    async def _infer_from_stat_type(self, stat_type: StatisticalType) -> Dict[str, str]:
        """基于统计类型推断参数"""
        if stat_type not in self.inference_rules:
            return {}
        
        rules = self.inference_rules[stat_type]
        return rules['default_params'].copy()
    
    async def _infer_from_semantics(
        self,
        description: str,
        semantic_info: Dict[str, Any]
    ) -> Dict[str, str]:
        """基于语义分析推断参数"""
        inferred_params = {}
        
        # 从描述中提取语义关键词
        for keyword, params in self.semantic_param_mapping.items():
            if keyword in description:
                inferred_params.update(params)
        
        # 从语义实体中推断参数
        entities = semantic_info.get('entities', [])
        for entity in entities:
            entity_params = await self._infer_from_entity(entity)
            inferred_params.update(entity_params)
        
        # 从数据维度中推断参数
        data_dimensions = semantic_info.get('data_dimensions', {})
        dimension_params = await self._infer_from_dimensions(data_dimensions)
        inferred_params.update(dimension_params)
        
        return inferred_params
    
    async def _infer_from_entity(self, entity: Dict[str, Any]) -> Dict[str, str]:
        """从实体推断参数"""
        params = {}
        entity_type = entity.get('type')
        entity_text = entity.get('text', '')
        
        if entity_type == 'TIME_PERIOD':
            params['时间范围'] = self._normalize_time_period(entity_text)
        elif entity_type == 'ORGANIZATION':
            params['部门'] = entity_text
        elif entity_type == 'PRODUCT':
            params['产品线'] = entity_text
        elif entity_type == 'METRIC':
            # 根据指标类型推断聚合方式
            if '数量' in entity_text or '个数' in entity_text:
                params['聚合方式'] = 'count'
            elif '平均' in entity_text:
                params['聚合方式'] = 'avg'
            elif '总' in entity_text or '合计' in entity_text:
                params['聚合方式'] = 'sum'
        
        return params
    
    async def _infer_from_dimensions(self, data_dimensions: Dict[str, Any]) -> Dict[str, str]:
        """从数据维度推断参数"""
        params = {}
        
        # 时间粒度
        granularity = data_dimensions.get('granularity')
        if granularity:
            params['时间粒度'] = granularity
        
        # 时间维度
        time_dimension = data_dimensions.get('time_dimension')
        if time_dimension:
            params['时间范围'] = self._normalize_time_period(time_dimension)
        
        # 组织维度
        org_dimension = data_dimensions.get('organizational_dimension')
        if org_dimension:
            params['分组'] = org_dimension
        
        return params
    
    async def _infer_from_context(
        self,
        context: DocumentContext,
        semantic_info: Dict[str, Any]
    ) -> Dict[str, str]:
        """基于文档上下文推断参数"""
        params = {}
        
        # 从段落内容中提取线索
        paragraph_content = context.paragraph_content
        section_title = context.section_title
        
        # 分析上下文线索
        context_text = f"{paragraph_content} {section_title}"
        
        for clue, clue_params in self.context_clue_mapping.items():
            if clue in context_text:
                params.update(clue_params)
        
        # 从章节标题推断参数
        if '月度' in section_title:
            params['时间粒度'] = 'monthly'
        elif '季度' in section_title:
            params['时间粒度'] = 'quarterly'
        elif '年度' in section_title:
            params['时间粒度'] = 'yearly'
        
        # 从文档结构推断参数
        doc_structure = context.document_structure
        if doc_structure and '报告类型' in doc_structure:
            params['报告类型'] = doc_structure['报告类型']
        
        return params
    
    async def _infer_from_domain(self, semantic_info: Dict[str, Any]) -> Dict[str, str]:
        """基于业务领域推断参数"""
        params = {}
        
        domain = semantic_info.get('business_domain', 'general')
        
        if domain in self.domain_param_mapping:
            domain_config = self.domain_param_mapping[domain]
            
            # 默认分组
            if 'default_grouping' in domain_config:
                params['分组'] = domain_config['default_grouping']
            
            # 默认时间范围
            if 'default_time_range' in domain_config:
                params['时间粒度'] = domain_config['default_time_range']
        
        return params
    
    async def _optimize_parameters(
        self,
        params: Dict[str, str],
        placeholder_spec: PlaceholderSpec,
        semantic_info: Dict[str, Any]
    ) -> Dict[str, str]:
        """优化参数组合"""
        optimized_params = params.copy()
        
        # 参数冲突解决
        optimized_params = await self._resolve_parameter_conflicts(optimized_params)
        
        # 参数完整性检查
        optimized_params = await self._ensure_parameter_completeness(
            optimized_params, placeholder_spec.statistical_type
        )
        
        # 参数值标准化
        optimized_params = await self._normalize_parameter_values(optimized_params)
        
        return optimized_params
    
    async def _resolve_parameter_conflicts(self, params: Dict[str, str]) -> Dict[str, str]:
        """解决参数冲突"""
        resolved_params = params.copy()
        
        # 时间相关参数冲突解决
        if '时间范围' in params and '时间粒度' in params:
            time_range = params['时间范围']
            time_granularity = params['时间粒度']
            
            # 检查兼容性
            if not self._are_time_params_compatible(time_range, time_granularity):
                # 优先保留时间范围，调整粒度
                resolved_params['时间粒度'] = self._adjust_granularity_for_range(time_range)
        
        # 排序和数量参数冲突解决
        if '排序' in params and '数量' not in params:
            # 如果有排序但没有数量，添加默认数量
            resolved_params['数量'] = '10'
        
        return resolved_params
    
    async def _ensure_parameter_completeness(
        self,
        params: Dict[str, str],
        stat_type: StatisticalType
    ) -> Dict[str, str]:
        """确保参数完整性"""
        complete_params = params.copy()
        
        # 基于统计类型确保必要参数
        if stat_type == StatisticalType.LIST:
            if '排序' not in complete_params:
                complete_params['排序'] = 'desc'
            if '数量' not in complete_params:
                complete_params['数量'] = '10'
        
        elif stat_type == StatisticalType.TREND:
            if '时间粒度' not in complete_params:
                complete_params['时间粒度'] = 'monthly'
        
        elif stat_type == StatisticalType.COMPARISON:
            if '对比期' not in complete_params:
                complete_params['对比期'] = 'last_period'
        
        return complete_params
    
    async def _normalize_parameter_values(self, params: Dict[str, str]) -> Dict[str, str]:
        """标准化参数值"""
        normalized_params = {}
        
        for key, value in params.items():
            normalized_value = await self._normalize_single_parameter(key, value)
            normalized_params[key] = normalized_value
        
        return normalized_params
    
    async def _normalize_single_parameter(self, param_name: str, param_value: str) -> str:
        """标准化单个参数值"""
        # 时间相关参数标准化
        if param_name in ['时间范围', '对比期']:
            return self._normalize_time_period(param_value)
        
        # 排序参数标准化
        elif param_name == '排序':
            if param_value in ['降序', '从高到低', 'desc']:
                return 'desc'
            elif param_value in ['升序', '从低到高', 'asc']:
                return 'asc'
            return param_value
        
        # 数量参数标准化
        elif param_name == '数量':
            # 提取数字
            import re
            numbers = re.findall(r'\d+', param_value)
            return numbers[0] if numbers else param_value
        
        # 图表类型标准化
        elif param_name == '图表类型':
            chart_mapping = {
                '柱状图': 'bar_chart',
                '折线图': 'line_chart',
                '饼图': 'pie_chart',
                '散点图': 'scatter_plot'
            }
            return chart_mapping.get(param_value, param_value)
        
        return param_value
    
    def _normalize_time_period(self, time_text: str) -> str:
        """标准化时间期间"""
        # 时间期间标准化映射
        time_mapping = {
            '本月': 'current_month',
            '上月': 'last_month',
            '这个月': 'current_month',
            '上个月': 'last_month',
            '今年': 'current_year',
            '去年': 'last_year',
            '本季度': 'current_quarter',
            '上季度': 'last_quarter',
            '同期': 'same_period_last_year',
            '上年同期': 'same_period_last_year'
        }
        
        return time_mapping.get(time_text, time_text)
    
    def _are_time_params_compatible(self, time_range: str, time_granularity: str) -> bool:
        """检查时间参数是否兼容"""
        # 简单的兼容性检查
        if 'month' in time_range and time_granularity == 'yearly':
            return False
        if 'year' in time_range and time_granularity == 'daily':
            return False
        return True
    
    def _adjust_granularity_for_range(self, time_range: str) -> str:
        """根据时间范围调整粒度"""
        if 'month' in time_range:
            return 'monthly'
        elif 'year' in time_range:
            return 'yearly'
        elif 'quarter' in time_range:
            return 'quarterly'
        else:
            return 'monthly'  # 默认
    
    def get_inference_explanation(
        self,
        inferred_params: Dict[str, str],
        placeholder_spec: PlaceholderSpec,
        semantic_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """获取推断解释"""
        explanation = {
            'inferred_parameters_count': len(inferred_params),
            'inference_sources': [],
            'parameter_details': {}
        }
        
        # 分析推断来源
        stat_type = placeholder_spec.statistical_type
        if stat_type in self.inference_rules:
            default_params = self.inference_rules[stat_type]['default_params']
            for param in inferred_params:
                if param in default_params:
                    explanation['inference_sources'].append(f"{param} 来自统计类型默认设置")
        
        # 语义推断来源
        description = placeholder_spec.description
        for keyword in self.semantic_param_mapping:
            if keyword in description:
                explanation['inference_sources'].append(f"关键词 '{keyword}' 触发了参数推断")
        
        # 参数详情
        for param, value in inferred_params.items():
            explanation['parameter_details'][param] = {
                'value': value,
                'confidence': 0.7,  # 简化的置信度
                'source': 'semantic_inference'
            }
        
        return explanation