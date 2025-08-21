from .interfaces import AIServiceInterface, AIResponse
from .context import PromptContextBuilder
from .adapter import AIServiceAdapter

# 新的上下文工程模块
from .context_manager import (
    ContextManager, AgentContext, ContextScope, ContextAwareAgent,
    get_context_manager
)
from .prompt_engine import (
    PromptEngine, PromptTemplate, ConversationManager,
    PromptType, create_default_prompt_engine
)
from .agent_registry import (
    AgentRegistry, AgentInstance, AgentCapability, AgentMatcher,
    get_agent_registry
)

# 增强版AI核心模块
from .prompt_builder import (
    PromptType as EnhancedPromptType,
    PromptContext,
    BasePromptBuilder,
    PlaceholderAnalysisPromptBuilder,
    SchemaAnalysisPromptBuilder,
    PromptBuilderFactory,
    build_placeholder_analysis_prompt
)

from .response_parser import (
    ResponseQuality,
    ResponseValidation,
    PlaceholderAnalysisParser,
    ResponseEnhancer,
    parse_placeholder_analysis_response
)

__all__ = [
    # 原有模块
    "AIServiceInterface",
    "AIResponse", 
    "PromptContextBuilder",
    "AIServiceAdapter",
    
    # 上下文工程模块
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
    
    # 增强版AI核心模块
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
    "parse_placeholder_analysis_response"
]


