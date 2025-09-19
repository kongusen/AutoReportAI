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
    complexity: str
    domain: str
    context_length: int
    response_format: str
    quality_level: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'complexity': self.complexity,
            'domain': self.domain,
            'context_length': self.context_length,
            'response_format': self.response_format,
            'quality_level': self.quality_level
        }


@dataclass
class ModelSelection:
    """模型选择结果"""
    server_id: int
    model_id: int
    server_name: str
    model_name: str
    reasoning: str
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'server_id': self.server_id,
            'model_id': self.model_id,
            'server_name': self.server_name,
            'model_name': self.model_name,
            'reasoning': self.reasoning,
            'confidence': self.confidence
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