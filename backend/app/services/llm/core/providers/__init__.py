"""
LLM提供商实现

支持的提供商：
- OpenAI (GPT系列)
- Anthropic (Claude系列)
- Google (Gemini系列) 
- Ollama (本地模型)
"""

from .base import BaseLLMProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .google_provider import GoogleProvider
from .ollama_provider import OllamaProvider

from ..models import ProviderType

# 提供商类型映射
PROVIDER_CLASSES = {
    ProviderType.OPENAI: OpenAIProvider,
    ProviderType.ANTHROPIC: AnthropicProvider,
    ProviderType.GOOGLE: GoogleProvider,
    ProviderType.OLLAMA: OllamaProvider,
    ProviderType.AZURE_OPENAI: OpenAIProvider,  # 使用OpenAI兼容的实现
}


def get_provider_class(provider_type: ProviderType):
    """根据类型获取提供商类"""
    return PROVIDER_CLASSES.get(provider_type)


__all__ = [
    'BaseLLMProvider',
    'OpenAIProvider', 
    'AnthropicProvider',
    'GoogleProvider',
    'OllamaProvider',
    'get_provider_class',
    'PROVIDER_CLASSES'
]