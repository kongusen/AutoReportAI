"""
TT 递归执行运行时

基于 Loom tt 函数实现自动迭代推理
这是整个 Agent 系统的核心执行引擎
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable, Tuple

from loom import Agent, agent as build_agent
from loom.interfaces.tool import BaseTool
from loom.interfaces.llm import BaseLLM

from .types import (
    AgentRequest, AgentResponse, ExecutionState, ExecutionStage,
    ToolCall, ContextInfo, AgentConfig, AgentEvent, TaskComplexity
)
from .llm_adapter import (
    ContainerLLMAdapter, create_llm_adapter,
    _CURRENT_USER_ID, _CURRENT_STAGE  # 导入 context variables
)
from .context_retriever import SchemaContextRetriever, create_schema_context_retriever

# 数据库相关导入
from app.db.session import get_db_session
from app import crud

# 🔥 导入Loom核心类型用于自定义Executor
from loom.core.agent_executor import AgentExecutor
from loom.core.events import AgentEvent as LoomAgentEvent, AgentEventType
from loom.core.types import Message, ToolResult
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from .quality_scorer import (
    EnhancedQualityScorer, QualityScorerConfig, QualityScore,
    create_quality_scorer
)
from .config.stage_config import StageConfigManager, get_stage_config_manager
from .tools import (
    create_schema_discovery_tool,
    create_schema_retrieval_tool,
    create_schema_cache_tool,
    create_sql_generator_tool,
    create_sql_validator_tool,
    create_sql_column_checker_tool,
    create_sql_auto_fixer_tool,
    create_sql_executor_tool,
    create_data_sampler_tool,
    create_data_analyzer_tool,
    create_time_window_tool,
    create_chart_generator_tool,
    create_chart_analyzer_tool
)
from .tool_result_formatter import format_tool_result, FormattedToolResult

logger = logging.getLogger(__name__)


class ContextAwareAgentExecutor(AgentExecutor):
    """
    🔥 上下文感知的Agent Executor
    
    重写递归消息准备逻辑，确保工具结果和历史消息能正确传递到下一轮递归中
    """
    
    def __init__(self, original_executor: AgentExecutor, context_retriever: Optional[SchemaContextRetriever] = None):
        # 复制原始executor的所有属性
        for attr_name in dir(original_executor):
            if not attr_name.startswith('_') and not callable(getattr(original_executor, attr_name)):
                setattr(self, attr_name, getattr(original_executor, attr_name))

        # 保存原始executor的引用
        self._original_executor = original_executor
        self._context_retriever = context_retriever

        # 复制所有方法
        for attr_name in dir(original_executor):
            if not attr_name.startswith('_') and callable(getattr(original_executor, attr_name)):
                if attr_name not in ['_prepare_recursive_messages']:  # 重写这个方法
                    setattr(self, attr_name, getattr(original_executor, attr_name))

    def _check_recursion_termination(
        self,
        turn_state: TurnState,
        tool_results: List[ToolResult],
        tt_context: Dict[str, Any]
    ) -> Optional[str]:
        """
        检查是否需要终止递归

        Returns:
            Optional[str]: 终止原因，None表示继续执行
        """
        current_turn = tt_context.get("turn_counter", turn_state.turn_counter)
        deep_recursion_threshold = 3
        max_recursion_threshold = 5

        # 检查工具调用历史，检测重复调用
        tool_call_history = getattr(turn_state, 'tool_call_history', [])
        if tool_call_history:
            tool_names = [getattr(call, 'tool_name', 'unknown') for call in tool_call_history]
            schema_discovery_count = tool_names.count('schema_discovery')

            # 如果schema_discovery被调用超过2次，强制终止
            if schema_discovery_count > 2:
                logger.warning(f"🚨 [ContextAwareExecutor] 检测到重复调用schema_discovery（{schema_discovery_count}次），强制终止")
                return "duplicate_tool_calls"

        # 检查最大递归次数
        if current_turn > max_recursion_threshold:
            logger.warning(f"🚨 [ContextAwareExecutor] 达到最大递归次数（第{current_turn}轮），强制终止循环")
            return "max_recursion"

        # 检查深度递归
        if current_turn > deep_recursion_threshold:
            logger.info(f"🔍 [ContextAwareExecutor] 检测到深度递归（第{current_turn}轮），调整上下文策略")
            return "deep_recursion"

        return None

    def _build_termination_message(self, reason: str) -> Message:
        """
        构建递归终止消息

        Args:
            reason: 终止原因 (duplicate_tool_calls, max_recursion, deep_recursion)
        """
        if reason == "duplicate_tool_calls":
            content = """# 重复工具调用检测

⚠️ 检测到重复调用schema_discovery工具，系统强制终止！

请立即生成SQL查询，不要再调用任何工具：

```json
{
  "reasoning": "已多次调用schema_discovery，现在生成SQL",
  "action": "finish",
  "content": "SELECT COUNT(*) FROM ods_refund WHERE status = '退货成功'"
}
```

不要再调用任何工具！"""

        elif reason == "max_recursion":
            content = """# 紧急终止指令

⚠️ 检测到无限循环，系统强制终止！

请立即生成一个简单的SQL查询，不要继续调用工具：

```json
{
  "reasoning": "系统检测到循环，强制生成SQL",
  "action": "finish",
  "content": "SELECT COUNT(*) FROM ods_refund WHERE status = '退货成功'"
}
```

不要再调用任何工具！"""

        else:  # deep_recursion - 这个不是完全终止，只是警告
            content = f"""# 循环检测警告

⚠️ 检测到深度递归，请立即生成SQL，不要再调用工具！

如果已经获取了表结构信息，请直接生成SQL：
```json
{{
  "reasoning": "已获取表结构，生成SQL查询",
  "action": "finish",
  "content": "SELECT COUNT(*) FROM ods_refund WHERE status = '退货成功'"
}}
```

