"""
Schema 工具集合（Loom 版）

提供：
    - 列出数据源中的表
    - 获取指定表的列信息
    - 按表名批量提取列，并生成便于 LLM 消化的结构化描述
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

from .base import Tool

logger = logging.getLogger(__name__)


def _get_data_source_adapter(container: Any):
    """统一访问容器中的数据源适配器。"""
    for attr in ("data_source", "data_source_service"):
        if hasattr(container, attr):
            return getattr(container, attr)
    return None


class SchemaListTablesTool(Tool):
    """列出数据源中的表名。"""

    def __init__(self, container: Any = None) -> None:
        super().__init__()
        self.name = "schema.list_tables"
        self.description = "列出数据源中的所有表名（不包含列信息）"
        self._container = container
        self._ds = _get_data_source_adapter(container) if container else None
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self._ds or not hasattr(self._ds, "run_query"):
            return {"success": False, "error": "data_source_adapter_unavailable"}

        cfg = input_data.get("data_source", {}) or {}
        sql = input_data.get("sql") or "SHOW TABLES"

        try:
            result = await self._ds.run_query(cfg, sql, limit=1000)
        except Exception as exc:  # pragma: no cover - 记录错误
            self._logger.error("列出表失败: %s", exc)
            return {"success": False, "error": str(exc)}

        if isinstance(result, dict) and result.get("success") is False:
            error_message = result.get("error") or result.get("message") or "schema_list_tables_failed"
            return {"success": False, "error": error_message}

        tables: List[str] = []
        for row in result.get("rows") or result.get("data") or []:
            if isinstance(row, dict):
                tables.extend(str(v) for v in row.values())
            elif isinstance(row, (list, tuple)) and row:
                tables.append(str(row[0]))
            elif isinstance(row, str):
                tables.append(row)

        tables = [t for t in tables if t]
        self._logger.info("SchemaListTablesTool -> %d tables", len(tables))
        return {
            "success": True,
            "tables": tables,
            "message": f"发现 {len(tables)} 个表",
        }


class SchemaListColumnsTool(Tool):
    """批量获取表的列信息，并生成简要描述。"""

    def __init__(self, container: Any = None) -> None:
        super().__init__()
        self.name = "schema.list_columns"
        self.description = "列出指定表的列信息（名称、类型、备注）"
        self._container = container
        self._ds = _get_data_source_adapter(container) if container else None
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        tables: Iterable[str] = input_data.get("tables") or []
        if isinstance(tables, str):
            tables = [tables]
        tables = [t for t in tables if t]

        if not tables:
            return {
                "success": False,
                "error": "tables_required",
                "message": "调用前需在 payload.tables 指定表名",
            }

        if not self._ds:
            existing = input_data.get("columns") or {}
            return {
                "success": True,
                "tables": list(tables),
                "columns": existing,
                "message": "容器缺少数据源服务，返回已有列信息",
            }

        cfg = input_data.get("data_source") or {}
        all_columns: Dict[str, List[Dict[str, Any]]] = {}
        basic_map: Dict[str, List[str]] = {}

        for table in tables:
            info = await self._fetch_columns_for_table(table, cfg)
            all_columns[table] = info
            basic_map[table] = [col.get("name") for col in info if col.get("name")]

        schema_descriptions = []
        column_total = 0
        for table, cols in all_columns.items():
            column_total += len(cols)
            formatted = ", ".join(
                f"{col['name']}({col.get('type','')})"
                + ("[PK]" if col.get("key") == "PRI" else "")
                for col in cols
            ) or "无列信息"
            schema_descriptions.append(f"**{table}**: {formatted}")

        summary = (
            f"共查询 {len(tables)} 个表，合计 {column_total} 列。\n"
            + "\n".join(schema_descriptions)
        )

        return {
            "success": True,
            "tables": list(tables),
            "columns": basic_map,
            "column_details": all_columns,
            "schema_summary": summary,
            "message": f"已获取 {len(tables)} 个表的列信息",
        }

    async def _fetch_columns_for_table(
        self, table: str, cfg: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        通过 `SHOW FULL COLUMNS` 获取列信息；若失败则回退到 `SELECT * LIMIT 0`。
        """
        candidates = [
            f"SHOW FULL COLUMNS FROM {table}",
            f"DESC {table}",
        ]

        for sql in candidates:
            try:
                result = await self._ds.run_query(cfg, sql, limit=1000)
            except Exception as exc:
                self._logger.warning("查询 %s 列信息失败 (%s): %s", table, sql, exc)
                continue
            if isinstance(result, dict) and result.get("success") is False:
                error_message = result.get("error") or result.get("message") or "schema_list_columns_failed"
                raise RuntimeError(error_message)
            rows = result.get("rows") or result.get("data") or []
            columns = self._parse_column_rows(rows)
            if columns:
                return columns

        # 回退：执行空查询只为拿列名
        try:
            result = await self._ds.run_query(cfg, f"SELECT * FROM {table} LIMIT 0", limit=1)
            if isinstance(result, dict) and result.get("success") is False:
                error_message = result.get("error") or result.get("message") or "schema_select_zero_failed"
                raise RuntimeError(error_message)
            names = result.get("columns") or result.get("column_names") or []
            return [{"name": name, "type": "", "key": "", "comment": ""} for name in names]
        except Exception as exc:  # pragma: no cover - 调试记录
            logger.warning("获取表 %s 列信息失败: %s", table, exc)
            raise

    @staticmethod
    def _parse_column_rows(rows: Iterable[Any]) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        for row in rows:
            if isinstance(row, dict):
                parsed.append(
                    {
                        "name": row.get("Field") or row.get("column_name") or row.get("COLUMN_NAME"),
                        "type": row.get("Type") or row.get("column_type") or row.get("DATA_TYPE"),
                        "nullable": row.get("Null") or row.get("IS_NULLABLE"),
                        "key": row.get("Key") or row.get("COLUMN_KEY"),
                        "default": row.get("Default"),
                        "comment": row.get("Comment") or row.get("COLUMN_COMMENT"),
                    }
                )
            elif isinstance(row, (list, tuple)) and row:
                name = str(row[0])
                col_type = str(row[1]) if len(row) > 1 else ""
                parsed.append(
                    {
                        "name": name,
                        "type": col_type,
                        "nullable": "",
                        "key": "",
                        "default": "",
                        "comment": "",
                    }
                )
        return [col for col in parsed if col.get("name")]


class SchemaGetColumnsTool(SchemaListColumnsTool):
    """
    与 `schema.list_columns` 相同，但专注于单表场景，保持旧接口兼容。
    """

    def __init__(self, container: Any = None) -> None:
        super().__init__(container)
        self.name = "schema.get_columns"
        self.description = "获取单个表的列信息"

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        table = input_data.get("table")
        if table:
            input_data = dict(input_data)
            input_data["tables"] = [table]
        return await super().execute(input_data)


__all__ = [
    "SchemaListTablesTool",
    "SchemaListColumnsTool",
    "SchemaGetColumnsTool",
]
