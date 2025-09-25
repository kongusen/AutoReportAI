"""
Agent系统 - PTOF (Plan-Tool-Observe-Finalize) 架构
基于简洁高效的设计理念，替换原有的复杂流式Agent框架

核心组件:
- AgentFacade: 统一入口门面
- UnifiedOrchestrator: 核心编排器
- StepExecutor: 步骤执行器
- AgentPlanner: 计划生成器
- ContextPromptController: 上下文控制器
- ToolRegistry: 工具注册表

设计特点:
- 简洁直观的4步执行流程
- 统一标准化的工具接口
- 高性能低延迟的执行引擎
- 易于扩展的架构设计
"""

from .facade import AgentFacade
from .types import AgentInput, AgentOutput, PlaceholderSpec, SchemaInfo, TaskContext, AgentConstraints


async def execute_agent_task(
    placeholder: dict,
    context: dict,
    schema: dict = None,
    user_id: str = "system"
) -> dict:
    """
    执行Agent任务的兼容性接口
    为了兼容现有的占位符处理系统

    Args:
        placeholder: 占位符信息
        context: 上下文信息
        schema: 数据库架构信息
        user_id: 用户ID

    Returns:
        处理结果字典
    """
    try:
        from ....core.container import Container

        # 创建Container和AgentFacade
        container = Container()
        facade = AgentFacade(container)

        # 构建PlaceholderSpec
        placeholder_spec = PlaceholderSpec(
            id=placeholder.get("id", "unknown"),
            description=placeholder.get("description", placeholder.get("name", "占位符")),
            type=placeholder.get("type", "stat"),
            granularity=placeholder.get("granularity", "daily")
        )

        # 构建SchemaInfo
        schema_info = SchemaInfo(
            tables=schema.get("tables", []) if schema else [],
            columns=schema.get("columns", {}) if schema else {}
        )

        # 构建AgentInput
        agent_input = AgentInput(
            user_prompt=context.get("user_prompt", placeholder.get("description", "处理占位符")),
            placeholder=placeholder_spec,
            schema=schema_info,
            context=TaskContext(
                timezone=context.get("timezone", "Asia/Shanghai")
            ),
            constraints=AgentConstraints(
                sql_only=True,
                output_kind="sql"
            ),
            user_id=user_id
        )

        # 执行Agent任务
        result = await facade.execute(agent_input)

        # 返回兼容的结果格式
        return {
            "success": result.success,
            "result": result.result,
            "sql": result.result if result.success else None,
            "metadata": result.metadata,
            "agent_response": {
                "success": result.success,
                "content": result.result,
                "reasoning": result.metadata.get("reasoning") if result.metadata else None
            }
        }

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Agent task execution failed: {e}")

        return {
            "success": False,
            "result": "",
            "sql": None,
            "error": str(e),
            "agent_response": {
                "success": False,
                "content": "",
                "error": str(e)
            }
        }


__all__ = [
    "AgentFacade",
    "AgentInput",
    "AgentOutput",
    "PlaceholderSpec",
    "SchemaInfo",
    "TaskContext",
    "AgentConstraints",
    "execute_agent_task"
]