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
from datetime import datetime


async def execute_agent_task(
    task_name: str = None,
    task_description: str = None,
    context_data: dict = None,
    additional_data: dict = None,
    # Legacy parameters for backward compatibility
    placeholder: dict = None,
    context: dict = None,
    schema: dict = None,
    user_id: str = "system"
) -> dict:
    """
    执行Agent任务的兼容性接口 - 使用任务验证智能模式
    支持新的调用模式和向后兼容

    Args:
        task_name: 任务名称 (新接口)
        task_description: 任务描述 (新接口)
        context_data: 上下文数据 (新接口)
        additional_data: 附加数据 (新接口)
        placeholder: 占位符信息 (兼容性)
        context: 上下文信息 (兼容性)
        schema: 数据库架构信息 (兼容性)
        user_id: 用户ID

    Returns:
        处理结果字典
    """
    try:
        from ....core.container import Container

        # 创建Container和AgentFacade
        container = Container()
        facade = AgentFacade(container)

        # 新接口处理
        if task_name or task_description or context_data:
            # 使用新的接口参数
            user_prompt = task_description or task_name or "执行Agent任务"

            # 从context_data和additional_data中提取信息
            all_context = {}
            if context_data:
                all_context.update(context_data)
            if additional_data:
                all_context.update(additional_data)

            # 尝试从additional_data中提取现有SQL
            existing_sql = None
            if additional_data:
                data_source_info = additional_data.get('data_source_info', {})
                existing_sql = (data_source_info.get('existing_sql') or
                              additional_data.get('current_sql') or
                              additional_data.get('template_sql'))

            # 构建PlaceholderSpec
            from .types import PlaceholderSpec
            placeholder_info = PlaceholderSpec(
                description=task_description or task_name or "Agent任务",
                type=all_context.get("task_type", "general")
            )

            # 构建SchemaInfo
            schema_info = SchemaInfo()
            if additional_data and 'data_source_info' in additional_data:
                ds_info = additional_data['data_source_info']
                schema_info.database_name = ds_info.get('database')
                if ds_info.get('type') == 'doris':
                    schema_info.host = ds_info.get('host', '192.168.31.160')
                    schema_info.port = ds_info.get('port', 8030)

            # 构建AgentInput
            agent_input = AgentInput(
                user_prompt=user_prompt,
                placeholder=placeholder_info,
                schema=schema_info,
                context=TaskContext(
                    task_time=int(datetime.now().timestamp()),
                    timezone=all_context.get("timezone", "Asia/Shanghai")
                ),
                task_driven_context=(lambda _ad=additional_data: (lambda _ctx: (
                    _ctx.update({
                        # 扁平化数据源信息，便于执行器自动加载连接配置
                        "data_source_info": (_ad.get('data_source_info') if isinstance(_ad, dict) else None),
                        "data_source_id": (
                            (_ad.get('data_source_info') or {}).get('id') if isinstance(_ad, dict) and isinstance(_ad.get('data_source_info'), dict) and (_ad.get('data_source_info') or {}).get('id') else
                            ((_ad.get('data_source_info') or {}).get('data_source_id') if isinstance(_ad, dict) and isinstance(_ad.get('data_source_info'), dict) else None)
                        )
                    }) or _ctx
                ))({
                    "task_name": task_name,
                    "current_sql": existing_sql,
                    "context_data": context_data,
                    "additional_data": additional_data,
                    "execution_mode": "compatibility_interface"
                })),
                user_id=user_id
            )

            # 🎯 使用任务验证智能模式
            result = await facade.execute_task_validation(agent_input)

        else:
            # 向后兼容的旧接口处理
            placeholder_spec = PlaceholderSpec(
                id=placeholder.get("id", "unknown") if placeholder else "unknown",
                description=placeholder.get("description", placeholder.get("name", "占位符")) if placeholder else "占位符",
                type=placeholder.get("type", "stat") if placeholder else "stat",
                granularity=placeholder.get("granularity", "daily") if placeholder else "daily"
            )

            schema_info = SchemaInfo(
                tables=schema.get("tables", []) if schema else [],
                columns=schema.get("columns", {}) if schema else {}
            )

            agent_input = AgentInput(
                user_prompt=context.get("user_prompt", placeholder.get("description", "处理占位符")) if context and placeholder else "处理占位符",
                placeholder=placeholder_spec,
                schema=schema_info,
                context=TaskContext(
                    timezone=context.get("timezone", "Asia/Shanghai") if context else "Asia/Shanghai"
                ),
                constraints=AgentConstraints(
                    sql_only=True,
                    output_kind="sql"
                ),
                task_driven_context={
                    "current_sql": context.get("current_sql") if context else None,
                    "execution_mode": "legacy_compatibility"
                },
                user_id=user_id
            )

            # 🎯 使用任务验证智能模式
            result = await facade.execute_task_validation(agent_input)

        # 统一提取文本结果（AgentOutput 使用 result 字段）
        try:
            text_result = getattr(result, 'result', None)
            if text_result is None:
                # 兼容极少数历史路径
                text_result = getattr(result, 'content', None)
            if text_result is None:
                text_result = ""
        except Exception:
            text_result = ""

        # 返回兼容的结果格式
        return {
            "success": bool(getattr(result, 'success', False)),
            "result": text_result,
            "sql": text_result if getattr(result, 'success', False) else None,
            "response": text_result,  # 新接口兼容
            "metadata": getattr(result, 'metadata', {}) or {},
            "generation_method": (result.metadata.get('generation_method', 'validation') if getattr(result, 'metadata', None) else 'validation'),
            "time_updated": (result.metadata.get('time_updated', False) if getattr(result, 'metadata', None) else False),
            "fallback_reason": (result.metadata.get('fallback_reason') if getattr(result, 'metadata', None) else None),
            "conversation_time": 0.1,  # 模拟执行时间
            "agent_response": {
                "success": bool(getattr(result, 'success', False)),
                "content": text_result,
                "reasoning": (result.metadata.get("reasoning") if getattr(result, 'metadata', None) else None)
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
            "response": "",
            "error": str(e),
            "conversation_time": 0.0,
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
