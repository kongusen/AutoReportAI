#!/usr/bin/env python3
"""
Self-test suite for AgentInput type-aware prompts and SQL guidance.
Runs without external deps or LLM/network access.

Usage:
  PYTHONPATH=backend backend/venv/bin/python backend/selftests/test_agentinput_suite.py
"""

import sys
from app.services.application.agent_input.prompt_templates import PromptComposer
from app.services.application.agent_input.builder import AgentInputBuilder
from app.services.application.context import Context
from app.services.infrastructure.agents.tools.sql_tools import SQLDraftTool, SQLValidateTool
import asyncio


def banner(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def test_prompt_ranking():
    banner("Test: Ranking prompt with TopN")
    pc = PromptComposer()
    consolidated = {
        "template_info": {"id": "tpl", "name": "测试模板"},
        "database_context": {
            "tables": [{
                "table_name": "orders",
                "measure_columns": ["amount"],
                "dimension_columns": ["product", "region"],
                "time_columns": ["created_at"],
            }]
        },
        "time_context": {"task_schedule": {"cron_expression": "0 0 * * 1", "timezone": "Asia/Shanghai"}},
        "business_rules": ["金额应排除取消订单"]
    }
    prompt = pc.compose(consolidated, "退货金额Top10商品", "sql", {"type": "ranking", "top_n": 10})
    print(prompt)
    assert "Top" in prompt or "Top N" in prompt
    print("PASS: Ranking prompt includes TopN guidance")


def test_prompt_compare():
    banner("Test: Compare prompt guidance")
    pc = PromptComposer()
    consolidated = {
        "template_info": {"id": "tpl", "name": "测试模板"},
        "database_context": {
            "tables": [{
                "table_name": "orders",
                "measure_columns": ["amount"],
                "time_columns": ["created_at"],
            }]
        },
        "time_context": {"task_schedule": {"cron_expression": "0 0 1 * *", "timezone": "Asia/Shanghai"}},
    }
    prompt = pc.compose(consolidated, "本月退货金额同比", "chart", {"type": "compare"})
    print(prompt)
    assert "百分比变化" in prompt
    print("PASS: Compare prompt includes percentage change guidance")


async def test_sql_guidance():
    banner("Test: SQL guidance in tools")
    draft = SQLDraftTool(container=None)
    schema = {"tables": ["orders"], "columns": {"orders": ["id", "amount", "created_at"]}}
    prompt = draft._build_sql_prompt(
        description="退货金额Top10商品",
        schema=schema,
        semantic_type="ranking",
        top_n=10,
        window={"task_schedule": {"cron_expression": "0 0 * * 1", "timezone": "Asia/Shanghai"}},
    )
    print(prompt)
    assert ("ORDER BY" in prompt) or ("RANK" in prompt) or ("LIMIT" in prompt) or ("Top" in prompt)
    print("PASS: Draft prompt contains ranking guidance")

    validate = SQLValidateTool(container=None)
    res = await validate.execute({"sql": "SELECT sum(amount) AS total FROM orders", "semantic_type": "compare"})
    print(res)
    assert not res["success"] and any("比较查询建议" in x for x in res.get("issues", []))
    print("PASS: Validate suggests compare columns")


def test_builder_integration():
    banner("Test: AgentInputBuilder integration")
    ctx = Context(
        context_id='c_demo',
        data_source_context={
            'database_name':'demo','database_type':'mysql',
            'tables':[{'table_name':'orders','columns':[{'name':'id'},{'name':'amount'},{'name':'created_at'}],
                       'measure_columns':['amount'],'dimension_columns':['product'],'time_columns':['created_at']}]
        },
        template_context={
            'template_info': {'id':'tpl1','name':'模板1'},
            'placeholder_contexts':[{'placeholder_name':'退货金额Top10商品','type':'统计类','context_paragraph':'...','position_info':{}, 'semantic_type':'ranking', 'parsed_params':{'top_n': 10}}]
        },
        task_context={'time_context':{'timezone':'Asia/Shanghai','agent_instructions':'最近30天'}}
    )
    b = AgentInputBuilder()
    res = b.build(ctx, '退货金额Top10商品', output_kind='sql')
    print(res['dynamic_user_prompt'])
    assert res['meta']['placeholder']['type'] == 'ranking'
    assert res['meta']['placeholder']['top_n'] == 10
    print("PASS: Builder integrates semantic_type and top_n")


def main():
    try:
        test_prompt_ranking()
        test_prompt_compare()
        asyncio.get_event_loop().run_until_complete(test_sql_guidance())
        test_builder_integration()
        banner("ALL TESTS PASSED")
        return 0
    except AssertionError as e:
        banner("TEST FAILED")
        print("AssertionError:", e)
        return 1
    except Exception as e:
        banner("TEST ERROR")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())

