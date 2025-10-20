"""
SQL generation primitives.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import sqlparse

logger = logging.getLogger(__name__)


@dataclass
class SQLResult:
    success: bool
    sql: str = ""
    explanation: str = ""
    confidence: float = 0.0
    error: Optional[str] = None
    raw_output: Optional[str] = None

    @classmethod
    def success_result(cls, sql: str, explanation: str, confidence: float, raw_output: Optional[str] = None) -> "SQLResult":
        return cls(success=True, sql=sql, explanation=explanation, confidence=confidence, raw_output=raw_output)

    @classmethod
    def failed_result(cls, error: str, raw_output: Optional[str] = None) -> "SQLResult":
        return cls(success=False, error=error, raw_output=raw_output)


class StructuredSQLGenerator:
    """
    Generates SQL using structured outputs from the LLM.
    """

    SQL_SCHEMA = {
        "type": "object",
        "properties": {
            "sql": {"type": "string"},
            "explanation": {"type": "string"},
            "tables_used": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"},
        },
        "required": ["sql", "explanation", "tables_used"],
    }

    def __init__(self, llm_client):
        self.llm = llm_client

    async def generate(self, prompt: str, attempt: int = 0) -> SQLResult:
        try:
            temperature = 0.05 if attempt == 0 else 0.2
            llm_response = await self.llm.ask(
                prompt=prompt,
                user_id="system",
                response_format={"type": "json_object"},
                llm_policy={
                    "stage": "tool",
                    "tool_name": "sql_generation",
                    "complexity": "high",
                    "temperature": temperature,
                },
            )

            raw = llm_response.get("response") if isinstance(llm_response, dict) else str(llm_response)
            parsed = self._parse_json(raw)
            if not parsed:
                return SQLResult.failed_result("JSON解析失败", raw_output=raw)

            sql = parsed.get("sql", "").strip()
            if not sql or not sql.lower().startswith(("select", "with")):
                return SQLResult.failed_result("结构化响应缺少有效SQL", raw_output=raw)

            if not self._basic_syntax_check(sql):
                return SQLResult.failed_result("SQL通过基础语法检查失败", raw_output=raw)

            explanation = parsed.get("explanation", "")
            confidence = float(parsed.get("confidence", 0.5))
            return SQLResult.success_result(sql, explanation, confidence, raw_output=raw)

        except Exception as exc:
            logger.error("StructuredSQLGenerator: 调用LLM失败: %s", exc, exc_info=True)
            return SQLResult.failed_result(f"llm_error: {exc}")

    def _parse_json(self, payload: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(payload)
        except Exception:
            if "{" in payload and "}" in payload:
                snippet = payload[payload.find("{") : payload.rfind("}") + 1]
                try:
                    return json.loads(snippet)
                except Exception:
                    return None
            return None

    def _basic_syntax_check(self, sql: str) -> bool:
        sql_lower = sql.lower()
        if "drop " in sql_lower or "truncate " in sql_lower or "delete " in sql_lower:
            return False
        try:
            parsed = sqlparse.parse(sql)
        except Exception:
            return False
        return bool(parsed)


class TemplateSQLGenerator:
    """
    Fallback SQL generator for scenarios where the LLM cannot produce valid SQL.
    """

    DEFAULT_LIMIT = 1000

    def generate(self, schema: Dict[str, Any], time_window: Dict[str, Any]) -> str:
        table = self._pick_table(schema)
        time_column = self._pick_time_column(schema.get(table, {}))

        start = time_window.get("start") or time_window.get("start_date") or "{{start_date}}"
        end = time_window.get("end") or time_window.get("end_date") or "{{end_date}}"

        return (
            f"SELECT *\n"
            f"FROM {table}\n"
            f"WHERE {time_column} BETWEEN '{start}' AND '{end}'\n"
            f"LIMIT {self.DEFAULT_LIMIT};"
        )

    def _pick_table(self, schema: Dict[str, Any]) -> str:
        if not schema:
            return "sales"
        return list(schema.keys())[0]

    def _pick_time_column(self, columns_map: Any) -> str:
        if isinstance(columns_map, dict):
            candidates = {key.lower(): key for key in columns_map.keys()}
        elif isinstance(columns_map, list):
            candidates = {str(col).lower(): str(col) for col in columns_map}
        else:
            candidates = {}

        for candidate in ["sale_date", "date", "dt", "created_at", "timestamp", "time"]:
            if candidate in candidates:
                return candidates[candidate]

        if candidates:
            return list(candidates.values())[0]
        return "date"
