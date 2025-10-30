from __future__ import annotations

from loom.interfaces.tool import BaseTool
"""
SQL 列检查工具

检查 SQL 查询中的列是否存在、类型是否匹配等
提供详细的列验证和修复建议
"""


import logging
import re
from typing import Any, Dict, List, Optional, Union, Tuple, Literal
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, Field


from ...types import ToolCategory, ContextInfo

logger = logging.getLogger(__name__)


class ColumnCheckType(str, Enum):
    """列检查类型"""
    EXISTENCE = "existence"      # 存在性检查
    TYPE_COMPATIBILITY = "type_compatibility"  # 类型兼容性
    NULLABILITY = "nullability"  # 可空性检查
    CONSTRAINT = "constraint"    # 约束检查
    INDEX = "index"             # 索引检查


class CheckResult(str, Enum):
    """检查结果"""
    PASS = "pass"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ColumnCheckIssue:
    """列检查问题"""
    column_name: str
    table_name: str
    check_type: ColumnCheckType
    result: CheckResult
    message: str
    suggestion: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ColumnCheckReport:
    """列检查报告"""
    total_columns: int
    checked_columns: int
    passed_columns: int
    warning_columns: int
    error_columns: int
    issues: List[ColumnCheckIssue]
    suggestions: List[str]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SQLColumnCheckerTool(BaseTool):
    """SQL 列检查工具"""
    
    def __init__(self, container: Any):
        """
        Args:
            container: 服务容器
        """
        super().__init__()

        self.name = "sql_column_checker"

        self.category = ToolCategory.SQL

        self.description = "检查 SQL 查询中的列是否存在、类型是否匹配等" 
        self.container = container
        
        # 使用 Pydantic 定义参数模式（args_schema）
        class SQLColumnCheckerArgs(BaseModel):
            sql: str = Field(description="要检查的 SQL 查询")
            connection_config: Dict[str, Any] = Field(description="数据源连接配置")
            check_types: Optional[List[Literal[
                "existence", "type_compatibility", "nullability", "constraint", "index"
            ]]] = Field(
                default=["existence", "type_compatibility", "nullability"], description="要执行的检查类型"
            )
            strict_mode: bool = Field(default=False, description="是否启用严格模式")
            schema_info: Optional[Dict[str, Any]] = Field(default=None, description="Schema 信息（可选）")

        self.args_schema = SQLColumnCheckerArgs
        
        # 数据类型兼容性映射
        self.type_compatibility = {
            "INT": ["INTEGER", "BIGINT", "SMALLINT", "TINYINT", "DECIMAL", "NUMERIC"],
            "INTEGER": ["INT", "BIGINT", "SMALLINT", "TINYINT", "DECIMAL", "NUMERIC"],
            "BIGINT": ["INT", "INTEGER", "SMALLINT", "TINYINT", "DECIMAL", "NUMERIC"],
            "SMALLINT": ["INT", "INTEGER", "BIGINT", "TINYINT", "DECIMAL", "NUMERIC"],
            "TINYINT": ["INT", "INTEGER", "BIGINT", "SMALLINT", "DECIMAL", "NUMERIC"],
            "DECIMAL": ["NUMERIC", "INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT"],
            "NUMERIC": ["DECIMAL", "INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT"],
            "FLOAT": ["DOUBLE", "REAL", "DECIMAL", "NUMERIC"],
            "DOUBLE": ["FLOAT", "REAL", "DECIMAL", "NUMERIC"],
            "REAL": ["FLOAT", "DOUBLE", "DECIMAL", "NUMERIC"],
            "VARCHAR": ["CHAR", "TEXT", "LONGTEXT"],
            "CHAR": ["VARCHAR", "TEXT", "LONGTEXT"],
            "TEXT": ["VARCHAR", "CHAR", "LONGTEXT"],
            "LONGTEXT": ["VARCHAR", "CHAR", "TEXT"],
            "DATE": ["DATETIME", "TIMESTAMP"],
            "DATETIME": ["DATE", "TIMESTAMP"],
            "TIMESTAMP": ["DATE", "DATETIME"],
            "TIME": ["DATETIME", "TIMESTAMP"],
            "BOOLEAN": ["BOOL", "TINYINT"],
            "BOOL": ["BOOLEAN", "TINYINT"],
            "JSON": ["TEXT", "LONGTEXT"],
            "BLOB": ["LONGBLOB", "MEDIUMBLOB", "TINYBLOB"]
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
                "name": "sql_column_checker",
                "description": "检查 SQL 查询中的列是否存在、类型是否匹配等",
                "parameters": parameters,
            },
        }
    
    async def run(

    
        self,
        sql: str,
        connection_config: Dict[str, Any],
        check_types: Optional[List[str]] = None,
        strict_mode: bool = False,
        schema_info: Optional[Dict[str, Any]] = None,
        **kwargs
    

    
    ) -> Dict[str, Any]:
        """
        执行列检查
        
        Args:
            sql: 要检查的 SQL 查询
            connection_config: 数据源连接配置
            check_types: 要执行的检查类型
            strict_mode: 是否启用严格模式
            schema_info: Schema 信息
            
        Returns:
            Dict[str, Any]: 检查结果
        """
        logger.info(f"🔍 [SQLColumnCheckerTool] 检查列")
        logger.info(f"   检查类型: {check_types}")

    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """向后兼容的execute方法"""
        return await self.run(**kwargs)

    
        return await self.run(**kwargs)
        logger.info(f"   严格模式: {strict_mode}")
        
        try:
            # 获取 Schema 信息
            if schema_info is None:
                schema_info = await self._get_schema_info(connection_config)
            
            # 设置默认检查类型
            if check_types is None:
                check_types = ["existence", "type_compatibility", "nullability"]
            
            # 提取列信息
            columns_info = self._extract_columns_from_sql(sql)
            
            # 执行检查
            report = await self._check_columns(
                columns_info, schema_info, check_types, strict_mode
            )
            
            return {
                "success": True,
                "report": report,
                "metadata": {
                    "check_types": check_types,
                    "strict_mode": strict_mode,
                    "sql_length": len(sql),
                    "columns_found": len(columns_info)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [SQLColumnCheckerTool] 检查失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "report": None
            }
    
    async def _get_schema_info(self, connection_config: Dict[str, Any]) -> Dict[str, Any]:
        """获取 Schema 信息"""
        try:
            from ..schema.retrieval import create_schema_retrieval_tool

            # 🔥 修复：传递 connection_config 以便工具能正确初始化
            retrieval_tool = create_schema_retrieval_tool(
                self.container,
                connection_config=connection_config
            )

            result = await retrieval_tool.run(
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
    
    def _extract_columns_from_sql(self, sql: str) -> List[Dict[str, Any]]:
        """从 SQL 中提取列信息"""
        columns_info = []
        
        # 提取 SELECT 子句中的列
        select_columns = self._extract_select_columns(sql)
        columns_info.extend(select_columns)
        
        # 提取 WHERE 子句中的列
        where_columns = self._extract_where_columns(sql)
        columns_info.extend(where_columns)
        
        # 提取 GROUP BY 子句中的列
        group_by_columns = self._extract_group_by_columns(sql)
        columns_info.extend(group_by_columns)
        
        # 提取 ORDER BY 子句中的列
        order_by_columns = self._extract_order_by_columns(sql)
        columns_info.extend(order_by_columns)
        
        # 提取 HAVING 子句中的列
        having_columns = self._extract_having_columns(sql)
        columns_info.extend(having_columns)
        
        # 去重
        unique_columns = {}
        for col_info in columns_info:
            key = f"{col_info['table_name']}.{col_info['column_name']}"
            if key not in unique_columns:
                unique_columns[key] = col_info
        
        return list(unique_columns.values())
    
    def _extract_select_columns(self, sql: str) -> List[Dict[str, Any]]:
        """提取 SELECT 子句中的列"""
        columns = []
        
        # 匹配 SELECT ... FROM 模式
        select_pattern = r'SELECT\s+(.*?)\s+FROM'
        select_match = re.search(select_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if select_match:
            select_clause = select_match.group(1)
            
            # 提取表名
            from_pattern = r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            from_match = re.search(from_pattern, sql, re.IGNORECASE)
            table_name = from_match.group(1) if from_match else ""
            
            # 解析列
            column_items = [item.strip() for item in select_clause.split(',')]
            
            for item in column_items:
                # 跳过函数调用
                if '(' in item and ')' in item:
                    continue
                
                # 处理别名
                if ' AS ' in item.upper():
                    column_name = item.split(' AS ')[0].strip()
                else:
                    column_name = item.strip()
                
                # 处理表前缀
                if '.' in column_name:
                    parts = column_name.split('.')
                    if len(parts) == 2:
                        table_name = parts[0]
                        column_name = parts[1]
                
                columns.append({
                    "column_name": column_name,
                    "table_name": table_name,
                    "context": "SELECT",
                    "alias": item.split(' AS ')[1].strip() if ' AS ' in item.upper() else None
                })
        
        return columns
    
    def _extract_where_columns(self, sql: str) -> List[Dict[str, Any]]:
        """提取 WHERE 子句中的列"""
        columns = []
        
        # 匹配 WHERE 子句
        where_pattern = r'WHERE\s+(.*?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s+HAVING|\s+LIMIT|$)'
        where_match = re.search(where_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if where_match:
            where_clause = where_match.group(1)
            
            # 提取列名
            column_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)'
            column_matches = re.findall(column_pattern, where_clause)
            
            for match in column_matches:
                if '.' in match:
                    table_name, column_name = match.split('.')
                else:
                    column_name = match
                    table_name = ""
                
                columns.append({
                    "column_name": column_name,
                    "table_name": table_name,
                    "context": "WHERE"
                })
        
        return columns
    
    def _extract_group_by_columns(self, sql: str) -> List[Dict[str, Any]]:
        """提取 GROUP BY 子句中的列"""
        columns = []
        
        # 匹配 GROUP BY 子句
        group_by_pattern = r'GROUP\s+BY\s+(.*?)(?:\s+HAVING|\s+ORDER\s+BY|\s+LIMIT|$)'
        group_by_match = re.search(group_by_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if group_by_match:
            group_by_clause = group_by_match.group(1)
            
            # 解析列
            column_items = [item.strip() for item in group_by_clause.split(',')]
            
            for item in column_items:
                if '.' in item:
                    table_name, column_name = item.split('.')
                else:
                    column_name = item
                    table_name = ""
                
                columns.append({
                    "column_name": column_name,
                    "table_name": table_name,
                    "context": "GROUP BY"
                })
        
        return columns
    
    def _extract_order_by_columns(self, sql: str) -> List[Dict[str, Any]]:
        """提取 ORDER BY 子句中的列"""
        columns = []
        
        # 匹配 ORDER BY 子句
        order_by_pattern = r'ORDER\s+BY\s+(.*?)(?:\s+LIMIT|$)'
        order_by_match = re.search(order_by_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if order_by_match:
            order_by_clause = order_by_match.group(1)
            
            # 解析列
            column_items = [item.strip() for item in order_by_clause.split(',')]
            
            for item in column_items:
                # 移除排序方向
                item = re.sub(r'\s+(ASC|DESC)$', '', item, flags=re.IGNORECASE)
                
                if '.' in item:
                    table_name, column_name = item.split('.')
                else:
                    column_name = item
                    table_name = ""
                
                columns.append({
                    "column_name": column_name,
                    "table_name": table_name,
                    "context": "ORDER BY"
                })
        
        return columns
    
    def _extract_having_columns(self, sql: str) -> List[Dict[str, Any]]:
        """提取 HAVING 子句中的列"""
        columns = []
        
        # 匹配 HAVING 子句
        having_pattern = r'HAVING\s+(.*?)(?:\s+ORDER\s+BY|\s+LIMIT|$)'
        having_match = re.search(having_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if having_match:
            having_clause = having_match.group(1)
            
            # 提取列名
            column_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)'
            column_matches = re.findall(column_pattern, having_clause)
            
            for match in column_matches:
                if '.' in match:
                    table_name, column_name = match.split('.')
                else:
                    column_name = match
                    table_name = ""
                
                columns.append({
                    "column_name": column_name,
                    "table_name": table_name,
                    "context": "HAVING"
                })
        
        return columns
    
    async def _check_columns(
        self,
        columns_info: List[Dict[str, Any]],
        schema_info: Dict[str, Any],
        check_types: List[str],
        strict_mode: bool
    ) -> ColumnCheckReport:
        """检查列"""
        issues = []
        
        # 获取 Schema 中的列信息
        schema_columns = schema_info.get("columns", [])
        schema_tables = schema_info.get("tables", [])
        
        for col_info in columns_info:
            column_name = col_info["column_name"]
            table_name = col_info["table_name"]
            context = col_info.get("context", "")
            
            # 执行各种检查
            if "existence" in check_types:
                existence_issues = self._check_column_existence(
                    column_name, table_name, schema_columns, context
                )
                issues.extend(existence_issues)
            
            if "type_compatibility" in check_types:
                type_issues = self._check_type_compatibility(
                    column_name, table_name, schema_columns, context
                )
                issues.extend(type_issues)
            
            if "nullability" in check_types:
                nullability_issues = self._check_nullability(
                    column_name, table_name, schema_columns, context
                )
                issues.extend(nullability_issues)
            
            if "constraint" in check_types:
                constraint_issues = self._check_constraints(
                    column_name, table_name, schema_info, context
                )
                issues.extend(constraint_issues)
            
            if "index" in check_types:
                index_issues = self._check_indexes(
                    column_name, table_name, schema_info, context
                )
                issues.extend(index_issues)
        
        # 分类问题
        passed_columns = len(columns_info) - len(issues)
        warning_columns = len([issue for issue in issues if issue.result == CheckResult.WARNING])
        error_columns = len([issue for issue in issues if issue.result == CheckResult.ERROR])
        
        # 提取建议
        suggestions = [issue.suggestion for issue in issues if issue.suggestion]
        
        return ColumnCheckReport(
            total_columns=len(columns_info),
            checked_columns=len(columns_info),
            passed_columns=passed_columns,
            warning_columns=warning_columns,
            error_columns=error_columns,
            issues=issues,
            suggestions=suggestions
        )
    
    def _check_column_existence(
        self,
        column_name: str,
        table_name: str,
        schema_columns: List[Dict[str, Any]],
        context: str
    ) -> List[ColumnCheckIssue]:
        """检查列是否存在"""
        issues = []
        
        # 查找列
        column_info = None
        for col in schema_columns:
            if col.get("name", "").lower() == column_name.lower():
                if not table_name or col.get("table_name", "").lower() == table_name.lower():
                    column_info = col
                    break
        
        if not column_info:
            issues.append(ColumnCheckIssue(
                column_name=column_name,
                table_name=table_name,
                check_type=ColumnCheckType.EXISTENCE,
                result=CheckResult.ERROR,
                message=f"列 '{column_name}' 不存在",
                suggestion=f"请检查列名是否正确，或确认表 '{table_name}' 中是否有此列"
            ))
        
        return issues
    
    def _check_type_compatibility(
        self,
        column_name: str,
        table_name: str,
        schema_columns: List[Dict[str, Any]],
        context: str
    ) -> List[ColumnCheckIssue]:
        """检查类型兼容性"""
        issues = []
        
        # 查找列信息
        column_info = None
        for col in schema_columns:
            if col.get("name", "").lower() == column_name.lower():
                if not table_name or col.get("table_name", "").lower() == table_name.lower():
                    column_info = col
                    break
        
        if not column_info:
            return issues
        
        data_type = column_info.get("data_type", "").upper()
        
        # 检查类型兼容性
        if context == "WHERE" and data_type in ["TEXT", "LONGTEXT"]:
            issues.append(ColumnCheckIssue(
                column_name=column_name,
                table_name=table_name,
                check_type=ColumnCheckType.TYPE_COMPATIBILITY,
                result=CheckResult.WARNING,
                message=f"在 WHERE 子句中使用 TEXT 类型列 '{column_name}' 可能影响性能",
                suggestion="考虑为 TEXT 列添加索引或使用全文搜索"
            ))
        
        if context == "ORDER BY" and data_type in ["TEXT", "LONGTEXT"]:
            issues.append(ColumnCheckIssue(
                column_name=column_name,
                table_name=table_name,
                check_type=ColumnCheckType.TYPE_COMPATIBILITY,
                result=CheckResult.WARNING,
                message=f"对 TEXT 类型列 '{column_name}' 排序可能影响性能",
                suggestion="考虑使用数值或日期列进行排序"
            ))
        
        return issues
    
    def _check_nullability(
        self,
        column_name: str,
        table_name: str,
        schema_columns: List[Dict[str, Any]],
        context: str
    ) -> List[ColumnCheckIssue]:
        """检查可空性"""
        issues = []
        
        # 查找列信息
        column_info = None
        for col in schema_columns:
            if col.get("name", "").lower() == column_name.lower():
                if not table_name or col.get("table_name", "").lower() == table_name.lower():
                    column_info = col
                    break
        
        if not column_info:
            return issues
        
        nullable = column_info.get("nullable", True)
        
        # 检查 NULL 值处理
        if not nullable and context == "WHERE":
            issues.append(ColumnCheckIssue(
                column_name=column_name,
                table_name=table_name,
                check_type=ColumnCheckType.NULLABILITY,
                result=CheckResult.WARNING,
                message=f"列 '{column_name}' 不允许 NULL 值",
                suggestion="确保 WHERE 条件不会产生 NULL 值"
            ))
        
        return issues
    
    def _check_constraints(
        self,
        column_name: str,
        table_name: str,
        schema_info: Dict[str, Any],
        context: str
    ) -> List[ColumnCheckIssue]:
        """检查约束"""
        issues = []
        
        # 获取约束信息
        constraints = schema_info.get("constraints", [])
        
        for constraint in constraints:
            if constraint.get("table_name", "").lower() == table_name.lower() and \
               constraint.get("column_name", "").lower() == column_name.lower():
                
                constraint_type = constraint.get("constraint_type", "")
                
                if constraint_type == "PRIMARY KEY":
                    issues.append(ColumnCheckIssue(
                        column_name=column_name,
                        table_name=table_name,
                        check_type=ColumnCheckType.CONSTRAINT,
                        result=CheckResult.WARNING,
                        message=f"列 '{column_name}' 是主键",
                        suggestion="主键列通常不需要在 WHERE 子句中检查 NULL 值"
                    ))
                
                elif constraint_type == "FOREIGN KEY":
                    issues.append(ColumnCheckIssue(
                        column_name=column_name,
                        table_name=table_name,
                        check_type=ColumnCheckType.CONSTRAINT,
                        result=CheckResult.WARNING,
                        message=f"列 '{column_name}' 是外键",
                        suggestion="外键列应该引用有效的主键值"
                    ))
        
        return issues
    
    def _check_indexes(
        self,
        column_name: str,
        table_name: str,
        schema_info: Dict[str, Any],
        context: str
    ) -> List[ColumnCheckIssue]:
        """检查索引"""
        issues = []
        
        # 获取索引信息
        indexes = schema_info.get("indexes", [])
        
        # 检查是否有索引
        has_index = False
        for index in indexes:
            if index.get("table_name", "").lower() == table_name.lower() and \
               index.get("column_name", "").lower() == column_name.lower():
                has_index = True
                break
        
        if not has_index and context == "WHERE":
            issues.append(ColumnCheckIssue(
                column_name=column_name,
                table_name=table_name,
                check_type=ColumnCheckType.INDEX,
                result=CheckResult.WARNING,
                message=f"列 '{column_name}' 没有索引",
                suggestion=f"考虑为列 '{column_name}' 添加索引以提高查询性能"
            ))
        
        return issues


def create_sql_column_checker_tool(container: Any) -> SQLColumnCheckerTool:
    """
    创建 SQL 列检查工具
    
    Args:
        container: 服务容器
        
    Returns:
        SQLColumnCheckerTool 实例
    """
    return SQLColumnCheckerTool(container)


# 导出
__all__ = [
    "SQLColumnCheckerTool",
    "ColumnCheckType",
    "CheckResult",
    "ColumnCheckIssue",
    "ColumnCheckReport",
    "create_sql_column_checker_tool",
]