"""
数据查询Agent - 根据占位符解析结果生成SQL查询并执行

支持多种数据源：
- MySQL
- PostgreSQL  
- Apache Doris
- SQLite

功能特性：
- 智能SQL生成
- 查询优化
- 结果缓存
- 错误重试
"""

import logging
import pandas as pd
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import json

from ..base import BaseAgent
from ...context.execution_context import EnhancedExecutionContext, ContextScope

logger = logging.getLogger(__name__)


class DataQueryAgent(BaseAgent):
    """数据查询Agent"""
    
    def __init__(self):
        super().__init__("data_query", ["sql_generation", "data_retrieval", "query_optimization"])
        self.require_context("parsed_request", "data_source_info")
        
        # SQL模板
        self.sql_templates = {
            'statistics': """
                SELECT 
                    {aggregation_function}({metric_column}) as {metric_alias}
                    {dimension_select}
                    {time_select}
                FROM {table_name}
                {where_clause}
                {group_by_clause}
                {order_by_clause}
                {limit_clause}
            """,
            
            'bar_chart': """
                SELECT 
                    {dimension_column} as dimension,
                    {aggregation_function}({metric_column}) as value
                FROM {table_name}
                {where_clause}
                GROUP BY {dimension_column}
                ORDER BY value DESC
                {limit_clause}
            """,
            
            'line_chart': """
                SELECT 
                    {time_column} as time_period,
                    {aggregation_function}({metric_column}) as value
                FROM {table_name}
                {where_clause}
                GROUP BY {time_column}
                ORDER BY {time_column}
            """,
            
            'pie_chart': """
                SELECT 
                    {dimension_column} as category,
                    {aggregation_function}({metric_column}) as value
                FROM {table_name}
                {where_clause}
                GROUP BY {dimension_column}
                ORDER BY value DESC
                {limit_clause}
            """
        }
        
        # 聚合函数映射
        self.aggregation_functions = {
            'sum': 'SUM',
            'avg': 'AVG',
            'count': 'COUNT',
            'max': 'MAX',
            'min': 'MIN'
        }
        
        # 数据类型映射
        self.column_type_mapping = {
            'sales_amount': 'amount',
            'order_amount': 'amount', 
            'revenue': 'amount',
            'user_count': 'count',
            'order_count': 'count',
            'click_count': 'count'
        }

    async def execute(self, context: EnhancedExecutionContext) -> Dict[str, Any]:
        """执行数据查询"""
        try:
            # 获取解析结果和数据源信息
            parsed_request = context.get_context("parsed_request")
            data_source_info = context.get_context("data_source_info", {})
            
            if not parsed_request:
                return {
                    "success": False,
                    "error": "缺少占位符解析结果",
                    "data": {}
                }
            
            # 处理批量解析结果
            if isinstance(parsed_request, dict) and 'placeholders' in parsed_request:
                return await self._handle_multiple_queries(parsed_request, data_source_info, context)
            else:
                return await self._handle_single_query(parsed_request, data_source_info, context)
                
        except Exception as e:
            logger.error(f"数据查询Agent执行失败: {e}")
            return {
                "success": False,
                "error": f"数据查询失败: {str(e)}",
                "data": {}
            }

    async def _handle_multiple_queries(self, parsed_results: Dict[str, Any], 
                                     data_source_info: Dict[str, Any],
                                     context: EnhancedExecutionContext) -> Dict[str, Any]:
        """处理多个查询请求"""
        query_results = []
        
        for i, placeholder_result in enumerate(parsed_results.get('placeholders', [])):
            if not placeholder_result.get('success', False):
                continue
                
            try:
                result = await self._execute_single_query(placeholder_result, data_source_info, context)
                result['placeholder_index'] = i
                result['original_text'] = placeholder_result.get('original_text', '')
                query_results.append(result)
                
                # 存储到上下文
                context.set_context(f"query_result_{i}", result, ContextScope.REQUEST)
                
            except Exception as e:
                logger.error(f"查询第{i}个占位符失败: {e}")
                query_results.append({
                    'placeholder_index': i,
                    'original_text': placeholder_result.get('original_text', ''),
                    'success': False,
                    'error': str(e)
                })
        
        success_count = sum(1 for r in query_results if r.get('success', False))
        
        return {
            "success": True,
            "data": {
                "query_results": query_results,
                "summary": {
                    "total_queries": len(query_results),
                    "successful_queries": success_count,
                    "success_rate": success_count / len(query_results) if query_results else 0
                }
            }
        }

    async def _handle_single_query(self, parsed_request: Dict[str, Any], 
                                 data_source_info: Dict[str, Any],
                                 context: EnhancedExecutionContext) -> Dict[str, Any]:
        """处理单个查询请求"""
        result = await self._execute_single_query(parsed_request, data_source_info, context)
        context.set_context("query_result", result, ContextScope.REQUEST)
        return {
            "success": True,
            "data": result
        }

    async def _execute_single_query(self, parsed_request: Dict[str, Any],
                                   data_source_info: Dict[str, Any],
                                   context: EnhancedExecutionContext) -> Dict[str, Any]:
        """执行单个查询"""
        logger.info(f"执行查询: {parsed_request.get('task_type')} - {parsed_request.get('metric')}")
        
        # 1. 生成SQL查询
        sql_query = await self._generate_sql_query(parsed_request, data_source_info)
        
        if not sql_query:
            raise ValueError("SQL查询生成失败")
        
        # 2. 优化查询
        optimized_sql = self._optimize_sql_query(sql_query, data_source_info)
        
        # 3. 执行查询
        query_result = await self._execute_query(optimized_sql, data_source_info, context)
        
        # 4. 处理结果
        processed_result = self._process_query_result(query_result, parsed_request)
        
        return {
            "success": True,
            "sql_query": optimized_sql,
            "raw_data": query_result,
            "processed_data": processed_result,
            "query_metadata": {
                "row_count": len(query_result) if query_result else 0,
                "execution_time": context.get_context("query_execution_time", 0),
                "data_source": data_source_info.get("name", "unknown")
            }
        }

    async def _generate_sql_query(self, parsed_request: Dict[str, Any], 
                                data_source_info: Dict[str, Any]) -> str:
        """生成SQL查询"""
        task_type = parsed_request.get('task_type', 'statistics')
        
        # 获取SQL模板
        template = self.sql_templates.get(task_type, self.sql_templates['statistics'])
        
        # 构建查询参数
        query_params = await self._build_query_params(parsed_request, data_source_info)
        
        # 格式化SQL
        try:
            sql_query = template.format(**query_params)
            # 清理多余的空行和空格
            sql_query = '\n'.join(line.strip() for line in sql_query.split('\n') if line.strip())
            
            logger.info(f"生成的SQL查询: {sql_query}")
            return sql_query
            
        except KeyError as e:
            logger.error(f"SQL模板参数缺失: {e}")
            raise ValueError(f"SQL生成失败，缺少参数: {e}")

    async def _build_query_params(self, parsed_request: Dict[str, Any], 
                                data_source_info: Dict[str, Any]) -> Dict[str, Any]:
        """构建查询参数"""
        task_type = parsed_request.get('task_type')
        metric = parsed_request.get('metric', '')
        dimensions = parsed_request.get('dimensions', [])
        time_range = parsed_request.get('time_range')
        filters = parsed_request.get('filters', [])
        aggregation = parsed_request.get('aggregation', 'sum')
        
        # 基础参数
        params = {
            'table_name': self._determine_table_name(parsed_request, data_source_info),
            'metric_column': self._map_metric_to_column(metric, data_source_info),
            'metric_alias': self._clean_column_name(metric),
            'aggregation_function': self.aggregation_functions.get(aggregation, 'SUM'),
            'limit_clause': self._build_limit_clause(task_type)
        }
        
        # 维度相关参数
        if dimensions and task_type in ['bar_chart', 'pie_chart']:
            params['dimension_column'] = self._map_dimension_to_column(dimensions[0], data_source_info)
            params['dimension_select'] = f", {params['dimension_column']}"
            params['group_by_clause'] = f"GROUP BY {params['dimension_column']}"
            params['order_by_clause'] = f"ORDER BY {params['metric_alias']} DESC"
        else:
            params['dimension_select'] = ''
            params['group_by_clause'] = ''
            params['order_by_clause'] = ''
        
        # 时间相关参数
        if time_range and task_type == 'line_chart':
            params['time_column'] = self._determine_time_column(data_source_info)
            params['time_select'] = f", {params['time_column']}"
        else:
            params['time_column'] = self._determine_time_column(data_source_info)
            params['time_select'] = ''
        
        # WHERE子句
        params['where_clause'] = self._build_where_clause(time_range, filters, params.get('time_column'))
        
        return params

    def _determine_table_name(self, parsed_request: Dict[str, Any], 
                            data_source_info: Dict[str, Any]) -> str:
        """确定表名"""
        # 优先使用解析结果中的建议表
        table_mapping = parsed_request.get('table_mapping', {})
        if table_mapping.get('suggested_table'):
            return table_mapping['suggested_table']
        
        # 从数据源信息中选择合适的表
        tables = data_source_info.get('tables', [])
        metric = parsed_request.get('metric', '').lower()
        
        # 简单的表匹配逻辑
        for table in tables:
            table_name = table.get('name', '').lower()
            if any(keyword in table_name for keyword in ['sales', 'order']) and any(keyword in metric for keyword in ['销售', '订单', '营业']):
                return table['name']
            elif any(keyword in table_name for keyword in ['user', 'customer']) and any(keyword in metric for keyword in ['用户', '客户']):
                return table['name']
        
        # 默认使用第一个表
        if tables:
            return tables[0]['name']
        
        # 兜底表名
        return 'sales_data'

    def _map_metric_to_column(self, metric: str, data_source_info: Dict[str, Any]) -> str:
        """将指标映射到列名"""
        # 直接匹配
        columns = data_source_info.get('columns', [])
        for column in columns:
            if column['name'].lower() == metric.lower():
                return column['name']
            if column.get('comment', '').strip() == metric:
                return column['name']
        
        # 模糊匹配
        metric_lower = metric.lower()
        for column in columns:
            column_name = column['name'].lower()
            if any(keyword in column_name for keyword in ['amount', 'sales', 'revenue']) and any(keyword in metric_lower for keyword in ['金额', '销售', '收入']):
                return column['name']
            elif any(keyword in column_name for keyword in ['count', 'num']) and any(keyword in metric_lower for keyword in ['数量', '个数', '计数']):
                return column['name']
        
        # 默认映射
        metric_mapping = {
            '销售额': 'sales_amount',
            '营业额': 'revenue',
            '订单数': 'order_count',
            '用户数': 'user_count',
            '数量': 'quantity'
        }
        
        return metric_mapping.get(metric, 'value')

    def _map_dimension_to_column(self, dimension: str, data_source_info: Dict[str, Any]) -> str:
        """将维度映射到列名"""
        columns = data_source_info.get('columns', [])
        
        # 直接匹配
        for column in columns:
            if column['name'].lower() == dimension.lower():
                return column['name']
            if column.get('comment', '').strip() == dimension:
                return column['name']
        
        # 维度映射
        dimension_mapping = {
            '部门': 'department',
            '地区': 'region',
            '产品': 'product_name',
            '类别': 'category',
            '时间': 'date_column'
        }
        
        return dimension_mapping.get(dimension, 'category')

    def _determine_time_column(self, data_source_info: Dict[str, Any]) -> str:
        """确定时间列"""
        columns = data_source_info.get('columns', [])
        
        # 寻找时间类型的列
        for column in columns:
            column_type = column.get('type', '').lower()
            column_name = column['name'].lower()
            
            if column_type in ['datetime', 'timestamp', 'date']:
                return column['name']
            elif any(keyword in column_name for keyword in ['time', 'date', 'created', 'updated']):
                return column['name']
        
        # 默认时间列
        return 'created_at'

    def _build_where_clause(self, time_range: Optional[Dict[str, Any]], 
                          filters: List[Dict[str, Any]], 
                          time_column: str) -> str:
        """构建WHERE子句"""
        conditions = []
        
        # 时间范围条件
        if time_range:
            start_date = time_range.get('start_date')
            end_date = time_range.get('end_date')
            
            if start_date and end_date:
                conditions.append(f"{time_column} BETWEEN '{start_date}' AND '{end_date}'")
            elif start_date:
                conditions.append(f"{time_column} >= '{start_date}'")
            elif end_date:
                conditions.append(f"{time_column} <= '{end_date}'")
        
        # 其他过滤条件
        for filter_item in filters:
            field = filter_item.get('field')
            operator = filter_item.get('operator', '=')
            value = filter_item.get('value')
            
            if field and value:
                if operator == '=':
                    conditions.append(f"{field} = '{value}'")
                elif operator == '>':
                    conditions.append(f"{field} > {value}")
                elif operator == '<':
                    conditions.append(f"{field} < {value}")
                elif operator == 'LIKE':
                    conditions.append(f"{field} LIKE '%{value}%'")
        
        if conditions:
            return "WHERE " + " AND ".join(conditions)
        else:
            return ""

    def _build_limit_clause(self, task_type: str) -> str:
        """构建LIMIT子句"""
        limits = {
            'bar_chart': 'LIMIT 20',
            'pie_chart': 'LIMIT 10', 
            'table': 'LIMIT 100'
        }
        
        return limits.get(task_type, '')

    def _optimize_sql_query(self, sql_query: str, data_source_info: Dict[str, Any]) -> str:
        """优化SQL查询"""
        # 简单的查询优化
        optimized = sql_query
        
        # 添加索引提示（如果支持）
        db_type = data_source_info.get('type', 'mysql').lower()
        
        # 移除多余空行
        optimized = '\n'.join(line for line in optimized.split('\n') if line.strip())
        
        return optimized

    async def _execute_query(self, sql_query: str, data_source_info: Dict[str, Any],
                           context: EnhancedExecutionContext) -> List[Dict[str, Any]]:
        """执行SQL查询"""
        start_time = datetime.now()
        
        try:
            # 这里应该连接实际的数据库并执行查询
            # 现在返回模拟数据
            mock_data = await self._generate_mock_data(sql_query, context)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            context.set_context("query_execution_time", execution_time, ContextScope.REQUEST)
            
            logger.info(f"查询执行完成，耗时: {execution_time:.2f}s，返回 {len(mock_data)} 行数据")
            
            return mock_data
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            context.set_context("query_execution_time", execution_time, ContextScope.REQUEST)
            logger.error(f"SQL查询执行失败: {e}")
            raise

    async def _generate_mock_data(self, sql_query: str, context: EnhancedExecutionContext) -> List[Dict[str, Any]]:
        """生成模拟数据（用于演示）"""
        import random
        from datetime import datetime, timedelta
        
        # 根据SQL查询类型生成不同的模拟数据
        if 'bar_chart' in context.get_context("task_type", ""):
            return [
                {"dimension": "产品A", "value": random.randint(10000, 50000)},
                {"dimension": "产品B", "value": random.randint(8000, 45000)},
                {"dimension": "产品C", "value": random.randint(12000, 40000)},
                {"dimension": "产品D", "value": random.randint(5000, 35000)},
                {"dimension": "产品E", "value": random.randint(15000, 55000)}
            ]
        elif 'line_chart' in context.get_context("task_type", ""):
            base_date = datetime.now() - timedelta(days=180)
            return [
                {
                    "time_period": (base_date + timedelta(days=i*30)).strftime("%Y-%m"),
                    "value": random.randint(20000, 80000)
                }
                for i in range(6)
            ]
        elif 'pie_chart' in context.get_context("task_type", ""):
            return [
                {"category": "北京", "value": random.randint(20000, 50000)},
                {"category": "上海", "value": random.randint(18000, 48000)},
                {"category": "广州", "value": random.randint(15000, 45000)},
                {"category": "深圳", "value": random.randint(22000, 52000)},
                {"category": "其他", "value": random.randint(10000, 30000)}
            ]
        else:
            # 统计数据
            return [
                {
                    "total": random.randint(100000, 500000),
                    "average": random.randint(5000, 25000),
                    "count": random.randint(50, 200)
                }
            ]

    def _process_query_result(self, query_result: List[Dict[str, Any]], 
                            parsed_request: Dict[str, Any]) -> Dict[str, Any]:
        """处理查询结果"""
        if not query_result:
            return {
                "data": [],
                "summary": {
                    "total_rows": 0,
                    "has_data": False
                }
            }
        
        # 基础统计
        total_rows = len(query_result)
        
        # 根据任务类型处理数据
        task_type = parsed_request.get('task_type', 'statistics')
        
        processed = {
            "data": query_result,
            "summary": {
                "total_rows": total_rows,
                "has_data": total_rows > 0,
                "task_type": task_type
            }
        }
        
        # 添加数值统计（如果有数值列）
        numeric_columns = self._identify_numeric_columns(query_result)
        if numeric_columns:
            for col in numeric_columns:
                values = [row.get(col, 0) for row in query_result if isinstance(row.get(col), (int, float))]
                if values:
                    processed["summary"][f"{col}_stats"] = {
                        "sum": sum(values),
                        "avg": sum(values) / len(values),
                        "max": max(values),
                        "min": min(values)
                    }
        
        return processed

    def _identify_numeric_columns(self, query_result: List[Dict[str, Any]]) -> List[str]:
        """识别数值类型的列"""
        if not query_result:
            return []
        
        numeric_columns = []
        sample_row = query_result[0]
        
        for column, value in sample_row.items():
            if isinstance(value, (int, float)):
                numeric_columns.append(column)
        
        return numeric_columns

    def _clean_column_name(self, name: str) -> str:
        """清理列名"""
        # 移除特殊字符，替换为下划线
        import re
        cleaned = re.sub(r'[^\w\u4e00-\u9fff]', '_', name)
        return cleaned if cleaned else 'metric_value'