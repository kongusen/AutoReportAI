"""
LLM协议适配器模块
================

支持多种LLM API协议的适配器，包括OpenAI、Azure OpenAI等
提供统一的接口和JSON输出控制
"""

from enum import Enum
from typing import Any

from .openai_adapter import (
    OpenAIAdapter,
    OpenAIModel,
    ResponseFormat,
    OpenAIConfig,
    create_openai_adapter
)

# 协议类型枚举
class ProtocolType(Enum):
    """协议类型枚举"""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


# 协议适配器工厂
class ProtocolAdapterFactory:
    """协议适配器工厂"""
    
    @staticmethod
    def create_adapter(protocol_type: ProtocolType, **kwargs) -> Any:
        """创建协议适配器"""
        if protocol_type == ProtocolType.OPENAI:
            return OpenAIAdapter(**kwargs)
        elif protocol_type == ProtocolType.AZURE_OPENAI:
            # 未来支持Azure OpenAI
            raise NotImplementedError("Azure OpenAI adapter not implemented yet")
        elif protocol_type == ProtocolType.ANTHROPIC:
            # 未来支持Anthropic
            raise NotImplementedError("Anthropic adapter not implemented yet")
        else:
            raise ValueError(f"Unsupported protocol type: {protocol_type}")


__all__ = [
    # OpenAI适配器
    "OpenAIAdapter",
    "OpenAIModel", 
    "ResponseFormat",
    "OpenAIConfig",
    "create_openai_adapter",
    
    # 协议类型
    "ProtocolType",
    
    # 工厂
    "ProtocolAdapterFactory"
]