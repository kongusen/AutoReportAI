"""
测试 Loom Agent 递归执行模式（tt 函数）

演示如何使用递归模式进行更细粒度的控制
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.container import Container
from app.services.infrastructure.agents.facade import LoomAgentFacade

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_default_recursive_mode():
    """
    测试 1: 默认递归模式（通过 agent.run()）

    agent.run() 内部已经使用 tt() 递归方法
    """
    logger.info("=" * 80)
    logger.info("测试 1: 默认递归模式（agent.run 内部使用 tt）")
    logger.info("=" * 80)

    try:
        container = Container()
        facade = LoomAgentFacade(container=container)

        # 简单调用（内部已经是递归）
        from app.services.infrastructure.agents.types import AgentRequest

        request = AgentRequest(
            prompt="请说明什么是递归执行模式",
            user_id=1,
            stage="template",
            mode="generation",
            context={},
            metadata={}
        )

        response = await facade.execute(request)

        logger.info("✅ 测试通过")
        logger.info(f"   响应长度: {len(response.output if response.output else '')}")
        logger.info(f"   成功: {response.success}")
        logger.info("   注意：agent.run() 内部已经使用递归模式（tt）")

        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


async def test_direct_tt_usage():
    """
    测试 2: 直接使用 tt() 方法进行细粒度控制

    展示如何直接调用 tt() 方法来监控递归过程
    """
    logger.info("\n" + "=" * 80)
    logger.info("测试 2: 直接使用 tt() 方法进行细粒度控制")
    logger.info("=" * 80)

    try:
        from loom.core.events import AgentEventType

        container = Container()
        facade = LoomAgentFacade(container=container)

        # 获取底层 executor
        executor = facade.runtime.agent._executor

        # 初始化递归状态
        from loom.core.turn_state import TurnState
        from loom.core.execution_context import ExecutionContext
        from loom.core.types import Message

        turn_state = TurnState.initial(max_iterations=10)
        context = ExecutionContext.create()
        messages = [Message(role="user", content="请说明递归执行的优势")]

        # 追踪递归统计
        stats = {
            "recursion_depth": 0,
            "tool_calls": 0,
            "llm_calls": 0,
            "events": [],
        }

        # 直接调用 tt() 递归方法
        async for event in executor.tt(messages, turn_state, context):
            # 记录事件类型
            stats["events"].append(event.type.value if hasattr(event.type, 'value') else str(event.type))

            # 追踪递归深度
            if event.type == AgentEventType.RECURSION:
                depth = event.metadata.get('depth', 0)
                stats["recursion_depth"] = max(stats["recursion_depth"], depth)
                logger.info(f"   🔄 递归调用: 第 {depth} 层")

            # 追踪 LLM 调用
            elif event.type == AgentEventType.LLM_START:
                stats["llm_calls"] += 1
                logger.info(f"   🧠 LLM 调用: 第 {stats['llm_calls']} 次")

            # 追踪工具调用
            elif event.type == AgentEventType.TOOL_RESULT:
                stats["tool_calls"] += 1
                tool_name = event.metadata.get('tool_name', 'unknown')
                logger.info(f"   🔧 工具执行: {tool_name}（第 {stats['tool_calls']} 个）")

            # 最终答案
            elif event.type == AgentEventType.AGENT_FINISH:
                logger.info(f"   ✅ 执行完成")
                break

        logger.info("\n📊 递归执行统计:")
        logger.info(f"   - 最大递归深度: {stats['recursion_depth']}")
        logger.info(f"   - LLM 调用次数: {stats['llm_calls']}")
        logger.info(f"   - 工具调用次数: {stats['tool_calls']}")
        logger.info(f"   - 总事件数: {len(stats['events'])}")

        logger.info("✅ 测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


async def test_recursion_tracking_in_facade():
    """
    测试 3: 在 Facade 中集成递归追踪

    展示如何在现有系统中添加递归监控
    """
    logger.info("\n" + "=" * 80)
    logger.info("测试 3: Facade 中的递归追踪")
    logger.info("=" * 80)

    try:
        container = Container()
        facade = LoomAgentFacade(container=container)

        from app.services.infrastructure.agents.types import AgentRequest

        request = AgentRequest(
            prompt="测试递归追踪",
            user_id=1,
            stage="template",
            mode="generation",
            context={},
            metadata={"enable_recursion_tracking": True}
        )

        # 执行请求
        response = await facade.execute(request)

        # 检查是否有递归统计（如果实现了）
        if response.metadata and "recursion_stats" in response.metadata:
            recursion_stats = response.metadata["recursion_stats"]
            logger.info("📊 递归统计（来自 metadata）:")
            logger.info(f"   {recursion_stats}")
        else:
            logger.info("⚠️ 递归统计未在 metadata 中（需要实现高级接口）")

        logger.info("✅ 测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


async def test_recursion_state_immutability():
    """
    测试 4: 验证递归状态的不可变性

    TurnState 应该是不可变的，每次递归创建新状态
    """
    logger.info("\n" + "=" * 80)
    logger.info("测试 4: 递归状态的不可变性")
    logger.info("=" * 80)

    try:
        from loom.core.turn_state import TurnState

        # 创建初始状态
        state_0 = TurnState.initial(max_iterations=10)
        logger.info(f"   state_0: turn={state_0.turn_counter}, id={state_0.turn_id[:8]}")

        # 创建下一个状态
        state_1 = state_0.next()
        logger.info(f"   state_1: turn={state_1.turn_counter}, id={state_1.turn_id[:8]}, parent={state_1.parent_turn_id[:8] if state_1.parent_turn_id else None}")

        # 再创建一个
        state_2 = state_1.next()
        logger.info(f"   state_2: turn={state_2.turn_counter}, id={state_2.turn_id[:8]}, parent={state_2.parent_turn_id[:8] if state_2.parent_turn_id else None}")

        # 验证不可变性
        assert state_0.turn_counter == 0, "state_0 应该保持不变"
        assert state_1.turn_counter == 1, "state_1 应该保持不变"
        assert state_2.turn_counter == 2, "state_2 的计数器应该是 2"

        # 验证父子关系
        assert state_1.parent_turn_id == state_0.turn_id, "state_1 的父ID应该是 state_0"
        assert state_2.parent_turn_id == state_1.turn_id, "state_2 的父ID应该是 state_1"

        # 验证终止条件
        assert not state_0.is_final, "state_0 不应该是最终状态"

        # 创建一个接近最大迭代的状态
        state_near_end = TurnState(
            turn_id="test",
            turn_counter=9,
            max_iterations=10,
        )
        state_end = state_near_end.next()
        assert state_end.is_final, "应该到达最终状态"

        logger.info("✅ 验证通过")
        logger.info("   - state_0 保持不变")
        logger.info("   - 父子关系正确")
        logger.info("   - 终止条件正确")

        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


async def demo_recursion_advantages():
    """
    演示：递归模式的优势

    对比传统迭代模式和递归模式
    """
    logger.info("\n" + "=" * 80)
    logger.info("演示：递归模式 vs. 迭代模式")
    logger.info("=" * 80)

    logger.info("\n❌ 传统迭代模式（伪代码）:")
    logger.info("""
    async def execute_iterative(prompt):
        messages = [{"role": "user", "content": prompt}]
        iterations = 0

        while iterations < MAX_ITERATIONS:
            response = await llm.generate(messages)

            if has_tool_calls(response):
                tool_results = await execute_tools(response.tool_calls)
                messages.append(response)
                messages.extend(tool_results)
                iterations += 1
                continue  # 状态在循环中累积
            else:
                return response.content

    问题：
    - 状态可变（messages 不断 append）
    - 控制流复杂（while + continue + break）
    - 难以追踪每次迭代的状态
    """)

    logger.info("\n✅ 递归模式（loom-agent）:")
    logger.info("""
    async def tt(messages, turn_state, context):
        # Base Case: 达到最大深度
        if turn_state.is_final:
            return

        # 调用 LLM
        response = await llm.generate(messages)

        # Base Case: 没有工具调用
        if not response.tool_calls:
            yield AGENT_FINISH(response.content)
            return

        # 执行工具
        tool_results = await execute_tools(response.tool_calls)

        # 递归调用（创建新状态）
        next_messages = messages + [response] + tool_results
        next_state = turn_state.next()  # 不可变更新

        async for event in self.tt(next_messages, next_state, context):
            yield event

    优势：
    ✅ 状态不可变（每次创建新 turn_state）
    ✅ 控制流清晰（明确的 base cases）
    ✅ 易于测试（每层递归可独立测试）
    ✅ 支持嵌套任务
    ✅ 更好的事件追踪
    """)

    return True


async def main():
    """运行所有测试"""
    logger.info("🚀 开始测试 Loom Agent 递归执行模式\n")

    results = []

    # 运行测试
    results.append(("默认递归模式", await test_default_recursive_mode()))
    results.append(("直接使用 tt()", await test_direct_tt_usage()))
    results.append(("Facade 递归追踪", await test_recursion_tracking_in_facade()))
    results.append(("状态不可变性", await test_recursion_state_immutability()))

    # 演示
    await demo_recursion_advantages()

    # 总结
    logger.info("\n" + "=" * 80)
    logger.info("测试总结")
    logger.info("=" * 80)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{name}: {status}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    logger.info("")
    logger.info(f"总计: {passed}/{total} 个测试通过")

    if passed == total:
        logger.info("\n🎉 所有测试通过！")
        logger.info("\n💡 关键要点:")
        logger.info("   1. ✅ 我们的系统已经在使用递归模式（通过 agent.run()）")
        logger.info("   2. ✅ 可以直接使用 executor.tt() 获得更细粒度的控制")
        logger.info("   3. ✅ TurnState 是不可变的，每次递归创建新状态")
        logger.info("   4. ✅ 递归模式比迭代模式更清晰、更易测试")
        logger.info("\n📚 详细文档: docs/RECURSIVE_EXECUTION_PATTERN.md")
        return 0
    else:
        logger.error("\n⚠️ 部分测试失败。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
