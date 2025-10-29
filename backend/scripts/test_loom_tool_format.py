#!/usr/bin/env python3
"""
测试 Loom 工具格式解析修复

验证：
1. 能够正确解析 Loom 的工具格式
2. 工具描述能够正确格式化
"""

import asyncio
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.infrastructure.agents.runtime import ContainerLLMAdapter


def test_loom_tool_format():
    """测试 Loom 工具格式解析"""
    print("=" * 80)
    print("测试 Loom 工具格式解析")
    print("=" * 80)

    # Loom 的标准工具格式
    loom_tools = [
        {
            "type": "function",
            "function": {
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
        },
        {
            "type": "function",
            "function": {
                "name": "schema.list_columns",
                "description": "获取指定表的列信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "表名"
                        }
                    },
                    "required": ["table_name"]
                }
            }
        }
    ]

    # 创建 mock service
    class MockService:
        async def ask(self, **kwargs):
            return {"response": "test"}

    adapter = ContainerLLMAdapter(MockService())

    # 测试格式化
    try:
        description = adapter._format_tools_description(loom_tools)

        print("\n✅ 工具描述格式化成功！\n")
        print("格式化结果：")
        print("-" * 80)
        print(description)
        print("-" * 80)

        # 验证关键内容
        checks = [
            ("工具1名称", "schema.list_tables" in description),
            ("工具1描述", "列出数据库中的所有表" in description),
            ("工具1参数", "database" in description),
            ("工具2名称", "schema.list_columns" in description),
            ("工具2描述", "获取指定表的列信息" in description),
            ("工具2参数", "table_name" in description),
            ("必需标记", "必需" in description),
        ]

        print("\n验证结果：")
        all_passed = True
        for name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"{status} {name}")
            if not passed:
                all_passed = False

        if all_passed:
            print("\n🎉 所有验证通过！")
            return True
        else:
            print("\n❌ 部分验证失败")
            return False

    except Exception as e:
        print(f"\n❌ 格式化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_legacy_tool_format():
    """测试兼容性：旧格式工具"""
    print("\n" + "=" * 80)
    print("测试旧格式工具（兼容性）")
    print("=" * 80)

    legacy_tools = [
        {
            "name": "test.tool",
            "description": "测试工具",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "参数1"}
                }
            }
        }
    ]

    class MockService:
        async def ask(self, **kwargs):
            return {"response": "test"}

    adapter = ContainerLLMAdapter(MockService())

    try:
        description = adapter._format_tools_description(legacy_tools)
        print("\n✅ 旧格式兼容性测试通过！\n")
        print(description)
        return True
    except Exception as e:
        print(f"\n❌ 旧格式测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("🧪 Loom 工具格式解析测试")
    print("=" * 80)

    results = []

    # 测试 1: Loom 格式
    results.append(("Loom 工具格式", test_loom_tool_format()))

    # 测试 2: 旧格式兼容性
    results.append(("旧格式兼容性", test_legacy_tool_format()))

    # 总结
    print("\n" + "=" * 80)
    print("📊 测试总结")
    print("=" * 80)

    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n🎉 所有测试通过！工具格式解析已修复")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
