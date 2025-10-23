"""
Compatibility helpers bridging the legacy agent dataclasses to the new
Loom-based runtime.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List

from .types import AgentInput, AgentOutput, AgentRequest, AgentResponse
from .auth_context import auth_manager
from .config_context import config_manager


def agent_input_to_request(agent_input: AgentInput) -> AgentRequest:
    """
    Convert a legacy `AgentInput` instance into the simplified `AgentRequest`
    used by the Loom runtime.
    """

    resolved_user_id = agent_input.user_id or auth_manager.get_current_user_id()

    stage = _infer_stage(agent_input)
    mode = _infer_mode(agent_input, stage)
    available_tools = _build_available_tools(stage)

    context = _build_context_block(agent_input)
    if available_tools:
        context["available_tools"] = available_tools

    config = config_manager.get_config(resolved_user_id)
    if config:
        context["system_config"] = _serialize(config)

    metadata = _build_metadata_block(agent_input)
    metadata.setdefault("stage", stage)
    metadata.setdefault("mode", mode)
    if agent_input.constraints and getattr(agent_input.constraints, "output_kind", None):
        metadata.setdefault("output_kind", agent_input.constraints.output_kind)

    return AgentRequest(
        prompt=agent_input.user_prompt,
        context=context,
        metadata=metadata,
        user_id=resolved_user_id,
        mode=mode,
        stage=stage,
    )


def agent_response_to_output(response: AgentResponse) -> AgentOutput:
    """Convert a Loom response back into the legacy `AgentOutput` structure."""

    return AgentOutput(
        success=response.success,
        result=response.output,
        metadata=response.metadata,
    )


def _build_context_block(agent_input: AgentInput) -> Dict[str, Any]:
    context: Dict[str, Any] = {}

    context["placeholder"] = _serialize(agent_input.placeholder)
    context["schema"] = {
        "tables": list(agent_input.schema.tables),
        "columns": _serialize(agent_input.schema.columns),
    }
    context["task_context"] = _serialize(agent_input.context)
    context["constraints"] = _serialize(agent_input.constraints)
    if agent_input.data_source:
        context["data_source"] = agent_input.data_source
    if agent_input.task_driven_context:
        context["task_driven_context"] = agent_input.task_driven_context

    return _prune_empty(context)


def _build_metadata_block(agent_input: AgentInput) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}
    if agent_input.template_id:
        metadata["template_id"] = agent_input.template_id
    if agent_input.placeholder and getattr(agent_input.placeholder, "id", None):
        metadata["placeholder_id"] = agent_input.placeholder.id
    if agent_input.placeholder and getattr(agent_input.placeholder, "type", None):
        metadata["placeholder_type"] = agent_input.placeholder.type
    return metadata


def _infer_stage(agent_input: AgentInput) -> str:
    constraints = agent_input.constraints
    placeholder_type = getattr(agent_input.placeholder, "type", "") or ""

    if constraints and constraints.output_kind == "chart":
        return "chart_generation"
    if "图表" in (agent_input.placeholder.description or ""):
        return "chart_generation"
    if placeholder_type in {"chart", "图表类"}:
        return "chart_generation"
    if agent_input.task_driven_context:
        return "task_execution"
    return "template"


def _infer_mode(agent_input: AgentInput, stage: str) -> str:
    # Preserve explicit hints from context if present
    task_ctx = agent_input.task_driven_context or {}
    if isinstance(task_ctx, dict) and task_ctx.get("mode"):
        return str(task_ctx["mode"])
    return stage


def _build_available_tools(stage: str) -> List[Dict[str, str]]:
    base_schema_tools = [
        {"name": "schema.list_tables", "desc": "列出数据库所有表名"},
        {"name": "schema.get_columns", "desc": "获取指定表的列信息"},
    ]

    sql_tools = [
        {"name": "sql.validate", "desc": "验证SQL语法与潜在错误"},
        {"name": "sql.policy", "desc": "执行SQL策略检查并自动补充LIMIT"},
        {"name": "sql.refine", "desc": "根据反馈修正SQL"},
        {"name": "sql.execute", "desc": "执行SQL并返回数据"},
    ]

    workflow_tools = [
        {"name": "workflow.stat_basic", "desc": "基础指标统计工作流"},
        {"name": "workflow.stat_ratio", "desc": "同比/环比等比例工作流"},
        {"name": "workflow.stat_category_mix", "desc": "分类构成分析工作流"},
    ]

    chart_tools = [
        {"name": "chart.spec", "desc": "根据数据生成标准图表配置"},
        {"name": "word_chart_generator", "desc": "生成可插入文档的图表图片"},
    ]

    extras = []
    if stage == "task_execution":
        extras.append({"name": "time.window", "desc": "推导任务执行时间窗口"})
        extras.append({"name": "data.quality", "desc": "检查结果数据质量"})
    if stage == "chart_generation":
        extras.extend(chart_tools)

    # Keep order intuitive: schema -> workflow -> sql -> extras
    tool_list = base_schema_tools + workflow_tools + sql_tools + extras
    return tool_list


def _serialize(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    return value


def _prune_empty(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in data.items() if v not in (None, {}, [], "")}


__all__ = [
    "agent_input_to_request",
    "agent_response_to_output",
]
