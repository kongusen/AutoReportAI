"""
Agents 核心模块
==============

包含Agent系统的核心组件：
- 消息传递系统
- Agent协调器
- 内存管理
- 进度聚合
- 流式解析
- 错误处理
"""

from .main import AgentCoordinator
from .message_types import (
    MessageType,
    MessagePriority,
    AgentState,
    MessageMetadata,
    AgentMessage,
    StreamingMessage,
    MessagePattern,
    MessageHandler,
    create_task_request,
    create_progress_message,
    create_result_message,
    create_error_message,
    create_heartbeat,
    create_broadcast
)
from .message_bus import (
    MessageBus,
    create_message_bus,
    create_simple_handler,
    RoutingStrategy,
    DeliveryGuarantee
)
from .memory_manager import (
    MemoryManager,
    create_memory_manager
)
from .progress_aggregator import (
    ProgressAggregator,
    create_simple_aggregator,
    AggregationStrategy,
    AgentProgress
)
from .streaming_parser import (
    StreamingMessageParser,
    parse_single_message
)
from .error_formatter import (
    ErrorFormatter,
    create_error_message as format_error
)

from .message_processor import (
    MessageProcessor, StructuredMessage, ProcessedContent,
    InputType, ContentType, process_user_message
)

__all__ = [
    # 核心协调器
    "AgentCoordinator",
    
    # 消息系统
    "MessageType",
    "MessagePriority", 
    "AgentState",
    "MessageMetadata",
    "AgentMessage",
    "StreamingMessage",
    "MessagePattern",
    "MessageHandler",
    "create_task_request",
    "create_progress_message",
    "create_result_message",
    "create_error_message",
    "create_heartbeat", 
    "create_broadcast",
    
    # 消息总线
    "MessageBus",
    "create_message_bus",
    "create_simple_handler",
    "RoutingStrategy",
    "DeliveryGuarantee",
    
    # 内存管理
    "MemoryManager",
    "create_memory_manager",
    
    # 进度聚合
    "ProgressAggregator",
    "create_simple_aggregator",
    "AggregationStrategy",
    "AgentProgress",
    
    # 流式解析
    "StreamingMessageParser", 
    "parse_single_message",
    
    # 错误处理
    "ErrorFormatter",
    "format_error",
    
    # 消息处理器
    "MessageProcessor",
    "StructuredMessage",
    "ProcessedContent",
    "InputType",
    "ContentType",
    "process_user_message"
]