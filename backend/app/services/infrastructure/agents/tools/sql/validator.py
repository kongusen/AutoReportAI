from __future__ import annotations

from loom.interfaces.tool import BaseTool
"""
SQL 验证工具

验证 SQL 查询的语法正确性和逻辑合理性
支持多种数据库的语法检查
"""


import logging
import re
from typing import Any, Dict, List, Optional, Union, Tuple, Literal
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, Field


from ...types import ToolCategory, ContextInfo

logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    """验证级别"""
    BASIC = "basic"      # 基础语法检查
    STRICT = "strict"    # 严格语法检查
    COMPREHENSIVE = "comprehensive"  # 全面检查


class ValidationResult(str, Enum):
    """验证结果"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


@dataclass
class ValidationIssue:
    """验证问题"""
    level: ValidationResult
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    suggestion: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ValidationReport:
    """验证报告"""
    is_valid: bool
    issues: List[ValidationIssue]
    warnings: List[ValidationIssue]
    errors: List[ValidationIssue]
    suggestions: List[str]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SQLValidatorTool(BaseTool):
    """SQL 验证工具"""
    
    def __init__(self, container: Any, connection_config: Optional[Dict[str, Any]] = None):
        """
        Args:
            container: 服务容器
            connection_config: 数据源连接配置（在初始化时注入，优先使用内部的配置）
        """
        super().__init__()
        self.name = "sql_validator"
        self.category = ToolCategory.SQL
        self.description = "验证 SQL 查询的语法正确性和逻辑合理性"
        self.container = container
        # 🔥 关键修复：在初始化时注入 connection_config
        self._connection_config = connection_config
        
        # 使用 Pydantic 定义参数模式（args_schema）
        class SQLValidatorArgs(BaseModel):
            sql: str = Field(description="要验证的 SQL 查询")
            validation_level: Literal["basic", "strict", "comprehensive"] = Field(
                default="comprehensive", description="验证级别"
            )
            check_syntax: bool = Field(default=True, description="是否检查语法")
            check_semantics: bool = Field(default=True, description="是否检查语义")
            check_performance: bool = Field(default=False, description="是否检查性能")
            schema_info: Optional[Dict[str, Any]] = Field(default=None, description="Schema 信息（可选）")

        self.args_schema = SQLValidatorArgs
        
        # SQL 关键字
        self.sql_keywords = {
            "SELECT", "FROM", "WHERE", "GROUP BY", "HAVING", "ORDER BY", "LIMIT",
            "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP",
            "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN",
            "UNION", "UNION ALL", "INTERSECT", "EXCEPT",
            "AND", "OR", "NOT", "IN", "EXISTS", "BETWEEN", "LIKE", "IS NULL", "IS NOT NULL",
            "COUNT", "SUM", "AVG", "MIN", "MAX", "DISTINCT"
        }
        
        # 数据类型
        self.data_types = {
            "INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT",
            "DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL",
            "VARCHAR", "CHAR", "TEXT", "LONGTEXT",
            "DATE", "DATETIME", "TIMESTAMP", "TIME",
            "BOOLEAN", "BOOL", "BLOB", "JSON"
        }
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数模式（基于 args_schema 生成）"""
        try:
            parameters = self.args_schema.model_json_schema()
        except Exception:
            parameters = self.args_schema.schema()  # type: ignore[attr-defined]
        return {
            "type": "function",
            "function": {
                "name": "sql_validator",
                "description": "验证 SQL 查询的语法正确性和逻辑合理性",
                "parameters": parameters,
            },
        }
    
    async def run(
        self,
        sql: str,
        connection_config: Optional[Dict[str, Any]] = None,
        validation_level: str = "comprehensive",
        check_syntax: bool = True,
        check_semantics: bool = True,
        check_performance: bool = False,
        schema_info: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行 SQL 验证
        
        Args:
            sql: 要验证的 SQL 查询
            connection_config: 数据源连接配置（可选，优先使用初始化时注入的配置）
            validation_level: 验证级别
            check_syntax: 是否检查语法
            check_semantics: 是否检查语义
            check_performance: 是否检查性能
            schema_info: Schema 信息
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        logger.info(f"🔍 [SQLValidatorTool] 验证 SQL")
        logger.info(f"   验证级别: {validation_level}")
        logger.info(f"   SQL 长度: {len(sql)} 字符")
        
        # 🔥 关键修复：优先使用初始化时注入的 connection_config，允许从 kwargs 临时传入以便验证/测试
        connection_config = self._connection_config or connection_config or kwargs.get("connection_config")
        if not connection_config:
            return {
                "success": False,
                "error": "未配置数据源连接，请在初始化工具时提供 connection_config",
                "report": None
            }
        
        try:
            # 🔧 在验证阶段安全替换时间占位符，避免语法校验误报
            resolved_sql, resolution_meta = self._resolve_time_placeholders(sql, kwargs)

            # 获取 Schema 信息
            if schema_info is None:
                # 🔥 修复：从SQL中提取表名，传给SchemaRetrievalTool
                table_names = self._extract_table_names(resolved_sql)
                schema_info = await self._get_schema_info(connection_config, table_names=table_names)
            
            # 执行验证
            report = await self._validate_sql(
                resolved_sql, validation_level, check_syntax, check_semantics, 
                check_performance, schema_info
            )
            
            return {
                "success": True,
                "report": report,
                "metadata": {
                    "validation_level": validation_level,
                    "sql_length": len(sql),
                    "resolved_sql_length": len(resolved_sql),
                    "resolved_sql": resolved_sql,
                    "placeholder_resolution": resolution_meta,
                    "issues_count": len(report.issues),
                    "warnings_count": len(report.warnings),
                    "errors_count": len(report.errors)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [SQLValidatorTool] 验证失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "report": None
            }

    def _resolve_time_placeholders(self, sql: str, kwargs: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """将 {{start_date}} / {{end_date}} 在验证阶段替换为安全的具体日期。

        优先从 kwargs['context'] 或 kwargs['task_context'] 或 kwargs['template_context'] 获取；
        可接受的键：('start_date','end_date') 或 ('time_window': {'start','end'})。
        若均不可用，使用安全的默认值，不影响最终存储（仅校验阶段使用）。
        """
        original_sql = sql
        meta: Dict[str, Any] = {"source": None, "used_defaults": False}

        # 快速路径：无占位符
        if "{{start_date}}" not in sql and "{{end_date}}" not in sql:
            return sql, {"changed": False}

        # 收集上下文
        ctx = kwargs.get("context") or {}
        task_ctx = kwargs.get("task_context") or {}
        tpl_ctx = kwargs.get("template_context") or {}

        def pick(k: str) -> Optional[str]:
            return (ctx.get(k) or task_ctx.get(k) or tpl_ctx.get(k)) if any([ctx, task_ctx, tpl_ctx]) else None

        start = pick("start_date")
        end = pick("end_date")

        # time_window 结构支持
        tw = pick("time_window") if isinstance(pick("time_window"), dict) else None
        if isinstance(tw, dict):
            start = start or tw.get("start") or tw.get("from")
            end = end or tw.get("end") or tw.get("to")

        # 默认安全值（仅用于验证阶段）
        if not start or not end:
            start = start or "2024-01-01"
            end = end or "2024-01-31"
            meta["used_defaults"] = True

        # 执行替换
        resolved = original_sql.replace("{{start_date}}", str(start)).replace("{{end_date}}", str(end))
        meta.update({"start_date": str(start), "end_date": str(end), "changed": resolved != original_sql})
        return resolved, meta
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """向后兼容的execute方法"""
        return await self.run(**kwargs)
    
    async def _get_schema_info(self, connection_config: Dict[str, Any], table_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取 Schema 信息
        
        Args:
            connection_config: 连接配置
            table_names: 可选的表名列表，如果提供则只获取这些表的结构信息
        """
        try:
            from ..schema.retrieval import create_schema_retrieval_tool

            # 🔥 修复：传递 connection_config 以便工具能正确初始化
            retrieval_tool = create_schema_retrieval_tool(
                self.container,
                connection_config=self._connection_config or connection_config
            )

            # 🔥 修复：如果提供了表名，传入SchemaRetrievalTool；否则尝试从上下文获取
            logger.info(f"🔍 [SQL验证] 开始检索 Schema 信息")
            if table_names:
                logger.info(f"   表名: {table_names}")
            else:
                logger.info(f"   表名: None (将从上下文获取)")

            result = await retrieval_tool.run(
                table_names=table_names,  # 🔥 关键修复：传入从SQL中提取的表名
                include_relationships=True,
                include_constraints=True,
                format="detailed"
            )
            
            if result.get("success"):
                return result.get("result", {})
            else:
                logger.warning(f"⚠️ 获取 Schema 信息失败: {result.get('error')}")
                # 🔥 如果SchemaRetrievalTool失败且没有表名，尝试返回空字典让验证继续进行
                if not table_names:
                    logger.warning(f"⚠️ SchemaRetrievalTool无法从上下文获取表名，将使用空Schema信息继续验证")
                    return {}
                else:
                    logger.error(f"❌ SchemaRetrievalTool失败，即使传入了表名: {result.get('error')}")
                    return {}
                
        except Exception as e:
            logger.warning(f"⚠️ 获取 Schema 信息失败: {e}")
            # 🔥 即使失败，也返回空字典让验证继续进行（使用语法验证）
            return {}
    
    async def _validate_sql(
        self,
        sql: str,
        validation_level: str,
        check_syntax: bool,
        check_semantics: bool,
        check_performance: bool,
        schema_info: Dict[str, Any]
    ) -> ValidationReport:
        """验证 SQL"""
        issues = []
        
        # 语法检查
        if check_syntax:
            syntax_issues = self._check_syntax(sql)
            issues.extend(syntax_issues)
        
        # 语义检查
        if check_semantics:
            semantic_issues = self._check_semantics(sql, schema_info)
            issues.extend(semantic_issues)
        
        # 性能检查
        if check_performance:
            performance_issues = self._check_performance(sql, schema_info)
            issues.extend(performance_issues)
        
        # 分类问题
        errors = [issue for issue in issues if issue.level == ValidationResult.INVALID]
        warnings = [issue for issue in issues if issue.level == ValidationResult.WARNING]
        
        # 提取建议
        suggestions = [issue.suggestion for issue in issues if issue.suggestion]
        
        # 判断整体有效性
        is_valid = len(errors) == 0
        
        return ValidationReport(
            is_valid=is_valid,
            issues=issues,
            warnings=warnings,
            errors=errors,
            suggestions=suggestions
        )
    
    def _check_syntax(self, sql: str) -> List[ValidationIssue]:
        """检查语法"""
        issues = []
        
        # 基本语法检查
        sql_upper = sql.upper().strip()
        
        # 检查是否为空
        if not sql.strip():
            issues.append(ValidationIssue(
                level=ValidationResult.INVALID,
                message="SQL 查询不能为空"
            ))
            return issues
        
        # 检查基本结构
        if not any(keyword in sql_upper for keyword in ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"]):
            issues.append(ValidationIssue(
                level=ValidationResult.INVALID,
                message="SQL 查询必须包含有效的 SQL 语句",
                suggestion="请确保查询包含 SELECT、INSERT、UPDATE、DELETE、CREATE、ALTER 或 DROP 语句"
            ))
        
        # 检查括号匹配
        if not self._check_parentheses(sql):
            issues.append(ValidationIssue(
                level=ValidationResult.INVALID,
                message="括号不匹配",
                suggestion="请检查并修正括号的匹配"
            ))
        
        # 检查引号匹配
        if not self._check_quotes(sql):
            issues.append(ValidationIssue(
                level=ValidationResult.INVALID,
                message="引号不匹配",
                suggestion="请检查并修正引号的匹配"
            ))
        
        # 检查分号
        if sql.strip().endswith(';'):
            issues.append(ValidationIssue(
                level=ValidationResult.WARNING,
                message="建议移除末尾的分号",
                suggestion="在大多数情况下，末尾的分号是不必要的"
            ))
        
        # 检查 SELECT 语句结构
        if sql_upper.startswith("SELECT"):
            select_issues = self._check_select_syntax(sql)
            issues.extend(select_issues)
        
        # 检查 INSERT 语句结构
        elif sql_upper.startswith("INSERT"):
            insert_issues = self._check_insert_syntax(sql)
            issues.extend(insert_issues)
        
        # 检查 UPDATE 语句结构
        elif sql_upper.startswith("UPDATE"):
            update_issues = self._check_update_syntax(sql)
            issues.extend(update_issues)
        
        # 检查 DELETE 语句结构
        elif sql_upper.startswith("DELETE"):
            delete_issues = self._check_delete_syntax(sql)
            issues.extend(delete_issues)
        
        return issues
    
    def _check_semantics(self, sql: str, schema_info: Dict[str, Any]) -> List[ValidationIssue]:
        """检查语义"""
        issues = []
        
        # 提取表名
        table_names = self._extract_table_names(sql)
        
        # 检查表是否存在
        available_tables = [table.get("name", "") for table in schema_info.get("tables", [])]
        for table_name in table_names:
            if table_name and table_name not in available_tables:
                issues.append(ValidationIssue(
                    level=ValidationResult.INVALID,
                    message=f"表 '{table_name}' 不存在",
                    suggestion=f"请检查表名是否正确，可用表: {', '.join(available_tables[:5])}"
                ))
        
        # 提取列名
        column_names = self._extract_column_names(sql)
        
        # 检查列是否存在
        available_columns = schema_info.get("columns", [])
        for column_name in column_names:
            if column_name and not self._column_exists(column_name, available_columns):
                issues.append(ValidationIssue(
                    level=ValidationResult.INVALID,
                    message=f"列 '{column_name}' 不存在",
                    suggestion="请检查列名是否正确"
                ))
        
        # 检查 JOIN 条件
        join_issues = self._check_joins(sql, schema_info)
        issues.extend(join_issues)
        
        return issues
    
    def _check_performance(self, sql: str, schema_info: Dict[str, Any]) -> List[ValidationIssue]:
        """检查性能"""
        issues = []
        
        sql_upper = sql.upper()
        
        # 检查是否有 LIMIT
        if "SELECT" in sql_upper and "LIMIT" not in sql_upper:
            issues.append(ValidationIssue(
                level=ValidationResult.WARNING,
                message="建议添加 LIMIT 子句限制结果数量",
                suggestion="添加 LIMIT 子句可以提高查询性能"
            ))
        
        # 检查是否有 WHERE 条件
        if "SELECT" in sql_upper and "WHERE" not in sql_upper and "JOIN" not in sql_upper:
            issues.append(ValidationIssue(
                level=ValidationResult.WARNING,
                message="建议添加 WHERE 条件过滤数据",
                suggestion="添加适当的 WHERE 条件可以减少扫描的数据量"
            ))
        
        # 检查是否有索引
        indexes = schema_info.get("indexes", [])
        table_names = self._extract_table_names(sql)
        
        for table_name in table_names:
            table_indexes = [idx for idx in indexes if idx.get("table_name") == table_name]
            if not table_indexes:
                issues.append(ValidationIssue(
                    level=ValidationResult.WARNING,
                    message=f"表 '{table_name}' 没有索引",
                    suggestion=f"考虑为表 '{table_name}' 添加适当的索引"
                ))
        
        # 检查子查询
        if "SELECT" in sql_upper and sql_upper.count("SELECT") > 1:
            issues.append(ValidationIssue(
                level=ValidationResult.WARNING,
                message="查询包含子查询，可能影响性能",
                suggestion="考虑使用 JOIN 替代子查询以提高性能"
            ))
        
        return issues
    
    def _check_parentheses(self, sql: str) -> bool:
        """检查括号匹配"""
        stack = []
        for char in sql:
            if char == '(':
                stack.append(char)
            elif char == ')':
                if not stack:
                    return False
                stack.pop()
        return len(stack) == 0
    
    def _check_quotes(self, sql: str) -> bool:
        """检查引号匹配"""
        single_quotes = sql.count("'")
        double_quotes = sql.count('"')
        return single_quotes % 2 == 0 and double_quotes % 2 == 0
    
    def _check_select_syntax(self, sql: str) -> List[ValidationIssue]:
        """检查 SELECT 语句语法"""
        issues = []
        sql_upper = sql.upper()
        
        # 检查 FROM 子句
        if "FROM" not in sql_upper:
            issues.append(ValidationIssue(
                level=ValidationResult.INVALID,
                message="SELECT 语句缺少 FROM 子句",
                suggestion="请添加 FROM 子句指定要查询的表"
            ))
        
        # 检查 GROUP BY 和 HAVING
        if "HAVING" in sql_upper and "GROUP BY" not in sql_upper:
            issues.append(ValidationIssue(
                level=ValidationResult.INVALID,
                message="HAVING 子句需要 GROUP BY 子句",
                suggestion="请添加 GROUP BY 子句或移除 HAVING 子句"
            ))
        
        return issues
    
    def _check_insert_syntax(self, sql: str) -> List[ValidationIssue]:
        """检查 INSERT 语句语法"""
        issues = []
        sql_upper = sql.upper()
        
        # 检查 INTO 关键字
        if "INTO" not in sql_upper:
            issues.append(ValidationIssue(
                level=ValidationResult.INVALID,
                message="INSERT 语句缺少 INTO 关键字",
                suggestion="请添加 INTO 关键字"
            ))
        
        # 检查 VALUES 或 SELECT
        if "VALUES" not in sql_upper and "SELECT" not in sql_upper:
            issues.append(ValidationIssue(
                level=ValidationResult.INVALID,
                message="INSERT 语句缺少 VALUES 或 SELECT 子句",
                suggestion="请添加 VALUES 或 SELECT 子句"
            ))
        
        return issues
    
    def _check_update_syntax(self, sql: str) -> List[ValidationIssue]:
        """检查 UPDATE 语句语法"""
        issues = []
        sql_upper = sql.upper()
        
        # 检查 SET 子句
        if "SET" not in sql_upper:
            issues.append(ValidationIssue(
                level=ValidationResult.INVALID,
                message="UPDATE 语句缺少 SET 子句",
                suggestion="请添加 SET 子句指定要更新的列"
            ))
        
        return issues
    
    def _check_delete_syntax(self, sql: str) -> List[ValidationIssue]:
        """检查 DELETE 语句语法"""
        issues = []
        sql_upper = sql.upper()
        
        # 检查 FROM 子句
        if "FROM" not in sql_upper:
            issues.append(ValidationIssue(
                level=ValidationResult.INVALID,
                message="DELETE 语句缺少 FROM 子句",
                suggestion="请添加 FROM 子句指定要删除的表"
            ))
        
        return issues
    
    def _extract_table_names(self, sql: str) -> List[str]:
        """提取表名"""
        table_names = []
        
        # 简单的正则表达式提取表名
        # FROM 子句
        from_pattern = r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        from_matches = re.findall(from_pattern, sql, re.IGNORECASE)
        table_names.extend(from_matches)
        
        # JOIN 子句
        join_pattern = r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        join_matches = re.findall(join_pattern, sql, re.IGNORECASE)
        table_names.extend(join_matches)
        
        # UPDATE 子句
        update_pattern = r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        update_matches = re.findall(update_pattern, sql, re.IGNORECASE)
        table_names.extend(update_matches)
        
        # DELETE 子句
        delete_pattern = r'DELETE\s+FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        delete_matches = re.findall(delete_pattern, sql, re.IGNORECASE)
        table_names.extend(delete_matches)
        
        return list(set(table_names))  # 去重
    
    def _extract_column_names(self, sql: str) -> List[str]:
        """提取列名"""
        column_names = []
        
        # SELECT 子句中的列
        select_pattern = r'SELECT\s+(.*?)\s+FROM'
        select_match = re.search(select_pattern, sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            # 简单的列名提取
            columns = [col.strip() for col in select_clause.split(',')]
            for col in columns:
                # 移除别名
                if ' AS ' in col.upper():
                    col = col.split(' AS ')[0].strip()
                # 移除函数
                if '(' in col and ')' in col:
                    continue
                column_names.append(col)
        
        # WHERE 子句中的列
        where_pattern = r'WHERE\s+(.*?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|$)'
        where_match = re.search(where_pattern, sql, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_clause = where_match.group(1)
            # 简单的列名提取
            where_columns = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)', where_clause)
            column_names.extend(where_columns)
        
        return list(set(column_names))  # 去重
    
    def _column_exists(self, column_name: str, available_columns: List[Dict[str, Any]]) -> bool:
        """检查列是否存在"""
        for col in available_columns:
            if col.get("name", "").lower() == column_name.lower():
                return True
        return False
    
    def _check_joins(self, sql: str, schema_info: Dict[str, Any]) -> List[ValidationIssue]:
        """检查 JOIN 条件"""
        issues = []
        
        # 提取 JOIN 条件
        join_pattern = r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+ON\s+(.*?)(?:\s+JOIN|\s+WHERE|\s+GROUP|\s+ORDER|\s+LIMIT|$)'
        join_matches = re.findall(join_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        relationships = schema_info.get("relationships", [])
        
        for table_name, join_condition in join_matches:
            # 检查 JOIN 条件是否合理
            if '=' not in join_condition:
                issues.append(ValidationIssue(
                    level=ValidationResult.WARNING,
                    message=f"JOIN 条件 '{join_condition}' 可能不正确",
                    suggestion="JOIN 条件通常使用等号 (=) 连接两个列"
                ))
        
        return issues


def create_sql_validator_tool(
    container: Any,
    connection_config: Optional[Dict[str, Any]] = None
) -> SQLValidatorTool:
    """
    创建 SQL 验证工具
    
    Args:
        container: 服务容器
        connection_config: 数据源连接配置（在初始化时注入）
        
    Returns:
        SQLValidatorTool 实例
    """
    return SQLValidatorTool(container, connection_config=connection_config)


# 导出
__all__ = [
    "SQLValidatorTool",
    "ValidationLevel",
    "ValidationResult",
    "ValidationIssue",
    "ValidationReport",
    "create_sql_validator_tool",
]