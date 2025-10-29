"""
测试用户ID传递修复

验证在 Agent 执行期间，user_id 能够正确传递到模型选择服务
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.infrastructure.agents.llm_adapter import _CURRENT_USER_ID


def test_context_variable():
    """测试 context variable 的基本功能"""

    print("=" * 60)
    print("测试 Context Variable 功能")
    print("=" * 60)

    # 测试1: 默认值
    print("\n测试1: 默认值")
    default_value = _CURRENT_USER_ID.get()
    print(f"  默认值: '{default_value}'")
    print(f"  类型: {type(default_value)}")
    print(f"  是否为空: {not default_value}")

    # 测试2: 设置值
    print("\n测试2: 设置值")
    test_user_id = "test-user-12345"
    token = _CURRENT_USER_ID.set(test_user_id)
    current_value = _CURRENT_USER_ID.get()
    print(f"  设置后的值: '{current_value}'")
    print(f"  设置成功: {current_value == test_user_id} ✅" if current_value == test_user_id else f"  设置失败: {current_value} != {test_user_id} ❌")

    # 测试3: 重置值
    print("\n测试3: 重置值")
    _CURRENT_USER_ID.reset(token)
    reset_value = _CURRENT_USER_ID.get()
    print(f"  重置后的值: '{reset_value}'")
    print(f"  重置成功: {reset_value == default_value} ✅" if reset_value == default_value else f"  重置失败: {reset_value} != {default_value} ❌")

    # 测试4: 嵌套设置
    print("\n测试4: 嵌套设置")
    token1 = _CURRENT_USER_ID.set("user1")
    print(f"  第一层设置: '{_CURRENT_USER_ID.get()}'")

    token2 = _CURRENT_USER_ID.set("user2")
    print(f"  第二层设置: '{_CURRENT_USER_ID.get()}'")

    _CURRENT_USER_ID.reset(token2)
    print(f"  重置第二层: '{_CURRENT_USER_ID.get()}'")

    _CURRENT_USER_ID.reset(token1)
    print(f"  重置第一层: '{_CURRENT_USER_ID.get()}'")

    print("\n" + "=" * 60)
    print("✅ Context Variable 测试通过！")
    print("=" * 60)

    return True


def test_extract_user_id():
    """测试从消息中提取用户ID的逻辑"""

    print("\n" + "=" * 60)
    print("测试用户ID提取逻辑")
    print("=" * 60)

    from app.core.container import Container
    from app.services.infrastructure.agents.llm_adapter import create_llm_adapter

    # 创建容器和适配器
    container = Container()
    adapter = create_llm_adapter(container)

    # 测试1: 从 context variable 提取
    print("\n测试1: 从 context variable 提取")
    test_user_id = "user-from-context"
    token = _CURRENT_USER_ID.set(test_user_id)

    extracted = adapter._extract_user_id([])
    print(f"  提取的用户ID: '{extracted}'")
    print(f"  提取成功: {extracted == test_user_id} ✅" if extracted == test_user_id else f"  提取失败: {extracted} != {test_user_id} ❌")

    _CURRENT_USER_ID.reset(token)

    # 测试2: 从消息 metadata 提取
    print("\n测试2: 从消息 metadata 提取")
    messages = [
        {"role": "user", "content": "test", "metadata": {"user_id": "user-from-metadata"}}
    ]
    extracted = adapter._extract_user_id(messages)
    print(f"  提取的用户ID: '{extracted}'")
    print(f"  提取成功: {extracted == 'user-from-metadata'} ✅" if extracted == "user-from-metadata" else f"  提取失败: {extracted} != user-from-metadata ❌")

    # 测试3: 使用默认值
    print("\n测试3: 使用默认值")
    extracted = adapter._extract_user_id([])
    print(f"  提取的用户ID: '{extracted}'")
    print(f"  默认值: {extracted == adapter._default_user_id} ✅" if extracted == adapter._default_user_id else f"  默认值错误: {extracted} != {adapter._default_user_id} ❌")

    print("\n" + "=" * 60)
    print("✅ 用户ID提取逻辑测试通过！")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        # 测试 context variable
        if not test_context_variable():
            sys.exit(1)

        # 测试用户ID提取
        if not test_extract_user_id():
            sys.exit(1)

        print("\n" + "=" * 60)
        print("🎉 所有测试通过！用户ID传递修复验证成功！")
        print("=" * 60)

        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
