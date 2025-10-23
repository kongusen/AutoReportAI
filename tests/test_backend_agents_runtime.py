from types import SimpleNamespace

import pytest

from app.services.infrastructure.agents import AgentRequest, LoomAgentFacade
from app.services.infrastructure.agents.tools import adapt_legacy_tool


class _DummyTool:
    def __init__(self, container=None):
        self.name = "dummy.increment"
        self.description = "Increase the provided value"
        self._container = container

    async def execute(self, input_data):
        value = input_data.get("value", 0)
        return {"success": True, "result": value + 1, "container": bool(self._container)}


@pytest.mark.asyncio
async def test_adapt_legacy_tool_uses_container():
    factory = adapt_legacy_tool(_DummyTool)
    tool = factory(SimpleNamespace(marker=True))
    result = await tool.run(value=10)
    assert result["success"] is True
    assert result["result"] == 11
    assert result["container"] is True


@pytest.mark.asyncio
async def test_facade_execute_with_mock_llm():
    container = SimpleNamespace()
    facade = LoomAgentFacade(
        container=container,
        config_overrides={"llm": {"mock_responses": ["回答内容"]}},
        include_legacy_tools=False,
    )

    request = AgentRequest(prompt="测试问题", context={"table": "orders"})
    response = await facade.execute(request)

    assert response.success is True
    assert response.output == "回答内容"
    assert "prompt" in response.metadata
