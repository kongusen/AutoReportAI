"""
图表数据查询Agent - 第一阶段：生成和执行SQL查询获取图表数据

专门处理图表类占位符的数据查询阶段：
1. 基于语义分析生成优化的SQL查询
2. 执行SQL查询获取原始数据  
3. 存储查询结果供图表生成使用
4. 支持测试模式（仅生成SQL）和执行模式（生成+执行SQL）
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

from ..base import BaseAgent
from ...context.execution_context import EnhancedExecutionContext, ContextScope
from .sql_generation_agent import SQLGenerationAgent

logger = logging.getLogger(__name__)


class ChartDataQueryAgent(BaseAgent):
    """图表数据查询Agent - 处理图表数据的第一阶段"""
    
    def __init__(self, db_session=None, user_id: str = None):
        super().__init__("chart_data_query", ["data_retrieval", "sql_generation", "chart_data_preparation"])
        self.require_context("semantic_analysis", "data_source_context")
        
        # 复用SQL生成Agent的能力
        self.sql_generator = SQLGenerationAgent(db_session=db_session, user_id=user_id)
        self.db_session = db_session
        self.user_id = user_id
        
    async def execute(self, context: EnhancedExecutionContext) -> Dict[str, Any]:
        """执行图表数据查询"""
        try:
            # 检查执行模式
            execution_mode = context.get_context('execution_mode', 'full_execution')  # test_only | full_execution
            placeholder_text = context.get_context('placeholder_text', '')
            
            logger.info(f"图表数据查询Agent开始执行: {placeholder_text}, 模式: {execution_mode}")
            
            # 第一步：生成SQL查询（复用SQLGenerationAgent的能力）
            sql_result = await self.sql_generator.execute(context)
            
            if not sql_result.get('success', False):
                return self._create_error_result("SQL生成失败", sql_result.get('error', '未知错误'))
            
            sql_data = sql_result.get('data', {})
            sql_query = sql_data.get('sql_query', '')
            
            # 存储SQL生成结果到上下文
            context.set_context('generated_sql', sql_query, ContextScope.REQUEST)
            context.set_context('sql_metadata', sql_data, ContextScope.REQUEST)
            
            # 如果是仅SQL模式，只返回SQL不执行
            if execution_mode == 'sql_only':
                return {
                    'success': True,
                    'agent': self.name,
                    'type': 'chart_data_query_sql_only',
                    'data': {
                        'sql_query': sql_query,
                        'sql_metadata': sql_data,
                        'execution_mode': 'sql_only',
                        'chart_ready': False,
                        'message': 'SQL已生成，等待用户测试验证'
                    }
                }
            
            # 第二步：执行SQL查询获取数据（完整执行模式或仅数据查询模式）
            query_result = await self._execute_sql_query(sql_query, context)
            
            if not query_result['success']:
                return self._create_error_result("SQL执行失败", query_result.get('error', '未知错误'))
            
            # 第三步：预处理数据供图表生成使用
            processed_data = await self._preprocess_chart_data(
                query_result['raw_data'], 
                sql_data, 
                context
            )
            
            # 存储处理后的数据到上下文
            context.set_context('chart_data', processed_data, ContextScope.REQUEST)
            context.set_context('query_result', query_result, ContextScope.REQUEST)
            
            processed_data_count = len(processed_data) if isinstance(processed_data, list) else 0
            logger.info(f"图表数据查询完成: {placeholder_text}, 获取{processed_data_count}条记录")
            
            # 根据执行模式决定是否需要图表就绪
            is_chart_ready = execution_mode in ['full_execution', 'test_with_chart']
            next_stage = 'chart_generation' if is_chart_ready else 'data_review'
            
            return {
                'success': True,
                'agent': self.name,
                'type': 'chart_data_query',
                'data': {
                    'sql_query': sql_query,
                    'sql_metadata': sql_data,
                    'raw_data': query_result['raw_data'],
                    'processed_data': processed_data,
                    'execution_metadata': {
                        'execution_time_ms': query_result.get('execution_time_ms', 0),
                        'row_count': processed_data_count,
                        'query_success': True,
                        'data_quality_score': self._assess_data_quality(processed_data)
                    },
                    'chart_ready': is_chart_ready,
                    'next_stage': next_stage
                }
            }
            
        except Exception as e:
            logger.error(f"图表数据查询Agent执行失败: {e}")
            return self._create_error_result("Agent执行异常", str(e))
    
    async def _execute_sql_query(self, sql_query: str, context: EnhancedExecutionContext) -> Dict[str, Any]:
        """执行SQL查询"""
        try:
            data_source_context = context.get_context('data_source_context', {})
            data_source_id = data_source_context.get('data_source_id')
            
            if not data_source_id:
                raise ValueError("缺少数据源ID")
            
            # 使用现有的数据连接器执行查询
            from app.services.data.connectors.connector_factory import create_connector
            from app.models.data_source import DataSource
            
            # 获取数据源实例
            data_source = self.db_session.query(DataSource).filter(DataSource.id == data_source_id).first()
            if not data_source:
                raise ValueError(f"数据源不存在: {data_source_id}")
            
            connector = create_connector(data_source)
            
            start_time = datetime.now()
            
            # 执行查询
            raw_data = await connector.execute_query(sql_query)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 处理DorisQueryResult对象
            if hasattr(raw_data, 'to_dict'):
                # 是DorisQueryResult对象，转换为字典格式
                result_dict = raw_data.to_dict()
                processed_raw_data = result_dict.get('data', [])
                row_count = result_dict.get('row_count', 0)
            elif hasattr(raw_data, 'data'):
                # 有data属性的对象
                processed_raw_data = raw_data.data.to_dict(orient='records') if hasattr(raw_data.data, 'to_dict') else []
                row_count = len(processed_raw_data)
            elif isinstance(raw_data, list):
                # 已经是列表格式
                processed_raw_data = raw_data
                row_count = len(raw_data)
            else:
                # 其他格式，尝试转换
                processed_raw_data = []
                row_count = 0
            
            return {
                'success': True,
                'raw_data': processed_raw_data,  # 确保这是列表格式
                'execution_time_ms': execution_time,
                'sql_executed': sql_query,
                'row_count': row_count
            }
            
        except Exception as e:
            logger.error(f"SQL查询执行失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'raw_data': [],
                'execution_time_ms': 0
            }
    
    async def _preprocess_chart_data(
        self, 
        raw_data: List[Dict[str, Any]], 
        sql_metadata: Dict[str, Any],
        context: EnhancedExecutionContext
    ) -> List[Dict[str, Any]]:
        """预处理图表数据"""
        # 确保raw_data是列表格式
        if not raw_data or not isinstance(raw_data, list):
            logger.warning(f"原始数据格式不正确，类型: {type(raw_data)}, 内容: {raw_data}")
            return []
        
        try:
            semantic_analysis = context.get_context('semantic_analysis', {})
            chart_type_hint = semantic_analysis.get('chart_type_hint', 'bar_chart')
            
            processed_data = []
            
            for i, row in enumerate(raw_data):
                if isinstance(row, dict):
                    processed_row = self._normalize_row_data(row, chart_type_hint)
                    processed_row['row_index'] = i
                    processed_data.append(processed_row)
                else:
                    logger.warning(f"跳过非字典格式的数据行: {type(row)}, {row}")
            
            # 根据图表类型进行特殊处理
            if chart_type_hint in ['pie_chart', 'funnel_chart']:
                processed_data = self._prepare_categorical_data(processed_data)
            elif chart_type_hint in ['line_chart', 'area_chart']:
                processed_data = self._prepare_temporal_data(processed_data)
            elif chart_type_hint in ['scatter_chart']:
                processed_data = self._prepare_scatter_data(processed_data)
            
            return processed_data
            
        except Exception as e:
            logger.error(f"图表数据预处理失败: {e}")
            return raw_data  # 返回原始数据作为fallback
    
    def _normalize_row_data(self, row: Dict[str, Any], chart_type: str) -> Dict[str, Any]:
        """标准化行数据"""
        normalized = {}
        
        # 寻找合适的维度字段（作为name/category）
        dimension_field = None
        for key, value in row.items():
            if isinstance(value, str) and key.lower() in ['name', 'category', 'label', 'dimension', 'type']:
                dimension_field = key
                break
        
        if not dimension_field:
            # 找第一个字符串字段作为维度
            for key, value in row.items():
                if isinstance(value, str):
                    dimension_field = key
                    break
        
        # 寻找合适的数值字段（作为value）
        value_field = None
        for key, value in row.items():
            if isinstance(value, (int, float)) and key.lower() in ['value', 'amount', 'count', 'sum', 'total']:
                value_field = key
                break
        
        if not value_field:
            # 找第一个数值字段作为值
            for key, value in row.items():
                if isinstance(value, (int, float)):
                    value_field = key
                    break
        
        # 构建标准化数据
        normalized['name'] = row.get(dimension_field, f'项目{len(normalized)}') if dimension_field else 'Unknown'
        normalized['value'] = row.get(value_field, 0) if value_field else 0
        
        # 保留原始数据
        normalized['original'] = row.copy()
        
        # 添加额外字段（如果存在）
        for key, value in row.items():
            if key not in [dimension_field, value_field] and isinstance(value, (int, float, str)):
                normalized[f'extra_{key}'] = value
        
        return normalized
    
    def _prepare_categorical_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """准备分类数据（饼图、漏斗图）"""
        # 按值排序（降序）
        data.sort(key=lambda x: x.get('value', 0), reverse=True)
        
        # 限制数据点数量（避免图表过于复杂）
        if len(data) > 10:
            top_data = data[:9]
            others_value = sum(item.get('value', 0) for item in data[9:])
            if others_value > 0:
                top_data.append({
                    'name': '其他',
                    'value': others_value,
                    'category': 'others',
                    'original': {'aggregated_count': len(data) - 9}
                })
            return top_data
        
        return data
    
    def _prepare_temporal_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """准备时间序列数据（折线图）"""
        # 尝试按时间排序
        try:
            data.sort(key=lambda x: self._parse_temporal_key(x.get('name', '')))
        except:
            # 如果排序失败，保持原序
            pass
        
        return data
    
    def _parse_temporal_key(self, key: str) -> datetime:
        """解析时间字段"""
        import re
        from dateutil.parser import parse as date_parse
        
        # 尝试解析日期
        try:
            return date_parse(str(key))
        except:
            # 尝试解析年月格式
            if re.match(r'\d{4}-\d{2}', str(key)):
                return datetime.strptime(f"{key}-01", "%Y-%m-%d")
            # 默认返回当前时间
            return datetime.now()
    
    def _prepare_scatter_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """准备散点图数据"""
        # 为散点图添加x,y坐标
        for i, item in enumerate(data):
            if 'x' not in item:
                item['x'] = i
            if 'y' not in item:
                item['y'] = item.get('value', 0)
        
        return data
    
    def _assess_data_quality(self, data: List[Dict[str, Any]]) -> float:
        """评估数据质量"""
        if not data:
            return 0.0
        
        quality_score = 0.0
        
        # 检查数据完整性
        complete_rows = sum(1 for row in data if row.get('name') and row.get('value') is not None)
        completeness = complete_rows / len(data)
        quality_score += completeness * 0.4
        
        # 检查数值有效性
        valid_values = sum(1 for row in data if isinstance(row.get('value'), (int, float)) and row.get('value') >= 0)
        validity = valid_values / len(data)
        quality_score += validity * 0.3
        
        # 检查数据多样性
        unique_names = len(set(row.get('name', '') for row in data))
        diversity = min(unique_names / len(data), 1.0)
        quality_score += diversity * 0.3
        
        return min(quality_score, 1.0)
    
    def _create_error_result(self, stage: str, error_msg: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            'success': False,
            'agent': self.name,
            'type': 'chart_data_query_error',
            'error': f'{stage}: {error_msg}',
            'data': {
                'chart_ready': False,
                'error_stage': stage,
                'error_message': error_msg,
                'fallback_available': True
            }
        }
    
    async def test_sql_only(
        self,
        placeholder_text: str,
        data_source_id: str,
        semantic_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """仅生成和测试SQL（用于模板中的占位符分析）"""
        try:
            from ...context.execution_context import EnhancedExecutionContext
            import uuid
            
            # 创建测试上下文
            context = EnhancedExecutionContext(
                session_id=f"test_{uuid.uuid4()}",
                user_id=self.user_id or 'system',
                request={}
            )
            
            # 设置必要的上下文数据
            context.set_context('placeholder_text', placeholder_text, ContextScope.REQUEST)
            context.set_context('execution_mode', 'test_only', ContextScope.REQUEST)
            
            # 加载数据源上下文
            data_source_context = await self.sql_generator._load_data_source_context(data_source_id)
            context.set_context('data_source_context', data_source_context, ContextScope.REQUEST)
            
            # 设置语义分析（如果提供）
            if semantic_analysis:
                context.set_context('semantic_analysis', semantic_analysis, ContextScope.REQUEST)
            else:
                # 提供默认的语义分析
                default_semantic = {
                    'primary_intent': 'chart_generation',
                    'data_type': 'statistical',
                    'chart_type_hint': 'bar_chart',
                    'confidence': 0.8
                }
                context.set_context('semantic_analysis', default_semantic, ContextScope.REQUEST)
            
            # 执行SQL生成（测试模式）
            result = await self.execute(context)
            
            return result
            
        except Exception as e:
            logger.error(f"SQL测试执行失败: {e}")
            return self._create_error_result("测试执行", str(e))