不要再调用 schema_discovery 或其他工具！"""

        return Message(role="system", content=content)

    def _prepare_history_messages(
        self,
        turn_state: TurnState,
        priority_hints: Dict[str, str],
        is_deep_recursion: bool
    ) -> List[Message]:
        """
        准备历史消息（支持智能截断）

        Args:
            turn_state: 回合状态
            priority_hints: 优先级提示
            is_deep_recursion: 是否深度递归

        Returns:
            历史消息列表
        """
        history_messages = []

        # 如果历史优先级为LOW，跳过获取
        if priority_hints.get("history", "MEDIUM") == "LOW":
            logger.info(f"📚 [ContextAwareExecutor] 历史优先级为LOW，跳过获取")
            return []

        # 从Memory中获取历史消息
        if self.memory:
            try:
                # 同步调用get_messages（因为这是同步方法）
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，使用run_in_executor
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.memory.get_messages())
                        history_messages = future.result()
                else:
                    history_messages = asyncio.run(self.memory.get_messages())
            except Exception as e:
                logger.warning(f"⚠️ [ContextAwareExecutor] 获取历史消息失败: {e}")
                history_messages = []

        # 根据优先级和深度调整历史消息数量
        if is_deep_recursion:
            max_history = 3  # 深度递归时只保留最近3条
        elif priority_hints.get("history") == "HIGH":
            max_history = 15  # 高优先级时保留更多历史
        else:
            max_history = 10  # 默认保留10条

        if history_messages:
            recent_history = history_messages[-max_history:]
            logger.info(f"📚 [ContextAwareExecutor] 从Memory获取到 {len(history_messages)} 条历史消息，保留 {len(recent_history)} 条")
            return recent_history
        else:
            logger.info(f"📚 [ContextAwareExecutor] 未获取到历史消息")
            return []

    def _prepare_tool_messages(self, tool_results: List[ToolResult]) -> Tuple[List[Message], List[FormattedToolResult]]:
        """
        准备工具结果消息

        Args:
            tool_results: 工具执行结果列表

        Returns:
            Tuple[工具消息列表, 格式化结果列表]
        """
        tool_messages = []
        formatted_results: List[FormattedToolResult] = []

        for result in tool_results:
            formatted = format_tool_result(result)
            formatted_results.append(formatted)
            tool_msg = Message(
                role="tool",
                content=formatted.message,
                tool_call_id=result.tool_call_id,
            )
            tool_messages.append(tool_msg)

        logger.info(f"🔧 [ContextAwareExecutor] 准备了 {len(tool_messages)} 条工具结果消息")

        return tool_messages, formatted_results
    
    def _prepare_recursive_messages(
        self,
        messages: List[Message],
        tool_results: List[ToolResult],
        turn_state: TurnState,
        context: ExecutionContext,
    ) -> List[Message]:
        """
        🔥 重写递归消息准备逻辑 - 增强 TT 上下文管理（已优化拆分）

        确保工具结果和历史消息能正确传递到下一轮递归中
        支持深度感知的上下文优先级调整和智能截断
        """
        # 从 ExecutionContext metadata 中提取 TT 上下文信息
        tt_context = context.metadata.get("tt", {}) if context.metadata else {}
        current_turn = tt_context.get("turn_counter", turn_state.turn_counter)
        priority_hints = tt_context.get("priority_hints", {})
        task_type = tt_context.get("task_type", "general")
        complexity = tt_context.get("complexity", "medium")

        logger.info(f"🔄 [ContextAwareExecutor] 准备递归消息（第{current_turn}轮）")
        logger.info(f"   任务类型: {task_type}, 复杂度: {complexity}")
        logger.info(f"   优先级提示: {priority_hints}")

        # 1. 检查是否需要终止递归
        termination_reason = self._check_recursion_termination(turn_state, tool_results, tt_context)

        # 处理深度递归（特殊情况：不完全终止，只是调整策略）
        is_deep_recursion = termination_reason == "deep_recursion"
        if is_deep_recursion:
            # 深度递归时，调整优先级
            priority_hints = {
                "base_instructions": "CRITICAL",
                "tool_definitions": "HIGH",
                "examples": "LOW",
                "history": "LOW"
            }
            # 添加警告消息
            warning_message = self._build_termination_message("deep_recursion")
            messages = [warning_message] + messages
        elif termination_reason:
            # 其他终止原因：直接返回终止消息
            return [self._build_termination_message(termination_reason)]

        # 2. 准备历史消息（支持智能截断）
        history_messages = self._prepare_history_messages(
            turn_state, priority_hints, is_deep_recursion
        )

        # 3. 准备工具结果消息
        tool_messages, formatted_results = self._prepare_tool_messages(tool_results)

        # 4. 生成智能指导消息
        guidance_message = self._generate_context_aware_guidance(
            messages, formatted_results, turn_state, history_messages,
            task_type=task_type, complexity=complexity, is_deep_recursion=is_deep_recursion
        )

        # 5. 组装完整的递归消息
        recursive_messages = []
        recursive_messages.extend(history_messages)  # 历史消息
        recursive_messages.extend(messages)  # 当前轮消息
        recursive_messages.extend(tool_messages)  # 工具结果消息
        recursive_messages.append(Message(role="user", content=guidance_message))  # 指导消息

        # 6. 上下文大小监控和日志记录
        total_messages = len(recursive_messages)
        total_chars = sum(len(msg.content) for msg in recursive_messages if hasattr(msg, 'content'))
        estimated_tokens = total_chars // 4  # 粗略估算：4字符≈1token

        logger.info(f"✅ [ContextAwareExecutor] 递归消息准备完成")
        logger.info(f"   总消息数: {total_messages}")
        logger.info(f"   总字符数: {total_chars}")
        logger.info(f"   估算Token数: {estimated_tokens}")
        logger.info(f"   深度递归模式: {'是' if is_deep_recursion else '否'}")

        # 如果上下文过大，记录警告
        if estimated_tokens > 8000:  # 假设模型上下文限制为8K
            logger.warning(f"⚠️ [ContextAwareExecutor] 上下文可能过大（{estimated_tokens} tokens），建议优化")

        return recursive_messages
    
    def _generate_context_aware_guidance(
        self,
        messages: List[Message],
        formatted_results: List[FormattedToolResult],
        turn_state: TurnState,
        history_messages: List[Message],
        task_type: str = "general",
        complexity: str = "medium",
        is_deep_recursion: bool = False
    ) -> str:
        """
        生成上下文感知的递归指导消息 - 增强任务类型和深度感知
        """
        # 分析工具结果
        has_schema_data = False
        has_query_data = False
        tool_summaries: List[str] = []
        tool_names_called = set()
        schema_info: Optional[FormattedToolResult] = None
        
        for formatted in formatted_results:
            tool_names_called.add(formatted.tool_name)
            tool_summaries.append(f"{formatted.tool_name}: {formatted.message}")
            if formatted.tool_name == "schema_discovery":
                schema_info = formatted
                tables_count = formatted.structured_summary.get("tables_count", 0)
                has_schema_data = tables_count > 0
            if formatted.tool_name in {"sql_generator", "sql_validator", "sql_executor"}:
                has_query_data = True
        
        # 🔥 关键修复：添加工具调用历史检测和明确指导
        guidance_parts = [f"第{turn_state.turn_counter}轮递归执行"]
        
        # 分析已调用的工具，提供明确的下一步指导
        if schema_info:
            tables_count = schema_info.structured_summary.get("tables_count", 0)
            preview = schema_info.structured_summary.get("tables_preview", []) or []
            preview_text = "、".join(preview[:3]) if preview else "暂无示例表"

            if schema_info.duplicate_call:
                guidance_parts.append("⚠️ schema_discovery 已在先前步骤完成，本轮复用了缓存结果")
            else:
                guidance_parts.append(f"✅ schema_discovery 完成，发现 {tables_count} 张表（如：{preview_text}）")

            if schema_info.next_actions:
                guidance_parts.append(f"📋 推荐下一步：{'；'.join(schema_info.next_actions)}")
        else:
            guidance_parts.append("📋 尚未获取数据库结构，请先调用 schema_discovery 工具")

        if "schema_retrieval" in tool_names_called:
            guidance_parts.append("✅ schema_retrieval 已提供列级信息，接下来使用 sql_generator 生成 SQL")
        if "sql_generator" in tool_names_called and "sql_validator" not in tool_names_called:
            guidance_parts.append("📋 下一步：调用 sql_validator 工具验证生成的 SQL")
        if "sql_validator" in tool_names_called:
            guidance_parts.append("✅ SQL 已通过验证，如无问题可以整理最终答案或执行后续操作")
        if schema_info and schema_info.duplicate_call:
            guidance_parts.append("🚫 请勿再次调用 schema_discovery，直接执行上一步建议的工具")
        
        # 根据任务类型添加额外指导
        if task_type == "sql_generation":
            guidance_parts.append("🎯 任务目标：生成准确的 SQL 查询")
            if has_schema_data:
                guidance_parts.append("✅ 表结构信息已获取")
            if has_query_data:
                guidance_parts.append("✅ 查询已执行")
        elif task_type == "chart_generation":
            guidance_parts.append("🎯 任务目标：生成图表")
            if has_query_data:
                guidance_parts.append("✅ 查询数据已获取")
        elif task_type == "completion":
            guidance_parts.append("🎯 任务目标：完成文档生成")
        
        # 添加复杂度提示
        if complexity == "high":
            guidance_parts.append("⚠️ 复杂任务，需要仔细分析")
        elif complexity == "low":
            guidance_parts.append("✅ 简单任务，可以快速处理")
        
        # 深度递归时的特殊处理
        if is_deep_recursion:
            guidance_parts.append("⚠️ 深度递归模式，请保持简洁，避免重复调用相同工具")
            # 只显示关键的工具结果
            if tool_summaries:
                key_summaries = [s for s in tool_summaries if any(keyword in s.lower() for keyword in ["schema", "table", "sql"])]
                if key_summaries:
                    guidance_parts.append(f"🔧 关键工具结果: {'; '.join(key_summaries[:2])}")
        else:
            # 正常递归时显示所有工具结果
            if tool_summaries:
                guidance_parts.append(f"🔧 工具结果: {'; '.join(tool_summaries)}")
        
        guidance = "。".join(guidance_parts) + "。请基于以上信息继续执行。"
        
        return guidance


# 🔥 工具实例缓存管理器
class ToolInstanceCache:
    """工具实例缓存管理器，避免重复创建工具"""
    
    def __init__(self):
        self._cache: Dict[str, BaseTool] = {}
        self._cache_keys: Dict[str, str] = {}
    
    def _generate_cache_key(self, tool_name: str, connection_config: Optional[Dict] = None) -> str:
        """生成工具缓存键"""
        # 🔥 优化：只有真正需要connection_config的工具才区分配置
        # 必须与 _create_tools_from_config 中的 tools_requiring_connection 保持一致
        tools_requiring_connection = {
            "schema_discovery",
            "schema_retrieval",
            "sql_executor",
            "sql_validator"  # 🔥 关键修复：添加 sql_validator
        }

        if connection_config and tool_name in tools_requiring_connection:
            # 基于连接配置生成键 - 使用实际的字段名
            host = connection_config.get('fe_hosts', [''])[0] if connection_config.get('fe_hosts') else ''
            port = connection_config.get('http_port', '')
            database = connection_config.get('name', '')
            config_key = f"{host}:{port}:{database}"
            return f"{tool_name}:{config_key}"
        else:
            # 🔥 对于不需要connection_config的工具，统一使用default键
            return f"{tool_name}:default"
    
    def get_tool(self, tool_name: str, connection_config: Optional[Dict] = None) -> Optional[BaseTool]:
        """获取缓存的工具实例"""
        cache_key = self._generate_cache_key(tool_name, connection_config)
        return self._cache.get(cache_key)
    
    def set_tool(self, tool_name: str, tool: BaseTool, connection_config: Optional[Dict] = None):
        """缓存工具实例"""
        cache_key = self._generate_cache_key(tool_name, connection_config)
        self._cache[cache_key] = tool
        self._cache_keys[tool_name] = cache_key
        logger.debug(f"🔧 [ToolCache] 缓存工具: {tool_name} -> {cache_key}")
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        self._cache_keys.clear()
        logger.info("🧹 [ToolCache] 清空工具缓存")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        # 统计唯一的工具名
        unique_tool_names = set()
        for cache_key in self._cache.keys():
            tool_name = cache_key.split(':')[0]  # 提取工具名
            unique_tool_names.add(tool_name)
        
        return {
            "cached_tools": len(self._cache),
            "unique_tool_names": len(unique_tool_names),
            "tool_names": list(unique_tool_names),
            "memory_usage": f"{len(self._cache)} tools"
        }


# 全局工具缓存实例
_tool_cache = ToolInstanceCache()


def _create_tools_from_config(container: Any, config: AgentConfig) -> List[BaseTool]:
    """
    根据配置自动创建工具实例

    Args:
        container: 服务容器
        config: Agent 配置

    Returns:
        工具实例列表
    """
    tools = []
    enabled_tools = config.tools.enabled_tools if hasattr(config.tools, 'enabled_tools') else []

    # 🔥 从container中读取临时存储的connection_config
    connection_config = getattr(container, '_temp_connection_config', None)

    # 🔧 调试日志
    logger.info(f"🔧 [ToolRegistry] connection_config 可用: {connection_config is not None}")
    if connection_config:
        logger.info(f"🔧 [ToolRegistry] connection_config keys: {list(connection_config.keys())[:5]}")

    # 工具名称到创建函数的映射
    tool_factory_map = {
        "schema_discovery": create_schema_discovery_tool,
        "schema_retrieval": create_schema_retrieval_tool,
        "schema_cache": create_schema_cache_tool,
        "sql_generator": create_sql_generator_tool,
        "sql_validator": create_sql_validator_tool,
        "sql_column_checker": create_sql_column_checker_tool,
        "sql_auto_fixer": create_sql_auto_fixer_tool,
        "sql_executor": create_sql_executor_tool,
        "data_sampler": create_data_sampler_tool,
        "data_analyzer": create_data_analyzer_tool,
        "time_window": create_time_window_tool,
        "chart_generator": create_chart_generator_tool,
        "chart_analyzer": create_chart_analyzer_tool,
    }

    # 需要connection_config的工具列表
    tools_requiring_connection = {
        "schema_discovery",
        "schema_retrieval", 
        "sql_executor",
        "sql_validator"  # 🔥 关键修复：添加 sql_validator 到需要 connection_config 的工具列表
    }

    # 🔥 使用缓存机制创建工具
    for tool_name in enabled_tools:
        # 1. 检查缓存
        cached_tool = _tool_cache.get_tool(tool_name, connection_config)
        if cached_tool:
            tools.append(cached_tool)
            logger.info(f"♻️ [ToolRegistry] 使用缓存工具: {tool_name}")
            continue
        
        # 2. 创建新工具
        factory_func = tool_factory_map.get(tool_name)
        if factory_func:
            try:
                # 🔥 如果是需要connection_config的工具，且connection_config可用，则传递它
                if tool_name in tools_requiring_connection and connection_config:
                    tool = factory_func(container, connection_config=connection_config)
                    logger.info(f"✅ [ToolRegistry] 成功创建工具（带connection_config）: {tool_name}")
                else:
                    tool = factory_func(container)
                    logger.info(f"✅ [ToolRegistry] 成功创建工具: {tool_name}")

                # 3. 缓存工具实例
                _tool_cache.set_tool(tool_name, tool, connection_config)
                tools.append(tool)
            except Exception as e:
                logger.warning(f"⚠️ [ToolRegistry] 创建工具失败: {tool_name}, 错误: {e}")
                import traceback
                logger.warning(traceback.format_exc())
        else:
            logger.warning(f"⚠️ [ToolRegistry] 未知工具: {tool_name}")

    # 记录缓存统计
    cache_stats = _tool_cache.get_cache_stats()
    logger.info(f"📦 [ToolRegistry] 共创建 {len(tools)} 个工具，缓存统计: {cache_stats}")
    return tools


def _extract_response_metrics(response_payload: Any) -> Tuple[float, int]:
    """提取质量评分和迭代次数，兼容字典和AgentResponse对象"""
    if isinstance(response_payload, AgentResponse):
        return (
            response_payload.quality_score or 0.0,
            response_payload.iterations_used or 0,
        )
    if isinstance(response_payload, dict):
        quality = response_payload.get("quality_score", 0.0) or 0.0
        iterations = response_payload.get("iterations_used", 0) or 0
        return (float(quality), int(iterations))
    return 0.0, 0


class ActionType(Enum):
    """下一步行动类型"""
    CONTINUE = "continue"  # 继续当前策略
    RETRY = "retry"  # 重试当前步骤
    FALLBACK = "fallback"  # 使用备用方案
    CHANGE_STRATEGY = "change_strategy"  # 改变策略
    EXPLORE = "explore"  # 探索新方法
    TERMINATE = "terminate"  # 终止执行


@dataclass
class IterationStep:
    """单次迭代步骤记录"""
    iteration: int
    timestamp: float
    tool_calls: List[str] = field(default_factory=list)
    has_error: bool = False
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    quality_score: Optional[float] = None
    result_summary: Optional[str] = None
    tokens_used: int = 0

    @property
    def is_successful(self) -> bool:
        """是否成功"""
        return not self.has_error and self.quality_score and self.quality_score > 0.7


@dataclass
class ActionPlan:
    """行动计划"""
    type: ActionType
    reason: str
    suggestion: str = ""
    priority: int = 1  # 1-5, 5最高

    def __str__(self):
        return f"[{self.type.value}] {self.reason} - {self.suggestion}"


class AdaptiveIterationTracker:
    """
    自适应迭代跟踪器 - 动态调整策略

    功能：
    - 跟踪每次迭代的详细信息
    - 分析错误模式和质量趋势
    - 基于历史建议下一步行动
    - 检测循环和卡顿
    """

    def __init__(self, goal: str, max_iterations: int = 10):
        self.goal = goal
        self.max_iterations = max_iterations

        # 历史记录
        self.iteration_history: List[IterationStep] = []
        self.quality_trend: List[float] = []
        self.error_count = 0
        self.consecutive_errors = 0

        # 工具调用统计
        self.tool_call_count = 0
        self.tool_call_frequency: Dict[str, int] = {}

        # 目标进度
        self.goal_progress: float = 0.0

        # 状态
        self.is_stuck = False
        self.last_tool_call_time = 0

    def record_step(
        self,
        iteration: int,
        tool_calls: List[str],
        result: Any = None,
        error: Optional[Exception] = None,
        quality_score: Optional[float] = None
    ):
        """
        记录一次迭代步骤

        Args:
            iteration: 迭代次数
            tool_calls: 本轮调用的工具列表
            result: 执行结果
            error: 错误（如果有）
            quality_score: 质量评分
        """
        # 创建步骤记录
        step = IterationStep(
            iteration=iteration,
            timestamp=time.time(),
            tool_calls=tool_calls,
            has_error=error is not None,
            error_message=str(error) if error else None,
            error_type=type(error).__name__ if error else None,
            quality_score=quality_score,
            result_summary=str(result)[:200] if result else None
        )

        # 添加到历史
        self.iteration_history.append(step)

        # 更新统计
        if error:
            self.error_count += 1
            self.consecutive_errors += 1
        else:
            self.consecutive_errors = 0

        # 更新工具调用统计
        for tool in tool_calls:
            self.tool_call_count += 1
            self.tool_call_frequency[tool] = self.tool_call_frequency.get(tool, 0) + 1

        # 更新质量趋势
        if quality_score is not None:
            self.quality_trend.append(quality_score)
            self._update_goal_progress(quality_score)

        # 检测是否卡住
        self._check_if_stuck()

        logger.info(f"📊 [AdaptiveTracker] 记录第{iteration}轮: "
                   f"工具={len(tool_calls)}, 错误={step.has_error}, 质量={quality_score:.2f if quality_score else 'N/A'}")

    def on_tool_call(self, tool_name: str):
        """工具调用时调用"""
        self.last_tool_call_time = time.time()
        self.tool_call_frequency[tool_name] = self.tool_call_frequency.get(tool_name, 0) + 1

    def suggest_next_action(self) -> ActionPlan:
        """
        基于历史建议下一步行动

        Returns:
            ActionPlan: 行动计划
        """
        # 1. 检查是否应该终止
        if len(self.iteration_history) >= self.max_iterations:
            return ActionPlan(
                type=ActionType.TERMINATE,
                reason="达到最大迭代次数",
                suggestion=f"已执行{len(self.iteration_history)}轮，建议终止",
                priority=5
            )

        # 2. 检查是否卡住
        if self.is_stuck:
            return ActionPlan(
                type=ActionType.FALLBACK,
                reason="检测到重复循环",
                suggestion="建议切换到备用策略或简化任务",
                priority=5
            )

        # 3. 检查连续错误
        if self.consecutive_errors >= 2:
            return ActionPlan(
                type=ActionType.CHANGE_STRATEGY,
                reason=f"连续{self.consecutive_errors}次错误",
                suggestion="建议改变当前方法，尝试不同的工具组合",
                priority=4
            )

        # 4. 检查质量趋势
        if len(self.quality_trend) >= 3:
            recent_trend = self._analyze_quality_trend()
            if recent_trend == "improving":
                return ActionPlan(
                    type=ActionType.CONTINUE,
                    reason="质量持续提升",
                    suggestion="继续当前策略",
                    priority=2
                )
            elif recent_trend == "declining":
                return ActionPlan(
                    type=ActionType.CHANGE_STRATEGY,
                    reason="质量下降",
                    suggestion="建议调整方法或回退到之前的状态",
                    priority=3
                )

        # 5. 检查单个工具调用频率
        if self._has_tool_overuse():
            overused_tool = max(self.tool_call_frequency, key=self.tool_call_frequency.get)
            return ActionPlan(
                type=ActionType.CHANGE_STRATEGY,
                reason=f"工具 {overused_tool} 被过度使用",
                suggestion=f"避免重复调用 {overused_tool}，尝试其他工具",
                priority=4
            )

        # 6. 默认：探索
        return ActionPlan(
            type=ActionType.EXPLORE,
            reason="正常执行中",
            suggestion="继续探索，使用合适的工具完成任务",
            priority=1
        )

    def estimate_iteration_count(self) -> int:
        """估算迭代次数（保持兼容性）"""
        return len(self.iteration_history) or max(1, self.tool_call_count // 2)

    def reset(self):
        """重置跟踪器"""
        self.iteration_history.clear()
        self.quality_trend.clear()
        self.error_count = 0
        self.consecutive_errors = 0
        self.tool_call_count = 0
        self.tool_call_frequency.clear()
        self.goal_progress = 0.0
        self.is_stuck = False

    def get_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            "total_iterations": len(self.iteration_history),
            "total_tool_calls": self.tool_call_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / len(self.iteration_history) if self.iteration_history else 0,
            "goal_progress": self.goal_progress,
            "quality_trend": self._analyze_quality_trend(),
            "most_used_tools": sorted(
                self.tool_call_frequency.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3],
            "is_stuck": self.is_stuck
        }

    # ===== 私有方法 =====

    def _update_goal_progress(self, quality_score: float):
        """更新目标进度"""
        # 基于质量评分和迭代次数综合计算
        iteration_progress = len(self.iteration_history) / self.max_iterations
        quality_weight = 0.7
        iteration_weight = 0.3

        self.goal_progress = min(1.0,
            quality_weight * quality_score + iteration_weight * iteration_progress
        )

    def _check_if_stuck(self):
        """检测是否卡住（循环）"""
        if len(self.iteration_history) < 3:
            return

        # 检查最近3次迭代是否有重复的工具调用模式
        recent_steps = self.iteration_history[-3:]
        tool_patterns = [set(step.tool_calls) for step in recent_steps]

        # 如果所有模式都相同，认为卡住了
        if len(set(map(frozenset, tool_patterns))) == 1:
            self.is_stuck = True
            logger.warning("🚨 [AdaptiveTracker] 检测到循环：最近3次迭代使用相同工具")

    def _analyze_quality_trend(self) -> str:
        """分析质量趋势"""
        if len(self.quality_trend) < 2:
            return "insufficient_data"

        recent = self.quality_trend[-3:]

        # 检查是否持续提升
        if all(recent[i] >= recent[i-1] for i in range(1, len(recent))):
            return "improving"

        # 检查是否持续下降
        if all(recent[i] <= recent[i-1] for i in range(1, len(recent))):
            return "declining"

        # 检查是否稳定
        variance = sum((x - sum(recent)/len(recent))**2 for x in recent) / len(recent)
        if variance < 0.01:
            return "stable"

        return "fluctuating"

    def _has_tool_overuse(self) -> bool:
        """检查是否有工具被过度使用"""
        if not self.tool_call_frequency:
            return False

        max_calls = max(self.tool_call_frequency.values())
        total_calls = sum(self.tool_call_frequency.values())

        # 如果某个工具占比超过60%，认为过度使用
        return max_calls / total_calls > 0.6 and max_calls > 3


class AdaptivePromptGenerator:
    """
    自适应提示词生成器 - 根据执行状态动态生成提示

    功能：
    - 根据目标和当前进度生成提示
    - 基于错误历史提供修复建议
    - 根据质量趋势调整策略
    - 动态调整提示内容和优先级

    集成 prompts 模块：
    - SystemPromptBuilder: 系统级提示词
    - StagePromptManager: 阶段感知提示
    - PromptTemplateManager: 模板化内容
    - ContextFormatter: 上下文格式化
    """

    def __init__(
        self,
        goal: str,
        tracker: AdaptiveIterationTracker,
        stage: Optional[ExecutionStage] = None,
        complexity: Optional[TaskComplexity] = None,
        context: Optional[ContextInfo] = None,
        base_system_prompt: Optional[str] = None
    ):
        """
        Args:
            goal: 任务目标描述
            tracker: 自适应迭代跟踪器
            stage: 当前执行阶段（可选）
            complexity: 任务复杂度（可选）
            context: 上下文信息（可选）
            base_system_prompt: 自定义系统提示（可选，覆盖默认）
        """
        self.goal = goal
        self.tracker = tracker
        self.stage = stage
        self.complexity = complexity
        self.context = context

        # ✅ 导入并初始化 prompts 组件
        from .prompts import (
            SystemPromptBuilder,
            StagePromptManager,
            PromptTemplateManager,
            ContextFormatter
        )

        self._system_builder = SystemPromptBuilder()
        self._stage_manager = StagePromptManager()
        self._template_manager = PromptTemplateManager()
        self._context_formatter = ContextFormatter()

        # 如果提供了自定义系统提示，使用它；否则使用 SystemPromptBuilder 生成
        if base_system_prompt:
            self.base_system_prompt = base_system_prompt
        else:
            self.base_system_prompt = self._system_builder.build_system_prompt(
                stage=stage,
                complexity=complexity
            )

    def generate_next_prompt(
        self,
        last_error: Optional[Exception] = None,
        last_result: Optional[str] = None
    ) -> str:
        """
        基于当前状态生成下一步提示

        Args:
            last_error: 上一步的错误（如果有）
            last_result: 上一步的结果

        Returns:
            生成的提示词
        """
        prompt_parts = []

        # 1. 基础系统提示（如果有）
        if self.base_system_prompt:
            prompt_parts.append(self.base_system_prompt)

        # 2. 目标和进度提醒
        progress = self.tracker.goal_progress
        prompt_parts.append(self._generate_goal_section(progress))

        # 3. 当前状态分析
        if last_error:
            prompt_parts.append(self._generate_error_guidance(last_error))
        elif last_result:
            prompt_parts.append(self._generate_progress_feedback(last_result))

        # 4. 下一步行动建议
        action_plan = self.tracker.suggest_next_action()
        prompt_parts.append(self._generate_action_guidance(action_plan))

        # 5. 动态约束条件
        constraints = self._generate_dynamic_constraints()
        if constraints:
            prompt_parts.append(constraints)

        # 6. 执行摘要（如果有历史）
        if self.tracker.iteration_history:
            prompt_parts.append(self._generate_execution_summary())

        return "\n\n".join(prompt_parts)

    def generate_initial_prompt(self, task_description: str) -> str:
        """
        生成初始提示词

        Args:
            task_description: 任务描述

        Returns:
            初始提示词
        """
        prompt_parts = []

        # 1. 系统提示
        if self.base_system_prompt:
            prompt_parts.append(self.base_system_prompt)

        # 2. 任务目标
        prompt_parts.append(f"# 任务目标\n\n{self.goal}")

        # 3. 任务描述
        prompt_parts.append(f"# 任务描述\n\n{task_description}")

        # 4. 初始指导
        prompt_parts.append(self._generate_initial_guidance())

        return "\n\n".join(prompt_parts)

    # ===== 私有方法：生成各部分提示 =====

    def _generate_goal_section(self, progress: float) -> str:
        """生成目标和进度部分"""
        progress_bar = "█" * int(progress * 10) + "░" * (10 - int(progress * 10))
        progress_emoji = "🎯" if progress < 0.3 else "📈" if progress < 0.7 else "✨"

        return f"""# 目标追踪

{progress_emoji} **当前目标**: {self.goal}
**进度**: [{progress_bar}] {progress:.0%}
**迭代**: 第 {len(self.tracker.iteration_history) + 1} / {self.tracker.max_iterations} 轮"""

    def _generate_error_guidance(self, error: Exception) -> str:
        """生成错误指导"""
        error_type = type(error).__name__
        error_msg = str(error)

        # 分析错误模式
        if self.tracker.consecutive_errors > 1:
            pattern = f"⚠️ **警告**: 已连续{self.tracker.consecutive_errors}次错误，建议改变策略"
        else:
            pattern = ""

        # 根据错误类型提供建议
        suggestions = self._get_error_fix_suggestions(error_type, error_msg)

        return f"""# ⚠️ 上一步执行失败

**错误类型**: {error_type}
**错误信息**: {error_msg}
{pattern}

## 建议修复方案

{suggestions}"""

    def _generate_progress_feedback(self, result: str) -> str:
        """生成进度反馈"""
        # 分析质量趋势
        trend = self.tracker._analyze_quality_trend()
        trend_emoji = {
            "improving": "📈",
            "stable": "➡️",
            "declining": "📉",
            "fluctuating": "〰️",
            "insufficient_data": "❓"
        }.get(trend, "❓")

        latest_quality = self.tracker.quality_trend[-1] if self.tracker.quality_trend else 0.0

        return f"""# ✅ 上一步执行成功

