"""
LLM模块共享类型定义

将共享的数据类移到这里以避免循环导入
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class TaskRequirement:
    """任务需求定义"""
    task_type: str = "general"
    complexity_level: str = "medium"
    complexity: str = "medium"  # 保持兼容性
    domain: str = "general"
    context_length: int = 4000
    response_format: str = "text"
    quality_level: str = "standard"
    requires_reasoning: bool = False
    requires_tool_use: bool = False
    max_tokens: int = 4000
    temperature: float = 0.7
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_type': self.task_type,
            'complexity_level': self.complexity_level,
            'complexity': self.complexity,
            'domain': self.domain,
            'context_length': self.context_length,
            'response_format': self.response_format,
            'quality_level': self.quality_level,
            'requires_reasoning': self.requires_reasoning,
            'requires_tool_use': self.requires_tool_use,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature
        }


@dataclass
class ModelSelection:
    """模型选择结果"""
    model_id: int
    model_name: str
    model_type: str
    server_id: int
    server_name: str
    provider_type: str
    reasoning: str
    confidence: float = 0.8
    fallback_model_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'model_id': self.model_id,
            'model_name': self.model_name,
            'model_type': self.model_type,
            'server_id': self.server_id,
            'server_name': self.server_name,
            'provider_type': self.provider_type,
            'reasoning': self.reasoning,
            'confidence': self.confidence,
            'fallback_model_id': self.fallback_model_id
        }


@dataclass
class LLMExecutionContext:
    """LLM执行上下文"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    task_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'session_id': self.session_id,
            'task_type': self.task_type,
            'metadata': self.metadata or {},
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }