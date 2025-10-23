from types import SimpleNamespace

import pytest

from app.services.infrastructure.agents import (
    LoomAgentFacade,
    agent_input_to_request,
    agent_response_to_output,
)
from app.services.infrastructure.agents.types import (
    AgentConstraints,
    AgentInput,
    PlaceholderSpec,
    SchemaInfo,
    TaskContext,
)


def _build_agent_input() -> AgentInput:
    placeholder = PlaceholderSpec(
        id="ph-1",
        description="销售额占比",
        type="chart",
        granularity="monthly",
    )
    schema = SchemaInfo(
        tables=["orders", "users"],
        columns={
            "orders": ["order_id", "amount", "user_id"],
            "users": ["user_id", "region"],
        },
    )
    context = TaskContext(
        task_time=1710000000.0,
        timezone="Asia/Shanghai",
        window={
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "time_column": "order_date",
        },
    )
    constraints = AgentConstraints(
        sql_only=True,
        output_kind="chart",
        max_attempts=3,
        policy_row_limit=10000,
        quality_min_rows=100,
    )

    return AgentInput(
        user_prompt="生成同比环比分析",
        placeholder=placeholder,
        schema=schema,
        context=context,
        constraints=constraints,
        template_id="template-1",
        data_source={"name": "primary", "type": "mysql"},
        task_driven_context={"current_sql": "SELECT * FROM orders"},
        user_id="user-1",
    )


def _build_template_agent_input() -> AgentInput:
    placeholder = PlaceholderSpec(
        id="ph-2",
        description="查看每日订单量",
        type="stat",
        granularity="daily",
    )
    schema = SchemaInfo(tables=["orders"], columns={"orders": ["order_id", "order_date"]})
    context = TaskContext(task_time=None, timezone="Asia/Shanghai", window=None)
    constraints = AgentConstraints(sql_only=True, output_kind="sql", max_attempts=3)

    return AgentInput(
        user_prompt="统计每日订单数",
        placeholder=placeholder,
        schema=schema,
        context=context,
        constraints=constraints,
        template_id=None,
        data_source=None,
        task_driven_context=None,
        user_id=None,
    )


def test_agent_input_to_request_conversion():
    agent_input = _build_agent_input()
    request = agent_input_to_request(agent_input)

    assert request.prompt == agent_input.user_prompt
    assert request.user_id == "user-1"
    assert request.metadata["template_id"] == "template-1"
    assert request.metadata["placeholder_type"] == "chart"
    assert request.stage == "chart_generation"
    assert request.mode == "chart_generation"

    schema_context = request.context["schema"]
    assert schema_context["tables"] == ["orders", "users"]
    assert "current_sql" in request.context["task_driven_context"]

    tools = request.context.get("available_tools", [])
    tool_names = {tool["name"] for tool in tools}
    assert "chart.spec" in tool_names
    assert "word_chart_generator" in tool_names

    assert "system_config" in request.context


@pytest.mark.asyncio
async def test_facade_execute_accepts_legacy_input():
    container = SimpleNamespace()
    facade = LoomAgentFacade(
        container=container,
        config_overrides={"llm": {"mock_responses": ["legacy 输出", "legacy 输出"]}},
        include_legacy_tools=False,
    )

    agent_input = _build_agent_input()
    response = await facade.execute(agent_input)

    assert response.success is True
    assert response.output == "legacy 输出"

    agent_output = await facade.execute_legacy(agent_input)
    converted = agent_response_to_output(response)

    assert agent_output.success is True
    assert agent_output.result == "legacy 输出"
    assert agent_output.metadata == converted.metadata


def test_agent_input_stage_defaults_to_template():
    request = agent_input_to_request(_build_template_agent_input())
    assert request.stage == "template"
    assert request.mode == "template"
    tools = request.context.get("available_tools", [])
    tool_names = {tool["name"] for tool in tools}
    assert "schema.list_tables" in tool_names
    assert "sql.validate" in tool_names
