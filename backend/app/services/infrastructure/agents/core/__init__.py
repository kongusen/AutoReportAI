"""
Agent Core - Clean Architecture
==============================

核心Agent系统的简洁架构实现。

模块组织：
- coordinator: 核心协调器
- tt_controller: TT控制循环
- message_*: 消息系统
- memory_manager: 内存管理
- progress_aggregator: 进度聚合
- error_formatter: 错误格式化
"""

# 核心协调器 - 新的清洁架构
from .coordinator import AgentCoordinator, get_coordinator, shutdown_coordinator

# TT控制循环
from .tt_controller import (
    TTController, TTContext, TTLoopState, TTEvent, TTEventType
)

# 消息系统
from .message_types import (
    AgentMessage, MessageType, MessagePriority,
    create_task_request, create_progress_message, create_result_message
)

from .message_bus import MessageBus

# 核心组件
from .memory_manager import MemoryManager
from .progress_aggregator import ProgressAggregator
from .streaming_parser import StreamingMessageParser
from .error_formatter import ErrorFormatter

__all__ = [
    # 核心协调器
    "AgentCoordinator",
    "get_coordinator", 
    "shutdown_coordinator",
    
    # TT控制循环
    "TTController",
    "TTContext",
    "TTLoopState", 
    "TTEvent",
    "TTEventType",
    
    # 消息系统
    "AgentMessage",
    "MessageType",
    "MessagePriority",
    "create_task_request",
    "create_progress_message", 
    "create_result_message",
    "MessageBus",
    
    # 核心组件
    "MemoryManager",
    "ProgressAggregator",
    "StreamingMessageParser",
    "ErrorFormatter",
]