**质量评分**: {latest_quality:.2f}
**趋势**: {trend_emoji} {trend}

**结果摘要**: {result[:150]}{"..." if len(result) > 150 else ""}"""

    def _generate_action_guidance(self, action_plan: ActionPlan) -> str:
        """生成行动指导"""
        priority_emoji = "🔴" if action_plan.priority >= 4 else "🟡" if action_plan.priority >= 2 else "🟢"

        return f"""# 下一步行动计划

{priority_emoji} **策略**: {action_plan.type.value}
**原因**: {action_plan.reason}
**建议**: {action_plan.suggestion or "继续执行任务"}"""

    def _generate_dynamic_constraints(self) -> str:
        """生成动态约束"""
        constraints = []

        # 基于工具使用频率的约束
        if self.tracker.tool_call_frequency:
            overused_tools = [
                tool for tool, count in self.tracker.tool_call_frequency.items()
                if count > 3
            ]
            if overused_tools:
                constraints.append(
                    f"- ⚠️ 避免过度使用以下工具: {', '.join(overused_tools)}"
                )

        # 基于错误历史的约束
        if self.tracker.error_count > 0:
            constraints.append(
                f"- 💡 已发生 {self.tracker.error_count} 次错误，请仔细验证每个步骤"
            )

        # 基于迭代次数的约束
        remaining = self.tracker.max_iterations - len(self.tracker.iteration_history)
        if remaining <= 2:
            constraints.append(
                f"- ⏰ 剩余迭代次数: {remaining}，请尽快完成任务"
            )

        if not constraints:
            return ""

        return f"""# 执行约束

{chr(10).join(constraints)}"""

    def _generate_execution_summary(self) -> str:
        """生成执行摘要"""
        summary = self.tracker.get_summary()

        most_used = ", ".join([f"{tool}({count})" for tool, count in summary["most_used_tools"][:3]])

        return f"""# 执行摘要

- **总迭代**: {summary['total_iterations']}
- **工具调用**: {summary['total_tool_calls']} 次
- **错误率**: {summary['error_rate']:.1%}
- **常用工具**: {most_used}
- **质量趋势**: {summary['quality_trend']}"""

    def _generate_initial_guidance(self) -> str:
        """
        生成初始指导

        ✅ 集成 StagePromptManager，支持阶段感知的初始指导

        Returns:
            初始指导文本
        """
        # 如果有指定阶段，使用阶段特定的指导
        if self.stage:
            try:
                stage_prompt = self._stage_manager.get_stage_prompt(
                    stage=self.stage,
                    context=self.context,
                    complexity=self.complexity
                )
                return f"""# 执行指导

## 当前阶段: {self.stage.value}

{stage_prompt}

## 通用原则

1. **理解需求**: 仔细分析任务目标和描述
2. **制定计划**: 确定需要使用的工具和执行顺序
3. **逐步执行**: 使用合适的工具，验证每一步的结果
4. **持续优化**: 根据反馈调整策略，向目标靠拢
5. **质量验证**: 确保最终结果符合要求

**重要提示**:
- 每次只执行一个关键步骤
- 遇到错误时，分析原因并调整方法
- 使用工具前先确认其适用性
- 保持输出的准确性和完整性"""
            except Exception as e:
                logger.warning(f"⚠️ 获取阶段提示失败: {e}，使用默认指导")

        # 默认通用指导
        return """# 执行指导

请按照以下步骤完成任务：

1. **理解需求**: 仔细分析任务目标和描述
2. **制定计划**: 确定需要使用的工具和执行顺序
3. **逐步执行**: 使用合适的工具，验证每一步的结果
4. **持续优化**: 根据反馈调整策略，向目标靠拢
5. **质量验证**: 确保最终结果符合要求

