"""
AI Layer

AI层入口，提供完整的人工智能服务：
- core: 核心AI功能 (提示词构建、响应解析等)
- legacy_agents: 旧版代理系统 (向后兼容)
- integration: AI服务集成
- agents: 新版AI代理
"""

# 核心AI功能
from .core import (
    # 提示词构建
    EnhancedPromptType,
    PromptContext, 
    BasePromptBuilder,
    PlaceholderAnalysisPromptBuilder,
    SchemaAnalysisPromptBuilder,
    PromptBuilderFactory,
    build_placeholder_analysis_prompt,
    
    # 响应解析
    ResponseQuality,
    ResponseValidation,
    PlaceholderAnalysisParser, 
    ResponseEnhancer,
    parse_placeholder_analysis_response,
    
    # 原有核心模块
    AIServiceInterface,
    AIResponse,
    PromptContextBuilder,
    AIServiceAdapter,
    ContextManager,
    AgentContext,
    ContextScope,
    ContextAwareAgent,
    get_context_manager,
    PromptEngine,
    PromptTemplate,
    ConversationManager,
    PromptType,
    create_default_prompt_engine,
    AgentRegistry,
    AgentInstance,
    AgentCapability,
    AgentMatcher,
    get_agent_registry,
)

# AI集成服务
from .integration.llm_service import AIService as LLMService
from .integration.ai_service_enhanced import EnhancedAIService


# 新版Agent系统
from .agents.placeholder_sql_agent import PlaceholderSQLAgent, PlaceholderSQLAnalyzer

__all__ = [
    # 核心AI功能 - 增强版
    "EnhancedPromptType",
    "PromptContext", 
    "BasePromptBuilder",
    "PlaceholderAnalysisPromptBuilder",
    "SchemaAnalysisPromptBuilder",
    "PromptBuilderFactory",
    "build_placeholder_analysis_prompt",
    "ResponseQuality",
    "ResponseValidation",
    "PlaceholderAnalysisParser", 
    "ResponseEnhancer",
    "parse_placeholder_analysis_response",
    
    # 核心AI功能 - 原有模块
    "AIServiceInterface",
    "AIResponse",
    "PromptContextBuilder",
    "AIServiceAdapter",
    "ContextManager",
    "AgentContext",
    "ContextScope", 
    "ContextAwareAgent",
    "get_context_manager",
    "PromptEngine",
    "PromptTemplate",
    "ConversationManager",
    "PromptType",
    "create_default_prompt_engine",
    "AgentRegistry",
    "AgentInstance",
    "AgentCapability",
    "AgentMatcher",
    "get_agent_registry",
    
    # AI集成服务
    "LLMService",
    "EnhancedAIService",
    
    # 新版Agent系统
    "PlaceholderSQLAgent",
    "PlaceholderSQLAnalyzer",
]