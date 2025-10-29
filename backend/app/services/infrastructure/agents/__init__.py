"""
Loom Agent 系统

基于 Loom 0.0.3 的智能 Agent 系统
提供 TT 递归执行、智能上下文注入和统一业务接口
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, AsyncGenerator

# 核心类型
from .types import (
    # 枚举类型
    ExecutionStage,
    TaskComplexity,
    ToolCategory,
    
    # 核心数据类型
    AgentRequest,
    AgentResponse,
    ToolCall,
    ContextInfo,
    ExecutionState,
    
    # 配置类型
    CoordinationConfig,
    LLMConfig,
    ToolConfig,
    AgentConfig,
    
    # 事件类型
    AgentEvent,
    
    # 接口类型
    BaseTool,
    BaseContextRetriever,
    
    # 类型别名
    ToolFactory,
    ContextRetrieverFactory,
    EventCallback,
    
    # 工厂函数
    create_default_agent_config,
    create_default_coordination_config,
    create_default_llm_config,
    create_default_tool_config,
)

# 核心运行时
from .runtime import (
    LoomAgentRuntime,
    StageAwareRuntime,
    build_default_runtime,
    build_stage_aware_runtime,
    create_runtime_with_context_retriever,
)

# LLM 适配器
from .llm_adapter import (
    ContainerLLMAdapter,
    create_llm_adapter,
    create_llm_adapter_from_config,
)

# 上下文检索器
from .context_retriever import (
    SchemaContextRetriever,
    IntelligentContextRetriever,
    create_schema_context_retriever,
    create_intelligent_context_retriever,
)

# StageAwareAgentAdapter
from .stage_aware_adapter import StageAwareAgentAdapter

# TT递归统一接口
from .tt_recursion import (
    execute_tt_recursion,
    TTRecursionRequest,
    TTRecursionResponse,
    # 三步骤Agent专用函数
    execute_sql_generation_tt,
    execute_chart_generation_tt,
    execute_document_generation_tt,
    # 兼容性函数
    analyze_data_tt,
    generate_sql_tt,
)

# 统一 Facade 接口
from .facade import (
    LoomAgentFacade,
    StageAwareFacade,
    create_agent_facade,
    create_stage_aware_facade,
    create_high_performance_facade,
    create_high_performance_stage_aware_facade,
    create_lightweight_facade,
    create_lightweight_stage_aware_facade,
)

# 配置模块
from .config.agent import (
    AgentRuntimeConfig,
    AgentConfigManager,
    create_default_agent_config as create_default_runtime_config,
    create_high_performance_agent_config,
    create_debug_agent_config,
    create_lightweight_agent_config,
)

# 阶段配置
from .config.stage_config import (
    StageConfig,
    StageConfigManager,
    get_stage_config_manager,
    create_custom_stage_config_manager,
)

from .config.coordination import (
    AdvancedCoordinationConfig,
    CoordinationManager,
    create_default_coordination_config as create_default_advanced_coordination_config,
    create_high_performance_config,
    create_debug_config,
)

# 阶段感知的Runtime（三阶段架构）
from .runtime import (
    StageAwareRuntime  # 已在runtime导入中，这里重复声明用于强调
)

# Prompt 模块
from .prompts.system import (
    SystemPromptBuilder,
    create_system_prompt,
    create_context_aware_system_prompt,
    DEFAULT_SYSTEM_PROMPT,
    SCHEMA_DISCOVERY_PROMPT,
    SQL_GENERATION_PROMPT,
    DATA_ANALYSIS_PROMPT,
    CHART_GENERATION_PROMPT,
)

from .prompts.stages import (
    StagePromptManager,
    get_stage_prompt,
    get_transition_prompt,
    get_stage_summary,
    INITIALIZATION_PROMPT,
    SCHEMA_DISCOVERY_PROMPT as STAGE_SCHEMA_DISCOVERY_PROMPT,
    SQL_GENERATION_PROMPT as STAGE_SQL_GENERATION_PROMPT,
    SQL_VALIDATION_PROMPT,
    DATA_EXTRACTION_PROMPT,
    ANALYSIS_PROMPT,
    CHART_GENERATION_PROMPT as STAGE_CHART_GENERATION_PROMPT,
    COMPLETION_PROMPT,
)

from .prompts.templates import (
    PromptTemplate,
    PromptTemplateManager,
    ContextFormatter,
    format_request_prompt,
    format_stage_prompt,
    format_error_prompt,
    format_result_summary,
)

# 版本信息
__version__ = "1.0.0"
__author__ = "AutoReportAI Team"
__description__ = "基于 Loom 0.0.3 的智能 Agent 系统"

logger = logging.getLogger(__name__)


class LoomAgentSystem:
    """
    Loom Agent 系统主类
    
    提供完整的 Agent 系统功能，包括初始化、配置管理和业务接口
    """
    
    def __init__(
        self,
        container: Any,
        config: Optional[AgentConfig] = None,
        auto_initialize: bool = True
    ):
        """
        Args:
            container: 服务容器
            config: Agent 配置
            auto_initialize: 是否自动初始化
        """
        self.container = container
        self.config = config or create_default_agent_config()
        self.auto_initialize = auto_initialize
        
        # 核心组件
        self._facade: Optional[LoomAgentFacade] = None
        self._initialized = False
        
        logger.info("🏗️ [LoomAgentSystem] 系统初始化")
    
    async def initialize(self):
        """初始化系统"""
        if self._initialized:
            return
        
        try:
            logger.info("🚀 [LoomAgentSystem] 开始系统初始化")
            
            # 创建 Facade
            self._facade = create_agent_facade(
                container=self.container,
                config=self.config,
                enable_context_retriever=True
            )
            
            # 初始化 Facade
            await self._facade.initialize()
            
            self._initialized = True
            logger.info("✅ [LoomAgentSystem] 系统初始化完成")
            
        except Exception as e:
            logger.error(f"❌ [LoomAgentSystem] 系统初始化失败: {e}", exc_info=True)
            raise
    
    async def analyze_placeholder(
        self,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        分析占位符
        
        Args:
            placeholder: 占位符文本
            data_source_id: 数据源ID
            user_id: 用户ID
            **kwargs: 其他参数
            
        Yields:
            AgentEvent: 执行事件流
        """
        if not self._initialized:
            await self.initialize()
        
        async for event in self._facade.analyze_placeholder(
            placeholder=placeholder,
            data_source_id=data_source_id,
            user_id=user_id,
            **kwargs
        ):
            yield event
    
    async def analyze_placeholder_sync(
        self,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> AgentResponse:
        """
        同步分析占位符
        
        Args:
            placeholder: 占位符文本
            data_source_id: 数据源ID
            user_id: 用户ID
            **kwargs: 其他参数
            
        Returns:
            AgentResponse: 分析结果
        """
        if not self._initialized:
            await self.initialize()
        
        return await self._facade.analyze_placeholder_sync(
            placeholder=placeholder,
            data_source_id=data_source_id,
            user_id=user_id,
            **kwargs
        )
    
    async def generate_sql(
        self,
        business_requirement: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> str:
        """
        生成 SQL 查询
        
        Args:
            business_requirement: 业务需求描述
            data_source_id: 数据源ID
            user_id: 用户ID
            **kwargs: 其他参数
            
        Returns:
            str: 生成的 SQL 查询
        """
        if not self._initialized:
            await self.initialize()
        
        return await self._facade.generate_sql(
            business_requirement=business_requirement,
            data_source_id=data_source_id,
            user_id=user_id,
            **kwargs
        )
    
    async def analyze_data(
        self,
        sql_query: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        分析数据
        
        Args:
            sql_query: SQL 查询
            data_source_id: 数据源ID
            user_id: 用户ID
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        if not self._initialized:
            await self.initialize()
        
        return await self._facade.analyze_data(
            sql_query=sql_query,
            data_source_id=data_source_id,
            user_id=user_id,
            **kwargs
        )
    
    async def generate_chart(
        self,
        data_summary: str,
        chart_requirements: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成图表配置
        
        Args:
            data_summary: 数据摘要
            chart_requirements: 图表需求
            data_source_id: 数据源ID
            user_id: 用户ID
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 图表配置
        """
        if not self._initialized:
            await self.initialize()
        
        return await self._facade.generate_chart(
            data_summary=data_summary,
            chart_requirements=chart_requirements,
            data_source_id=data_source_id,
            user_id=user_id,
            **kwargs
        )
    
    async def get_schema_info(
        self,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        获取数据源 Schema 信息
        
        Args:
            data_source_id: 数据源ID
            user_id: 用户ID
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: Schema 信息
        """
        if not self._initialized:
            await self.initialize()
        
        return await self._facade.get_schema_info(
            data_source_id=data_source_id,
            user_id=user_id,
            **kwargs
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        if not self._facade:
            return {"initialized": False}
        
        return self._facade.get_metrics()
    
    def get_config(self) -> AgentConfig:
        """获取当前配置"""
        return self.config
    
    def update_config(self, new_config: AgentConfig):
        """更新配置"""
        self.config = new_config
        if self._facade:
            self._facade.update_config(new_config)
        self._initialized = False


def create_agent_system(
    container: Any,
    config: Optional[AgentConfig] = None,
    auto_initialize: bool = True
) -> LoomAgentSystem:
    """
    创建 Agent 系统实例
    
    Args:
        container: 服务容器
        config: Agent 配置
        auto_initialize: 是否自动初始化
        
    Returns:
        LoomAgentSystem 实例
    """
    return LoomAgentSystem(
        container=container,
        config=config,
        auto_initialize=auto_initialize
    )


def create_high_performance_system(container: Any) -> LoomAgentSystem:
    """创建高性能系统"""
    return LoomAgentSystem(
        container=container,
        config=create_high_performance_agent_config(),
        auto_initialize=True
    )


def create_lightweight_system(container: Any) -> LoomAgentSystem:
    """创建轻量级系统"""
    return LoomAgentSystem(
        container=container,
        config=create_lightweight_agent_config(),
        auto_initialize=True
    )


def create_debug_system(container: Any) -> LoomAgentSystem:
    """创建调试系统"""
    return LoomAgentSystem(
        container=container,
        config=create_debug_agent_config(),
        auto_initialize=True
    )


# 便捷函数
async def quick_analyze(
    placeholder: str,
    data_source_id: int,
    user_id: str,
    container: Any,
    config: Optional[AgentConfig] = None
) -> AgentResponse:
    """
    快速分析占位符
    
    Args:
        placeholder: 占位符文本
        data_source_id: 数据源ID
        user_id: 用户ID
        container: 服务容器
        config: Agent 配置
        
    Returns:
        AgentResponse: 分析结果
    """
    system = create_agent_system(container, config)
    return await system.analyze_placeholder_sync(
        placeholder=placeholder,
        data_source_id=data_source_id,
        user_id=user_id
    )


async def quick_generate_sql(
    business_requirement: str,
    data_source_id: int,
    user_id: str,
    container: Any,
    config: Optional[AgentConfig] = None
) -> str:
    """
    快速生成 SQL
    
    Args:
        business_requirement: 业务需求描述
        data_source_id: 数据源ID
        user_id: 用户ID
        container: 服务容器
        config: Agent 配置
        
    Returns:
        str: 生成的 SQL 查询
    """
    system = create_agent_system(container, config)
    return await system.generate_sql(
        business_requirement=business_requirement,
        data_source_id=data_source_id,
        user_id=user_id
    )


# 导出所有公共接口
__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__description__",
    
    # 核心类型
    "ExecutionStage",
    "TaskComplexity",
    "ToolCategory",
    "AgentRequest",
    "AgentResponse",
    "ToolCall",
    "ContextInfo",
    "ExecutionState",
    "CoordinationConfig",
    "LLMConfig",
    "ToolConfig",
    "AgentConfig",
    "AgentEvent",
    "BaseTool",
    "BaseContextRetriever",
    "ToolFactory",
    "ContextRetrieverFactory",
    "EventCallback",
    
    # 工厂函数
    "create_default_agent_config",
    "create_default_coordination_config",
    "create_default_llm_config",
    "create_default_tool_config",
    
    # 核心运行时
    "LoomAgentRuntime",
    "StageAwareRuntime",  # 阶段感知的Runtime
    "build_default_runtime",
    "build_stage_aware_runtime",  # 构建三阶段Runtime
    "create_runtime_with_context_retriever",
    
    # LLM 适配器
    "ContainerLLMAdapter",
    "create_llm_adapter",
    "create_llm_adapter_from_config",
    
    # 上下文检索器
    "SchemaContextRetriever",
    "IntelligentContextRetriever",
    "create_schema_context_retriever",
    "create_intelligent_context_retriever",
    
    # TT递归统一接口
    "execute_tt_recursion",
    "TTRecursionRequest", 
    "TTRecursionResponse",
    # 三步骤Agent专用函数
    "execute_sql_generation_tt",
    "execute_chart_generation_tt", 
    "execute_document_generation_tt",
    # 兼容性函数
    "analyze_data_tt",
    "generate_sql_tt",
    
    # 统一 Facade 接口
    "LoomAgentFacade",
    "StageAwareFacade",  # 三阶段专用Facade
    "create_agent_facade",
    "create_stage_aware_facade",  # 创建三阶段Facade
    "create_high_performance_facade",
    "create_high_performance_stage_aware_facade",
    "create_lightweight_facade",
    "create_lightweight_stage_aware_facade",
    
    # 配置模块
    "AgentRuntimeConfig",
    "AgentConfigManager",
    "create_default_runtime_config",
    "create_high_performance_agent_config",
    "create_debug_agent_config",
    "create_lightweight_agent_config",
    "AdvancedCoordinationConfig",
    "CoordinationManager",
    "create_default_advanced_coordination_config",
    "create_high_performance_config",
    "create_debug_config",
    
    # Prompt 模块
    "SystemPromptBuilder",
    "create_system_prompt",
    "create_context_aware_system_prompt",
    "DEFAULT_SYSTEM_PROMPT",
    "SCHEMA_DISCOVERY_PROMPT",
    "SQL_GENERATION_PROMPT",
    "DATA_ANALYSIS_PROMPT",
    "CHART_GENERATION_PROMPT",
    "StagePromptManager",
    "get_stage_prompt",
    "get_transition_prompt",
    "get_stage_summary",
    "INITIALIZATION_PROMPT",
    "STAGE_SCHEMA_DISCOVERY_PROMPT",
    "STAGE_SQL_GENERATION_PROMPT",
    "SQL_VALIDATION_PROMPT",
    "DATA_EXTRACTION_PROMPT",
    "ANALYSIS_PROMPT",
    "STAGE_CHART_GENERATION_PROMPT",
    "COMPLETION_PROMPT",
    "PromptTemplate",
    "PromptTemplateManager",
    "ContextFormatter",
    "format_request_prompt",
    "format_stage_prompt",
    "format_error_prompt",
    "format_result_summary",
    
    # 阶段配置
    "StageConfig",
    "StageConfigManager",
    "get_stage_config_manager",
    "create_custom_stage_config_manager",

    # 系统主类
    "LoomAgentSystem",
    "create_agent_system",
    "create_high_performance_system",
    "create_lightweight_system",
    "create_debug_system",
    
    # 便捷函数
    "quick_analyze",
    "quick_generate_sql",
]