**重要提示**:
- 每次只执行一个关键步骤
- 遇到错误时，分析原因并调整方法
- 使用工具前先确认其适用性
- 保持输出的准确性和完整性"""

    # ===== 类常量：错误修复建议映射 =====
    ERROR_FIX_SUGGESTIONS = {
        "TableNotFoundError": """
- 检查表名是否正确（可能需要使用 schema_discovery 工具）
- 确认数据库连接配置是否正确
- 使用上下文中提供的表名，避免猜测""",

        "ColumnNotFoundError": """
- 使用 schema_retrieval 工具获取表的列信息
- 检查列名拼写是否正确
- 确认该列是否存在于目标表中""",

        "SyntaxError": """
- 检查 SQL 语法是否符合 Doris 规范
- 使用 sql_validator 工具验证 SQL
- 参考系统提示中的 SQL 示例""",

        "ConnectionError": """
- 检查数据库连接配置
- 确认网络连接是否正常
- 稍后重试操作""",

        "TimeoutError": """
- 简化查询逻辑
- 减少数据量
- 优化查询性能""",

        "ValidationError": """
- 检查输入数据的格式和类型
- 确认所有必需字段都已提供
- 验证数据是否符合约束条件""",

        "ToolExecutionError": """
- 检查工具参数是否正确
- 确认工具的前置条件已满足
- 查看工具文档了解正确用法"""
    }

    DEFAULT_ERROR_SUGGESTION = """
