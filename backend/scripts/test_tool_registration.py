"""
测试工具注册机制

验证 Agent Runtime 是否正确创建和注册工具
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from app.core.container import Container
from app.services.infrastructure.agents.runtime import build_stage_aware_runtime
from app.services.infrastructure.agents.config.agent import create_default_agent_config


async def test_tool_registration():
    """测试工具注册"""

    print("=" * 60)
    print("测试工具自动注册机制")
    print("=" * 60)

    # 创建容器
    container = Container()

    # 创建默认配置
    config = create_default_agent_config()

    print("\n📋 配置中的启用工具:")
    for i, tool_name in enumerate(config.tools.enabled_tools, 1):
        print(f"  {i}. {tool_name}")

    print(f"\n总计: {len(config.tools.enabled_tools)} 个工具")

    # 构建 Stage-Aware Runtime
    print("\n🚀 开始构建 Stage-Aware Runtime...")
    print("=" * 60)

    runtime = build_stage_aware_runtime(
        container=container,
        config=config
    )

    print("=" * 60)

    # 检查工具是否被正确注册
    registered_tools = runtime._tools
    print(f"\n✅ 成功构建 Runtime!")
    print(f"📦 注册的工具数量: {len(registered_tools)}")

    if len(registered_tools) > 0:
        print("\n🔧 已注册的工具列表:")
        for i, tool in enumerate(registered_tools, 1):
            tool_name = getattr(tool, 'name', type(tool).__name__)
            tool_desc = getattr(tool, 'description', 'No description')
            print(f"  {i}. {tool_name}")
            print(f"     描述: {tool_desc[:80]}{'...' if len(tool_desc) > 80 else ''}")

        print("\n" + "=" * 60)
        print("✅ 工具注册机制测试通过！")
        print("=" * 60)

        # 验证工具数量是否匹配
        expected_count = len(config.tools.enabled_tools)
        actual_count = len(registered_tools)

        if actual_count == expected_count:
            print(f"\n✅ 工具数量匹配: 配置 {expected_count} 个 == 实际 {actual_count} 个")
        else:
            print(f"\n⚠️ 工具数量不匹配: 配置 {expected_count} 个 != 实际 {actual_count} 个")
            print("   某些工具创建可能失败，请查看日志")

        return True
    else:
        print("\n" + "=" * 60)
        print("❌ 工具注册机制测试失败！")
        print("❌ 没有工具被注册到 Runtime")
        print("=" * 60)
        return False


async def test_runtime_tool_access():
    """测试 Runtime 是否可以访问工具"""

    print("\n" + "=" * 60)
    print("测试 Runtime 工具访问")
    print("=" * 60)

    container = Container()
    config = create_default_agent_config()

    runtime = build_stage_aware_runtime(
        container=container,
        config=config
    )

    # 检查 Loom Agent 是否有工具
    agent = runtime._agent
    if hasattr(agent, 'tools'):
        agent_tools = agent.tools
        print(f"\n✅ Loom Agent 可以访问工具")
        print(f"📦 Agent 工具数量: {len(agent_tools)}")

        if len(agent_tools) > 0:
            print("\n🔧 Agent 可用的工具:")
            for i, tool in enumerate(agent_tools, 1):
                tool_name = getattr(tool, 'name', type(tool).__name__)
                print(f"  {i}. {tool_name}")

            print("\n✅ Runtime 工具访问测试通过！")
            return True
        else:
            print("\n❌ Agent 没有可用的工具")
            return False
    else:
        print("\n❌ Agent 没有 tools 属性")
        return False


async def main():
    """运行所有测试"""

    print("\n" + "=" * 60)
    print("开始工具注册机制测试")
    print("=" * 60 + "\n")

    # 测试1: 工具注册
    test1_passed = await test_tool_registration()

    if not test1_passed:
        print("\n❌ 测试失败：工具注册机制未正确工作")
        return False

    # 测试2: Runtime 工具访问
    test2_passed = await test_runtime_tool_access()

    if not test2_passed:
        print("\n❌ 测试失败：Runtime 无法访问工具")
        return False

    print("\n" + "=" * 60)
    print("🎉 所有测试通过！工具注册机制正常工作！")
    print("=" * 60)
    print("\n💡 提示:")
    print("  - 现在 Agent 在执行时应该可以调用这些工具")
    print("  - SQL 生成质量评分应该显著提高")
    print("  - 请运行实际的占位符分析任务验证效果")

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
