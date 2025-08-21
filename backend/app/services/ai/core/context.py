from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class PromptContext:
    user_id: Optional[str] = None
    data_source_summary: Optional[str] = None
    schema_highlights: List[str] = field(default_factory=list)
    task_hint: Optional[str] = None
    placeholders_preview: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


class PromptContextBuilder:
    """构建上下文工程的提示词上下文"""

    def __init__(self):
        self._ctx = PromptContext()

    def with_user(self, user_id: str) -> "PromptContextBuilder":
        self._ctx.user_id = user_id
        return self

    def with_data_source_summary(self, summary: str) -> "PromptContextBuilder":
        self._ctx.data_source_summary = summary
        return self

    def add_schema_highlight(self, text: str) -> "PromptContextBuilder":
        self._ctx.schema_highlights.append(text)
        return self

    def with_task_hint(self, hint: str) -> "PromptContextBuilder":
        self._ctx.task_hint = hint
        return self

    def add_placeholder_preview(self, text: str) -> "PromptContextBuilder":
        self._ctx.placeholders_preview.append(text)
        return self

    def add_constraint(self, constraint: str) -> "PromptContextBuilder":
        self._ctx.constraints.append(constraint)
        return self

    def build_prompt(self, user_prompt: str) -> str:
        parts: List[str] = []
        if self._ctx.task_hint:
            parts.append(f"任务: {self._ctx.task_hint}")
        if self._ctx.data_source_summary:
            parts.append(f"数据源概要: {self._ctx.data_source_summary}")
        if self._ctx.schema_highlights:
            highlights = "\n- ".join(self._ctx.schema_highlights[:10])
            parts.append(f"关键表/字段: \n- {highlights}")
        if self._ctx.placeholders_preview:
            previews = "\n- ".join(self._ctx.placeholders_preview[:10])
            parts.append(f"占位符预览: \n- {previews}")
        if self._ctx.constraints:
            constr = "\n- ".join(self._ctx.constraints[:10])
            parts.append(f"约束: \n- {constr}")
        parts.append(f"用户问题: {user_prompt}")
        return "\n\n".join(parts)


