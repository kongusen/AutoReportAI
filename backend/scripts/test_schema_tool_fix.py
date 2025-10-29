"""
测试修复后的 DataSourceAdapter 和 Schema 发现工具
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


async def test_data_source_adapter_with_invalid_input():
    """测试 DataSourceAdapter 对各种无效输入的处理"""
    from app.core.container import DataSourceAdapter

    adapter = DataSourceAdapter()

    test_cases = [
        ("正常字典", {"source_type": "mysql", "host": "localhost", "port": 3306}),
        ("空字典", {}),
        ("None", None),
        ("字符串", "host=localhost"),
        ("列表", ["host", "port"]),
        ("单字符", "h"),
    ]

    print("=" * 80)
    print("测试 DataSourceAdapter.run_query 的输入验证")
    print("=" * 80)

    for name, config in test_cases:
        print(f"\n测试: {name}")
        print(f"输入类型: {type(config)}")
        print(f"输入值: {config}")

        try:
            result = await adapter.run_query(config, "SELECT 1", limit=10)
            print(f"✅ 结果: {result}")
        except Exception as e:
            print(f"❌ 异常: {type(e).__name__}: {e}")


async def test_schema_discovery_tool():
    """测试 Schema 发现工具的参数验证"""
    from app.services.infrastructure.agents.tools.schema.discovery import SchemaDiscoveryTool
    from app.core.container import ServiceContainer

    # 创建一个简单的容器
    class SimpleContainer:
        def __init__(self):
            self.data_source = DataSourceAdapter()

    container = SimpleContainer()
    tool = SchemaDiscoveryTool(container, enable_lazy_loading=True)

    test_cases = [
        ("正常字典", {"source_type": "mysql", "host": "localhost", "port": 3306, "database": "test"}),
        ("空字典", {}),
        ("None", None),
        ("字符串", "connection_string"),
    ]

    print("\n" + "=" * 80)
    print("测试 SchemaDiscoveryTool 的输入验证")
    print("=" * 80)

    for name, config in test_cases:
        print(f"\n测试: {name}")
        print(f"输入类型: {type(config)}")
        print(f"输入值: {config}")

        try:
            result = await tool.run(
                connection_config=config,
                discovery_type="tables",
                max_tables=5
            )
            print(f"✅ 结果: success={result.get('success')}, error={result.get('error', 'None')}")
            if not result.get('success'):
                print(f"   错误消息: {result.get('error')}")
        except Exception as e:
            print(f"❌ 异常: {type(e).__name__}: {e}")


class DataSourceAdapter:
    """本地测试用的简化版 DataSourceAdapter"""
    async def run_query(self, connection_config, sql, limit=1000):
        # 模拟我们修复后的逻辑
        if not connection_config:
            return {"success": False, "error": "missing_connection_config"}

        if not isinstance(connection_config, dict):
            return {
                "success": False,
                "error": f"connection_config must be a dictionary, got {type(connection_config).__name__}"
            }

        # 模拟成功响应
        return {
            "success": True,
            "rows": [{"table": "test_table"}],
            "columns": ["table"]
        }


async def main():
    await test_data_source_adapter_with_invalid_input()
    await test_schema_discovery_tool()


if __name__ == "__main__":
    asyncio.run(main())