- 仔细阅读错误信息，理解问题根源
- 检查上一步的操作是否正确
- 尝试使用不同的方法或工具
- 如果问题持续，考虑简化任务或使用备用方案"""

    def _get_error_fix_suggestions(self, error_type: str, error_msg: str) -> str:
        """
        根据错误类型提供修复建议

        ✅ 使用类常量替代硬编码字典，提高可维护性

        Args:
            error_type: 错误类型名称
            error_msg: 错误信息

        Returns:
            修复建议文本
        """
        # 查找匹配的错误类型
        for key, suggestion in self.ERROR_FIX_SUGGESTIONS.items():
            if key in error_type or key.lower() in error_msg.lower():
                return suggestion

        # 默认建议
        return self.DEFAULT_ERROR_SUGGESTION


class LoomAgentRuntime:
    """
    Loom Agent 运行时
    
    基于 Loom 0.0.3 的 TT 递归执行机制，提供自动迭代推理能力
    
    🔥 关键修复：确保工具结果在递归循环中正确传递到上下文中
    """

    def __init__(
        self,
        agent: Agent,
        tools: List[BaseTool],
        config: AgentConfig,
        context_retriever: Optional[SchemaContextRetriever] = None,
        container: Optional[Any] = None,
    ):
        """
        Args:
            agent: Loom Agent 实例
            tools: 工具列表
            config: Agent 配置
            context_retriever: 上下文检索器
            container: 服务容器（用于高级功能）
        """
        self._agent = agent
        self._tools = tools
        self._config = config
        self._context_retriever = context_retriever
        self.container = container  # 添加 container 属性

        # 执行状态
        self._current_state: Optional[ExecutionState] = None
        self._event_callbacks: List[Callable[[AgentEvent], None]] = []

        # 🔥 使用增强的自适应迭代跟踪器（待初始化，需要goal信息）
        self._iteration_tracker: Optional[AdaptiveIterationTracker] = None
        self._prompt_generator: Optional[AdaptivePromptGenerator] = None

        # 质量评分器
        self._quality_scorer = create_quality_scorer()

        # 设置工具调用回调
        self._setup_tool_call_tracking()

    @property
    def agent(self) -> Agent:
        """获取 Loom Agent 实例"""
        return self._agent

    @property
    def config(self) -> AgentConfig:
        """获取配置"""
        return self._config

    @property
    def tools(self) -> List[BaseTool]:
        """获取工具列表"""
        return self._tools

    @property
    def context_retriever(self) -> Optional[SchemaContextRetriever]:
        """获取上下文检索器"""
        return self._context_retriever

    async def execute_with_tt(
        self,
        request: AgentRequest,
        max_iterations: Optional[int] = None
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        使用 TT 递归执行 - 自动迭代推理
        
        这是核心方法，使用 Loom 0.0.3 的 tt 函数实现自动迭代
        
        Args:
            request: Agent 请求
            max_iterations: 最大迭代次数
            
        Yields:
            AgentEvent: 执行事件流
        """
        start_time = time.time()
        max_iterations = max_iterations or request.max_iterations

        logger.info(f"🚀 [LoomAgentRuntime] 开始 TT 递归执行")
        logger.info(f"   占位符: {request.placeholder[:100]}...")
        logger.info(f"   数据源ID: {request.data_source_id}")
        logger.info(f"   用户ID: {request.user_id}")
        logger.info(f"   最大迭代次数: {max_iterations}")

        # 🔥 初始化自适应跟踪器和提示词生成器
        goal = f"完成{request.stage.value}阶段任务: {request.placeholder[:50]}"
        self._iteration_tracker = AdaptiveIterationTracker(
            goal=goal,
            max_iterations=max_iterations
        )

        # ✅ 创建初始上下文（从请求中获取）
        initial_context = ContextInfo()
        if hasattr(request, 'context') and request.context:
            initial_context = request.context

        # ✅ 初始化自适应提示词生成器，传入 stage, complexity, context
        self._prompt_generator = AdaptivePromptGenerator(
            goal=goal,
            tracker=self._iteration_tracker,
            stage=request.stage,  # ✅ 传入阶段信息
            complexity=getattr(request, 'complexity', None),  # ✅ 传入复杂度
            context=initial_context,  # ✅ 传入上下文
            base_system_prompt=self._config.system_prompt  # 可选：覆盖默认系统提示
        )

        logger.info(f"🎯 [AdaptiveRuntime] 目标: {goal}")

        # 初始化执行状态
        self._current_state = ExecutionState(
            current_stage=request.stage,
            iteration_count=0,
            start_time=start_time,
            context=ContextInfo(),
            max_iterations=max_iterations,
            max_context_tokens=self._config.max_context_tokens
        )

        # 发送初始化事件
        init_event = AgentEvent(
            event_type="execution_started",
            stage=request.stage,
            data={
                "request": request,
                "max_iterations": max_iterations,
                "timestamp": start_time
            }
        )
        yield init_event
        await self._notify_callbacks(init_event)

        # 🔥 设置用户ID的 context variable，以便 LLM adapter 可以获取
        token = _CURRENT_USER_ID.set(request.user_id)

        try:
            # 🔥 核心：使用 Loom 的 Agent.run() 进行 TT 递归执行
            # Loom 0.0.3 的 Agent.run() 内部使用 tt 函数实现自动迭代

            # 构建初始 prompt
            initial_prompt = await self._build_initial_prompt(request)

            logger.info(f"📝 [LoomAgentRuntime] 初始 prompt 长度: {len(initial_prompt)} 字符")

            # 🔥 TT 递归执行 - 使用 execute() 获取事件流
            from loom.core.events import AgentEventType

            result = ""
            tool_call_count = 0

            async for event in self._agent.execute(initial_prompt):
                # 记录 LLM 开始
                if event.type == AgentEventType.LLM_START:
                    logger.info(f"🧠 [LoomAgentRuntime] LLM 开始生成（迭代 {self._current_state.iteration_count + 1}）")

                # 记录工具调用事件
                elif event.type == AgentEventType.LLM_TOOL_CALLS:
                    tool_count = event.metadata.get("tool_count", 0)
                    tool_names = event.metadata.get("tool_names", [])
                    tool_call_count += tool_count
                    logger.info(f"🔧 [LoomAgentRuntime] LLM 调用了 {tool_count} 个工具: {tool_names}")

                    # 更新迭代计数
                    if self._current_state:
                        self._current_state.iteration_count += 1

                # 工具执行进度
                elif event.type == AgentEventType.TOOL_PROGRESS:
                    tool_name = event.metadata.get("tool_name", "unknown")
                    status = event.metadata.get("status", "unknown")
                    logger.info(f"🔧 [LoomAgentRuntime] 工具 {tool_name}: {status}")

                # 工具执行结果
                elif event.type == AgentEventType.TOOL_RESULT:
                    logger.info(f"✅ [LoomAgentRuntime] 工具执行完成")

                # 🔥 递归事件
                elif event.type == AgentEventType.RECURSION:
                    logger.info(f"🔄 [LoomAgentRuntime] 开始递归（基于工具结果）")

                # 记录 LLM 输出增量
                elif event.type == AgentEventType.LLM_DELTA:
                    if event.content:
                        result += event.content

                # Agent 完成
                elif event.type == AgentEventType.AGENT_FINISH:
                    result = event.content or result
                    logger.info(f"✅ [LoomAgentRuntime] Agent 执行完成")
                    logger.info(f"📊 [LoomAgentRuntime] 总工具调用次数: {tool_call_count}")
                    logger.info(f"📊 [LoomAgentRuntime] 总迭代次数: {self._current_state.iteration_count}")
                    break

                # 达到最大迭代次数
                elif event.type == AgentEventType.MAX_ITERATIONS_REACHED:
                    logger.warning(f"⚠️ [LoomAgentRuntime] 达到最大迭代次数")
                    break

                # 错误处理
                elif event.type == AgentEventType.ERROR:
                    error_msg = str(event.error) if event.error else "Unknown error"
                    logger.error(f"❌ [LoomAgentRuntime] Agent 执行错误: {error_msg}")
                    if event.error:
                        raise event.error
                    break

            # 计算执行时间
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # 更新迭代计数
            estimated_iterations = self._iteration_tracker.estimate_iteration_count()
            self._current_state.iteration_count = estimated_iterations
            
            # 构建响应
            response = await self._build_response(request, result, execution_time_ms)
            
            # 发送完成事件
            completion_event = AgentEvent(
                event_type="execution_completed",
                stage=ExecutionStage.COMPLETION,
                data={
                    "response": response,
                    "execution_time_ms": execution_time_ms,
                    "iterations_used": self._current_state.iteration_count
                }
            )
            yield completion_event
            await self._notify_callbacks(completion_event)
            
            logger.info(f"✅ [LoomAgentRuntime] TT 递归执行完成")
            logger.info(f"   执行时间: {execution_time_ms}ms")
            logger.info(f"   迭代次数: {self._current_state.iteration_count}")
            logger.info(f"   工具调用次数: {len(self._current_state.tool_call_history)}")
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"❌ [LoomAgentRuntime] TT 递归执行失败: {e}", exc_info=True)
            
            # 发送错误事件
            error_event = AgentEvent(
                event_type="execution_failed",
                stage=self._current_state.current_stage,
                data={
                    "error": str(e),
                    "execution_time_ms": execution_time_ms,
                    "iterations_used": self._current_state.iteration_count
                }
            )
            yield error_event
            await self._notify_callbacks(error_event)

            # 重新抛出异常
            raise
        finally:
            # 🔥 清理 context variable
            try:
                _CURRENT_USER_ID.reset(token)
            except (ValueError, LookupError) as e:
                # 在生成器关闭时，token 可能已经在不同的上下文中
                # 这种情况下忽略 reset 错误
                logger.debug(f"⚠️ Context variable reset failed (可以忽略): {e}")

    async def _build_initial_prompt(self, request: AgentRequest) -> str:
        """构建初始 prompt"""
        prompt_parts = []

        # 1. 系统指令（🔥 关键修复：确保系统提示被包含）
        # ✅ 使用 SystemPromptBuilder 生成系统提示（去除硬编码）
        from .prompts import SystemPromptBuilder

        system_builder = SystemPromptBuilder()

        if self._config.system_prompt:
            # 使用配置的系统提示
            prompt_parts.append(f"# 系统指令\n{self._config.system_prompt}")
        else:
            # 使用 SystemPromptBuilder 动态生成
            system_prompt = system_builder.build_system_prompt(
                stage=request.stage,
                complexity=getattr(request, 'complexity', None)
            )
            prompt_parts.append(f"# 系统指令\n{system_prompt}")

        # 🔥 关键修复：手动调用 context_retriever 并注入 Schema 信息
        if self._context_retriever:
            try:
                logger.info("🔍 [_build_initial_prompt] 手动调用 ContextRetriever 获取 Schema")
                # 调用 retrieve 方法获取相关表结构
                documents = await self._context_retriever.retrieve(
                    query=request.placeholder,
                    top_k=5  # 获取最相关的5个表
                )

                if documents:
                    logger.info(f"✅ [_build_initial_prompt] 检索到 {len(documents)} 个表结构")
                    # 构建 Schema 上下文部分
                    schema_lines = ["# 数据库 Schema 信息", ""]
                    for doc in documents:
                        schema_lines.append(doc.content)
                        schema_lines.append("")  # 空行分隔

                    schema_context = "\n".join(schema_lines)
                    prompt_parts.append(schema_context)

                    logger.info(f"✅ [_build_initial_prompt] Schema 信息已注入到 prompt（{len(schema_context)} 字符）")
                else:
                    logger.warning("⚠️ [_build_initial_prompt] ContextRetriever 未返回任何表结构")
            except Exception as e:
                logger.error(f"❌ [_build_initial_prompt] 调用 ContextRetriever 失败: {e}", exc_info=True)

        # 2. 任务描述
        prompt_parts.append(f"# 任务描述\n{request.placeholder}")

        # 3. 上下文信息
        if request.task_context:
            prompt_parts.append(f"# 任务上下文\n{self._format_context(request.task_context)}")

        # 4. 约束条件
        if request.constraints:
            prompt_parts.append(f"# 约束条件\n{self._format_constraints(request.constraints)}")

        # 5. 执行指导
        prompt_parts.append(self._get_execution_guidance(request))

        return "\n\n".join(prompt_parts)

    def _format_context(self, context: Dict[str, Any]) -> str:
        """格式化上下文信息"""
        lines = []
        for key, value in context.items():
            if isinstance(value, (dict, list)):
                lines.append(f"- {key}: {str(value)[:200]}...")
            else:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def _format_constraints(self, constraints: Dict[str, Any]) -> str:
        """格式化约束条件"""
        lines = []
        for key, value in constraints.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def _get_execution_guidance(self, request: AgentRequest) -> str:
        """获取执行指导"""
        guidance = [
            "# 执行指导",
            "",
            "请按照以下步骤完成任务：",
            "",
            "1. **理解需求**: 仔细分析占位符中的业务需求",
            "2. **探索数据**: 使用可用的工具探索数据源结构",
            "3. **生成SQL**: 基于数据结构和需求生成准确的SQL查询",
            "4. **验证结果**: 验证SQL的正确性和结果的合理性",
            "5. **优化改进**: 根据验证结果优化查询",
            "",
            "**重要提示**:",
            "- 优先使用工具获取准确的数据结构信息",
            "- 生成的SQL必须符合数据库语法规范",
            "- 确保查询结果的准确性和完整性",
            "- 如果遇到问题，请尝试不同的方法或工具",
        ]
        
        # 根据复杂度添加特定指导
        if request.complexity == TaskComplexity.COMPLEX:
            guidance.extend([
                "",
                "**复杂任务指导**:",
                "- 将复杂任务分解为多个步骤",
                "- 逐步验证每个步骤的结果",
                "- 使用多个工具组合完成任务",
            ])
        
        return "\n".join(guidance)

    async def _build_response(
        self, 
        request: AgentRequest, 
        result: Any, 
        execution_time_ms: int
    ) -> AgentResponse:
        """构建响应"""
        # 提取结果内容
        if isinstance(result, str):
            content = result
        elif isinstance(result, dict):
            content = result.get("content", result.get("result", str(result)))
        else:
            content = str(result)
        
        # 计算质量评分
        quality_score = await self._calculate_quality_score(content, request)
        
        return AgentResponse(
            success=True,
            result=content,
            stage=ExecutionStage.COMPLETION,
            iterations_used=self._current_state.iteration_count,
            execution_time_ms=execution_time_ms,
            reasoning=self._extract_reasoning(result),
            quality_score=quality_score,
            tool_calls=self._current_state.tool_call_history,
            metadata={
                "data_source_id": request.data_source_id,
                "user_id": request.user_id,
                "complexity": request.complexity.value,
                "config": self._config.metadata
            }
        )

    async def _calculate_quality_score(self, content: str, request: AgentRequest) -> float:
        """
        计算质量评分

        使用增强的多维度质量评分系统，支持阶段感知的质量阈值
        """
        try:
            # 🔥 获取当前阶段的质量阈值（优先使用阶段配置）
            quality_threshold = 0.8  # 默认阈值
            if hasattr(self, 'stage_config_manager'):
                stage_config = self.stage_config_manager.get_stage_config(request.stage)
                if stage_config:
                    quality_threshold = stage_config.quality_threshold
                    logger.debug(f"🎯 [质量评分] 使用阶段阈值: {quality_threshold} (阶段: {request.stage.value})")
            
            # 动态更新质量评分器的阈值
            if hasattr(self._quality_scorer, 'config'):
                self._quality_scorer.config.passing_threshold = quality_threshold
                logger.debug(f"📝 [质量评分] 质量评分器阈值已更新为: {quality_threshold}")

            # 准备执行结果（如果有）
            execution_result = None
            if hasattr(self._current_state, 'accumulated_results') and self._current_state.accumulated_results:
                # 获取最后一个执行结果
                last_result = self._current_state.accumulated_results[-1]
                if isinstance(last_result, dict):
                    execution_result = last_result

            # 准备数据源服务和连接配置（用于SQL执行验证）
            data_source_service = None
            connection_config = None
            
            if hasattr(self.container, 'data_source') and request.data_source_id:
                try:
                    data_source_service = self.container.data_source
                    # 获取数据源配置
                    with get_db_session() as db:
                        data_source = crud.data_source.get(db, id=request.data_source_id)
                        if data_source:
                            connection_config = {
                                "source_type": data_source.source_type,
                                "name": data_source.name,
                                "doris_fe_hosts": data_source.doris_fe_hosts,
                                "doris_be_hosts": data_source.doris_be_hosts,
                                "doris_http_port": data_source.doris_http_port,
                                "doris_query_port": data_source.doris_query_port,
                                "doris_database": data_source.doris_database,
                                "doris_username": data_source.doris_username,
                                "doris_password": data_source.doris_password,
                            }
                except Exception as e:
                    logger.warning(f"⚠️ 获取数据源配置失败: {e}")

            # 使用增强的质量评分器
            quality_score_result = await self._quality_scorer.calculate_quality_score(
                content=content,
                execution_result=execution_result,
                tool_call_history=self._current_state.tool_call_history if self._current_state else None,
                request_context={
                    "complexity": request.complexity.value,
                    "stage": request.stage.value,
                    "constraints": request.constraints,
                    "quality_threshold": quality_threshold,  # 🔥 传递质量阈值到上下文
                },
                data_source_service=data_source_service,
                connection_config=connection_config
            )

            # 🔥 增强的日志记录：显示阈值和是否通过
            passed_status = "✅ 通过" if quality_score_result.passed else "❌ 未通过"
            logger.info(f"📊 [质量评分] 总体评分: {quality_score_result.overall_score:.2f}/{quality_threshold:.2f} ({quality_score_result.grade}) {passed_status}")
            
            # 记录各维度评分（仅在debug模式下或未通过时显示）
            if not quality_score_result.passed or logger.isEnabledFor(logging.DEBUG):
                for dimension, dim_score in quality_score_result.dimension_scores.items():
                    logger.debug(f"   📈 {dimension.value}: {dim_score.score:.2f} (权重: {dim_score.weight:.2f})")
            
            # 记录建议（仅在未通过或debug模式下显示）
            if quality_score_result.suggestions:
                if not quality_score_result.passed:
                    logger.warning(f"💡 [质量建议] {len(quality_score_result.suggestions)} 条改进建议:")
                    for suggestion in quality_score_result.suggestions[:5]:  # 显示前5条
                        logger.warning(f"   - {suggestion}")
                elif logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"💡 [质量建议] {len(quality_score_result.suggestions)} 条优化建议:")
                    for suggestion in quality_score_result.suggestions[:3]:  # debug模式下只显示前3条
                        logger.debug(f"   - {suggestion}")

            return quality_score_result.overall_score

        except Exception as e:
            logger.warning(f"⚠️ 质量评分失败，使用基础评分: {e}")
            # 降级到基础评分
            return self._calculate_basic_quality_score(content)

    def _calculate_basic_quality_score(self, content: str) -> float:
        """基础质量评分（降级方案）"""
        score = 0.0

        # 基础评分
        if content and len(content.strip()) > 0:
            score += 0.3

        # SQL 质量评分
        if "SELECT" in content.upper() or "WITH" in content.upper():
            score += 0.4

            # 检查 SQL 结构
            if "FROM" in content.upper():
                score += 0.1
            if "WHERE" in content.upper() or "GROUP BY" in content.upper():
                score += 0.1
            if "ORDER BY" in content.upper():
                score += 0.1

        # 工具使用评分
        if self._current_state and self._current_state.tool_call_history:
            score += min(0.2, len(self._current_state.tool_call_history) * 0.05)

        return min(1.0, score)

    def _extract_reasoning(self, result: Any) -> str:
        """提取推理过程"""
        if isinstance(result, dict):
            return result.get("reasoning", result.get("explanation", ""))
        return ""

    async def run(self, prompt: str, **kwargs) -> str:
        """
        简化的运行接口
        
        Args:
            prompt: 输入 prompt
            **kwargs: 其他参数
            
        Returns:
            执行结果
        """
        # 创建临时请求
        request = AgentRequest(
            placeholder=prompt,
            data_source_id=kwargs.get("data_source_id", 0),
            user_id=kwargs.get("user_id", "system")
        )
        
        # 执行并收集结果
        result = None
        async for event in self.execute_with_tt(request):
            if event.event_type == "execution_completed":
                result = event.data["response"].result
                break
        
        return result or ""

    async def stream(self, prompt: str):
        """流式执行"""
        request = AgentRequest(
            placeholder=prompt,
            data_source_id=0,
            user_id="system"
        )
        
        async for event in self.execute_with_tt(request):
            yield event

    def add_event_callback(self, callback: Callable[[AgentEvent], None]):
        """添加事件回调"""
        self._event_callbacks.append(callback)

    def remove_event_callback(self, callback: Callable[[AgentEvent], None]):
        """移除事件回调"""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)

    async def _notify_callbacks(self, event: AgentEvent):
        """通知回调函数"""
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.warning(f"⚠️ 事件回调执行失败: {e}")

    def _setup_tool_call_tracking(self):
        """设置工具调用跟踪"""
        # 如果 agent 有 LLM 适配器，设置工具调用回调
        if hasattr(self._agent, 'llm') and hasattr(self._agent.llm, '_tool_call_callback'):
            def tool_call_callback(tool_name: str, arguments: Dict[str, Any]):
                """工具调用回调"""
                if self._current_state:
                    # 记录工具调用
                    tool_call = ToolCall(
                        tool_name=tool_name,
                        arguments=arguments,
                        timestamp=time.time(),
                        success=True
                    )
                    self._current_state.tool_call_history.append(tool_call)
                    
                    # 更新迭代跟踪器
                    self._iteration_tracker.on_tool_call()
                    
                    logger.info(f"🔧 [LoomAgentRuntime] 工具调用: {tool_name}")
            
            # 设置回调
            self._agent.llm._tool_call_callback = tool_call_callback


