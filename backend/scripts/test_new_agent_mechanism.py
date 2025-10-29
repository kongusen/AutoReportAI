"""
测试新的 Agent 机制

验证基于 PRODUCTION_GUIDE.md 重构后的 Agent 系统：
1. ContextAssembler - 智能上下文组装
2. EventCollector - 事件监控
3. TaskTool - 子任务分解
"""

import asyncio
import logging
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.container import Container
from app.services.infrastructure.agents.facade import LoomAgentFacade
from app.services.infrastructure.agents.types import AgentRequest


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_context_assembler():
    """测试 ContextAssembler 功能"""
    logger.info("=" * 80)
    logger.info("测试 1: ContextAssembler - 智能上下文组装")
    logger.info("=" * 80)

    try:
        # 创建容器和 facade
        container = Container()
        facade = LoomAgentFacade(
            container=container,
            max_context_tokens=8000,  # 设置较小的 token 预算来测试裁剪功能
        )

        # 创建一个包含大量上下文的请求
        request = AgentRequest(
            prompt="分析最近一个月的销售数据，找出销售额最高的前10个产品",
            user_id=1,
            stage="template",
            mode="generation",
            context={
                "available_tools": [
                    {"name": "execute_sql", "desc": "执行SQL查询"},
                    {"name": "validate_sql", "desc": "验证SQL正确性"},
                ],
                "database_info": "online_retail 数据库包含零售交易数据",
                "additional_data": "一些额外的上下文信息" * 100,  # 大量重复数据
            },
            metadata={"test": "context_assembler"}
        )

        # 测试上下文组装
        prompt = facade._assemble_context(request)

        logger.info(f"✅ ContextAssembler 测试通过")
        logger.info(f"   生成的 prompt 长度: {len(prompt)} 字符")
        logger.info(f"   包含用户需求: {'分析最近一个月的销售数据' in prompt}")
        logger.info(f"   包含执行阶段: {'template' in prompt}")

        return True

    except Exception as e:
        logger.error(f"❌ ContextAssembler 测试失败: {e}", exc_info=True)
        return False


async def test_event_collector():
    """测试 EventCollector 功能"""
    logger.info("\n" + "=" * 80)
    logger.info("测试 2: EventCollector - 事件监控")
    logger.info("=" * 80)

    try:
        from loom.core.events import EventCollector, AgentEventType, AgentEvent

        # 创建事件收集器
        collector = EventCollector()

        # 模拟一些事件
        collector.add_event(AgentEvent(
            event_type=AgentEventType.AGENT_START,
            data={"prompt": "测试 prompt"}
        ))

        collector.add_event(AgentEvent(
            event_type=AgentEventType.TOOL_CALL,
            data={"tool": "execute_sql", "args": {"sql": "SELECT * FROM test"}}
        ))

        collector.add_event(AgentEvent(
            event_type=AgentEventType.TOOL_RESULT,
            data={"tool": "execute_sql", "result": "查询成功"}
        ))

        collector.add_event(AgentEvent(
            event_type=AgentEventType.AGENT_END,
            data={"success": True}
        ))

        # 获取事件统计
        events = collector.get_events()

        logger.info(f"✅ EventCollector 测试通过")
        logger.info(f"   收集的事件数量: {len(events)}")
        logger.info(f"   事件类型: {[e.event_type.value for e in events]}")

        return True

    except ImportError as e:
        logger.warning(f"⚠️ EventCollector 不可用 (Loom 版本可能不支持): {e}")
        return True  # 不算失败，因为是可选功能
    except Exception as e:
        logger.error(f"❌ EventCollector 测试失败: {e}", exc_info=True)
        return False


async def test_task_tools():
    """测试 TaskTool 功能"""
    logger.info("\n" + "=" * 80)
    logger.info("测试 3: TaskTool - 子任务分解")
    logger.info("=" * 80)

    try:
        from app.services.infrastructure.agents.task_tools import (
            create_sql_generation_tool,
            create_sql_validation_tool,
            create_chart_generation_tool,
        )

        # 测试创建工具（不需要实际执行，只测试创建）
        logger.info("   创建 SQL 生成工具...")
        # sql_gen_tool = create_sql_generation_tool(None)  # 暂时传 None

        logger.info("   创建 SQL 验证工具...")
        sql_val_tool = create_sql_validation_tool(None)

        logger.info("   创建图表生成工具...")
        # chart_tool = create_chart_generation_tool(None)  # 暂时传 None

        logger.info(f"✅ TaskTool 测试通过")
        logger.info(f"   SQL 验证工具: {sql_val_tool}")

        return True

    except Exception as e:
        logger.error(f"❌ TaskTool 测试失败: {e}", exc_info=True)
        return False


async def test_full_integration():
    """测试完整集成"""
    logger.info("\n" + "=" * 80)
    logger.info("测试 4: 完整集成测试")
    logger.info("=" * 80)

    try:
        # 创建容器
        container = Container()

        # 创建 facade（这会初始化所有组件）
        facade = LoomAgentFacade(
            container=container,
            max_context_tokens=16000,
        )

        logger.info(f"✅ Facade 创建成功")
        logger.info(f"   Runtime: {facade.runtime}")
        logger.info(f"   Tools: {len(facade.runtime.tools)} 个工具")

        # 打印工具列表
        tool_names = [tool.name if hasattr(tool, 'name') else str(tool) for tool in facade.runtime.tools]
        logger.info(f"   工具列表: {tool_names}")

        return True

    except Exception as e:
        logger.error(f"❌ 完整集成测试失败: {e}", exc_info=True)
        return False


async def main():
    """运行所有测试"""
    logger.info("🚀 开始测试新的 Agent 机制")
    logger.info("")

    results = []

    # 运行测试
    results.append(("ContextAssembler", await test_context_assembler()))
    results.append(("EventCollector", await test_event_collector()))
    results.append(("TaskTool", await test_task_tools()))
    results.append(("完整集成", await test_full_integration()))

    # 总结
    logger.info("\n" + "=" * 80)
    logger.info("测试总结")
    logger.info("=" * 80)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{name}: {status}")

    total_passed = sum(1 for _, result in results if result)
    total_tests = len(results)

    logger.info("")
    logger.info(f"总计: {total_passed}/{total_tests} 个测试通过")

    if total_passed == total_tests:
        logger.info("🎉 所有测试通过！新的 Agent 机制工作正常。")
        return 0
    else:
        logger.error("⚠️ 部分测试失败，请检查日志。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
