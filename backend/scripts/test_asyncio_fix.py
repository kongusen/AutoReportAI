#!/usr/bin/env python3
"""
测试 asyncio 嵌套事件循环修复

验证 run_async() 辅助函数能否在 Celery worker 环境中正确执行异步代码
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.infrastructure.task_queue.tasks import run_async


async def sample_async_function():
    """示例异步函数"""
    await asyncio.sleep(0.1)
    return "异步执行成功"


def test_run_async_without_loop():
    """测试在没有运行事件循环的情况下"""
    print("测试 1: 在没有运行事件循环的情况下执行...")
    try:
        result = run_async(sample_async_function())
        print(f"✅ 成功: {result}")
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def test_run_async_with_existing_loop():
    """测试在已有运行事件循环的情况下（模拟 Celery worker）"""
    print("\n测试 2: 在已有运行事件循环的情况下执行...")

    async def outer_async():
        """外层异步函数，模拟已存在的事件循环"""
        try:
            # 此时应该有一个运行中的事件循环
            result = run_async(sample_async_function())
            print(f"✅ 成功: {result}")
            return True
        except Exception as e:
            print(f"❌ 失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    # 运行外层异步函数
    return asyncio.run(outer_async())


def test_multiple_nested_calls():
    """测试多个嵌套调用"""
    print("\n测试 3: 多个嵌套异步调用...")

    async def async_task_1():
        await asyncio.sleep(0.05)
        return "任务1完成"

    async def async_task_2():
        await asyncio.sleep(0.05)
        return "任务2完成"

    async def outer_async():
        try:
            result1 = run_async(async_task_1())
            print(f"  结果1: {result1}")

            result2 = run_async(async_task_2())
            print(f"  结果2: {result2}")

            print("✅ 多个嵌套调用成功")
            return True
        except Exception as e:
            print(f"❌ 失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    return asyncio.run(outer_async())


if __name__ == "__main__":
    print("=" * 60)
    print("测试 asyncio 嵌套事件循环修复")
    print("=" * 60)

    results = []

    # 运行测试
    results.append(test_run_async_without_loop())
    results.append(test_run_async_with_existing_loop())
    results.append(test_multiple_nested_calls())

    # 总结
    print("\n" + "=" * 60)
    print(f"测试完成: {sum(results)}/{len(results)} 通过")
    print("=" * 60)

    if all(results):
        print("✅ 所有测试通过！修复生效。")
        sys.exit(0)
    else:
        print("❌ 部分测试失败，需要进一步检查。")
        sys.exit(1)
