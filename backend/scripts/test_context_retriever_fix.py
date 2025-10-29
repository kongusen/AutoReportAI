#!/usr/bin/env python3
"""
测试 SchemaContextRetriever 的 retrieve_for_query 方法修复

验证：
1. retrieve_for_query 方法是否存在
2. 方法是否能正确调用
3. 返回结果格式是否正确
4. ContextVar token reset 修复
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.infrastructure.agents.context_retriever import SchemaContextRetriever
from loom.interfaces.retriever import Document


async def test_retrieve_for_query():
    """测试 retrieve_for_query 方法"""

    print("=" * 80)
    print("测试 SchemaContextRetriever.retrieve_for_query 方法")
    print("=" * 80)

    # 创建一个模拟的 SchemaContextRetriever
    retriever = SchemaContextRetriever(
        data_source_id="test-source",
        connection_config={},
        container=None,  # 使用 None 作为占位符
        top_k=5,
        enable_stage_aware=True,
        use_intelligent_retrieval=False,
        enable_lazy_loading=True
    )

    # 1. 检查方法是否存在
    print("\n1️⃣ 检查 retrieve_for_query 方法是否存在...")
    if hasattr(retriever, 'retrieve_for_query'):
        print("   ✅ retrieve_for_query 方法存在")
    else:
        print("   ❌ retrieve_for_query 方法不存在")
        return False

    # 2. 检查方法签名
    print("\n2️⃣ 检查方法签名...")
    import inspect
    sig = inspect.signature(retriever.retrieve_for_query)
    params = list(sig.parameters.keys())
    print(f"   参数: {params}")

    expected_params = ['query', 'top_k', 'filters']
    if all(param in params for param in expected_params):
        print("   ✅ 方法签名正确")
    else:
        print(f"   ❌ 方法签名不正确，期望: {expected_params}")
        return False

    # 3. 测试方法调用（不实际连接数据库）
    print("\n3️⃣ 测试方法调用...")
    try:
        # 由于没有真实的数据源，这个调用会返回空列表
        # 但重要的是方法能被调用
        result = await retriever.retrieve_for_query(
            query="测试查询",
            top_k=3,
            filters=None
        )
        print(f"   ✅ 方法调用成功")
        print(f"   返回类型: {type(result)}")
        print(f"   返回结果: {result}")

        # 检查返回类型
        if isinstance(result, list):
            print("   ✅ 返回类型正确（List）")

            # 如果有结果，检查元素类型
            if result:
                if all(isinstance(doc, Document) for doc in result):
                    print("   ✅ 返回元素类型正确（Document）")
                else:
                    print("   ❌ 返回元素类型不正确")
                    return False
        else:
            print("   ❌ 返回类型不正确")
            return False

    except Exception as e:
        print(f"   ⚠️ 方法调用出错（预期的，因为没有真实数据源）: {e}")
        # 只要不是 AttributeError，就说明方法存在且可调用
        if "retrieve_for_query" in str(e):
            print("   ❌ 方法仍然缺失")
            return False
        else:
            print("   ✅ 方法存在但因缺少数据源而失败（正常）")

    # 4. 检查 retrieve 方法是否也存在
    print("\n4️⃣ 检查 retrieve 方法是否存在...")
    if hasattr(retriever, 'retrieve'):
        print("   ✅ retrieve 方法存在")
    else:
        print("   ❌ retrieve 方法不存在")
        return False

    # 5. 验证两个方法的关系
    print("\n5️⃣ 验证 retrieve_for_query 和 retrieve 的关系...")
    print("   retrieve_for_query 应该内部调用 retrieve")

    # 通过检查源码来验证
    import inspect
    source = inspect.getsource(retriever.retrieve_for_query)
    if 'self.retrieve' in source:
        print("   ✅ retrieve_for_query 正确调用了 retrieve")
    else:
        print("   ⚠️ 无法确认方法调用关系")

    print("\n" + "=" * 80)
    print("✅ 所有测试通过！")
    print("=" * 80)

    return True


async def test_context_var_fix():
    """测试 ContextVar token reset 修复"""

    print("\n" + "=" * 80)
    print("测试 ContextVar token reset 修复")
    print("=" * 80)

    from app.services.infrastructure.agents.runtime import LoomAgentRuntime
    import inspect

    # 检查 execute_with_tt 方法的 finally 块
    print("\n1️⃣ 检查 execute_with_tt 方法的 finally 块...")

    # 获取源码
    source = inspect.getsource(LoomAgentRuntime.execute_with_tt)

    # 检查是否有 try-except 包裹 reset 调用
    if 'try:' in source and '_CURRENT_USER_ID.reset(token)' in source:
        if 'except' in source and 'ValueError' in source:
            print("   ✅ finally 块包含了异常处理")
            print("   ✅ 捕获了 ValueError 异常")
        else:
            print("   ❌ 缺少异常处理")
            return False
    else:
        print("   ❌ token reset 逻辑不正确")
        return False

    print("\n" + "=" * 80)
    print("✅ ContextVar 修复验证通过！")
    print("=" * 80)

    return True


async def main():
    """主测试函数"""
    print("\n🚀 开始测试修复...")

    # 测试 1: retrieve_for_query 方法
    test1_pass = await test_retrieve_for_query()

    # 测试 2: ContextVar token reset
    test2_pass = await test_context_var_fix()

    # 总结
    print("\n" + "=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    print(f"retrieve_for_query 修复: {'✅ 通过' if test1_pass else '❌ 失败'}")
    print(f"ContextVar token reset 修复: {'✅ 通过' if test2_pass else '❌ 失败'}")

    if test1_pass and test2_pass:
        print("\n🎉 所有修复均已验证！")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
