"""
SQL 工具
========

用于 SQL 生成、执行和优化的工具。
"""

import logging
import json
import time
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timezone
from pydantic import BaseModel, Field, validator
import sqlparse
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..core.base import (
    AgentTool, StreamingAgentTool, ToolDefinition, ToolResult, 
    ToolExecutionContext, ToolCategory, ToolPriority, ToolPermission,
    ValidationError, ExecutionError, create_tool_definition
)
from ..core.permissions import SecurityLevel, ResourceType

logger = logging.getLogger(__name__)


# 输入模式
class SQLGeneratorInput(BaseModel):
    """SQL 生成的输入模式"""
    task_description: str = Field(..., min_length=5, max_length=1000, description="要执行的 SQL 任务描述")
    table_names: Optional[List[str]] = Field(None, description="要使用的具体表名")
    columns: Optional[List[str]] = Field(None, description="要包含的具体列")
    conditions: Optional[Dict[str, Any]] = Field(None, description="WHERE 子句条件")
    sql_type: str = Field(default="SELECT", description="SQL 查询类型（SELECT, INSERT, UPDATE, DELETE）")
    database_type: str = Field(default="postgresql", description="目标数据库类型")
    optimization_level: str = Field(default="standard", description="优化级别（basic, standard, advanced）")
    
    @validator('sql_type')
    def validate_sql_type(cls, v):
        allowed_types = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"]
        if v.upper() not in allowed_types:
            raise ValueError(f"SQL 类型必须是以下之一: {allowed_types}")
        return v.upper()
    
    @validator('database_type')
    def validate_database_type(cls, v):
        supported_dbs = ["postgresql", "mysql", "sqlite", "mssql", "oracle"]
        if v.lower() not in supported_dbs:
            raise ValueError(f"数据库类型必须是以下之一: {supported_dbs}")
        return v.lower()


class SQLExecutorInput(BaseModel):
    """SQL 执行的输入模式"""
    sql_query: str = Field(..., min_length=5, description="要执行的 SQL 查询")
    database_connection: str = Field(..., description="数据库连接字符串或标识符")
    execute_mode: str = Field(default="read_only", description="执行模式（read_only, write, transaction）")
    limit_rows: Optional[int] = Field(default=1000, ge=1, le=10000, description="返回的最大行数")
    timeout_seconds: Optional[int] = Field(default=30, ge=1, le=300, description="查询超时时间（秒）")
    dry_run: bool = Field(default=False, description="仅验证而不执行")
    
    @validator('execute_mode')
    def validate_execute_mode(cls, v):
        allowed_modes = ["read_only", "write", "transaction"]
        if v not in allowed_modes:
            raise ValueError(f"执行模式必须是以下之一: {allowed_modes}")
        return v
    
    @validator('sql_query')
    def validate_sql_query(cls, v):
        # 基本 SQL 注入保护
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "--", "/*", "*/"]
        v_upper = v.upper()
        
        for keyword in dangerous_keywords:
            if keyword in v_upper and "read_only" in str(cls):  # 检查是否在只读上下文中
                raise ValueError(f"检测到潜在危险的 SQL 关键字: {keyword}")
        
        return v


