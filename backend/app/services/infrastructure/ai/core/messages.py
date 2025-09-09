"""
统一消息格式 - 类似 Claude Code 的消息系统
"""

import uuid
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class MessageType(Enum):
    """消息类型"""
    PROGRESS = "progress"
    RESULT = "result" 
    ERROR = "error"
    TOOL_CALL = "tool_call"
    STATUS = "status"


@dataclass
class ProgressData:
    """进度数据"""
    current_step: str
    total_steps: Optional[int] = None
    current_step_number: Optional[int] = None
    percentage: Optional[float] = None
    details: Optional[str] = None


@dataclass  
class ErrorData:
    """错误数据"""
    error_type: str
    error_message: str
    error_code: Optional[str] = None
    stacktrace: Optional[str] = None
    recoverable: bool = True


@dataclass
class AgentMessage:
    """统一的Agent消息格式"""
    type: MessageType
    uuid: str
    timestamp: str
    
    # 内容载荷
    content: Optional[Dict[str, Any]] = None
    progress: Optional[ProgressData] = None
    error: Optional[ErrorData] = None
    
    # 元数据
    tool_name: Optional[str] = None
    user_id: Optional[str] = None
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    
    @classmethod
    def create_progress(
        cls,
        current_step: str,
        user_id: str,
        task_id: str,
        total_steps: Optional[int] = None,
        current_step_number: Optional[int] = None,
        percentage: Optional[float] = None,
        details: Optional[str] = None,
        tool_name: Optional[str] = None
    ) -> "AgentMessage":
        """创建进度消息"""
        return cls(
            type=MessageType.PROGRESS,
            uuid=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            progress=ProgressData(
                current_step=current_step,
                total_steps=total_steps,
                current_step_number=current_step_number,
                percentage=percentage,
                details=details
            ),
            user_id=user_id,
            task_id=task_id,
            tool_name=tool_name
        )
    
    @classmethod
    def create_result(
        cls,
        content: Dict[str, Any],
        user_id: str,
        task_id: str,
        tool_name: Optional[str] = None
    ) -> "AgentMessage":
        """创建结果消息"""
        return cls(
            type=MessageType.RESULT,
            uuid=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            content=content,
            user_id=user_id,
            task_id=task_id,
            tool_name=tool_name
        )
    
    @classmethod
    def create_error(
        cls,
        error_type: str,
        error_message: str,
        user_id: str,
        task_id: str,
        error_code: Optional[str] = None,
        stacktrace: Optional[str] = None,
        recoverable: bool = True,
        tool_name: Optional[str] = None
    ) -> "AgentMessage":
        """创建错误消息"""
        return cls(
            type=MessageType.ERROR,
            uuid=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            error=ErrorData(
                error_type=error_type,
                error_message=error_message,
                error_code=error_code,
                stacktrace=stacktrace,
                recoverable=recoverable
            ),
            user_id=user_id,
            task_id=task_id,
            tool_name=tool_name
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于JSON序列化"""
        result = {
            "type": self.type.value,
            "uuid": self.uuid,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "tool_name": self.tool_name
        }
        
        if self.content:
            result["content"] = self.content
        
        if self.progress:
            result["progress"] = {
                "current_step": self.progress.current_step,
                "total_steps": self.progress.total_steps,
                "current_step_number": self.progress.current_step_number,
                "percentage": self.progress.percentage,
                "details": self.progress.details
            }
        
        if self.error:
            result["error"] = {
                "error_type": self.error.error_type,
                "error_message": self.error.error_message,
                "error_code": self.error.error_code,
                "stacktrace": self.error.stacktrace,
                "recoverable": self.error.recoverable
            }
        
        return result