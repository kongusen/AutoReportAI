"""
工具结果格式化器

负责将各类工具执行结果整理成便于 LLM 理解的摘要文本，以及结构化的元数据
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from loom.core.types import ToolResult


@dataclass
class FormattedToolResult:
    """格式化后的工具结果"""

    tool_name: str
    message: str
    structured_summary: Dict[str, Any] = field(default_factory=dict)
    next_actions: List[str] = field(default_factory=list)
    raw_payload: Any = None
    duplicate_call: bool = False


def _safe_parse_content(content: Any) -> Tuple[Optional[Dict[str, Any]], Any]:
    """尝试将工具原始 content 解析为字典"""
    if isinstance(content, dict):
        return content, content

    if isinstance(content, str):
        text = content.strip()
        if not text:
            return None, content
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed, parsed
        except json.JSONDecodeError:
            pass
    return None, content


def _format_schema_discovery(payload: Dict[str, Any]) -> FormattedToolResult:
    summary = payload.get("llm_summary")
    structured = payload.get("structured_summary") or {}
    next_actions = payload.get("next_actions") or []
    duplicate_call = bool(payload.get("cached"))

    if not summary:
        tables = structured.get("tables_preview") or payload.get("tables") or []
        tables_preview = tables[:5] if isinstance(tables, list) else []
        tables_count = structured.get("tables_count") or len(tables_preview)
        preview = ", ".join(tables_preview) if tables_preview else "未提供表名"
        summary = f"Schema discovery 完成，发现 {tables_count} 张表：{preview}"

    # 补充下一步提示
    if next_actions:
        summary += f"。建议下一步：{'；'.join(next_actions)}"

    return FormattedToolResult(
        tool_name="schema_discovery",
        message=summary,
        structured_summary=structured,
        next_actions=next_actions,
        raw_payload=payload,
        duplicate_call=duplicate_call,
    )


def _format_generic(tool_name: str, payload: Optional[Dict[str, Any]], fallback: Any) -> FormattedToolResult:
    if payload:
        preview_source = payload.get("llm_summary") or payload
        summary = json.dumps(preview_source, ensure_ascii=False) if isinstance(preview_source, (dict, list)) else str(preview_source)
    else:
        summary = str(fallback)
    return FormattedToolResult(
        tool_name=tool_name,
        message=f"工具 {tool_name} 返回：{summary}",
        structured_summary=payload or {},
        raw_payload=payload or fallback,
    )


def format_tool_result(tool_result: ToolResult) -> FormattedToolResult:
    """将 Loom 的 ToolResult 转换为统一格式"""
    payload, raw = _safe_parse_content(tool_result.content)

    if tool_result.tool_name == "schema_discovery" and payload:
        return _format_schema_discovery(payload)

    return _format_generic(tool_result.tool_name, payload, raw)


def render_tool_message(tool_result: ToolResult) -> str:
    """直接返回便于 LLM 理解的字符串"""
    formatted = format_tool_result(tool_result)
    return formatted.message