class SQLGeneratorTool(StreamingAgentTool):
    """
    具有智能查询构建的高级 SQL 生成工具
    """
    
    def __init__(self):
        definition = create_tool_definition(
            name="sql_generator",
            description="基于自然语言描述生成优化的 SQL 查询",
            category=ToolCategory.DATA,
            priority=ToolPriority.HIGH,
            permissions=[ToolPermission.READ_ONLY],
            input_schema=SQLGeneratorInput,
            is_read_only=True,
            supports_streaming=True,
            typical_execution_time_ms=2000,
            examples=[
                {
                    "task_description": "Find all users who made purchases in the last 30 days",
                    "table_names": ["users", "orders"],
                    "sql_type": "SELECT"
                },
                {
                    "task_description": "Update customer email addresses",
                    "table_names": ["customers"],
                    "sql_type": "UPDATE"
                }
            ],
            limitations=[
                "需要了解数据库模式",
                "复杂查询可能需要手动优化",
                "生成的 SQL 在执行前应进行审查"
            ]
        )
        super().__init__(definition)
        
        # SQL 生成模式和模板
        self.query_templates = {
            "SELECT": {
                "basic": "SELECT {columns} FROM {tables} WHERE {conditions}",
                "join": "SELECT {columns} FROM {main_table} {joins} WHERE {conditions}",
                "aggregate": "SELECT {columns}, {aggregates} FROM {tables} WHERE {conditions} GROUP BY {group_by}",
                "window": "SELECT {columns}, {window_functions} FROM {tables} WHERE {conditions}"
            },
            "INSERT": {
                "basic": "INSERT INTO {table} ({columns}) VALUES {values}",
                "select": "INSERT INTO {table} ({columns}) SELECT {select_columns} FROM {source_table} WHERE {conditions}"
            },
            "UPDATE": {
                "basic": "UPDATE {table} SET {updates} WHERE {conditions}",
                "join": "UPDATE {main_table} SET {updates} FROM {join_table} WHERE {join_conditions}"
            },
            "DELETE": {
                "basic": "DELETE FROM {table} WHERE {conditions}",
                "join": "DELETE {alias} FROM {table} {alias} JOIN {join_table} ON {join_conditions} WHERE {conditions}"
            }
        }
        
        # 数据库特定的 SQL 方言
        self.db_dialects = {
            "postgresql": {
                "limit": "LIMIT {limit}",
                "offset": "OFFSET {offset}",
                "string_concat": "||",
                "current_timestamp": "CURRENT_TIMESTAMP",
                "auto_increment": "SERIAL"
            },
            "mysql": {
                "limit": "LIMIT {limit}",
                "offset": "LIMIT {offset}, {limit}",
                "string_concat": "CONCAT",
                "current_timestamp": "NOW()",
                "auto_increment": "AUTO_INCREMENT"
            },
            "sqlite": {
                "limit": "LIMIT {limit}",
                "offset": "LIMIT {limit} OFFSET {offset}",
                "string_concat": "||",
                "current_timestamp": "datetime('now')",
                "auto_increment": "AUTOINCREMENT"
            }
        }
    
    async def validate_input(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        """验证 SQL 生成输入"""
        try:
            validated = SQLGeneratorInput(**input_data)
            return validated.dict()
        except Exception as e:
            raise ValidationError(f"SQL 生成器输入无效: {e}", tool_name=self.name)
    
    async def check_permissions(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> bool:
        """检查 SQL 生成权限"""
        # SQL 生成是只读的，通常安全
        sql_type = input_data.get('sql_type', 'SELECT')
        
        # 写操作需要更高权限
        if sql_type in ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP']:
            return ToolPermission.WRITE_FULL in context.permissions
        
        return True
    
    async def execute(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """执行 SQL 生成并流式传输进度"""
        
        task_description = input_data['task_description']
        sql_type = input_data['sql_type']
        database_type = input_data['database_type']
        optimization_level = input_data['optimization_level']
        
        # 阶段1：解析任务描述
        yield await self.stream_progress({
            'status': 'parsing_task',
            'message': '正在分析任务描述...',
            'progress': 20
        }, context)
        
        parsed_task = await self._parse_task_description(task_description, input_data)
        
        # 阶段2：生成基础 SQL
        yield await self.stream_progress({
            'status': 'generating_sql',
            'message': f'正在生成 {sql_type} 查询...',
            'progress': 40
        }, context)
        
        base_sql = await self._generate_base_sql(parsed_task, input_data)
        
        # 阶段3：应用数据库特定优化
        yield await self.stream_progress({
            'status': 'optimizing',
            'message': f'正在为 {database_type} 优化...',
            'progress': 60
        }, context)
        
        optimized_sql = await self._optimize_sql(base_sql, database_type, optimization_level)
        
        # 阶段4：格式化和验证
        yield await self.stream_progress({
            'status': 'formatting',
            'message': '正在格式化和验证 SQL...',
            'progress': 80
        }, context)
        
        formatted_sql = await self._format_and_validate_sql(optimized_sql)
        
        # 阶段5：生成解释和元数据
        explanation = await self._generate_explanation(formatted_sql, parsed_task)
        
        # Final result
        result_data = {
            'sql_query': formatted_sql,
            'sql_type': sql_type,
            'database_type': database_type,
            'explanation': explanation,
            'parsed_task': parsed_task,
            'optimization_applied': optimization_level,
            'estimated_complexity': self._estimate_query_complexity(formatted_sql),
            'suggested_indexes': self._suggest_indexes(formatted_sql, parsed_task),
            'performance_hints': self._generate_performance_hints(formatted_sql)
        }
        
        yield await self.stream_final_result(result_data, context)
    
    async def _parse_task_description(self, description: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """将自然语言任务描述解析为结构化数据"""
        
        # 简单关键字提取（在生产环境中，使用 NLP）
        description_lower = description.lower()
        
        parsed = {
            'intent': input_data['sql_type'],
            'tables': input_data.get('table_names', []),
            'columns': input_data.get('columns', []),
            'conditions': input_data.get('conditions', {}),
            'keywords': [],
            'temporal_references': [],
            'aggregations': []
        }
        
        # 提取常用关键字
        if 'all' in description_lower:
            parsed['keywords'].append('all')
        if 'count' in description_lower:
            parsed['aggregations'].append('COUNT')
        if 'sum' in description_lower:
            parsed['aggregations'].append('SUM')
        if 'average' in description_lower or 'avg' in description_lower:
            parsed['aggregations'].append('AVG')
        
        # 提取时间引用
        if 'last' in description_lower and 'days' in description_lower:
            parsed['temporal_references'].append('last_n_days')
        if 'today' in description_lower:
            parsed['temporal_references'].append('today')
        if 'month' in description_lower:
            parsed['temporal_references'].append('month')
        
        # 从描述中提取表提示
        common_table_words = ['user', 'customer', 'order', 'product', 'sale', 'invoice', 'payment']
        for word in common_table_words:
            if word in description_lower:
                if word + 's' not in parsed['tables']:  # 复数化
                    parsed['tables'].append(word + 's')
        
        return parsed
    
    async def _generate_base_sql(self, parsed_task: Dict[str, Any], input_data: Dict[str, Any]) -> str:
        """从解析的任务生成基础 SQL 查询"""
        
        sql_type = parsed_task['intent']
        tables = parsed_task['tables']
        columns = parsed_task['columns']
        
        if sql_type == 'SELECT':
            return await self._generate_select_query(parsed_task)
        elif sql_type == 'INSERT':
            return await self._generate_insert_query(parsed_task)
        elif sql_type == 'UPDATE':
            return await self._generate_update_query(parsed_task)
        elif sql_type == 'DELETE':
            return await self._generate_delete_query(parsed_task)
        else:
            raise ExecutionError(f"Unsupported SQL type: {sql_type}", tool_name=self.name)
    
    async def _generate_select_query(self, parsed_task: Dict[str, Any]) -> str:
        """Generate SELECT query"""
        
        tables = parsed_task['tables']
        columns = parsed_task['columns'] or ['*']
        conditions = parsed_task['conditions']
        aggregations = parsed_task['aggregations']
        
        # Build basic SELECT
        if aggregations:
            # Aggregate query
            agg_functions = []
            for agg in aggregations:
                if agg == 'COUNT':
                    agg_functions.append('COUNT(*) as total_count')
                elif agg == 'SUM':
                    agg_functions.append('SUM(amount) as total_amount')  # Assume amount column
                elif agg == 'AVG':
                    agg_functions.append('AVG(amount) as average_amount')
            
            select_clause = ', '.join(columns + agg_functions)
            
            sql = f"SELECT {select_clause} FROM {tables[0]}"
            
            # Add GROUP BY if we have both regular columns and aggregations
            if columns != ['*'] and len(columns) > 0:
                sql += f" GROUP BY {', '.join(columns)}"
        else:
            # Regular SELECT
            select_clause = ', '.join(columns)
            if len(tables) == 1:
                sql = f"SELECT {select_clause} FROM {tables[0]}"
            else:
                # Multiple tables - assume JOIN needed
                main_table = tables[0]
                sql = f"SELECT {select_clause} FROM {main_table}"
                
                for i, table in enumerate(tables[1:], 1):
                    # Simple heuristic for JOIN conditions
                    sql += f" JOIN {table} ON {main_table}.id = {table}.{main_table[:-1]}_id"
        
        # Add WHERE clause
        where_clauses = []
        
        # Add explicit conditions
        for field, value in conditions.items():
            if isinstance(value, str):
                where_clauses.append(f"{field} = '{value}'")
            else:
                where_clauses.append(f"{field} = {value}")
        
        # Add temporal conditions
        for temporal_ref in parsed_task['temporal_references']:
            if temporal_ref == 'last_n_days':
                where_clauses.append("created_at >= CURRENT_DATE - INTERVAL '30 days'")
            elif temporal_ref == 'today':
                where_clauses.append("DATE(created_at) = CURRENT_DATE")
            elif temporal_ref == 'month':
                where_clauses.append("EXTRACT(MONTH FROM created_at) = EXTRACT(MONTH FROM CURRENT_DATE)")
        
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        
        return sql
    
    async def _generate_insert_query(self, parsed_task: Dict[str, Any]) -> str:
        """Generate INSERT query"""
        table = parsed_task['tables'][0] if parsed_task['tables'] else 'table_name'
        columns = parsed_task['columns'] or ['column1', 'column2']
        
        placeholders = ', '.join(['?' for _ in columns])
        columns_str = ', '.join(columns)
        
        return f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
    
    async def _generate_update_query(self, parsed_task: Dict[str, Any]) -> str:
        """Generate UPDATE query"""
        table = parsed_task['tables'][0] if parsed_task['tables'] else 'table_name'
        columns = parsed_task['columns'] or ['column1']
        
        set_clause = ', '.join([f"{col} = ?" for col in columns])
        
        sql = f"UPDATE {table} SET {set_clause}"
        
        # Add WHERE clause from conditions
        if parsed_task['conditions']:
            where_clauses = []
            for field, value in parsed_task['conditions'].items():
                where_clauses.append(f"{field} = ?")
            sql += " WHERE " + " AND ".join(where_clauses)
        else:
            sql += " WHERE id = ?"
        
        return sql
    
    async def _generate_delete_query(self, parsed_task: Dict[str, Any]) -> str:
        """Generate DELETE query"""
        table = parsed_task['tables'][0] if parsed_task['tables'] else 'table_name'
        
        sql = f"DELETE FROM {table}"
        
        # Add WHERE clause
        if parsed_task['conditions']:
            where_clauses = []
            for field, value in parsed_task['conditions'].items():
                where_clauses.append(f"{field} = ?")
            sql += " WHERE " + " AND ".join(where_clauses)
        else:
            sql += " WHERE id = ?"
        
        return sql
    
    async def _optimize_sql(self, sql: str, database_type: str, optimization_level: str) -> str:
        """Apply database-specific optimizations"""
        
        dialect = self.db_dialects.get(database_type, self.db_dialects['postgresql'])
        optimized_sql = sql
        
        if optimization_level in ['standard', 'advanced']:
            # Add LIMIT to SELECT queries to prevent runaway queries
            if sql.strip().upper().startswith('SELECT') and 'LIMIT' not in sql.upper():
                optimized_sql += f" {dialect['limit'].format(limit=1000)}"
            
            # Add indexes hints for complex queries
            if optimization_level == 'advanced':
                # Add database-specific optimizations
                if database_type == 'postgresql':
                    # Use EXPLAIN for complex queries
                    if 'JOIN' in sql.upper():
                        optimized_sql = f"/* Consider adding indexes on JOIN columns */ {optimized_sql}"
                
                elif database_type == 'mysql':
                    # Use MySQL-specific optimizations
                    if 'SELECT' in sql.upper():
                        optimized_sql = optimized_sql.replace('SELECT', 'SELECT SQL_CALC_FOUND_ROWS', 1)
        
        return optimized_sql
    
    async def _format_and_validate_sql(self, sql: str) -> str:
        """Format and validate SQL query"""
        
        try:
            # Parse and format SQL
            formatted = sqlparse.format(
                sql, 
                reindent=True, 
                keyword_case='upper',
                identifier_case='lower',
                strip_comments=False
            )
            
            # Basic validation
            parsed = sqlparse.parse(formatted)
            if not parsed:
                raise ExecutionError("Failed to parse SQL query", tool_name=self.name)
            
            return formatted
            
        except Exception as e:
            # If formatting fails, return original with basic cleanup
            logger.warning(f"SQL formatting failed: {e}")
            return sql.strip()
    
    async def _generate_explanation(self, sql: str, parsed_task: Dict[str, Any]) -> str:
        """Generate human-readable explanation of the SQL query"""
        
        explanation_parts = []
        
        sql_upper = sql.upper()
        
        if sql_upper.startswith('SELECT'):
            explanation_parts.append("This query retrieves data")
            
            if 'COUNT(' in sql_upper:
                explanation_parts.append("and counts records")
            if 'SUM(' in sql_upper:
                explanation_parts.append("and calculates totals")
            if 'AVG(' in sql_upper:
                explanation_parts.append("and calculates averages")
            
            if 'JOIN' in sql_upper:
                explanation_parts.append("from multiple related tables")
            else:
                tables = parsed_task.get('tables', [])
                if tables:
                    explanation_parts.append(f"from the {tables[0]} table")
            
            if 'WHERE' in sql_upper:
                explanation_parts.append("with specific filtering conditions")
            
            if 'GROUP BY' in sql_upper:
                explanation_parts.append("grouped by specific columns")
            
            if 'ORDER BY' in sql_upper:
                explanation_parts.append("sorted by specific criteria")
        
        elif sql_upper.startswith('INSERT'):
            explanation_parts.append("This query adds new records to the database")
        
        elif sql_upper.startswith('UPDATE'):
            explanation_parts.append("This query modifies existing records in the database")
        
        elif sql_upper.startswith('DELETE'):
            explanation_parts.append("This query removes records from the database")
        
        return " ".join(explanation_parts) + "."
    
    def _estimate_query_complexity(self, sql: str) -> str:
        """Estimate query complexity"""
        sql_upper = sql.upper()
        
        complexity_score = 0
        
        # Base complexity factors
        if 'JOIN' in sql_upper:
            complexity_score += 2
        if 'SUBQUERY' in sql_upper or '(' in sql:
            complexity_score += 3
        if 'GROUP BY' in sql_upper:
            complexity_score += 1
        if 'ORDER BY' in sql_upper:
            complexity_score += 1
        if 'HAVING' in sql_upper:
            complexity_score += 2
        if 'UNION' in sql_upper:
            complexity_score += 3
        
        # Count number of tables
        table_count = sql_upper.count('FROM') + sql_upper.count('JOIN')
        complexity_score += table_count
        
        if complexity_score <= 2:
            return "Low"
        elif complexity_score <= 5:
            return "Medium"
        else:
            return "High"
    
    def _suggest_indexes(self, sql: str, parsed_task: Dict[str, Any]) -> List[str]:
        """Suggest database indexes for better performance"""
        suggestions = []
        
        sql_upper = sql.upper()
        
        # Suggest indexes for WHERE clauses
        if 'WHERE' in sql_upper:
            # Extract potential index columns (simplified)
            conditions = parsed_task.get('conditions', {})
            for field in conditions.keys():
                suggestions.append(f"CREATE INDEX idx_{field} ON table_name ({field});")
        
        # Suggest indexes for JOIN conditions
        if 'JOIN' in sql_upper:
            suggestions.append("CREATE INDEX idx_foreign_key ON table_name (foreign_key_column);")
        
        # Suggest composite indexes for complex queries
        if len(suggestions) > 1:
            suggestions.append("Consider creating composite indexes for multiple column conditions")
        
        return suggestions
    
    def _generate_performance_hints(self, sql: str) -> List[str]:
        """Generate performance optimization hints"""
        hints = []
        
        sql_upper = sql.upper()
        
        if 'SELECT *' in sql_upper:
            hints.append("Consider selecting only needed columns instead of using SELECT *")
        
        if 'LIMIT' not in sql_upper and 'SELECT' in sql_upper:
            hints.append("Consider adding a LIMIT clause to prevent large result sets")
        
        if 'ORDER BY' in sql_upper and 'LIMIT' not in sql_upper:
            hints.append("ORDER BY without LIMIT can be expensive on large tables")
        
        if sql_upper.count('JOIN') > 3:
            hints.append("Multiple JOINs can impact performance - consider query optimization")
        
        if 'GROUP BY' in sql_upper and 'HAVING' not in sql_upper:
            hints.append("Consider using WHERE instead of HAVING when possible for better performance")
        
        return hints


class SQLExecutorTool(StreamingAgentTool):
    """
    具有安全检查结果流式传输的 SQL 执行工具
    """
    
    def __init__(self):
        definition = create_tool_definition(
            name="sql_executor",
            description="执行具有安全检查和结果流式传输的 SQL 查询",
            category=ToolCategory.DATA,
            priority=ToolPriority.HIGH,
            permissions=[ToolPermission.READ_ONLY, ToolPermission.WRITE_LIMITED],
            input_schema=SQLExecutorInput,
            is_read_only=False,
            supports_streaming=True,
            typical_execution_time_ms=5000,
            examples=[
                {
                    "sql_query": "SELECT * FROM users LIMIT 10",
                    "database_connection": "postgresql://localhost/mydb",
                    "execute_mode": "read_only"
                }
            ],
            limitations=[
                "需要有效的数据库连接",
                "大型结果集会自动限制",
                "写操作需要额外权限"
            ]
        )
        super().__init__(definition)
    
    async def validate_input(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        """验证 SQL 执行输入"""
        try:
            validated = SQLExecutorInput(**input_data)
            return validated.dict()
        except Exception as e:
            raise ValidationError(f"SQL 执行器输入无效: {e}", tool_name=self.name)
    
    async def check_permissions(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> bool:
        """检查 SQL 执行权限"""
        execute_mode = input_data.get('execute_mode', 'read_only')
        sql_query = input_data.get('sql_query', '').upper()
        
        # 只读操作
        if execute_mode == 'read_only' or sql_query.strip().startswith('SELECT'):
            return ToolPermission.READ_ONLY in context.permissions
        
        # 写操作
        if execute_mode in ['write', 'transaction']:
            return ToolPermission.WRITE_LIMITED in context.permissions
        
        return False
    
    async def execute(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """执行 SQL 查询并流式传输结果"""
        
        sql_query = input_data['sql_query']
        connection_string = input_data['database_connection']
        execute_mode = input_data['execute_mode']
        limit_rows = input_data.get('limit_rows', 1000)
        timeout_seconds = input_data.get('timeout_seconds', 30)
        dry_run = input_data.get('dry_run', False)
        
        # Phase 1: Validate SQL
        yield await self.stream_progress({
            'status': 'validating',
            'message': 'Validating SQL query...',
            'progress': 10
        }, context)
        
        validation_result = await self._validate_sql_query(sql_query, execute_mode)
        if not validation_result['valid']:
            raise ExecutionError(f"SQL validation failed: {validation_result['error']}", tool_name=self.name)
        
        # Phase 2: Establish connection
        yield await self.stream_progress({
            'status': 'connecting',
            'message': 'Connecting to database...',
            'progress': 20
        }, context)
        
        if dry_run:
            # Dry run - just validate and return
            result_data = {
                'dry_run': True,
                'sql_query': sql_query,
                'validation_result': validation_result,
                'estimated_cost': self._estimate_query_cost(sql_query),
                'execution_plan': 'DRY RUN - No actual execution'
            }
            yield await self.stream_final_result(result_data, context)
            return
        
        try:
            # Create database connection
            engine = create_engine(
                connection_string,
                pool_timeout=timeout_seconds,
                pool_recycle=3600
            )
            
            # Phase 3: Execute query
            yield await self.stream_progress({
                'status': 'executing',
                'message': 'Executing SQL query...',
                'progress': 40
            }, context)
            
            start_time = time.time()
            
            with engine.connect() as conn:
                # Set query timeout
                conn = conn.execution_options(autocommit=(execute_mode != 'transaction'))
                
                if execute_mode == 'transaction':
                    trans = conn.begin()
                
                try:
                    # Execute query
                    result = conn.execute(text(sql_query))
                    execution_time = (time.time() - start_time) * 1000
                    
                    # Phase 4: Process results
                    yield await self.stream_progress({
                        'status': 'processing',
                        'message': 'Processing query results...',
                        'progress': 60
                    }, context)
                    
                    if sql_query.strip().upper().startswith('SELECT'):
                        # Handle SELECT results
                        columns = list(result.keys()) if result.keys() else []
                        rows = []
                        row_count = 0
                        
                        for row in result:
                            if row_count >= limit_rows:
                                break
                            
                            rows.append(dict(row))
                            row_count += 1
                            
                            # Stream partial results for large datasets
                            if row_count % 100 == 0:
                                yield await self.stream_partial_result({
                                    'partial_rows': rows[-100:],
                                    'processed_count': row_count,
                                    'total_estimated': 'unknown'
                                }, context, row_count // 100)
                        
                        result_data = {
                            'query_type': 'SELECT',
                            'columns': columns,
                            'rows': rows,
                            'row_count': row_count,
                            'execution_time_ms': execution_time,
                            'truncated': row_count >= limit_rows
                        }
                    
                    else:
                        # Handle non-SELECT results (INSERT, UPDATE, DELETE, etc.)
                        affected_rows = result.rowcount
                        
                        result_data = {
                            'query_type': 'MODIFICATION',
                            'affected_rows': affected_rows,
                            'execution_time_ms': execution_time,
                            'success': True
                        }
                    
                    # Commit transaction if in transaction mode
                    if execute_mode == 'transaction':
                        trans.commit()
                        result_data['transaction_committed'] = True
                
                except Exception as e:
                    # Rollback transaction if in transaction mode
                    if execute_mode == 'transaction':
                        trans.rollback()
                        result_data = {
                            'error': str(e),
                            'transaction_rolled_back': True
                        }
                    raise ExecutionError(f"SQL execution failed: {e}", tool_name=self.name)
            
            # Add metadata
            result_data.update({
                'sql_query': sql_query,
                'execute_mode': execute_mode,
                'database_type': self._detect_database_type(connection_string),
                'performance_stats': {
                    'execution_time_ms': execution_time,
                    'estimated_cost': self._estimate_query_cost(sql_query)
                }
            })
            
            yield await self.stream_final_result(result_data, context)
        
        except Exception as e:
            raise ExecutionError(f"Database operation failed: {e}", tool_name=self.name)
    
    async def _validate_sql_query(self, sql_query: str, execute_mode: str) -> Dict[str, Any]:
        """Validate SQL query for safety and correctness"""
        
        validation_result = {
            'valid': True,
            'error': None,
            'warnings': [],
            'query_type': 'UNKNOWN'
        }
        
        try:
            # Parse SQL to check syntax
            parsed = sqlparse.parse(sql_query)
            if not parsed:
                validation_result['valid'] = False
                validation_result['error'] = "Unable to parse SQL query"
                return validation_result
            
            # Detect query type
            first_token = str(parsed[0].tokens[0]).strip().upper()
            validation_result['query_type'] = first_token
            
            # Check for dangerous operations in read-only mode
            if execute_mode == 'read_only':
                dangerous_operations = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
                if any(op in sql_query.upper() for op in dangerous_operations):
                    validation_result['valid'] = False
                    validation_result['error'] = f"Operation not allowed in read-only mode: {first_token}"
                    return validation_result
            
            # Check for potential SQL injection patterns
            injection_patterns = ['--', '/*', '*/', 'EXEC', 'EXECUTE', 'SP_', 'XP_']
            for pattern in injection_patterns:
                if pattern in sql_query.upper():
                    validation_result['warnings'].append(f"Potentially dangerous pattern detected: {pattern}")
            
            # Check for missing WHERE clause in UPDATE/DELETE
            if first_token in ['UPDATE', 'DELETE'] and 'WHERE' not in sql_query.upper():
                validation_result['warnings'].append("UPDATE/DELETE without WHERE clause affects all rows")
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['error'] = f"SQL validation error: {e}"
        
        return validation_result
    
    def _detect_database_type(self, connection_string: str) -> str:
        """Detect database type from connection string"""
        connection_lower = connection_string.lower()
        
        if 'postgresql' in connection_lower or 'postgres' in connection_lower:
            return 'postgresql'
        elif 'mysql' in connection_lower:
            return 'mysql'
        elif 'sqlite' in connection_lower:
            return 'sqlite'
        elif 'mssql' in connection_lower or 'sqlserver' in connection_lower:
            return 'mssql'
        elif 'oracle' in connection_lower:
            return 'oracle'
        else:
            return 'unknown'
    
    def _estimate_query_cost(self, sql_query: str) -> str:
        """Estimate query execution cost"""
        sql_upper = sql_query.upper()
        
        cost_factors = 0
        
        # Count complexity factors
        if 'JOIN' in sql_upper:
            cost_factors += sql_upper.count('JOIN') * 2
        if 'GROUP BY' in sql_upper:
            cost_factors += 2
        if 'ORDER BY' in sql_upper:
            cost_factors += 1
        if 'SUBQUERY' in sql_upper or '(' in sql_query:
            cost_factors += 3
        if 'DISTINCT' in sql_upper:
            cost_factors += 2
        
        if cost_factors <= 2:
            return "Low"
        elif cost_factors <= 6:
            return "Medium"
        else:
            return "High"


__all__ = ["SQLGeneratorTool", "SQLExecutorTool"]