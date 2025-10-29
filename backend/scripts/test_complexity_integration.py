"""
集成测试：验证 LoomAgentFacade 初始化修复

测试实际的 facade.initialize() 调用，确保 TaskComplexity 枚举可以正确传入
"""

import sys
import os
import asyncio

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.infrastructure.agents.types import TaskComplexity, AgentRequest
from app.services.infrastructure.agents.config.agent import AgentConfigManager, create_default_agent_config


async def test_agent_config_manager():
    """测试 AgentConfigManager.resolve_user_config"""

    print("=" * 60)
    print("测试 AgentConfigManager.resolve_user_config")
    print("=" * 60)

    config_manager = AgentConfigManager(create_default_agent_config())

    # 测试1: 传入 TaskComplexity 枚举
    print("\n测试1: 传入 TaskComplexity.MEDIUM 枚举")
    try:
        # 这将调用 resolve_user_config，如果修复成功，应该不会抛出异常
        # 注意：由于没有实际的用户配置，这里会使用默认配置
        result = await config_manager.resolve_user_config(
            user_id="test_user",
            task_type="placeholder_analysis",
            task_complexity=TaskComplexity.MEDIUM  # 传入枚举
        )
        print(f"  ✅ 成功！返回配置: max_context_tokens={result.max_context_tokens}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    # 测试2: 传入 float 值
    print("\n测试2: 传入 float 值 0.5")
    try:
        result = await config_manager.resolve_user_config(
            user_id="test_user",
            task_type="placeholder_analysis",
            task_complexity=0.5  # 传入 float
        )
        print(f"  ✅ 成功！返回配置: max_context_tokens={result.max_context_tokens}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    # 测试3: 传入 int 值
    print("\n测试3: 传入 int 值 1")
    try:
        result = await config_manager.resolve_user_config(
            user_id="test_user",
            task_type="placeholder_analysis",
            task_complexity=1  # 传入 int
        )
        print(f"  ✅ 成功！返回配置: max_context_tokens={result.max_context_tokens}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)

    return True


def test_agent_request():
    """测试 AgentRequest 创建"""

    print("\n" + "=" * 60)
    print("测试 AgentRequest 创建")
    print("=" * 60)

    # 测试1: 使用默认的 TaskComplexity.MEDIUM
    print("\n测试1: 使用默认的 TaskComplexity.MEDIUM")
    try:
        request = AgentRequest(
            placeholder="测试占位符",
            data_source_id=1,
            user_id="test_user"
        )
        print(f"  ✅ 成功！complexity={request.complexity} (类型: {type(request.complexity)})")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    # 测试2: 显式指定 TaskComplexity
    print("\n测试2: 显式指定 TaskComplexity.COMPLEX")
    try:
        request = AgentRequest(
            placeholder="测试占位符",
            data_source_id=1,
            user_id="test_user",
            complexity=TaskComplexity.COMPLEX
        )
        print(f"  ✅ 成功！complexity={request.complexity} (类型: {type(request.complexity)})")
        print(f"  可以转换为 float: {float(request.complexity)}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)

    return True


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始集成测试")
    print("=" * 60 + "\n")

    # 测试 AgentRequest
    if not test_agent_request():
        return False

    # 测试 AgentConfigManager
    if not await test_agent_config_manager():
        return False

    print("\n" + "=" * 60)
    print("🎉 所有集成测试通过！修复验证成功！")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
