"""
ai_integration 服务模块

提供 ai_integration 相关的业务逻辑处理
"""

# 模块版本
__version__ = "1.0.0"

# 导入核心组件
from .llm_service import AIService, LLMProviderManager, LLMRequest, LLMResponse
from .content_generator import ContentGenerator, GeneratedContent, FormatConfig
from .chart_generator import ChartGenerator, ChartConfig, ChartResult
from .ai_service_enhanced import EnhancedAIService, AIRequest, AIResponse, AIModelType, AIServiceMetrics

# 模块导出
__all__ = [
    "AIService",
    "LLMProviderManager",
    "LLMRequest",
    "LLMResponse",
    "ContentGenerator",
    "GeneratedContent",
    "FormatConfig",
    "ChartGenerator",
    "ChartConfig",
    "ChartResult",
    "EnhancedAIService",
    "AIRequest",
    "AIResponse",
    "AIModelType",
    "AIServiceMetrics"
]