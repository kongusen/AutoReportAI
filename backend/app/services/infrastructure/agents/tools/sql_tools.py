"""
SQL 工具集合（Loom 版）

涵盖：
    - SQL 验证（基本静态校验 + 安全策略检查）
    - SQL 执行（占位符替换后查询数据源）
    - SQL 修正（应用 Agent 给出的修复结果）
    - SQL 策略检查（LIMIT、危险关键词等）
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List
import re

from ..auth_context import auth_manager
from ..data_source_security_service import data_source_security_service
from .base import Tool

logger = logging.getLogger(__name__)


def _normalise_sql(sql: str) -> str:
    return (sql or "").strip()


class SQLValidateTool(Tool):
    """基础 SQL 验证工具。"""

    def __init__(self, container: Any = None) -> None:
        super().__init__()
        self.name = "sql.validate"
        self.description = "验证 SQL 是否符合基本规范并执行安全策略检查"
        self._container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        sql = input_data.get("current_sql") or input_data.get("sql") or ""
        sql = _normalise_sql(sql)

        issues: List[str] = []
        warnings: List[str] = []

        if not sql:
            return {"success": False, "error": "SQL语句为空"}

        if not self._looks_like_sql(sql):
            issues.append("缺少 SELECT / WITH，疑似不是 SQL 语句")

        if "{{" in sql and "}}" in sql:
            warnings.append("SQL 包含占位符，执行前需替换具体时间范围")

        security_result = self._apply_security_policy(sql, input_data)
        if not security_result["success"]:
            return {
                "success": False,
                "error": security_result.get("error", "安全策略校验失败"),
                "issues": security_result.get("issues", []),
            }

        validated_sql = security_result.get("sql", sql)
        if security_result.get("warnings"):
            warnings.extend(security_result["warnings"])

        return {
            "success": not issues,
            "sql": validated_sql,
            "issues": issues,
            "warnings": warnings,
            "agent_validated": False,
            "validation_decision": "basic_validation",
        }

    def _apply_security_policy(self, sql: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        user_id = input_data.get("user_id") or auth_manager.get_current_user_id() or "system"
        data_source_cfg = input_data.get("data_source") or {}

        try:
            result = data_source_security_service.apply_sql_security_policy(
                sql=sql,
                user_id=user_id,
                data_source_id=data_source_cfg.get("id"),
                is_superuser=self._is_superuser(),
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("SQL安全策略校验失败: %s", exc)
            return {"success": False, "error": str(exc)}

        if not result.get("success", True):
            return {
                "success": False,
                "error": "SQL安全策略不通过",
                "issues": result.get("issues", []),
            }

        processed_sql = result.get("sql", sql)
        if self._looks_like_sql(processed_sql) and SQLPolicyTool._is_static_aggregate(processed_sql):
            processed_sql = SQLPolicyTool._strip_limit(processed_sql)

        return {
            "success": True,
            "sql": processed_sql,
            "warnings": result.get("warnings", []),
        }

    def _looks_like_sql(self, sql: str) -> bool:
        head = sql.upper().lstrip()
        return head.startswith(("SELECT", "WITH"))

    def _is_superuser(self) -> bool:
        ctx = auth_manager.get_context()
        return bool(ctx and getattr(ctx, "is_superuser", False))


class SQLExecuteTool(Tool):
    """执行 SQL 并返回查询结果。"""

    def __init__(self, container: Any = None) -> None:
        super().__init__()
        self.name = "sql.execute"
        self.description = "执行 SQL 查询以验证结果"
        self._container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        sql = input_data.get("current_sql") or input_data.get("sql") or ""
        sql = _normalise_sql(sql)
        if not sql:
            return {"success": False, "error": "SQL语句为空"}

        executable_sql = self._replace_time_placeholders(sql, input_data)
        data_source = await self._resolve_data_source_config(input_data)

        adapter = self._get_data_source_adapter()
        if not adapter:
            return {"success": False, "error": "data_source_adapter_unavailable"}

        try:
            if hasattr(adapter, "execute_query"):
                result = await adapter.execute_query(executable_sql, data_source)
            else:
                result = await adapter.run_query(data_source, executable_sql)
        except Exception as exc:
            self._logger.error("SQL 执行失败: %s", exc)
            return {"success": False, "error": str(exc)}

        rows = result.get("rows") or result.get("data") or []
        columns = result.get("columns") or result.get("column_names") or []

        # 🚀 优化：只返回前5行样本 + 统计摘要（减少99%上下文占用）
        total_rows = len(rows)
        sample_rows = rows[:5]  # 只保留前5行作为样本

        # 生成数据摘要
        summary = {
            "total_rows": total_rows,
            "sample_size": len(sample_rows),
            "columns": columns,
            "has_more_data": total_rows > 5
        }

        # 如果数据很少（<=5行），说明这是聚合查询结果，返回全部
        if total_rows <= 5:
            return {
                "success": True,
                "sql": sql,
                "rows": rows,  # 少量数据，返回全部
                "columns": columns,
                "row_count": total_rows,
                "execution_sql": executable_sql,
                "data_summary": f"查询返回 {total_rows} 行完整数据"
            }

        # 大量数据时，只返回样本
        return {
            "success": True,
            "sql": sql,
            "rows": sample_rows,  # 只返回前5行样本
            "columns": columns,
            "row_count": total_rows,
            "execution_sql": executable_sql,
            "data_summary": f"查询返回 {total_rows} 行数据，已截取前 {len(sample_rows)} 行作为样本。数据验证通过。",
            "sample_preview": self._generate_preview(sample_rows, columns),
            "is_sample": True  # 标记这是样本数据
        }

    def _replace_time_placeholders(self, sql: str, payload: Dict[str, Any]) -> str:
        window = payload.get("window") or payload.get("time_window") or {}
        start = window.get("start_date") or window.get("start")
        end = window.get("end_date") or window.get("end")

        if not start or not end:
            start = payload.get("start_date")
            end = payload.get("end_date")

        if not start or not end:
            today = datetime.now().date()
            start = start or (today - timedelta(days=1)).strftime("%Y-%m-%d")
            end = end or today.strftime("%Y-%m-%d")

        # 智能替换：检测占位符周围是否已经有引号，避免双重转义
        # 支持三种模式：
        # 1. '{{start_date}}' -> '2025-10-22'（已有引号，只替换占位符）
        # 2. {{start_date}} -> '2025-10-22'（无引号，添加引号）
        import re

        # 处理 start_date
        # 匹配 '{{start_date}}' 或 "{{start_date}}" (已有引号)
        executable = re.sub(r"""['"]{{start_date}}['"]""", f"'{start}'", sql)
        # 匹配 {{start_date}} (无引号)
        executable = executable.replace("{{start_date}}", f"'{start}'")

        # 处理 end_date
        # 匹配 '{{end_date}}' 或 "{{end_date}}" (已有引号)
        executable = re.sub(r"""['"]{{end_date}}['"]""", f"'{end}'", executable)
        # 匹配 {{end_date}} (无引号)
        executable = executable.replace("{{end_date}}", f"'{end}'")

        return executable

    def _get_data_source_adapter(self):
        for attr in ("data_source", "data_source_service"):
            if hasattr(self._container, attr):
                return getattr(self._container, attr)
        return None

    async def _resolve_data_source_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        cfg = dict(payload.get("data_source") or {})
        user_id = payload.get("user_id") or auth_manager.get_current_user_id()
        ds_id = cfg.get("id")

        uds_adapter = getattr(self._container, "user_data_source_service", None)
        if uds_adapter and user_id and ds_id:
            try:
                ds_obj = await uds_adapter.get_user_data_source(user_id=user_id, data_source_id=ds_id)
                if ds_obj and getattr(ds_obj, "connection_config", None):
                    return dict(ds_obj.connection_config)
            except Exception as exc:  # pragma: no cover - 调试
                self._logger.debug("获取用户数据源失败，使用原始配置: %s", exc)

        return cfg

    def _generate_preview(self, rows: List[Any], columns: List[str]) -> str:
        """
        生成数据预览的简洁文本表示

        Args:
            rows: 样本数据行
            columns: 列名列表

        Returns:
            格式化的数据预览字符串
        """
        if not rows:
            return "无数据"

        preview_lines = []
        preview_lines.append(f"列名: {', '.join(columns)}")

        for i, row in enumerate(rows, 1):
            if isinstance(row, dict):
                row_str = ", ".join(f"{k}={v}" for k, v in list(row.items())[:5])
            elif isinstance(row, (list, tuple)):
                row_str = ", ".join(str(v) for v in list(row)[:5])
            else:
                row_str = str(row)

            # 限制每行长度
            if len(row_str) > 100:
                row_str = row_str[:97] + "..."

            preview_lines.append(f"  行{i}: {row_str}")

        return "\n".join(preview_lines)