def build_default_runtime(
    *,
    container: Any,
    config: Optional[AgentConfig] = None,
    additional_tools: Optional[List[BaseTool]] = None,
    llm: Optional[BaseLLM] = None,
    context_retriever: Optional[SchemaContextRetriever] = None,
) -> LoomAgentRuntime:
    """
    构建默认运行时

    Args:
        container: 服务容器
        config: Agent 配置
        additional_tools: 额外工具
        llm: LLM 实例
        context_retriever: 上下文检索器

    Returns:
        LoomAgentRuntime 实例
    """
    from .types import create_default_agent_config

    # 使用默认配置
    if config is None:
        config = create_default_agent_config()

    # 创建 LLM 适配器
    if llm is None:
        llm = create_llm_adapter(container)

    # 🔥 构建工具列表 - 从配置自动创建
    tools = _create_tools_from_config(container, config)
    if additional_tools:
        tools.extend(additional_tools)
        logger.info(f"➕ [ToolRegistry] 添加额外工具: {len(additional_tools)} 个")

    logger.info(f"🔧 [LoomAgentRuntime] 最终工具数量: {len(tools)}")

    # 创建 Loom Agent
    # 🔥 关键修复：添加 memory 以支持对话历史管理
    from loom.builtin.memory import InMemoryMemory

    agent_kwargs = {
        "llm": llm,
        "tools": tools,
        "memory": InMemoryMemory(),  # 🔥 添加 memory
        "max_iterations": config.max_iterations,
        "max_context_tokens": config.max_context_tokens,
    }

    if config.system_prompt:
        agent_kwargs["system_instructions"] = config.system_prompt

    if context_retriever:
        agent_kwargs["context_retriever"] = context_retriever
        try:
            logger.info(f"🧩 [LoomAgentRuntime] 已注入 ContextRetriever: {type(context_retriever).__name__}")
        except Exception:
            logger.info("🧩 [LoomAgentRuntime] 已注入 ContextRetriever")

    agent = build_agent(**agent_kwargs)

    # 🔥 关键修复：替换默认的executor为自定义的上下文感知executor
    agent._executor = ContextAwareAgentExecutor(
        original_executor=agent.executor,
        context_retriever=context_retriever
    )

    logger.info(f"✅ [LoomAgentRuntime] Agent 已创建，配置了 memory: True 和 ContextAwareExecutor")
    
    return LoomAgentRuntime(
        agent=agent,
        tools=tools,
        config=config,
        context_retriever=context_retriever
    )


def create_runtime_with_context_retriever(
    container: Any,
    data_source_id: str,
    connection_config: Dict[str, Any],
    config: Optional[AgentConfig] = None
) -> LoomAgentRuntime:
    """
    创建带上下文检索器的运行时
    
    Args:
        container: 服务容器
        data_source_id: 数据源ID
        connection_config: 连接配置
        config: Agent 配置
        
    Returns:
        LoomAgentRuntime 实例
    """
    # 创建上下文检索器
    context_retriever = create_schema_context_retriever(
        data_source_id=data_source_id,
        connection_config=connection_config,
        container=container
    )
    
    # 创建运行时
    return build_default_runtime(
        container=container,
        config=config,
        context_retriever=context_retriever
    )


