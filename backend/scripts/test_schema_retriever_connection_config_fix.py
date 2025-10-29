#!/usr/bin/env python3
"""
测试 SchemaContextRetriever 初始化修复

验证内容：
1. SchemaContextRetriever 可以正常初始化（带 connection_config）
2. 连接配置参数传递正确
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.infrastructure.agents.context_retriever import SchemaContextRetriever


class MockContainer:
    """模拟容器"""
    pass


def test_schema_context_retriever_init():
    """测试 SchemaContextRetriever 初始化"""
    print("=" * 80)
    print("🧪 测试 SchemaContextRetriever 初始化")
    print("=" * 80)

    # 测试用例
    test_cases = [
        {
            "name": "完整配置",
            "data_source_id": "test-source-1",
            "connection_config": {
                "source_type": "doris",
                "database_name": "test_db",
                "host": "localhost",
                "port": 8030,
            },
        },
        {
            "name": "空配置",
            "data_source_id": "test-source-2",
            "connection_config": {},
        },
        {
            "name": "最小配置",
            "data_source_id": "test-source-3",
            "connection_config": {
                "database_name": "minimal_db",
            },
        },
    ]

    all_passed = True

    for test_case in test_cases:
        try:
            print(f"\n📝 测试用例: {test_case['name']}")
            print(f"   数据源ID: {test_case['data_source_id']}")
            print(f"   连接配置: {test_case['connection_config']}")

            # 创建实例
            container = MockContainer()
            retriever = SchemaContextRetriever(
                data_source_id=test_case["data_source_id"],
                connection_config=test_case["connection_config"],
                container=container
            )

            # 验证属性
            assert retriever.data_source_id == test_case["data_source_id"], "数据源ID不匹配"
            assert retriever.connection_config == test_case["connection_config"], "连接配置不匹配"
            assert retriever.container is container, "容器不匹配"
            assert retriever.schema_cache == {}, "Schema缓存应该为空"
            assert retriever._initialized is False, "初始化状态应该为False"

            print(f"   ✅ 初始化成功")

        except Exception as e:
            print(f"   ❌ 初始化失败: {e}")
            all_passed = False

    print()
    print("=" * 80)
    if all_passed:
        print("🎉 所有测试通过！SchemaContextRetriever 初始化修复成功。")
    else:
        print("❌ 部分测试失败，请检查实现。")
    print("=" * 80)

    return 0 if all_passed else 1


def test_missing_parameter():
    """测试缺少必需参数时的错误处理"""
    print("\n" + "=" * 80)
    print("🧪 测试缺少必需参数")
    print("=" * 80)

    container = MockContainer()

    # 测试缺少 connection_config
    try:
        print("\n📝 尝试创建 SchemaContextRetriever（缺少 connection_config）...")
        retriever = SchemaContextRetriever(
            data_source_id="test",
            container=container
            # 故意不传 connection_config
        )
        print("   ❌ 应该抛出 TypeError，但没有")
        return False
    except TypeError as e:
        if "connection_config" in str(e):
            print(f"   ✅ 正确抛出 TypeError: {e}")
            return True
        else:
            print(f"   ❌ 抛出了 TypeError，但不是因为 connection_config: {e}")
            return False
    except Exception as e:
        print(f"   ❌ 抛出了错误的异常类型: {type(e).__name__}: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n")
    print("=" * 80)
    print(" 🧪 SchemaContextRetriever 初始化修复测试套件")
    print("=" * 80)
    print()

    # 运行测试
    result1 = test_schema_context_retriever_init()
    result2 = test_missing_parameter()

    # 汇总结果
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)

    if result1 == 0 and result2:
        print("✅ 所有测试通过")
        print()
        print("🎯 修复验证成功：")
        print("   1. SchemaContextRetriever 可以正常初始化")
        print("   2. connection_config 参数正确传递")
        print("   3. 缺少必需参数时正确报错")
        print()
        return 0
    else:
        print("❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
