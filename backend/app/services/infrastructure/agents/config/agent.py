"""
Agent 配置

定义 Agent 系统的核心配置
包括 LLM 配置、工具配置和 Agent 行为配置
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field

from ..types import LLMConfig, ToolConfig, AgentConfig, ExecutionStage, TaskComplexity
from .coordination import AdvancedCoordinationConfig, create_default_coordination_config

logger = logging.getLogger(__name__)


@dataclass
class LLMRuntimeConfig(LLMConfig):
    """LLM 运行时配置"""
    # 基础配置
    provider: str = "container"  # 使用容器LLM服务
    model: str = "auto"  # 自动选择模型
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    
    # 高级配置
    enable_tool_calling: bool = True
    enable_streaming: bool = False
    
    # 策略配置
    selection_policy: Dict[str, Any] = field(default_factory=dict)
    fallback_strategy: str = "auto_retry"
    
    # 性能配置
    request_timeout: int = 30  # 秒
    max_retries: int = 3
    retry_delay: float = 1.0  # 秒
    
    # 缓存配置
    enable_response_caching: bool = True
    cache_ttl: int = 300  # 秒
    cache_size: int = 100


@dataclass
class ToolRuntimeConfig(ToolConfig):
    """工具运行时配置"""
    # 工具启用状态
    enabled_tools: List[str] = field(default_factory=lambda: [
        "schema_discovery", "schema_retrieval", "schema_cache",
        "sql_generator", "sql_validator", "sql_column_checker", 
        "sql_auto_fixer", "sql_executor",
        "data_sampler", "data_analyzer",
        "time_window", "chart_generator", "chart_analyzer"
    ])
    
    # 工具超时
    tool_timeout: int = 30  # 秒
    
    # 工具重试
    max_retries: int = 3
    retry_delay: float = 1.0  # 秒
    
    # 工具限制
    max_tool_calls_per_iteration: int = 5
    max_total_tool_calls: int = 50
    
    # 工具优先级
    tool_priorities: Dict[str, int] = field(default_factory=lambda: {
        "schema_discovery": 10,
        "schema_retrieval": 9,
        "sql_generator": 8,
        "sql_validator": 7,
        "sql_executor": 6,
        "data_sampler": 5,
        "data_analyzer": 4,
        "chart_generator": 3,
    })
    
    # 工具组合策略
    enable_tool_combination: bool = True
    combination_strategies: List[str] = field(default_factory=lambda: [
        "sequential", "parallel", "conditional"
    ])


@dataclass
class AgentBehaviorConfig:
    """Agent 行为配置"""
    # 执行策略
    execution_strategy: str = "adaptive"  # adaptive, aggressive, conservative
    enable_self_correction: bool = True
    enable_learning: bool = True
    
    # 决策配置
    decision_threshold: float = 0.7
    confidence_threshold: float = 0.8
    uncertainty_handling: str = "ask_for_clarification"  # ask_for_clarification, make_best_guess, abort
    
    # 交互配置
    enable_user_interaction: bool = False
    interaction_timeout: int = 60  # 秒
    max_interaction_rounds: int = 3
    
    # 错误处理
    error_recovery_strategy: str = "retry_with_backoff"  # retry_with_backoff, fallback_tool, abort
    max_error_recovery_attempts: int = 3
    error_recovery_delay: float = 2.0  # 秒
    
    # 质量保证
    enable_result_validation: bool = True
    validation_strategies: List[str] = field(default_factory=lambda: [
        "syntax_check", "semantic_check", "data_consistency_check"
    ])
    quality_threshold: float = 0.8


@dataclass
class AgentRuntimeConfig(AgentConfig):
    """Agent 运行时配置"""
    # 核心配置
    llm: LLMRuntimeConfig = field(default_factory=LLMRuntimeConfig)
    tools: ToolRuntimeConfig = field(default_factory=ToolRuntimeConfig)
    coordination: AdvancedCoordinationConfig = field(default_factory=create_default_coordination_config)
    
    # 行为配置
    behavior: AgentBehaviorConfig = field(default_factory=AgentBehaviorConfig)
    
    # 执行配置
    max_iterations: int = 10
    max_context_tokens: int = 16000
    
    # 系统提示
    system_prompt: Optional[str] = None
    
    # 回调函数
    callbacks: List[Callable] = field(default_factory=list)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentConfigManager:
    """Agent 配置管理器"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self._user_model_resolver = None
        self._validation_rules: Dict[str, Callable] = {}
        self._setup_validation_rules()
    
    async def resolve_user_config(
        self,
        user_id: str,
        task_type: str = "placeholder_analysis",
        task_complexity: Union[TaskComplexity, float] = 0.5
    ) -> AgentConfig:
        """
        基于用户配置解析Agent配置

        Args:
            user_id: 用户ID
            task_type: 任务类型
            task_complexity: 任务复杂度，可以是 TaskComplexity 枚举或 float (0.0-1.0)

        Returns:
            AgentConfig: 解析后的Agent配置
        """
        try:
            from .user_model_resolver import get_user_model_config, user_model_resolver

            # 转换 task_complexity 为 float
            complexity_value = float(task_complexity) if isinstance(task_complexity, (TaskComplexity, float, int)) else 0.5

            # 获取用户模型配置
            user_model_config = await get_user_model_config(user_id, task_type)

            # 根据任务复杂度选择合适的模型
            selected_model = user_model_resolver.select_model_for_task(
                user_model_config, complexity_value, task_type
            )

            # 计算最大上下文tokens
            max_context_tokens = user_model_resolver.get_max_context_tokens(
                user_model_config, selected_model
            )
            
            # 创建新的配置实例
            resolved_config = AgentConfig(
                llm=LLMRuntimeConfig(
                    provider="container",
                    model=selected_model.model_name,
                    temperature=selected_model.temperature,
                    max_tokens=selected_model.max_tokens,
                    enable_tool_calling=selected_model.supports_function_calls,
                    enable_streaming=False,
                    selection_policy={
                        "user_model": selected_model.model_name,
                        "model_type": selected_model.model_type,
                        "supports_thinking": selected_model.supports_thinking,
                        "task_complexity": complexity_value
                    },
                    fallback_strategy="auto_retry",
                    request_timeout=30,
                    max_retries=3,
                    retry_delay=1.0,
                    enable_response_caching=True,
                    cache_ttl=300,
                    cache_size=100
                ),
                tools=self.config.tools,
                coordination=self.config.coordination,
                max_iterations=self.config.max_iterations,
                max_context_tokens=max_context_tokens,  # 🔥 关键：使用动态计算的context_tokens
                system_prompt=self.config.system_prompt,
                callbacks=self.config.callbacks,
                metadata={
                    **self.config.metadata,
                    "user_id": user_id,
                    "task_type": task_type,
                    "task_complexity": complexity_value,
                    "selected_model": selected_model.model_name,
                    "model_type": selected_model.model_type,
                    "supports_thinking": selected_model.supports_thinking,
                    "max_context_tokens": max_context_tokens
                }
            )

            logger.info(f"✅ 解析用户配置完成: user_id={user_id}, model={selected_model.model_name}({selected_model.model_type}), context_tokens={max_context_tokens}")
            return resolved_config
            
        except Exception as e:
            logger.error(f"❌ 解析用户配置失败: {e}")
            # 回退到原始配置
            return self.config
    
    def validate_config(self) -> Dict[str, List[str]]:
        """验证配置"""
        errors = {}
        
        for key, validator in self._validation_rules.items():
            try:
                config_value = getattr(self.config, key, None)
                if config_value:
                    errors[key] = validator(config_value)
                else:
                    errors[key] = []
            except Exception as e:
                errors[key] = [f"验证 {key} 配置时出错: {str(e)}"]
        
        return errors
    
    def _setup_validation_rules(self):
        """设置验证规则"""
        self._validation_rules = {
            "llm": self._validate_llm_config,
            "tools": self._validate_tools_config,
            "coordination": self._validate_coordination_config,
            "behavior": self._validate_behavior_config,
        }
    
    def _validate_llm_config(self, config: LLMRuntimeConfig) -> List[str]:
        """验证 LLM 配置"""
        errors = []
        
        if config.temperature < 0 or config.temperature > 2:
            errors.append("Temperature 必须在 0-2 之间")
        
        if config.max_tokens and config.max_tokens < 100:
            errors.append("Max tokens 必须至少为 100")
        
        if config.request_timeout < 1:
            errors.append("Request timeout 必须至少为 1 秒")
        
        if config.max_retries < 0:
            errors.append("Max retries 不能为负数")
        
        return errors
    
    def _validate_tools_config(self, config: ToolRuntimeConfig) -> List[str]:
        """验证工具配置"""
        errors = []
        
        if config.tool_timeout < 1:
            errors.append("Tool timeout 必须至少为 1 秒")
        
        if config.max_tool_calls_per_iteration < 1:
            errors.append("Max tool calls per iteration 必须至少为 1")
        
        if config.max_total_tool_calls < config.max_tool_calls_per_iteration:
            errors.append("Max total tool calls 必须大于等于 max tool calls per iteration")
        
        # 验证工具优先级
        priorities = list(config.tool_priorities.values())
        if priorities and (min(priorities) < 1 or max(priorities) > 10):
            errors.append("Tool priorities 必须在 1-10 之间")
        
        return errors
    
    def _validate_coordination_config(self, config: AdvancedCoordinationConfig) -> List[str]:
        """验证协调配置"""
        errors = []
        
        if config.recursion.max_recursion_depth < 1:
            errors.append("Max recursion depth 必须至少为 1")
        
        if config.token_budget.max_tokens_per_iteration < 1000:
            errors.append("Max tokens per iteration 必须至少为 1000")
        
        if config.token_budget.max_total_tokens < config.token_budget.max_tokens_per_iteration:
            errors.append("Max total tokens 必须大于等于 max tokens per iteration")
        
        return errors
    
    def _validate_behavior_config(self, config: AgentBehaviorConfig) -> List[str]:
        """验证行为配置"""
        errors = []
        
        if config.decision_threshold < 0 or config.decision_threshold > 1:
            errors.append("Decision threshold 必须在 0-1 之间")
        
        if config.confidence_threshold < 0 or config.confidence_threshold > 1:
            errors.append("Confidence threshold 必须在 0-1 之间")
        
        if config.max_error_recovery_attempts < 0:
            errors.append("Max error recovery attempts 不能为负数")
        
        if config.quality_threshold < 0 or config.quality_threshold > 1:
            errors.append("Quality threshold 必须在 0-1 之间")
        
        return errors
    
    def validate_config(self) -> Dict[str, List[str]]:
        """验证整个配置"""
        validation_results = {}
        
        # 验证各个配置模块
        validation_results["llm"] = self._validate_llm_config(self.config.llm)
        validation_results["tools"] = self._validate_tools_config(self.config.tools)
        validation_results["coordination"] = self._validate_coordination_config(self.config.coordination)
        validation_results["behavior"] = self._validate_behavior_config(self.config.behavior)
        
        # 检查是否有错误
        all_errors = []
        for module, errors in validation_results.items():
            all_errors.extend([f"{module}: {error}" for error in errors])
        
        if all_errors:
            logger.warning(f"⚠️ 配置验证发现问题: {all_errors}")
        else:
            logger.info("✅ 配置验证通过")
        
        return validation_results
    
    def optimize_config(self, performance_metrics: Dict[str, Any]) -> AgentRuntimeConfig:
        """根据性能指标优化配置"""
        optimized_config = self.config
        
        # 根据执行时间优化
        avg_execution_time = performance_metrics.get("average_execution_time", 0)
        if avg_execution_time > 10000:  # 10秒
            # 增加并行度
            optimized_config.coordination.performance.max_concurrent_tools = min(
                optimized_config.coordination.performance.max_concurrent_tools + 1, 5
            )
            # 减少迭代次数
            optimized_config.max_iterations = max(optimized_config.max_iterations - 1, 5)
        
        # 根据工具调用频率优化
        tool_call_count = performance_metrics.get("tool_call_count", 0)
        if tool_call_count > 30:
            # 启用工具缓存
            optimized_config.tools.enable_tool_result_caching = True
            # 增加工具超时
            optimized_config.tools.tool_timeout = min(
                optimized_config.tools.tool_timeout + 5, 60
            )
        
        # 根据 Token 使用优化
        token_usage = performance_metrics.get("token_usage", {})
        if token_usage.get("total", 0) > optimized_config.coordination.token_budget.max_total_tokens * 0.9:
            # 增加 Token 预算
            optimized_config.coordination.token_budget.max_total_tokens += 2000
            optimized_config.max_context_tokens += 2000
        
        logger.info("🔧 [AgentConfigManager] 配置已根据性能指标优化")
        return optimized_config
    
    def get_config_for_stage(self, stage: ExecutionStage) -> Dict[str, Any]:
        """获取特定阶段的配置"""
        stage_configs = {
            ExecutionStage.SCHEMA_DISCOVERY: {
                "enabled_tools": ["schema_discovery", "schema_retrieval"],
                "max_iterations": 3,
                "tool_timeout": 20,
            },
            ExecutionStage.SQL_GENERATION: {
                "enabled_tools": ["sql_generator", "sql_validator"],
                "max_iterations": 5,
                "tool_timeout": 30,
            },
            ExecutionStage.SQL_VALIDATION: {
                "enabled_tools": ["sql_validator", "sql_column_checker"],
                "max_iterations": 3,
                "tool_timeout": 15,
            },
            ExecutionStage.DATA_EXTRACTION: {
                "enabled_tools": ["sql_executor", "data_sampler"],
                "max_iterations": 2,
                "tool_timeout": 45,
            },
            ExecutionStage.ANALYSIS: {
                "enabled_tools": ["data_analyzer"],
                "max_iterations": 3,
                "tool_timeout": 30,
            },
            ExecutionStage.CHART_GENERATION: {
                "enabled_tools": ["chart_generator", "chart_analyzer"],
                "max_iterations": 2,
                "tool_timeout": 20,
            },
        }
        
        return stage_configs.get(stage, {})
    
    def get_config_for_complexity(self, complexity: TaskComplexity) -> Dict[str, Any]:
        """获取特定复杂度的配置"""
        complexity_configs = {
            TaskComplexity.SIMPLE: {
                "max_iterations": 5,
                "max_tool_calls_per_iteration": 3,
                "tool_timeout": 20,
                "enable_parallel_execution": False,
            },
            TaskComplexity.MEDIUM: {
                "max_iterations": 8,
                "max_tool_calls_per_iteration": 5,
                "tool_timeout": 30,
                "enable_parallel_execution": True,
            },
            TaskComplexity.COMPLEX: {
                "max_iterations": 12,
                "max_tool_calls_per_iteration": 7,
                "tool_timeout": 45,
                "enable_parallel_execution": True,
                "max_concurrent_tools": 4,
            },
        }
        
        return complexity_configs.get(complexity, {})


