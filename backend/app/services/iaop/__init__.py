"""
IAOP (Intelligent Agent Orchestration Platform) 架构

智能Agent编排平台，提供统一的Agent管理、上下文处理和任务编排能力

完整的架构包括：
- 核心基础设施（服务工厂、配置管理、中间件、钩子）
- Agent系统（注册器、基础Agent、专用Agent）
- 上下文管理和任务编排
- API接口层
"""

# 导出核心基础设施
from .core import (
    # 服务工厂
    ServiceFactory,
    IAOPServiceFactory,
    get_service_factory,
    initialize_iaop_services,
    shutdown_iaop_services,
    
    # 配置管理（简化版）
    settings,
    get_config_manager,
    get_config,
    load_default_config,
    
    # 中间件和钩子
    MiddlewareManager,
    HookManager,
    get_middleware_manager,
    get_hook_manager,
    setup_common_hooks
)

# 导出集成器
from .core.integration import (
    IAOPIntegrator,
    get_iaop_integrator,
    initialize_iaop_system,
    shutdown_iaop_system,
    with_iaop_context
)

# 导出核心组件
from .context.context_manager import IAOPContextManager, get_iaop_context_manager
from .registry.agent_registry import IAOPAgentRegistry, get_iaop_agent_registry
from .orchestration.engine import OrchestrationEngine, get_orchestration_engine

# 导出基础Agent
from .agents.base import BaseAgent, AgentCapabilities, AgentType, ExecutionContext

# 导出专用Agent
from .agents.specialized import (
    PlaceholderParserAgent,
    DataQueryAgent,
    DataAnalysisAgent,
    ChartGeneratorAgent,
    InsightNarratorAgent,
    register_all_specialized_agents
)

# 导出API层
from .api import (
    IAOPService,
    get_iaop_service,
    create_iaop_router,
    get_iaop_router
)

__all__ = [
    # 核心基础设施
    'ServiceFactory',
    'IAOPServiceFactory',
    'get_service_factory',
    'initialize_iaop_services',
    'shutdown_iaop_services',
    # 配置类已集成到系统配置中
    'get_config_manager',
    'get_config',
    'load_default_config',
    'MiddlewareManager',
    'HookManager',
    'get_middleware_manager',
    'get_hook_manager',
    'setup_common_hooks',
    
    # 集成器
    'IAOPIntegrator',
    'get_iaop_integrator',
    'initialize_iaop_system',
    'shutdown_iaop_system',
    'with_iaop_context',
    
    # 核心组件
    'IAOPContextManager',
    'IAOPAgentRegistry', 
    'OrchestrationEngine',
    'get_iaop_context_manager',
    'get_iaop_agent_registry',
    'get_orchestration_engine',
    
    # 基础Agent
    'BaseAgent',
    'AgentCapabilities',
    'AgentType',
    'ExecutionContext',
    
    # 专用Agent
    'PlaceholderParserAgent',
    'DataQueryAgent',
    'DataAnalysisAgent', 
    'ChartGeneratorAgent',
    'InsightNarratorAgent',
    'register_all_specialized_agents',
    
    # API层
    'IAOPService',
    'get_iaop_service',
    'create_iaop_router',
    'get_iaop_router'
]