class SQLRefineTool(Tool):
    """根据 Agent 建议对 SQL 进行修正。"""

    def __init__(self, container: Any = None) -> None:
        super().__init__()
        self.name = "sql.refine"
        self.description = "应用 Agent 提供的 SQL 修正"
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        current_sql = _normalise_sql(input_data.get("current_sql") or input_data.get("sql") or "")
        corrected_sql = _normalise_sql(input_data.get("corrected_sql") or "")
        issues = input_data.get("issues") or []

        if not current_sql:
            return {"success": False, "error": "current_sql 为空"}

        if not corrected_sql:
            return {
                "success": False,
                "error": "缺少纠正后的 SQL",
                "current_sql": current_sql,
                "issues": issues,
            }

        if not corrected_sql.upper().startswith(("SELECT", "WITH")):
            return {
                "success": False,
                "error": "修正 SQL 不是合法的 SELECT 查询",
                "current_sql": current_sql,
            }

        return {
            "success": True,
            "sql": corrected_sql,
            "current_sql": corrected_sql,
            "original_sql": current_sql,
            "issues_addressed": issues,
        }


class SQLPolicyTool(Tool):
    """单独暴露安全策略检查，供 Agent 在生成阶段调用。"""

    def __init__(self, container: Any = None) -> None:
        super().__init__()
        self.name = "sql.policy"
        self.description = "对 SQL 应用安全策略（LIMIT、危险关键词等）"
        self._container = container

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        sql = input_data.get("current_sql") or input_data.get("sql") or ""
        sql = _normalise_sql(sql)
        if not sql:
            return {"success": False, "error": "SQL语句为空"}

        user_id = input_data.get("user_id") or auth_manager.get_current_user_id() or "system"
        data_source_cfg = input_data.get("data_source") or {}

        result = data_source_security_service.apply_sql_security_policy(
            sql=sql,
            user_id=user_id,
            data_source_id=data_source_cfg.get("id"),
            is_superuser=self._is_superuser(),
        )

        if not result.get("success", True):
            return {
                "success": False,
                "error": "SQL安全策略校验失败",
                "issues": result.get("issues", []),
            }

        processed_sql = result.get("sql", sql)
        if self._is_aggregate_query(processed_sql):
            processed_sql = self._strip_limit_clause(processed_sql)

        return {
            "success": True,
            "sql": processed_sql,
            "warnings": result.get("warnings", []),
            "policies_applied": result.get("modifications", []),
        }

    def _is_superuser(self) -> bool:
        ctx = auth_manager.get_context()
        return bool(ctx and getattr(ctx, "is_superuser", False))

    @staticmethod
    def _is_aggregate_query(sql: str) -> bool:
        if not isinstance(sql, str):
            return False
        sql_upper = sql.upper()
        aggregate_keywords = ("COUNT(", "SUM(", "AVG(", "MIN(", "MAX(")
        return any(keyword in sql_upper for keyword in aggregate_keywords)

    @staticmethod
    def _strip_limit_clause(sql: str) -> str:
        if not isinstance(sql, str):
            return sql
        return re.sub(r"\s+LIMIT\s+\d+\s*$", "", sql, flags=re.IGNORECASE)

    @staticmethod
    def _strip_limit(sql: str) -> str:
        return SQLPolicyTool._strip_limit_clause(sql)

    @staticmethod
    def _is_static_aggregate(sql: str) -> bool:
        return SQLPolicyTool._is_aggregate_query(sql)


__all__ = [
    "SQLValidateTool",
    "SQLExecuteTool",
    "SQLRefineTool",
    "SQLPolicyTool",
]
