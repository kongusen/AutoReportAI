"""
Query Builder Service

基于schema信息构建智能查询的服务
"""

import logging
import re
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .schema_service import DatabaseSchema, TableSchema

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """查询类型"""
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    COUNT = "count"
    AGGREGATE = "aggregate"


@dataclass
class QueryContext:
    """查询上下文"""
    query_type: QueryType
    target_tables: List[str] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    joins: List[Dict[str, str]] = field(default_factory=list)
    aggregations: List[Dict[str, str]] = field(default_factory=list)
    order_by: List[Dict[str, str]] = field(default_factory=list)
    limit: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SchemaAwareQueryBuilder:
    """基于schema的智能查询构建器"""
    
    def __init__(self, schema: DatabaseSchema):
        self.schema = schema
        self.table_relationships = self._build_relationship_map()
    
    def _build_relationship_map(self) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
        """构建表关系映射"""
        relationships = {}
        
        for table_name, table in self.schema.tables.items():
            relationships[table_name] = {'outgoing': [], 'incoming': []}
            
            # 外键关系
            for fk in table.foreign_keys:
                relationships[table_name]['outgoing'].append({
                    'target_table': fk.get('referenced_table'),
                    'source_column': fk.get('column'),
                    'target_column': fk.get('referenced_column'),
                    'type': 'foreign_key'
                })
        
        # 构建反向关系
        for table_name, table_rels in relationships.items():
            for outgoing in table_rels['outgoing']:
                target_table = outgoing['target_table']
                if target_table in relationships:
                    relationships[target_table]['incoming'].append({
                        'source_table': table_name,
                        'source_column': outgoing['source_column'],
                        'target_column': outgoing['target_column'],
                        'type': 'foreign_key'
                    })
        
        return relationships
    
    def suggest_columns_for_table(self, table_name: str, 
                                 include_related: bool = True) -> List[Dict[str, Any]]:
        """建议表的列"""
        suggestions = []
        
        if table_name not in self.schema.tables:
            return suggestions
        
        table = self.schema.tables[table_name]
        
        # 添加当前表的列
        for column in table.columns:
            suggestions.append({
                'table': table_name,
                'column': column['name'],
                'type': column.get('type'),
                'nullable': column.get('nullable', True),
                'comment': column.get('comment'),
                'source': 'direct'
            })
        
        # 添加相关表的列
        if include_related and table_name in self.table_relationships:
            for rel in self.table_relationships[table_name]['outgoing']:
                related_table = rel['target_table']
                if related_table in self.schema.tables:
                    for column in self.schema.tables[related_table].columns:
                        suggestions.append({
                            'table': related_table,
                            'column': column['name'],
                            'type': column.get('type'),
                            'nullable': column.get('nullable', True),
                            'comment': column.get('comment'),
                            'source': 'related',
                            'relationship': rel
                        })
        
        return suggestions
    
    def find_join_path(self, source_table: str, target_table: str) -> List[Dict[str, str]]:
        """找出两个表之间的连接路径"""
        if source_table not in self.schema.tables or target_table not in self.schema.tables:
            return []
        
        if source_table == target_table:
            return []
        
        # 使用BFS寻找最短路径
        from collections import deque
        
        queue = deque([(source_table, [])])
        visited = {source_table}
        
        while queue:
            current_table, path = queue.popleft()
            
            if current_table == target_table:
                return path
            
            if current_table in self.table_relationships:
                # 检查外键关系
                for rel in self.table_relationships[current_table]['outgoing']:
                    next_table = rel['target_table']
                    if next_table not in visited and next_table in self.schema.tables:
                        visited.add(next_table)
                        new_path = path + [{
                            'from_table': current_table,
                            'to_table': next_table,
                            'from_column': rel['source_column'],
                            'to_column': rel['target_column'],
                            'join_type': 'INNER'
                        }]
                        queue.append((next_table, new_path))
                
                # 检查反向关系
                for rel in self.table_relationships[current_table]['incoming']:
                    next_table = rel['source_table']
                    if next_table not in visited and next_table in self.schema.tables:
                        visited.add(next_table)
                        new_path = path + [{
                            'from_table': current_table,
                            'to_table': next_table,
                            'from_column': rel['target_column'],
                            'to_column': rel['source_column'],
                            'join_type': 'INNER'
                        }]
                        queue.append((next_table, new_path))
        
        return []  # 没有找到路径
    
    def build_select_query(self, context: QueryContext) -> str:
        """构建SELECT查询"""
        if not context.target_tables:
            raise ValueError("No target tables specified")
        
        primary_table = context.target_tables[0]
        columns_clause = self._build_columns_clause(context.columns, primary_table)
        from_clause = self._build_from_clause(context.target_tables)
        joins_clause = self._build_joins_clause(context.joins)
        where_clause = self._build_where_clause(context.conditions)
        order_clause = self._build_order_clause(context.order_by)
        limit_clause = self._build_limit_clause(context.limit)
        
        query_parts = [
            f"SELECT {columns_clause}",
            f"FROM {from_clause}"
        ]
        
        if joins_clause:
            query_parts.append(joins_clause)
        
        if where_clause:
            query_parts.append(f"WHERE {where_clause}")
        
        if order_clause:
            query_parts.append(f"ORDER BY {order_clause}")
        
        if limit_clause:
            query_parts.append(limit_clause)
        
        return "\n".join(query_parts)
    
    def build_count_query(self, context: QueryContext) -> str:
        """构建COUNT查询"""
        if not context.target_tables:
            raise ValueError("No target tables specified")
        
        primary_table = context.target_tables[0]
        from_clause = self._build_from_clause(context.target_tables)
        joins_clause = self._build_joins_clause(context.joins)
        where_clause = self._build_where_clause(context.conditions)
        
        query_parts = [
            "SELECT COUNT(*)",
            f"FROM {from_clause}"
        ]
        
        if joins_clause:
            query_parts.append(joins_clause)
        
        if where_clause:
            query_parts.append(f"WHERE {where_clause}")
        
        return "\n".join(query_parts)
    
    def _build_columns_clause(self, columns: List[str], primary_table: str) -> str:
        """构建列子句"""
        if not columns:
            return "*"
        
        formatted_columns = []
        for column in columns:
            if "." in column:
                # 已经包含表前缀
                formatted_columns.append(column)
            else:
                # 尝试确定列属于哪个表
                table_name = self._find_column_table(column, primary_table)
                if table_name:
                    formatted_columns.append(f"{table_name}.{column}")
                else:
                    formatted_columns.append(column)
        
        return ", ".join(formatted_columns)
    
    def _find_column_table(self, column_name: str, default_table: str) -> Optional[str]:
        """找出列属于哪个表"""
        # 首先检查默认表
        if default_table in self.schema.tables:
            table = self.schema.tables[default_table]
            if any(col['name'] == column_name for col in table.columns):
                return default_table
        
        # 检查所有表
        for table_name, table in self.schema.tables.items():
            if any(col['name'] == column_name for col in table.columns):
                return table_name
        
        return None
    
    def _build_from_clause(self, tables: List[str]) -> str:
        """构建FROM子句"""
        return tables[0] if tables else ""
    
    def _build_joins_clause(self, joins: List[Dict[str, str]]) -> str:
        """构建JOIN子句"""
        if not joins:
            return ""
        
        join_clauses = []
        for join in joins:
            join_type = join.get('type', 'INNER')
            table = join.get('table')
            condition = join.get('condition')
            
            if table and condition:
                join_clauses.append(f"{join_type} JOIN {table} ON {condition}")
        
        return "\n".join(join_clauses)
    
    def _build_where_clause(self, conditions: List[Dict[str, Any]]) -> str:
        """构建WHERE子句"""
        if not conditions:
            return ""
        
        condition_parts = []
        for condition in conditions:
            column = condition.get('column')
            operator = condition.get('operator', '=')
            value = condition.get('value')
            
            if column and value is not None:
                if isinstance(value, str) and operator in ['=', '!=', 'LIKE', 'NOT LIKE']:
                    condition_parts.append(f"{column} {operator} '{value}'")
                else:
                    condition_parts.append(f"{column} {operator} {value}")
        
        return " AND ".join(condition_parts)
    
    def _build_order_clause(self, order_by: List[Dict[str, str]]) -> str:
        """构建ORDER BY子句"""
        if not order_by:
            return ""
        
        order_parts = []
        for order in order_by:
            column = order.get('column')
            direction = order.get('direction', 'ASC')
            
            if column:
                order_parts.append(f"{column} {direction}")
        
        return ", ".join(order_parts)
    
    def _build_limit_clause(self, limit: Optional[int]) -> str:
        """构建LIMIT子句"""
        return f"LIMIT {limit}" if limit else ""
    
    def suggest_query_optimizations(self, query: str) -> List[Dict[str, Any]]:
        """建议查询优化"""
        suggestions = []
        
        # 检查是否使用了SELECT *
        if re.search(r'\bSELECT\s+\*', query, re.IGNORECASE):
            suggestions.append({
                'type': 'avoid_select_all',
                'message': 'Consider specifying explicit columns instead of SELECT *',
                'priority': 'medium'
            })
        
        # 检查是否缺少LIMIT
        if not re.search(r'\bLIMIT\b', query, re.IGNORECASE):
            suggestions.append({
                'type': 'consider_limit',
                'message': 'Consider adding LIMIT clause for large result sets',
                'priority': 'low'
            })
        
        # 检查是否使用了复杂的WHERE条件
        where_match = re.search(r'\bWHERE\s+(.+?)(?:\s+ORDER\s+BY|\s+GROUP\s+BY|\s+LIMIT|$)', 
                              query, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_clause = where_match.group(1)
            if 'OR' in where_clause.upper() and 'AND' in where_clause.upper():
                suggestions.append({
                    'type': 'complex_where',
                    'message': 'Complex WHERE clause might benefit from indexing',
                    'priority': 'medium'
                })
        
        return suggestions


class NaturalLanguageQueryBuilder:
    """自然语言查询构建器"""
    
    def __init__(self, schema: DatabaseSchema):
        self.schema = schema
        self.query_builder = SchemaAwareQueryBuilder(schema)
        self.table_keywords = self._build_table_keywords()
        self.column_keywords = self._build_column_keywords()
    
    def _build_table_keywords(self) -> Dict[str, str]:
        """构建表关键词映射"""
        keywords = {}
        
        for table_name in self.schema.tables:
            # 表名本身
            keywords[table_name.lower()] = table_name
            
            # 单复数变化
            if table_name.endswith('s'):
                keywords[table_name[:-1].lower()] = table_name
            else:
                keywords[f"{table_name}s".lower()] = table_name
            
            # 下划线转换
            if '_' in table_name:
                keywords[table_name.replace('_', ' ').lower()] = table_name
        
        return keywords
    
    def _build_column_keywords(self) -> Dict[str, List[Tuple[str, str]]]:
        """构建列关键词映射"""
        keywords = {}
        
        for table_name, table in self.schema.tables.items():
            for column in table.columns:
                column_name = column['name'].lower()
                
                if column_name not in keywords:
                    keywords[column_name] = []
                
                keywords[column_name].append((table_name, column['name']))
                
                # 处理下划线
                if '_' in column_name:
                    alt_name = column_name.replace('_', ' ')
                    if alt_name not in keywords:
                        keywords[alt_name] = []
                    keywords[alt_name].append((table_name, column['name']))
        
        return keywords
    
    def parse_natural_query(self, natural_query: str) -> Optional[QueryContext]:
        """解析自然语言查询"""
        query_lower = natural_query.lower()
        
        # 确定查询类型
        if any(word in query_lower for word in ['show', 'list', 'get', 'find', 'select']):
            query_type = QueryType.SELECT
        elif any(word in query_lower for word in ['count', 'how many']):
            query_type = QueryType.COUNT
        else:
            query_type = QueryType.SELECT  # 默认
        
        context = QueryContext(query_type=query_type)
        
        # 识别表
        context.target_tables = self._extract_tables(query_lower)
        
        # 识别列
        context.columns = self._extract_columns(query_lower, context.target_tables)
        
        # 识别条件
        context.conditions = self._extract_conditions(query_lower)
        
        return context if context.target_tables else None
    
    def _extract_tables(self, query: str) -> List[str]:
        """从查询中提取表名"""
        identified_tables = []
        
        for keyword, table_name in self.table_keywords.items():
            if keyword in query:
                if table_name not in identified_tables:
                    identified_tables.append(table_name)
        
        return identified_tables
    
    def _extract_columns(self, query: str, target_tables: List[str]) -> List[str]:
        """从查询中提取列名"""
        identified_columns = []
        
        # 优先匹配目标表的列
        for table_name in target_tables:
            if table_name in self.schema.tables:
                for column in self.schema.tables[table_name].columns:
                    column_name = column['name'].lower()
                    if column_name in query:
                        if column['name'] not in identified_columns:
                            identified_columns.append(column['name'])
        
        # 如果没有找到具体列，返回空列表（使用SELECT *）
        return identified_columns
    
    def _extract_conditions(self, query: str) -> List[Dict[str, Any]]:
        """从查询中提取条件"""
        conditions = []
        
        # 简单的条件提取（可以扩展）
        condition_patterns = [
            (r'(\w+)\s*=\s*["\']([^"\']+)["\']', '='),
            (r'(\w+)\s*>\s*(\d+)', '>'),
            (r'(\w+)\s*<\s*(\d+)', '<'),
        ]
        
        for pattern, operator in condition_patterns:
            matches = re.findall(pattern, query)
            for column, value in matches:
                conditions.append({
                    'column': column,
                    'operator': operator,
                    'value': value
                })
        
        return conditions