def create_default_agent_config() -> AgentRuntimeConfig:
    """创建默认 Agent 配置"""
    return AgentRuntimeConfig()


def create_high_performance_agent_config() -> AgentRuntimeConfig:
    """创建高性能 Agent 配置"""
    config = AgentRuntimeConfig()
    
    # 优化 LLM 配置
    config.llm.enable_response_caching = True
    config.llm.cache_size = 200
    config.llm.request_timeout = 60
    
    # 优化工具配置
    config.tools.enable_tool_combination = True
    config.tools.max_concurrent_tools = 4
    config.tools.tool_timeout = 45
    
    # 优化协调配置
    config.coordination = create_default_coordination_config()
    config.coordination.performance.enable_parallel_execution = True
    config.coordination.performance.max_concurrent_tools = 5
    
    # 优化行为配置
    config.behavior.enable_self_correction = True
    config.behavior.enable_result_validation = True
    
    return config


def create_debug_agent_config() -> AgentRuntimeConfig:
    """创建调试 Agent 配置"""
    config = AgentRuntimeConfig()
    
    # 启用调试功能
    config.coordination.monitoring.enable_debug_mode = True
    config.coordination.monitoring.debug_tool_calls = True
    config.coordination.monitoring.enable_detailed_logging = True
    config.coordination.monitoring.log_level = "DEBUG"
    
    # 减少限制以便调试
    config.max_iterations = 15
    config.tools.max_total_tool_calls = 100
    config.tools.tool_timeout = 60
    
    # 启用所有工具
    config.tools.enabled_tools = [
        "schema_discovery", "schema_retrieval", "schema_cache",
        "sql_generator", "sql_validator", "sql_column_checker", 
        "sql_auto_fixer", "sql_executor",
        "data_sampler", "data_analyzer",
        "time_window", "chart_generator", "chart_analyzer"
    ]
    
    return config


def create_lightweight_agent_config() -> AgentRuntimeConfig:
    """创建轻量级 Agent 配置"""
    config = AgentRuntimeConfig()
    
    # 减少资源使用
    config.max_iterations = 5
    config.max_context_tokens = 8000
    config.tools.max_tool_calls_per_iteration = 3
    config.tools.max_total_tool_calls = 20
    
    # 禁用高级功能
    config.coordination.performance.enable_parallel_execution = False
    config.coordination.performance.enable_batch_processing = False
    config.tools.enable_tool_combination = False
    
    # 只启用核心工具
    config.tools.enabled_tools = [
        "schema_retrieval", "sql_generator", "sql_validator", "sql_executor"
    ]
    
    return config


# 导出
__all__ = [
    "AgentRuntimeConfig",
    "AgentConfigManager",
    "create_default_agent_config",
    "create_high_performance_agent_config",
    "create_debug_agent_config",
    "create_lightweight_agent_config",
]