class StageAwareRuntime(LoomAgentRuntime):
    """
    阶段感知的Runtime
    
    保留TT递归能力，根据当前阶段动态切换配置
    这是基于TT递归的三阶段Agent架构的核心实现
    """
    
    def __init__(
        self,
        agent: Agent,
        tools: List[BaseTool],
        config: AgentConfig,
        context_retriever: Optional[SchemaContextRetriever] = None,
        stage_config_manager: Optional[StageConfigManager] = None,
    ):
        """
        Args:
            agent: Loom Agent 实例
            tools: 工具列表
            config: Agent 配置
            context_retriever: 上下文检索器
            stage_config_manager: 阶段配置管理器
        """
        super().__init__(agent, tools, config, context_retriever)
        
        # 当前执行阶段
        self.current_stage: Optional[ExecutionStage] = None
        
        # 阶段配置管理器
        self.stage_config_manager = stage_config_manager or get_stage_config_manager()
        
        # 原始配置备份（用于恢复）
        self._original_config = AgentConfig(
            llm=config.llm,
            tools=config.tools,
            coordination=config.coordination,
            max_iterations=config.max_iterations,
            max_context_tokens=config.max_context_tokens,
            system_prompt=config.system_prompt,
            callbacks=config.callbacks.copy(),
            metadata=config.metadata.copy()
        )
        
        logger.info("🎯 [StageAwareRuntime] 初始化完成")
        logger.info(f"   支持阶段: {self.stage_config_manager.get_all_stages()}")
    
    async def execute_with_stage(
        self,
        request: AgentRequest,
        stage: ExecutionStage
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        在指定阶段执行（保留TT递归）
        
        Args:
            request: Agent请求
            stage: 执行阶段
            
        Yields:
            AgentEvent: 执行事件（包含TT递归的所有步骤）
        """
        # 1. 切换到对应阶段配置
        self.current_stage = stage
        stage_config = self.stage_config_manager.get_stage_config(stage)
        
        if not stage_config:
            logger.error(f"❌ [StageAwareRuntime] 未找到阶段配置: {stage.value}")
            raise ValueError(f"未找到阶段配置: {stage.value}")
        
        # 应用阶段配置
        self._apply_stage_config(stage_config)
        
        # 🔥 增强的阶段进入日志
        logger.info(f"🎯 [StageAwareRuntime] 进入阶段: {stage.value}")
        logger.info(f"   🔧 启用工具: {len(stage_config.enabled_tools)} 个 - {', '.join(stage_config.enabled_tools[:3])}{'...' if len(stage_config.enabled_tools) > 3 else ''}")
        logger.info(f"   🎯 质量阈值: {stage_config.quality_threshold:.2f} (必须达到此阈值才能通过)")
        logger.info(f"   🔢 最大迭代: {stage_config.max_iterations} 次")
        logger.info(f"   📌 阶段目标: {stage_config.stage_goal}")
        logger.info(f"   ✅ 约束条件: {list(stage_config.constraints.keys())}")
        
        # 2. 更新请求配置
        stage_request = AgentRequest(
            placeholder=request.placeholder,
            data_source_id=request.data_source_id,
            user_id=request.user_id,
            task_context=request.task_context,
            template_context=request.template_context,
            max_iterations=stage_config.max_iterations,
            complexity=request.complexity,
            stage=stage,
            constraints={**request.constraints, **stage_config.constraints},
            metadata={**request.metadata, **stage_config.metadata}
        )
        
        # 3. 使用TT递归执行（这是核心！）
        async for event in self.execute_with_tt(stage_request):
            # 添加阶段信息到事件
            event.data['current_stage'] = stage.value
            event.data['stage_goal'] = stage_config.stage_goal
            event.data['stage_quality_threshold'] = stage_config.quality_threshold
            
            yield event
        
        logger.info(f"✅ [StageAwareRuntime] 阶段完成: {stage.value}")
        
        # 4. 恢复原始配置（可选）
        # self._restore_original_config()
    
    def _apply_stage_config(self, stage_config):
        """应用阶段配置"""
        # 切换工具集（这里需要根据实际工具管理方式调整）
        # 注意：实际的工具切换需要在Agent层面实现
        # 这里主要是更新配置信息
        
        # 切换系统提示
        self._config.system_prompt = stage_config.system_prompt
        
        # 🔥 切换质量阈值（如果有质量评分器）- 增强日志
        old_threshold = None
        if hasattr(self, '_quality_scorer') and hasattr(self._quality_scorer, 'config'):
            old_threshold = getattr(self._quality_scorer.config, 'passing_threshold', None)
            self._quality_scorer.config.passing_threshold = stage_config.quality_threshold
            if old_threshold != stage_config.quality_threshold:
                logger.info(f"🔄 [质量阈值] 已更新: {old_threshold:.2f} → {stage_config.quality_threshold:.2f}")
        
        # 切换迭代次数
        self._config.max_iterations = stage_config.max_iterations
        
        # 🔥 增强的配置应用日志
        logger.info(f"📝 [StageAwareRuntime] 已应用阶段配置")
        logger.info(f"   📋 系统提示长度: {len(stage_config.system_prompt)} 字符")
        logger.info(f"   🎯 质量阈值: {stage_config.quality_threshold:.2f}")
        logger.info(f"   🔢 最大迭代: {stage_config.max_iterations}")
        logger.info(f"   🔧 启用工具数: {len(stage_config.enabled_tools)} 个")
        logger.info(f"   📌 阶段目标: {stage_config.stage_goal}")
    
    def _restore_original_config(self):
        """恢复原始配置"""
        self._config.system_prompt = self._original_config.system_prompt
        self._config.max_iterations = self._original_config.max_iterations
        
        if hasattr(self, '_quality_scorer') and hasattr(self._quality_scorer, 'config'):
            self._quality_scorer.config.quality_threshold = 0.8  # 默认阈值
        
        logger.debug("🔄 [StageAwareRuntime] 已恢复原始配置")
    
    def get_current_stage(self) -> Optional[ExecutionStage]:
        """获取当前执行阶段"""
        return self.current_stage
    
    def get_stage_config(self, stage: ExecutionStage):
        """获取阶段配置"""
        return self.stage_config_manager.get_stage_config(stage)
    
    def is_stage_configured(self, stage: ExecutionStage) -> bool:
        """检查阶段是否已配置"""
        return self.stage_config_manager.is_stage_configured(stage)
    
    async def execute_sql_generation_stage(
        self,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        执行SQL生成阶段（使用TT递归）
        
        内部会自动迭代优化：
        - 发现Schema
        - 生成SQL
        - 验证SQL
        - 修复问题
        - 再次验证
        - ... 直到达到质量阈值
        
        Yields:
            AgentEvent: 包含所有TT递归步骤的事件
        """
        logger.info("🎯 [SQL生成阶段] 开始执行（TT递归模式）")
        
        # 创建请求
        request = AgentRequest(
            placeholder=placeholder,
            data_source_id=data_source_id,
            user_id=user_id,
            task_context=kwargs.get('task_context', {}),
            template_context=kwargs.get('template_context'),
            max_iterations=8,  # SQL阶段的迭代次数
            complexity=kwargs.get('complexity', TaskComplexity.MEDIUM),
            stage=ExecutionStage.SQL_GENERATION,
            constraints=kwargs.get('constraints', {})
        )
        
        # 使用TT递归执行
        async for event in self.execute_with_stage(request, ExecutionStage.SQL_GENERATION):
            # 记录TT递归的每一步
            if event.event_type == 'execution_started':
                logger.info(f"🚀 [SQL阶段] 开始TT递归执行")
            elif event.event_type == 'execution_completed':
                logger.info(f"✅ [SQL阶段] TT递归执行完成")
                response_payload = event.data.get('response')
                quality_score, iterations_used = _extract_response_metrics(response_payload)
                logger.info(f"   质量评分: {quality_score:.2f}")
                logger.info(f"   迭代次数: {iterations_used}")
            
            yield event
        
        logger.info("✅ [SQL生成阶段] 完成（TT递归自动优化）")
    
    async def execute_chart_generation_stage(
        self,
        etl_data: Dict[str, Any],
        chart_placeholder: str,
        user_id: str,
        **kwargs
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        执行图表生成阶段（使用TT递归）
        
        内部会自动迭代优化：
        - 分析数据特征
        - 选择图表类型
        - 生成图表配置
        - 验证配置
        - 优化配置
        - ... 直到达到最优
        
        Yields:
            AgentEvent: 包含所有TT递归步骤的事件
        """
        logger.info("🎯 [图表生成阶段] 开始执行（TT递归模式）")
        
        # 创建请求
        request = AgentRequest(
            placeholder=chart_placeholder,
            data_source_id=kwargs.get('data_source_id', 0),
            user_id=user_id,
            task_context={
                'etl_data': etl_data,
                'statistics': kwargs.get('statistics', {}),
                **kwargs.get('task_context', {})
            },
            max_iterations=6,  # 图表阶段的迭代次数
            complexity=kwargs.get('complexity', TaskComplexity.MEDIUM),
            stage=ExecutionStage.CHART_GENERATION,
            constraints={'output_format': 'chart_config'}
        )
        
        # 使用TT递归执行
        async for event in self.execute_with_stage(request, ExecutionStage.CHART_GENERATION):
            if event.event_type == 'execution_completed':
                logger.info(f"✅ [图表阶段] TT递归执行完成")
                response_payload = event.data.get('response')
                quality_score, _ = _extract_response_metrics(response_payload)
                logger.info(f"   质量评分: {quality_score:.2f}")
            
            yield event
        
        logger.info("✅ [图表生成阶段] 完成（TT递归自动优化）")
    
    async def execute_document_generation_stage(
        self,
        paragraph_context: str,
        placeholder_data: Dict[str, Any],
        user_id: str,
        **kwargs
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        执行文档生成阶段（使用TT递归）
        
        内部会自动迭代优化：
        - 分析段落结构
        - 生成文本
        - 检查风格
        - 验证一致性
        - 优化表达
        - ... 直到达到最优
        
        Yields:
            AgentEvent: 包含所有TT递归步骤的事件
        """
        logger.info("🎯 [文档生成阶段] 开始执行（TT递归模式）")
        
        # 创建请求
        request = AgentRequest(
            placeholder=paragraph_context,
            data_source_id=kwargs.get('data_source_id', 0),
            user_id=user_id,
            task_context={
                'paragraph_context': paragraph_context,
                'placeholder_data': placeholder_data,
                'document_context': kwargs.get('document_context', {}),
                **kwargs.get('task_context', {})
            },
            max_iterations=5,  # 文档阶段的迭代次数
            complexity=kwargs.get('complexity', TaskComplexity.MEDIUM),
            stage=ExecutionStage.DOCUMENT_GENERATION,
            constraints={'output_format': 'text'}
        )
        
        # 使用TT递归执行
        async for event in self.execute_with_stage(request, ExecutionStage.DOCUMENT_GENERATION):
            if event.event_type == 'execution_completed':
                logger.info(f"✅ [文档阶段] TT递归执行完成")
                response_payload = event.data.get('response')
                quality_score, _ = _extract_response_metrics(response_payload)
                logger.info(f"   质量评分: {quality_score:.2f}")
            
            yield event
        
        logger.info("✅ [文档生成阶段] 完成（TT递归自动优化）")


def build_stage_aware_runtime(
    *,
    container: Any,
    config: Optional[AgentConfig] = None,
    additional_tools: Optional[List[BaseTool]] = None,
    llm: Optional[BaseLLM] = None,
    context_retriever: Optional[SchemaContextRetriever] = None,
    stage_config_manager: Optional[StageConfigManager] = None,
) -> StageAwareRuntime:
    """
    构建Stage-Aware运行时

    Args:
        container: 服务容器
        config: Agent 配置
        additional_tools: 额外工具
        llm: LLM 实例
        context_retriever: 上下文检索器
        stage_config_manager: 阶段配置管理器

    Returns:
        StageAwareRuntime 实例
    """
    from .types import create_default_agent_config

    # 使用默认配置
    if config is None:
        config = create_default_agent_config()

    # 创建 LLM 适配器
    if llm is None:
        llm = create_llm_adapter(container)

    # 🔥 构建工具列表 - 从配置自动创建
    tools = _create_tools_from_config(container, config)
    if additional_tools:
        tools.extend(additional_tools)
        logger.info(f"➕ [ToolRegistry] 添加额外工具: {len(additional_tools)} 个")

    logger.info(f"🔧 [StageAwareRuntime] 最终工具数量: {len(tools)}")

    # 创建 Loom Agent
    agent_kwargs = {
        "llm": llm,
        "tools": tools,
        "max_iterations": config.max_iterations,
        "max_context_tokens": config.max_context_tokens,
    }
    
    if config.system_prompt:
        agent_kwargs["system_instructions"] = config.system_prompt
    
    if context_retriever:
        agent_kwargs["context_retriever"] = context_retriever
        try:
            logger.info(f"🧩 [StageAwareRuntime] 已注入 ContextRetriever: {type(context_retriever).__name__}")
        except Exception:
            logger.info("🧩 [StageAwareRuntime] 已注入 ContextRetriever")
    
    agent = build_agent(**agent_kwargs)
    
    return StageAwareRuntime(
        agent=agent,
        tools=tools,
        config=config,
        context_retriever=context_retriever,
        stage_config_manager=stage_config_manager
    )


# 导出
__all__ = [
    "LoomAgentRuntime",
    "StageAwareRuntime",
    "build_default_runtime",
    "build_stage_aware_runtime",
    "create_runtime_with_context_retriever",
]
