"""
LLM客户端 - 连接独立LLM服务器的客户端库

提供统一的接口来调用独立的LLM服务器
"""

from .client import (
    LLMServerClient,
    LLMClientConfig,
    LLMRequest,
    LLMResponse,
    LLMMessage,
    get_llm_client,
    call_llm,
    call_llm_with_system_prompt,
    reset_llm_client
)

__all__ = [
    'LLMServerClient',
    'LLMClientConfig',
    'LLMRequest',
    'LLMResponse', 
    'LLMMessage',
    'get_llm_client',
    'call_llm',
    'call_llm_with_system_prompt',
    'reset_llm_client'
]