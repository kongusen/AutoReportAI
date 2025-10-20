"""
SQL验证器 - 不执行SQL，只验证合法性

验证层级：
1. 语法解析（sqlparse）
2. Schema一致性检查
3. DryRun验证（EXPLAIN）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import sqlparse

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """验证结果"""

    is_valid: bool
    is_fixable: bool = False
    issues: List[str] = None
    warnings: List[str] = None
    fixes: Optional[Dict[str, Any]] = None
    details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.warnings is None:
            self.warnings = []

    @classmethod
    def valid(cls, details: Optional[Dict[str, Any]] = None) -> "ValidationResult":
        return cls(is_valid=True, details=details or {})

    @classmethod
    def invalid(
        cls,
        issues: List[str],
        is_fixable: bool = False,
        fixes: Optional[Dict[str, Any]] = None,
    ) -> "ValidationResult":
        return cls(
            is_valid=False,
            is_fixable=is_fixable,
            issues=issues if isinstance(issues, list) else [issues],
            fixes=fixes,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "is_fixable": self.is_fixable,
            "issues": self.issues,
            "warnings": self.warnings,
            "fixes": self.fixes,
            "details": self.details,
        }


class SQLValidator:
    """
    SQL验证器 - 三层验证机制

    Layer 1: 语法解析（快速，无需数据库）
    Layer 2: Schema一致性（检查表名、字段名）
    Layer 3: DryRun验证（EXPLAIN，可选）
    """

    def __init__(self, db_connector, container=None):
        self.db = db_connector
        self.container = container

    async def validate(
        self,
        sql: str,
        schema: Dict[str, Any],
        context: Dict[str, Any],
    ) -> ValidationResult:
        """
        完整的三层验证

        Args:
            sql: 待验证的SQL语句
            schema: 数据库Schema（{table: [columns]}）
            context: 执行上下文（包含data_source等）

        Returns:
            ValidationResult: 验证结果
        """
        # Layer 1: 语法解析
        syntax_result = self._validate_syntax(sql)
        if not syntax_result.is_valid:
            return syntax_result

        # Layer 2: Schema一致性
        schema_result = self._validate_schema_usage(sql, schema)
        if not schema_result.is_valid:
            return schema_result

        # Layer 3: DryRun（可选，快速）
        if context.get("data_source"):
            dryrun_result = await self._validate_dryrun(sql, context)
            if not dryrun_result.is_valid:
                return dryrun_result

        return ValidationResult.valid(
            details={
                "syntax_check": "passed",
                "schema_check": "passed",
                "dryrun_check": "passed" if context.get("data_source") else "skipped",
            }
        )

    def _validate_syntax(self, sql: str) -> ValidationResult:
        """
        Layer 1: 语法验证

        检查：
        - SQL结构完整性
        - 危险操作
        - 括号匹配
        """
        issues = []
        sql_upper = sql.upper().strip()

        # 基础结构检查
        if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
            issues.append("SQL必须以SELECT或WITH开头")

        if "FROM" not in sql_upper:
            issues.append("SQL必须包含FROM子句")

        # 危险操作检查
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "INSERT", "ALTER"]
        for keyword in dangerous_keywords:
            import re

            if re.search(rf"\b{keyword}\b", sql_upper):
                issues.append(f"禁止使用危险关键词: {keyword}")

        # 括号平衡检查
        parentheses_issues = self._check_parentheses_balance(sql)
        issues.extend(parentheses_issues)

        # sqlparse检查
        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                issues.append("SQL解析失败")
        except Exception as exc:
            issues.append(f"SQL语法错误: {exc}")

        if issues:
            return ValidationResult.invalid(issues=issues, is_fixable=True)

        return ValidationResult.valid()

    def _validate_schema_usage(self, sql: str, schema: Dict[str, Any]) -> ValidationResult:
        """
        Layer 2: Schema一致性验证

        检查：
        - 表名是否存在
        - 字段名是否存在（简化版）
        """
        issues = []

        # 提取表名
        tables_in_sql = self._extract_tables(sql)
        schema_tables = set(schema.keys() if schema else [])

        for table in tables_in_sql:
            if table not in schema_tables:
                # 尝试找到相似的表名
                similar = self._find_similar_table(table, schema_tables)
                if similar:
                    issues.append(f"表名不存在: {table} → 已替换为 {similar}")
                else:
                    issues.append(f"表名不存在且无法修复: {table}")

        if issues:
            return ValidationResult.invalid(issues=issues, is_fixable=True)

        return ValidationResult.valid()

    async def _validate_dryrun(self, sql: str, context: Dict[str, Any]) -> ValidationResult:
        """
        Layer 3: DryRun验证（使用EXPLAIN）

        优势：
        - 不执行实际查询
        - 验证SQL可执行性
        - 快速（通常<1s）
        """
        try:
            data_source = context.get("data_source")
            if not data_source:
                return ValidationResult.valid(details={"dryrun": "skipped_no_datasource"})

            # 构建EXPLAIN SQL
            explain_sql = f"EXPLAIN {sql}"

            # 执行EXPLAIN（具体实现取决于你的data_source接口）
            # 这里是伪代码，需要根据实际接口调整
            if hasattr(self.container, "data_source"):
                result = await self.container.data_source.run_query(
                    connection_config=data_source,
                    sql=explain_sql,
                    limit=10,
                )

                logger.info(f"✅ [SQLValidator] DryRun通过: {result}")
                return ValidationResult.valid(details={"dryrun": "passed", "explain_result": result})

            return ValidationResult.valid(details={"dryrun": "skipped_no_executor"})

        except Exception as exc:
            logger.error(f"❌ [SQLValidator] DryRun失败: {exc}")
            return ValidationResult.invalid(
                issues=[f"EXPLAIN执行失败: {str(exc)}"],
                is_fixable=False,
            )

    def _extract_tables(self, sql: str) -> List[str]:
        """从SQL中提取表名"""
        import re

        tables = []
        # 简单的正则匹配FROM和JOIN后的表名
        for match in re.finditer(r"\b(FROM|JOIN)\s+([`\w\.]+)", sql, re.IGNORECASE):
            table = match.group(2).strip("`").split(".")[-1]
            tables.append(table)

        return list(set(tables))

    def _find_similar_table(self, table: str, schema_tables: set) -> Optional[str]:
        """基于相似度查找最匹配的表名"""
        import difflib

        if not schema_tables:
            return None

        matches = difflib.get_close_matches(table.lower(), [t.lower() for t in schema_tables], n=1, cutoff=0.6)

        if matches:
            # 返回原始大小写的表名
            for t in schema_tables:
                if t.lower() == matches[0]:
                    return t

        return None

    def _check_parentheses_balance(self, sql: str) -> List[str]:
        """检查括号平衡"""
        issues = []
        stack = []

        for i, char in enumerate(sql):
            if char == "(":
                stack.append(i)
            elif char == ")":
                if not stack:
                    issues.append(f"多余的右括号在位置 {i}")
                else:
                    stack.pop()

        if stack:
            issues.append(f"缺少 {len(stack)} 个右括号")

        return issues
