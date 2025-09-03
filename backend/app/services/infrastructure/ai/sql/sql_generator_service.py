"""
智能SQL生成器服务

负责根据自然语言需求和数据结构信息生成优化的SQL查询语句
"""

import logging
import re
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """查询类型"""
    SELECT = "select"           # 查询
    AGGREGATE = "aggregate"     # 聚合查询
    JOIN = "join"              # 连接查询
    SUBQUERY = "subquery"      # 子查询
    UNION = "union"            # 联合查询
    WINDOW = "window"          # 窗口函数查询
    CTE = "cte"                # 公用表表达式


class QueryComplexity(Enum):
    """查询复杂度"""
    SIMPLE = "simple"           # 简单查询
    MODERATE = "moderate"       # 中等查询
    COMPLEX = "complex"         # 复杂查询
    ADVANCED = "advanced"       # 高级查询


class SQLDialect(Enum):
    """SQL方言"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    DORIS = "doris"
    CLICKHOUSE = "clickhouse"
    STANDARD = "standard"


@dataclass
class GeneratedQuery:
    """生成的查询"""
    sql: str
    query_type: QueryType
    complexity: QueryComplexity
    parameters: Dict[str, Any]
    explanation: str
    performance_hints: List[str]
    estimated_cost: float
    metadata: Dict[str, Any]


class SQLGeneratorService:
    """智能SQL生成器服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # SQL模板库
        self.query_templates = {
            "basic_select": "SELECT {columns} FROM {table} {where_clause} {order_clause} {limit_clause}",
            "aggregate": "SELECT {group_columns}, {agg_functions} FROM {table} {where_clause} {group_by} {having_clause} {order_clause}",
            "join": "SELECT {columns} FROM {main_table} {join_clauses} {where_clause} {order_clause} {limit_clause}",
            "window": "SELECT {columns}, {window_functions} FROM {table} {where_clause} {order_clause}",
            "cte": "WITH {cte_definitions} SELECT {columns} FROM {table} {where_clause} {order_clause}",
            "subquery": "SELECT {columns} FROM {table} WHERE {column} IN (SELECT {sub_columns} FROM {sub_table} {sub_where}) {order_clause}"
        }
        
        # 聚合函数映射
        self.aggregation_mapping = {
            "总数": "COUNT(*)",
            "求和": "SUM({column})",
            "平均": "AVG({column})",
            "最大": "MAX({column})",
            "最小": "MIN({column})",
            "count": "COUNT(*)",
            "sum": "SUM({column})",
            "avg": "AVG({column})", 
            "average": "AVG({column})",
            "max": "MAX({column})",
            "min": "MIN({column})",
            "distinct": "COUNT(DISTINCT {column})"
        }
        
        # 时间函数映射
        self.time_functions = {
            "today": "CURRENT_DATE",
            "yesterday": "DATE_SUB(CURRENT_DATE, INTERVAL 1 DAY)",
            "this_month": "EXTRACT(YEAR_MONTH FROM CURRENT_DATE)",
            "last_month": "EXTRACT(YEAR_MONTH FROM DATE_SUB(CURRENT_DATE, INTERVAL 1 MONTH))",
            "this_year": "YEAR(CURRENT_DATE)",
            "last_year": "YEAR(CURRENT_DATE) - 1"
        }
        
        # 常见字段名映射
        self.field_mappings = {
            "时间": ["time", "date", "timestamp", "created_at", "updated_at"],
            "金额": ["amount", "price", "cost", "revenue", "money"],
            "数量": ["count", "quantity", "num", "number", "qty"],
            "名称": ["name", "title", "label", "description"],
            "状态": ["status", "state", "condition", "flag"],
            "类型": ["type", "category", "classification", "kind"]
        }

    async def generate_query(
        self, 
        requirements: Dict[str, Any], 
        schema_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        生成智能SQL查询
        
        Args:
            requirements: 查询需求描述
            schema_info: 数据库schema信息
            
        Returns:
            生成的查询结果字典
        """
        try:
            self.logger.info(f"开始智能SQL生成: {requirements.get('description', 'Unknown')}")
            
            # 分析需求
            parsed_requirements = self._parse_requirements(requirements)
            
            # 确定查询类型和复杂度
            query_type = self._determine_query_type(parsed_requirements)
            complexity = self._assess_complexity(parsed_requirements, schema_info)
            
            # 生成SQL结构
            sql_structure = await self._build_sql_structure(
                parsed_requirements, query_type, schema_info
            )
            
            # 构建完整SQL
            generated_sql = self._build_complete_sql(sql_structure, query_type)
            
            # 优化查询
            optimized_sql = self._optimize_query(generated_sql, complexity, schema_info)
            
            # 生成性能提示
            performance_hints = self._generate_performance_hints(
                optimized_sql, complexity, schema_info
            )
            
            # 估算查询成本
            estimated_cost = self._estimate_query_cost(optimized_sql, schema_info)
            
            # 生成解释
            explanation = self._generate_explanation(
                parsed_requirements, query_type, optimized_sql
            )
            
            result = {
                "sql": optimized_sql,
                "query_type": query_type.value,
                "complexity": complexity.value,
                "parameters": parsed_requirements.get("parameters", {}),
                "explanation": explanation,
                "performance_hints": performance_hints,
                "estimated_cost": estimated_cost,
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "requirements_processed": len(parsed_requirements),
                    "schema_tables_used": len(schema_info.get("tables", [])) if schema_info else 0,
                    "optimization_applied": True,
                    "dialect": "standard"
                }
            }
            
            self.logger.info(
                f"SQL生成完成: 类型={query_type.value}, 复杂度={complexity.value}, "
                f"成本={estimated_cost:.2f}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"SQL生成失败: {e}")
            raise ValueError(f"SQL生成失败: {str(e)}")

    def _parse_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """解析查询需求"""
        parsed = {
            "description": requirements.get("description", ""),
            "entity": requirements.get("entity", "table"),
            "columns": requirements.get("columns", ["*"]),
            "operation": requirements.get("operation", "SELECT"),
            "filters": requirements.get("filters", []),
            "aggregations": requirements.get("aggregations", []),
            "grouping": requirements.get("grouping", []),
            "sorting": requirements.get("sorting", []),
            "limit": requirements.get("limit"),
            "time_range": requirements.get("time_range"),
            "joins": requirements.get("joins", []),
            "parameters": requirements.get("parameters", {})
        }
        
        # 解析自然语言描述
        if parsed["description"]:
            parsed.update(self._parse_natural_language(parsed["description"]))
        
        return parsed

    def _parse_natural_language(self, description: str) -> Dict[str, Any]:
        """解析自然语言描述"""
        description_lower = description.lower()
        parsed = {}
        
        # 检测聚合操作
        for chinese, sql_func in self.aggregation_mapping.items():
            if chinese in description_lower:
                parsed.setdefault("aggregations", []).append({
                    "function": sql_func,
                    "detected_from": chinese
                })
        
        # 检测时间过滤
        time_patterns = {
            r'今天|today': 'today',
            r'昨天|yesterday': 'yesterday', 
            r'本月|this month': 'this_month',
            r'上月|last month': 'last_month',
            r'今年|this year': 'this_year',
            r'去年|last year': 'last_year'
        }
        
        for pattern, time_key in time_patterns.items():
            if re.search(pattern, description_lower):
                parsed["time_range"] = time_key
                break
        
        # 检测排序
        if any(kw in description_lower for kw in ['排序', '按照', '升序', '降序', 'order', 'sort', 'asc', 'desc']):
            if any(kw in description_lower for kw in ['降序', 'desc', '最大到最小']):
                parsed["sorting"] = [{"direction": "DESC"}]
            else:
                parsed["sorting"] = [{"direction": "ASC"}]
        
        # 检测限制
        limit_match = re.search(r'前(\d+)|top\s*(\d+)|limit\s*(\d+)', description_lower)
        if limit_match:
            limit_num = next(g for g in limit_match.groups() if g)
            parsed["limit"] = int(limit_num)
        
        return parsed

    def _determine_query_type(self, requirements: Dict[str, Any]) -> QueryType:
        """确定查询类型"""
        
        # 检查是否有聚合
        if requirements.get("aggregations") or requirements.get("grouping"):
            return QueryType.AGGREGATE
        
        # 检查是否有连接
        if requirements.get("joins"):
            return QueryType.JOIN
        
        # 检查是否有窗口函数需求
        description = requirements.get("description", "").lower()
        if any(kw in description for kw in ['排名', '排序', 'rank', 'row_number', 'lag', 'lead']):
            return QueryType.WINDOW
        
        # 检查是否需要子查询
        if any(kw in description for kw in ['其中', '满足条件', 'where exists', 'in (']):
            return QueryType.SUBQUERY
        
        # 默认为基础查询
        return QueryType.SELECT

    def _assess_complexity(
        self, 
        requirements: Dict[str, Any], 
        schema_info: Dict[str, Any] = None
    ) -> QueryComplexity:
        """评估查询复杂度"""
        
        complexity_score = 0
        
        # 基于需求特征评分
        if requirements.get("aggregations"):
            complexity_score += len(requirements["aggregations"]) * 0.2
        
        if requirements.get("joins"):
            complexity_score += len(requirements["joins"]) * 0.3
        
        if requirements.get("filters"):
            complexity_score += len(requirements["filters"]) * 0.1
        
        if requirements.get("grouping"):
            complexity_score += len(requirements["grouping"]) * 0.15
        
        # 基于schema复杂度
        if schema_info:
            table_count = len(schema_info.get("tables", []))
            if table_count > 5:
                complexity_score += 0.3
            elif table_count > 2:
                complexity_score += 0.1
        
        # 基于描述复杂度
        description_length = len(requirements.get("description", ""))
        if description_length > 200:
            complexity_score += 0.2
        elif description_length > 100:
            complexity_score += 0.1
        
        # 映射到复杂度等级
        if complexity_score < 0.3:
            return QueryComplexity.SIMPLE
        elif complexity_score < 0.7:
            return QueryComplexity.MODERATE
        elif complexity_score < 1.2:
            return QueryComplexity.COMPLEX
        else:
            return QueryComplexity.ADVANCED

    async def _build_sql_structure(
        self,
        requirements: Dict[str, Any],
        query_type: QueryType,
        schema_info: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """构建SQL结构"""
        
        structure = {
            "columns": self._build_columns_clause(requirements),
            "from": self._build_from_clause(requirements, schema_info),
            "where": self._build_where_clause(requirements),
            "group_by": self._build_group_by_clause(requirements),
            "having": self._build_having_clause(requirements),
            "order_by": self._build_order_by_clause(requirements),
            "limit": self._build_limit_clause(requirements),
            "joins": self._build_joins_clause(requirements, schema_info)
        }
        
        return structure

    def _build_columns_clause(self, requirements: Dict[str, Any]) -> str:
        """构建列选择子句"""
        columns = requirements.get("columns", ["*"])
        aggregations = requirements.get("aggregations", [])
        
        # 处理聚合函数
        if aggregations:
            agg_columns = []
            for agg in aggregations:
                if isinstance(agg, dict):
                    func = agg.get("function", "COUNT(*)")
                    # 如果需要列名，尝试推断
                    if "{column}" in func:
                        column = agg.get("column") or self._infer_column_name(requirements)
                        func = func.format(column=column)
                    agg_columns.append(f"{func} as {agg.get('alias', 'result')}")
                else:
                    agg_columns.append(str(agg))
            
            # 添加分组列
            group_columns = requirements.get("grouping", [])
            all_columns = group_columns + agg_columns
            return ", ".join(all_columns) if all_columns else "COUNT(*) as total"
        
        # 处理普通列选择
        if isinstance(columns, list):
            return ", ".join(columns)
        else:
            return str(columns)

    def _build_from_clause(self, requirements: Dict[str, Any], schema_info: Dict[str, Any] = None) -> str:
        """构建FROM子句"""
        entity = requirements.get("entity", "table")
        
        # 如果有schema信息，尝试匹配真实表名
        if schema_info and "tables" in schema_info:
            tables = schema_info["tables"]
            # 简单匹配逻辑
            for table_info in tables:
                table_name = table_info.get("name", "")
                if entity.lower() in table_name.lower() or table_name.lower() in entity.lower():
                    return table_name
        
        return entity

    def _build_where_clause(self, requirements: Dict[str, Any]) -> str:
        """构建WHERE子句"""
        filters = requirements.get("filters", [])
        time_range = requirements.get("time_range")
        
        conditions = []
        
        # 处理过滤条件
        for filter_item in filters:
            if isinstance(filter_item, str):
                conditions.append(filter_item)
            elif isinstance(filter_item, dict):
                column = filter_item.get("column", "id")
                operator = filter_item.get("operator", "=")
                value = filter_item.get("value", "")
                conditions.append(f"{column} {operator} '{value}'")
        
        # 处理时间范围
        if time_range:
            time_condition = self._build_time_condition(time_range)
            if time_condition:
                conditions.append(time_condition)
        
        return f"WHERE {' AND '.join(conditions)}" if conditions else ""

    def _build_time_condition(self, time_range: str) -> str:
        """构建时间条件"""
        time_column = "created_at"  # 默认时间字段
        
        if time_range in self.time_functions:
            time_func = self.time_functions[time_range]
            if time_range in ["today", "yesterday"]:
                return f"DATE({time_column}) = {time_func}"
            elif "month" in time_range:
                return f"EXTRACT(YEAR_MONTH FROM {time_column}) = {time_func}"
            elif "year" in time_range:
                return f"YEAR({time_column}) = {time_func}"
        
        return ""

    def _build_group_by_clause(self, requirements: Dict[str, Any]) -> str:
        """构建GROUP BY子句"""
        grouping = requirements.get("grouping", [])
        if grouping:
            return f"GROUP BY {', '.join(grouping)}"
        return ""

    def _build_having_clause(self, requirements: Dict[str, Any]) -> str:
        """构建HAVING子句"""
        # 简单实现，可扩展
        return ""

    def _build_order_by_clause(self, requirements: Dict[str, Any]) -> str:
        """构建ORDER BY子句"""
        sorting = requirements.get("sorting", [])
        if sorting:
            order_items = []
            for sort_item in sorting:
                if isinstance(sort_item, dict):
                    column = sort_item.get("column", "id")
                    direction = sort_item.get("direction", "ASC")
                    order_items.append(f"{column} {direction}")
                else:
                    order_items.append(f"{sort_item} ASC")
            return f"ORDER BY {', '.join(order_items)}"
        return ""

    def _build_limit_clause(self, requirements: Dict[str, Any]) -> str:
        """构建LIMIT子句"""
        limit = requirements.get("limit")
        if limit:
            return f"LIMIT {limit}"
        return ""

    def _build_joins_clause(self, requirements: Dict[str, Any], schema_info: Dict[str, Any] = None) -> List[str]:
        """构建JOIN子句"""
        joins = requirements.get("joins", [])
        join_clauses = []
        
        for join in joins:
            if isinstance(join, dict):
                join_type = join.get("type", "INNER")
                table = join.get("table", "")
                condition = join.get("condition", "")
                join_clauses.append(f"{join_type} JOIN {table} ON {condition}")
            else:
                join_clauses.append(str(join))
        
        return join_clauses

    def _build_complete_sql(self, structure: Dict[str, str], query_type: QueryType) -> str:
        """构建完整SQL语句"""
        
        sql_parts = []
        
        # SELECT子句
        sql_parts.append(f"SELECT {structure['columns']}")
        
        # FROM子句
        sql_parts.append(f"FROM {structure['from']}")
        
        # JOIN子句
        if structure.get("joins"):
            for join in structure["joins"]:
                sql_parts.append(join)
        
        # WHERE子句
        if structure.get("where"):
            sql_parts.append(structure["where"])
        
        # GROUP BY子句
        if structure.get("group_by"):
            sql_parts.append(structure["group_by"])
        
        # HAVING子句
        if structure.get("having"):
            sql_parts.append(structure["having"])
        
        # ORDER BY子句
        if structure.get("order_by"):
            sql_parts.append(structure["order_by"])
        
        # LIMIT子句
        if structure.get("limit"):
            sql_parts.append(structure["limit"])
        
        return " ".join(sql_parts)

    def _optimize_query(
        self, 
        sql: str, 
        complexity: QueryComplexity, 
        schema_info: Dict[str, Any] = None
    ) -> str:
        """优化查询"""
        optimized = sql
        
        # 基本优化：添加适当的括号
        optimized = re.sub(r'\s+', ' ', optimized)  # 规范空格
        optimized = optimized.strip()
        
        # 复杂查询优化
        if complexity in [QueryComplexity.COMPLEX, QueryComplexity.ADVANCED]:
            # 添加查询提示（如果支持的话）
            if "SELECT" in optimized and "FROM" in optimized:
                # 对于复杂查询，建议添加适当的索引提示
                pass
        
        return optimized

    def _generate_performance_hints(
        self, 
        sql: str, 
        complexity: QueryComplexity, 
        schema_info: Dict[str, Any] = None
    ) -> List[str]:
        """生成性能提示"""
        hints = []
        
        # 基于复杂度的提示
        if complexity == QueryComplexity.SIMPLE:
            hints.append("查询相对简单，预期性能良好")
        elif complexity == QueryComplexity.MODERATE:
            hints.append("中等复杂度查询，建议检查相关字段索引")
        elif complexity == QueryComplexity.COMPLEX:
            hints.extend([
                "复杂查询，建议优化WHERE条件顺序",
                "考虑添加合适的数据库索引"
            ])
        else:  # ADVANCED
            hints.extend([
                "高级查询，建议分析执行计划",
                "考虑查询缓存或结果缓存",
                "建议监控查询执行时间"
            ])
        
        # 基于SQL内容的提示
        if "JOIN" in sql.upper():
            hints.append("多表连接查询，确保连接字段有索引")
        
        if "GROUP BY" in sql.upper():
            hints.append("分组查询，注意分组字段的选择性")
        
        if "ORDER BY" in sql.upper() and "LIMIT" not in sql.upper():
            hints.append("全表排序，建议添加LIMIT限制结果数量")
        
        return hints

    def _estimate_query_cost(self, sql: str, schema_info: Dict[str, Any] = None) -> float:
        """估算查询成本"""
        base_cost = 1.0
        
        # 基于SQL复杂度评分
        complexity_factors = {
            "JOIN": 0.5,
            "GROUP BY": 0.3,
            "ORDER BY": 0.3,
            "HAVING": 0.2,
            "SUBQUERY": 0.4,
            "UNION": 0.3
        }
        
        for keyword, factor in complexity_factors.items():
            if keyword in sql.upper():
                base_cost += factor
        
        # 基于预估数据量调整
        if schema_info:
            estimated_rows = schema_info.get("estimated_rows", 1000)
            if estimated_rows > 100000:
                base_cost *= 1.5
            elif estimated_rows > 10000:
                base_cost *= 1.2
        
        return round(min(base_cost, 10.0), 2)  # 最大成本限制为10

    def _generate_explanation(
        self, 
        requirements: Dict[str, Any], 
        query_type: QueryType, 
        sql: str
    ) -> str:
        """生成查询解释"""
        
        explanation_parts = []
        
        # 基础说明
        operation = requirements.get("operation", "查询")
        entity = requirements.get("entity", "数据")
        explanation_parts.append(f"此查询用于{operation}{entity}")
        
        # 查询类型说明
        type_descriptions = {
            QueryType.SELECT: "执行基础数据查询",
            QueryType.AGGREGATE: "执行聚合统计查询",
            QueryType.JOIN: "执行多表连接查询",
            QueryType.SUBQUERY: "使用子查询进行条件筛选",
            QueryType.WINDOW: "使用窗口函数进行高级分析",
            QueryType.UNION: "合并多个查询结果",
            QueryType.CTE: "使用公用表表达式简化复杂查询"
        }
        explanation_parts.append(type_descriptions.get(query_type, "执行数据查询"))
        
        # 特殊功能说明
        if "GROUP BY" in sql.upper():
            explanation_parts.append("包含数据分组和聚合计算")
        
        if "ORDER BY" in sql.upper():
            explanation_parts.append("结果按指定字段排序")
        
        if "LIMIT" in sql.upper():
            explanation_parts.append("限制返回结果数量")
        
        return "。".join(explanation_parts) + "。"

    def _infer_column_name(self, requirements: Dict[str, Any]) -> str:
        """推断列名"""
        description = requirements.get("description", "").lower()
        
        # 基于描述推断可能的列名
        for chinese, english_options in self.field_mappings.items():
            if chinese in description:
                return english_options[0]  # 返回第一个选项
        
        # 默认返回
        return "id"

    def get_supported_functions(self) -> Dict[str, List[str]]:
        """获取支持的函数列表"""
        return {
            "aggregation_functions": list(self.aggregation_mapping.keys()),
            "time_functions": list(self.time_functions.keys()),
            "query_types": [qt.value for qt in QueryType],
            "complexity_levels": [qc.value for qc in QueryComplexity]
        }

    def validate_sql(self, sql: str) -> Dict[str, Any]:
        """验证生成的SQL"""
        issues = []
        warnings = []
        
        # 基本语法检查
        if not sql.strip():
            issues.append("SQL语句为空")
        
        sql_upper = sql.upper()
        if not sql_upper.startswith("SELECT"):
            warnings.append("非SELECT语句，请谨慎执行")
        
        # 检查潜在的性能问题
        if "SELECT *" in sql_upper:
            warnings.append("使用了SELECT *，可能影响性能")
        
        if "ORDER BY" in sql_upper and "LIMIT" not in sql_upper:
            warnings.append("全表排序但没有LIMIT，可能消耗大量资源")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "safety_score": 1.0 - (len(issues) * 0.3 + len(warnings) * 0.1)
        }


# 全局实例
sql_generator_service = SQLGeneratorService()