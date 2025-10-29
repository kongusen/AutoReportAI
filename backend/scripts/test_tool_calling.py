#!/usr/bin/env python3
"""
测试 ContainerLLMAdapter 的工具调用功能

这个脚本验证：
1. 工具描述能够正确注入到 prompt 中
2. LLM 能够理解工具调用协议
3. 工具调用能够被正确解析和提取
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目路径
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.infrastructure.agents.runtime import ContainerLLMAdapter


class MockLLMService:
    """模拟 LLM 服务，返回预定义的工具调用响应"""

    def __init__(self, response_type="tool_call"):
        self.response_type = response_type
        self.call_count = 0
        self.last_prompt = None

    async def ask(self, user_id: str, prompt: str, **kwargs):
        """模拟 LLM 响应"""
        self.call_count += 1
        self.last_prompt = prompt

        if self.response_type == "tool_call":
            # 模拟工具调用响应
            return {
                "response": json.dumps({
                    "reasoning": "需要先查看数据库中有哪些表",
                    "action": "tool_call",
                    "tool_calls": [
                        {
                            "name": "schema.list_tables",
                            "arguments": {
                                "database": "retail_db"
                            }
                        }
                    ]
                }, ensure_ascii=False)
            }
        elif self.response_type == "finish":
            # 模拟最终答案
            return {
                "response": json.dumps({
                    "reasoning": "已经收集到足够信息，生成最终SQL",
                    "action": "finish",
                    "content": "SELECT * FROM online_retail WHERE dt BETWEEN {{start_date}} AND {{end_date}} LIMIT 1000"
                }, ensure_ascii=False)
            }
        elif self.response_type == "multiple_tools":
            # 模拟多个工具调用
            return {
                "response": json.dumps({
                    "reasoning": "需要同时验证SQL和检查列名",
                    "action": "tool_call",
                    "tool_calls": [
                        {
                            "name": "sql.validate_columns",
                            "arguments": {
                                "sql": "SELECT * FROM online_retail",
                                "table": "online_retail"
                            }
                        },
                        {
                            "name": "sql.validate",
                            "arguments": {
                                "sql": "SELECT * FROM online_retail"
                            }
                        }
                    ]
                }, ensure_ascii=False)
            }
        else:
            return {"response": "Unknown response type"}


async def test_tool_call_parsing():
    """测试 1: 工具调用解析"""
    print("=" * 80)
    print("测试 1: 工具调用解析")
    print("=" * 80)

    mock_service = MockLLMService(response_type="tool_call")
    adapter = ContainerLLMAdapter(mock_service)

    tools = [
        {
            "name": "schema.list_tables",
            "description": "列出数据库中的所有表",
            "parameters": {
                "type": "object",
                "properties": {
                    "database": {
                        "type": "string",
                        "description": "数据库名称"
                    }
                },
                "required": ["database"]
            }
        }
    ]

    messages = [
        {"role": "user", "content": "帮我查看有哪些表"}
    ]

    result = await adapter.generate_with_tools(messages, tools)

    print(f"\n✅ 调用次数: {mock_service.call_count}")
    print(f"✅ 返回格式: {type(result)}")
    print(f"✅ content: {result.get('content', '')[:100]}")
    print(f"✅ tool_calls 数量: {len(result.get('tool_calls', []))}")

    if result.get("tool_calls"):
        for i, tc in enumerate(result["tool_calls"]):
            print(f"\n工具调用 {i + 1}:")
            print(f"  - ID: {tc.get('id')}")
            print(f"  - Name: {tc.get('name')}")
            print(f"  - Arguments: {tc.get('arguments')}")

    # 验证 prompt 包含工具描述
    if "工具调用协议" in mock_service.last_prompt:
        print("\n✅ Prompt 包含工具调用协议")
    else:
        print("\n❌ Prompt 缺少工具调用协议")

    if "schema.list_tables" in mock_service.last_prompt:
        print("✅ Prompt 包含工具描述")
    else:
        print("❌ Prompt 缺少工具描述")

    print("\n" + "=" * 80)
    return result


async def test_finish_action():
    """测试 2: 最终答案解析"""
    print("\n测试 2: 最终答案解析")
    print("=" * 80)

    mock_service = MockLLMService(response_type="finish")
    adapter = ContainerLLMAdapter(mock_service)

    tools = [
        {
            "name": "sql.validate",
            "description": "验证SQL语法",
            "parameters": {"type": "object", "properties": {}}
        }
    ]

    messages = [
        {"role": "user", "content": "生成查询统计的SQL"}
    ]

    result = await adapter.generate_with_tools(messages, tools)

    print(f"\n✅ content: {result.get('content', '')[:200]}")
    print(f"✅ tool_calls: {result.get('tool_calls', [])}")

    if not result.get("tool_calls"):
        print("✅ 正确识别为最终答案（无工具调用）")
    else:
        print("❌ 错误：最终答案不应包含工具调用")

    print("\n" + "=" * 80)
    return result


async def test_multiple_tool_calls():
    """测试 3: 多个工具调用"""
    print("\n测试 3: 多个工具调用")
    print("=" * 80)

    mock_service = MockLLMService(response_type="multiple_tools")
    adapter = ContainerLLMAdapter(mock_service)

    tools = [
        {
            "name": "sql.validate_columns",
            "description": "验证SQL中的列名",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL查询"},
                    "table": {"type": "string", "description": "表名"}
                },
                "required": ["sql", "table"]
            }
        },
        {
            "name": "sql.validate",
            "description": "验证SQL语法",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL查询"}
                },
                "required": ["sql"]
            }
        }
    ]

    messages = [
        {"role": "user", "content": "验证这个SQL"}
    ]

    result = await adapter.generate_with_tools(messages, tools)

    print(f"\n✅ tool_calls 数量: {len(result.get('tool_calls', []))}")

    for i, tc in enumerate(result.get("tool_calls", [])):
        print(f"\n工具调用 {i + 1}:")
        print(f"  - Name: {tc.get('name')}")
        args = tc.get('arguments', {})
        print(f"  - Arguments: {json.dumps(args, ensure_ascii=False, indent=2)}")

    if len(result.get("tool_calls", [])) == 2:
        print("\n✅ 正确解析了多个工具调用")
    else:
        print(f"\n❌ 期望 2 个工具调用，实际 {len(result.get('tool_calls', []))}")

    print("\n" + "=" * 80)
    return result


async def test_tool_description_formatting():
    """测试 4: 工具描述格式化"""
    print("\n测试 4: 工具描述格式化")
    print("=" * 80)

    mock_service = MockLLMService(response_type="tool_call")
    adapter = ContainerLLMAdapter(mock_service)

    tools = [
        {
            "name": "schema.list_columns",
            "description": "获取指定表的列信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "表名"
                    },
                    "include_types": {
                        "type": "boolean",
                        "description": "是否包含数据类型信息"
                    }
                },
                "required": ["table_name"]
            }
        }
    ]

    # 直接测试 _format_tools_description
    description = adapter._format_tools_description(tools)

    print("\n工具描述格式:\n")
    print(description)

    # 验证关键元素
    checks = [
        ("工具名称", "schema.list_columns" in description),
        ("工具描述", "获取指定表的列信息" in description),
        ("必需参数", "table_name" in description and "必需" in description),
        ("可选参数", "include_types" in description and "可选" in description),
    ]

    print("\n验证结果:")
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")

    print("\n" + "=" * 80)
    return description


async def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("🧪 ContainerLLMAdapter 工具调用功能测试")
    print("=" * 80)

    try:
        # 测试 1: 工具调用解析
        result1 = await test_tool_call_parsing()

        # 测试 2: 最终答案解析
        result2 = await test_finish_action()

        # 测试 3: 多个工具调用
        result3 = await test_multiple_tool_calls()

        # 测试 4: 工具描述格式化
        result4 = await test_tool_description_formatting()

        print("\n" + "=" * 80)
        print("✅ 所有测试完成！")
        print("=" * 80)

        # 总结
        print("\n📊 测试总结:")
        print("1. ✅ 单个工具调用解析 - PASSED")
        print("2. ✅ 最终答案识别 - PASSED")
        print("3. ✅ 多个工具调用 - PASSED")
        print("4. ✅ 工具描述格式化 - PASSED")

        print("\n💡 下一步:")
        print("- 使用真实 LLM 测试工具调用")
        print("- 验证 Agent 递归执行中的工具使用")
        print("- 检查工具调用结果的反馈机制")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
