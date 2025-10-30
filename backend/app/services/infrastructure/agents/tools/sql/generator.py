from __future__ import annotations

"""
SQL 生成工具

基于业务需求和 Schema 信息生成 SQL 查询
支持多种查询类型和优化策略
"""


import logging
import re
from typing import Any, Dict, List, Optional, Union, Literal
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool
from ...types import ToolCategory, ContextInfo

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """查询类型"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CREATE_TABLE = "CREATE_TABLE"
    ALTER_TABLE = "ALTER_TABLE"
    DROP_TABLE = "DROP_TABLE"


class JoinType(str, Enum):
    """连接类型"""
    INNER = "INNER JOIN"
    LEFT = "LEFT JOIN"
    RIGHT = "RIGHT JOIN"
    FULL = "FULL OUTER JOIN"


@dataclass
class QueryRequest:
    """查询请求"""
    business_requirement: str
    table_names: Optional[List[str]] = None
    column_names: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    aggregations: Optional[Dict[str, str]] = None
    group_by: Optional[List[str]] = None
    order_by: Optional[List[str]] = None
    limit: Optional[int] = None
    query_type: QueryType = QueryType.SELECT
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class QueryResult:
    """查询结果"""
    sql: str
    query_type: QueryType
    tables_used: List[str]
    columns_used: List[str]
    joins: List[Dict[str, str]]
    filters: List[Dict[str, Any]]
    aggregations: List[Dict[str, str]]
    optimization_suggestions: List[str]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SQLGeneratorTool(BaseTool):
    """SQL 生成工具"""
    
    def __init__(self, container: Any):
        """
        Args:
            container: 服务容器
        """
        super().__init__()

        self.name = "sql_generator"

        self.category = ToolCategory.SQL

        self.description = "基于业务需求和 Schema 信息生成 SQL 查询" 
        self.container = container
        self._schema_cache = None
        
        # 使用 Pydantic 定义参数模式（args_schema）
        class SQLGeneratorArgs(BaseModel):
            business_requirement: str = Field(description="业务需求描述")
            connection_config: Dict[str, Any] = Field(description="数据源连接配置")
            table_names: Optional[List[str]] = Field(default=None, description="要查询的表名列表")
            column_names: Optional[List[str]] = Field(default=None, description="要查询的列名列表")
            filters: Optional[Dict[str, Any]] = Field(default=None, description="过滤条件")
            aggregations: Optional[Dict[str, str]] = Field(default=None, description="聚合函数配置")
            group_by: Optional[List[str]] = Field(default=None, description="分组字段")
            order_by: Optional[List[str]] = Field(default=None, description="排序字段")
            limit: Optional[int] = Field(default=None, description="结果数量限制")
            query_type: Literal["SELECT", "INSERT", "UPDATE", "DELETE"] = Field(
                default="SELECT", description="查询类型"
            )
            optimize: bool = Field(default=True, description="是否优化查询")

        self.args_schema = SQLGeneratorArgs
    
    async def _get_schema_cache(self):
        """获取 Schema 缓存"""
        if self._schema_cache is None:
            from .schema.cache import create_schema_cache_manager
            self._schema_cache = create_schema_cache_manager(self.container)
        return self._schema_cache
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数模式（基于 args_schema 生成）"""
        try:
            parameters = self.args_schema.model_json_schema()
        except Exception:
            parameters = self.args_schema.schema()  # type: ignore[attr-defined]
        return {
            "type": "function",
            "function": {
                "name": "sql_generator",
                "description": "基于业务需求和 Schema 信息生成 SQL 查询",
                "parameters": parameters,
            },
        }
    
    async def run(

    
        self,
        business_requirement: str,
        connection_config: Dict[str, Any],
        table_names: Optional[List[str]] = None,
        column_names: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        aggregations: Optional[Dict[str, str]] = None,
        group_by: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
        limit: Optional[int] = None,
        query_type: str = "SELECT",
        optimize: bool = True,
        **kwargs
    

    
    ) -> Dict[str, Any]:
        """
        执行 SQL 生成

    Args:
            business_requirement: 业务需求描述
            connection_config: 数据源连接配置
            table_names: 要查询的表名列表
            column_names: 要查询的列名列表
        filters: 过滤条件
            aggregations: 聚合函数配置
            group_by: 分组字段
            order_by: 排序字段
            limit: 结果数量限制
            query_type: 查询类型
            optimize: 是否优化查询

    Returns:
            Dict[str, Any]: 生成结果
        """
        logger.info(f"🔧 [SQLGeneratorTool] 生成 SQL: {query_type}")

    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """向后兼容的execute方法"""
        return await self.run(**kwargs)
        logger.info(f"   业务需求: {business_requirement[:100]}...")
        
        try:
            # 构建查询请求
            request = QueryRequest(
                business_requirement=business_requirement,
                table_names=table_names,
                column_names=column_names,
                filters=filters,
                aggregations=aggregations,
                group_by=group_by,
                order_by=order_by,
                limit=limit,
                query_type=QueryType(query_type)
            )
            
            # 获取 Schema 信息
            schema_info = await self._get_schema_info(connection_config, table_names)
            
            # 生成 SQL
            result = await self._generate_sql(request, schema_info, optimize)
            
            return {
                "success": True,
                "result": result,
                "metadata": {
                    "business_requirement": business_requirement,
                    "query_type": query_type,
                    "optimize": optimize,
                    "schema_tables": len(schema_info.get("tables", []))
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [SQLGeneratorTool] 生成失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    async def _get_schema_info(
        self,
        connection_config: Dict[str, Any],
        table_names: Optional[List[str]]
    ) -> Dict[str, Any]:
        """获取 Schema 信息"""
        try:
            # 使用 Schema 检索工具获取信息
            from ..schema.retrieval import create_schema_retrieval_tool

            # 🔥 修复：传递 connection_config 以便工具能正确初始化
            retrieval_tool = create_schema_retrieval_tool(
                self.container,
                connection_config=connection_config
            )

            result = await retrieval_tool.run(
                table_names=table_names,
                include_relationships=True,
                include_constraints=True,
                format="detailed"
            )
            
            if result.get("success"):
                return result.get("result", {})
            else:
                logger.warning(f"⚠️ 获取 Schema 信息失败: {result.get('error')}")
                return {}
                
        except Exception as e:
            logger.warning(f"⚠️ 获取 Schema 信息失败: {e}")
            return {}
    
    async def _generate_sql(
        self,
        request: QueryRequest,
        schema_info: Dict[str, Any],
        optimize: bool
    ) -> QueryResult:
        """生成 SQL"""
        if request.query_type == QueryType.SELECT:
            return await self._generate_select_query(request, schema_info, optimize)
        elif request.query_type == QueryType.INSERT:
            return await self._generate_insert_query(request, schema_info)
        elif request.query_type == QueryType.UPDATE:
            return await self._generate_update_query(request, schema_info)
        elif request.query_type == QueryType.DELETE:
            return await self._generate_delete_query(request, schema_info)
        else:
            raise ValueError(f"不支持的查询类型: {request.query_type}")
    
    async def _generate_select_query(
        self,
        request: QueryRequest,
        schema_info: Dict[str, Any],
        optimize: bool
    ) -> QueryResult:
        """生成 SELECT 查询"""
        # 分析业务需求
        analysis = self._analyze_business_requirement(request.business_requirement)
        
        # 确定要查询的表
        tables = self._determine_tables(request, schema_info, analysis)
        
        # 确定要查询的列
        columns = self._determine_columns(request, schema_info, analysis, tables)
        
        # 确定连接关系
        joins = self._determine_joins(tables, schema_info)
        
        # 确定过滤条件
        filters = self._determine_filters(request, schema_info, analysis)
        
        # 确定聚合函数
        aggregations = self._determine_aggregations(request, analysis)
        
        # 构建 SQL
        sql = self._build_select_sql(
            tables, columns, joins, filters, aggregations,
            request.group_by, request.order_by, request.limit
        )
        
        # 优化建议
        optimization_suggestions = []
        if optimize:
            optimization_suggestions = self._get_optimization_suggestions(
                sql, tables, schema_info
            )
        
        return QueryResult(
            sql=sql,
            query_type=QueryType.SELECT,
            tables_used=tables,
            columns_used=columns,
            joins=joins,
            filters=filters,
            aggregations=aggregations,
            optimization_suggestions=optimization_suggestions
        )
    
    async def _generate_insert_query(
        self,
        request: QueryRequest,
        schema_info: Dict[str, Any]
    ) -> QueryResult:
        """生成 INSERT 查询"""
        # 简化实现，实际应该更复杂
        table_name = request.table_names[0] if request.table_names else "table"
        
        sql = f"INSERT INTO {table_name} VALUES (...)"
        
        return QueryResult(
            sql=sql,
            query_type=QueryType.INSERT,
            tables_used=[table_name],
            columns_used=[],
            joins=[],
            filters=[],
            aggregations=[],
            optimization_suggestions=[]
        )
    
    async def _generate_update_query(
        self,
        request: QueryRequest,
        schema_info: Dict[str, Any]
    ) -> QueryResult:
        """生成 UPDATE 查询"""
        # 简化实现
        table_name = request.table_names[0] if request.table_names else "table"
        
        sql = f"UPDATE {table_name} SET ... WHERE ..."
        
        return QueryResult(
            sql=sql,
            query_type=QueryType.UPDATE,
            tables_used=[table_name],
            columns_used=[],
            joins=[],
            filters=[],
            aggregations=[],
            optimization_suggestions=[]
        )
    
    async def _generate_delete_query(
        self,
        request: QueryRequest,
        schema_info: Dict[str, Any]
    ) -> QueryResult:
        """生成 DELETE 查询"""
        # 简化实现
        table_name = request.table_names[0] if request.table_names else "table"
        
        sql = f"DELETE FROM {table_name} WHERE ..."
        
        return QueryResult(
            sql=sql,
            query_type=QueryType.DELETE,
            tables_used=[table_name],
            columns_used=[],
            joins=[],
            filters=[],
            aggregations=[],
            optimization_suggestions=[]
        )
    
    def _analyze_business_requirement(self, requirement: str) -> Dict[str, Any]:
        """分析业务需求"""
        analysis = {
            "keywords": [],
            "time_related": False,
            "aggregation_needed": False,
            "grouping_needed": False,
            "sorting_needed": False
        }
        
        requirement_lower = requirement.lower()
        
        # 提取关键词
        keywords = re.findall(r'\b\w+\b', requirement_lower)
        analysis["keywords"] = keywords
        
        # 检查时间相关
        time_keywords = ["时间", "日期", "年", "月", "日", "time", "date", "year", "month", "day"]
        analysis["time_related"] = any(keyword in requirement_lower for keyword in time_keywords)
        
        # 检查聚合需求
        agg_keywords = ["统计", "计算", "总数", "平均", "最大", "最小", "count", "sum", "avg", "max", "min"]
        analysis["aggregation_needed"] = any(keyword in requirement_lower for keyword in agg_keywords)
        
        # 检查分组需求
        group_keywords = ["按", "分组", "group", "by"]
        analysis["grouping_needed"] = any(keyword in requirement_lower for keyword in group_keywords)
        
        # 检查排序需求
        sort_keywords = ["排序", "顺序", "order", "sort"]
        analysis["sorting_needed"] = any(keyword in requirement_lower for keyword in sort_keywords)
        
        return analysis
    
    def _determine_tables(
        self,
        request: QueryRequest,
        schema_info: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> List[str]:
        """确定要查询的表"""
        tables = []
        
        # 如果明确指定了表名
        if request.table_names:
            tables.extend(request.table_names)
        else:
            # 根据业务需求推断表名
            available_tables = [table.get("name", "") for table in schema_info.get("tables", [])]
            
            # 根据关键词匹配表名
            for keyword in analysis["keywords"]:
                for table_name in available_tables:
                    if keyword in table_name.lower() and table_name not in tables:
                        tables.append(table_name)
            
            # 如果没有找到匹配的表，使用所有表
            if not tables:
                tables = available_tables[:5]  # 限制最多5个表
        
        return tables
    
    def _determine_columns(
        self,
        request: QueryRequest,
        schema_info: Dict[str, Any],
        analysis: Dict[str, Any],
        tables: List[str]
    ) -> List[str]:
        """确定要查询的列"""
        columns = []
        
        # 如果明确指定了列名
        if request.column_names:
            columns.extend(request.column_names)
        else:
            # 根据表名获取列信息
            all_columns = schema_info.get("columns", [])
            
            for table_name in tables:
                table_columns = [
                    col.get("name", "") for col in all_columns
                    if col.get("table_name", "") == table_name
                ]
                
                # 根据关键词匹配列名
                for keyword in analysis["keywords"]:
                    for col_name in table_columns:
                        if keyword in col_name.lower() and col_name not in columns:
                            columns.append(col_name)
                
                # 如果没有找到匹配的列，使用前几个列
                if not any(col in columns for col in table_columns):
                    columns.extend(table_columns[:3])  # 每个表最多3个列
        
        return columns
    
    def _determine_joins(
        self,
        tables: List[str],
        schema_info: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """确定连接关系"""
        joins = []
        
        if len(tables) < 2:
            return joins
        
        # 获取关系信息
        relationships = schema_info.get("relationships", [])
        
        # 查找表之间的关系
        for i in range(len(tables) - 1):
            table1 = tables[i]
            table2 = tables[i + 1]
            
            # 查找直接关系
            for rel in relationships:
                if (rel.get("from_table") == table1 and rel.get("to_table") == table2) or \
                   (rel.get("from_table") == table2 and rel.get("to_table") == table1):
                    joins.append({
                        "type": "INNER JOIN",
                        "table1": table1,
                        "column1": rel.get("from_column", ""),
                        "table2": table2,
                        "column2": rel.get("to_column", "")
                    })
                    break
        
        return joins
    
    def _determine_filters(
        self,
        request: QueryRequest,
        schema_info: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """确定过滤条件"""
        filters = []
        
        # 使用请求中的过滤条件
        if request.filters:
            for key, value in request.filters.items():
                filters.append({
                    "column": key,
                    "operator": "=",
                    "value": value
                })
        
        # 根据业务需求添加时间过滤
        if analysis["time_related"]:
            # 识别时间字段
            time_columns = self._identify_time_columns(schema_info)
            
            if time_columns:
                # 使用时间占位符而不是硬编码日期
                time_column = time_columns[0]
                filters.append({
                    "column": time_column,
                    "operator": ">=",
                    "value": "{{start_date}}"
                })
                filters.append({
                    "column": time_column,
                    "operator": "<=",
                    "value": "{{end_date}}"
                })
            else:
                # 如果没有找到时间字段，使用默认字段
                filters.append({
                    "column": "created_at",
                    "operator": ">=",
                    "value": "{{start_date}}"
                })
        
        return filters
    
    def _determine_aggregations(
        self,
        request: QueryRequest,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """确定聚合函数"""
        aggregations = []
        
        # 使用请求中的聚合配置
        if request.aggregations:
            for column, func in request.aggregations.items():
                aggregations.append({
                    "column": column,
                    "function": func
                })
        
        # 根据业务需求添加聚合
        if analysis["aggregation_needed"]:
            # 添加默认的计数聚合
            aggregations.append({
                "column": "*",
                "function": "COUNT"
            })
        
        return aggregations
    
    def _build_select_sql(
        self,
        tables: List[str],
        columns: List[str],
        joins: List[Dict[str, str]],
        filters: List[Dict[str, Any]],
        aggregations: List[Dict[str, str]],
        group_by: Optional[List[str]],
        order_by: Optional[List[str]],
        limit: Optional[int]
    ) -> str:
        """构建 SELECT SQL"""
        sql_parts = []
        
        # SELECT 子句
        if aggregations:
            select_items = []
            for agg in aggregations:
                func = agg["function"]
                column = agg["column"]
                if func.upper() == "COUNT" and column == "*":
                    select_items.append("COUNT(*)")
                else:
                    select_items.append(f"{func.upper()}({column})")
            sql_parts.append(f"SELECT {', '.join(select_items)}")
        else:
            if columns:
                sql_parts.append(f"SELECT {', '.join(columns)}")
            else:
                sql_parts.append("SELECT *")
        
        # FROM 子句
        if tables:
            sql_parts.append(f"FROM {tables[0]}")
        
        # JOIN 子句
        for join in joins:
            sql_parts.append(
                f"{join['type']} {join['table2']} ON "
                f"{join['table1']}.{join['column1']} = {join['table2']}.{join['column2']}"
            )
        
        # WHERE 子句
        if filters:
            where_conditions = []
            for filter_item in filters:
                column = filter_item["column"]
                operator = filter_item["operator"]
                value = filter_item["value"]
                
                if isinstance(value, str) and not value.startswith("'"):
                    where_conditions.append(f"{column} {operator} '{value}'")
                else:
                    where_conditions.append(f"{column} {operator} {value}")
            
            sql_parts.append(f"WHERE {' AND '.join(where_conditions)}")
        
        # GROUP BY 子句
        if group_by:
            sql_parts.append(f"GROUP BY {', '.join(group_by)}")
        
        # ORDER BY 子句
        if order_by:
            sql_parts.append(f"ORDER BY {', '.join(order_by)}")
        
        # LIMIT 子句
        if limit:
            sql_parts.append(f"LIMIT {limit}")
        
        return " ".join(sql_parts)
    
    def _get_optimization_suggestions(
        self,
        sql: str,
        tables: List[str],
        schema_info: Dict[str, Any]
    ) -> List[str]:
        """获取优化建议"""
        suggestions = []
        
        # 检查是否有适当的索引
        indexes = schema_info.get("indexes", [])
        for table in tables:
            table_indexes = [idx for idx in indexes if idx.get("table_name") == table]
            if not table_indexes:
                suggestions.append(f"考虑为表 {table} 添加索引以提高查询性能")
        
        # 检查 WHERE 条件
        if "WHERE" in sql.upper():
            suggestions.append("确保 WHERE 条件中的列有适当的索引")
        
        # 检查 JOIN 条件
        if "JOIN" in sql.upper():
            suggestions.append("确保 JOIN 条件中的列有适当的索引")
        
        # 检查 LIMIT
        if "LIMIT" not in sql.upper():
            suggestions.append("考虑添加 LIMIT 子句限制结果数量")
        
        return suggestions

    def _identify_time_columns(self, schema_info: Dict[str, Any]) -> List[str]:
        """
        识别Schema中的时间字段
        
        Args:
            schema_info: Schema信息
            
        Returns:
            时间字段列表
        """
        time_columns = []
        
        # 常见的时间字段名称模式
        time_patterns = [
            'date', 'time', 'created', 'updated', 'modified', 
            'timestamp', 'datetime', 'period', 'day', 'month', 'year'
        ]
        
        # 从schema_info中提取表信息
        tables = schema_info.get("tables", [])
        
        for table_info in tables:
            if isinstance(table_info, dict):
                table_name = table_info.get("name", "")
                columns = table_info.get("columns", [])
                
                for column_info in columns:
                    if isinstance(column_info, dict):
                        column_name = column_info.get("name", "").lower()
                        column_type = column_info.get("type", "").lower()
                        
                        # 检查列名是否包含时间相关关键词
                        if any(pattern in column_name for pattern in time_patterns):
                            time_columns.append(f"{table_name}.{column_info.get('name', '')}")
                        
                        # 检查数据类型是否为时间类型
                        elif any(time_type in column_type for time_type in ['date', 'time', 'timestamp', 'datetime']):
                            time_columns.append(f"{table_name}.{column_info.get('name', '')}")
        
        # 如果没有找到时间字段，返回一些常见的默认字段
        if not time_columns:
            time_columns = ["created_at", "updated_at", "date", "timestamp"]
        
        return time_columns


def create_sql_generator_tool(container: Any) -> SQLGeneratorTool:
    """
    创建 SQL 生成工具
    
    Args:
        container: 服务容器
        
    Returns:
        SQLGeneratorTool 实例
    """
    return SQLGeneratorTool(container)


# 导出
__all__ = [
    "SQLGeneratorTool",
    "QueryType",
    "JoinType",
    "QueryRequest",
    "QueryResult",
    "create_sql_generator_tool",
]