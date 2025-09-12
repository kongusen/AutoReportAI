"""
Agent Message Types and Core Interfaces
=======================================

Defines the message passing interfaces inspired by Claude Code's novel components.
Supports streaming, progress aggregation, and error handling patterns.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable, AsyncGenerator
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import logging
import weakref

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Message types for agent communication - inspired by Claude Code's MessageType"""
    # Core message types
    AGENT_SPAWN = "agent_spawn"           # Agent creation
    AGENT_READY = "agent_ready"           # Agent ready for work
    AGENT_SHUTDOWN = "agent_shutdown"     # Agent termination
    
    # Task execution
    TASK_REQUEST = "task_request"         # Task assignment
    TASK_PROGRESS = "task_progress"       # Progress updates
    TASK_RESULT = "task_result"           # Task completion
    TASK_ERROR = "task_error"             # Task failure
    
    # Inter-agent communication
    MESSAGE_SEND = "message_send"         # Agent-to-agent message
    MESSAGE_BROADCAST = "message_broadcast"  # Broadcast message
    MESSAGE_REPLY = "message_reply"       # Reply to message
    
    # Streaming and real-time updates
    STREAM_START = "stream_start"         # Stream initialization
    STREAM_CHUNK = "stream_chunk"         # Streaming data chunk
    STREAM_END = "stream_end"             # Stream completion
    STREAM_ERROR = "stream_error"         # Stream error
    
    # System coordination
    HEARTBEAT = "heartbeat"               # Keep-alive signal
    STATUS_UPDATE = "status_update"       # Status information
    RESOURCE_REQUEST = "resource_request" # Resource allocation request
    RESOURCE_RESPONSE = "resource_response"  # Resource allocation response
    
    # Error handling and recovery
    ERROR_REPORT = "error_report"         # Error notification
    RECOVERY_ATTEMPT = "recovery_attempt" # Recovery action
    RECOVERY_SUCCESS = "recovery_success" # Recovery completed
    RECOVERY_FAILED = "recovery_failed"   # Recovery failed


class MessagePriority(Enum):
    """Message priority levels for queue management"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class AgentState(Enum):
    """Agent lifecycle states"""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    WAITING = "waiting"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class MessageMetadata:
    """Message metadata for routing and processing"""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sequence_number: int = 0
    retry_count: int = 0
    max_retries: int = 3
    ttl_seconds: Optional[int] = None
    routing_key: Optional[str] = None
    reply_to: Optional[str] = None
    content_type: str = "application/json"
    compression: Optional[str] = None
    
    # Performance tracking
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    processing_time_ms: Optional[float] = None
    
    # Custom headers
    headers: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if message has expired"""
        if self.ttl_seconds is None:
            return False
        return datetime.utcnow() > self.created_at + timedelta(seconds=self.ttl_seconds)

    def should_retry(self) -> bool:
        """Check if message should be retried"""
        return self.retry_count < self.max_retries

    def mark_processed(self):
        """Mark message as processed and calculate processing time"""
        self.processed_at = datetime.utcnow()
        if self.created_at:
            self.processing_time_ms = (self.processed_at - self.created_at).total_seconds() * 1000


@dataclass
class AgentMessage:
    """
    Core agent message - inspired by Claude Code's StreamMessage
    Supports streaming, error recovery, and progress tracking
    """
    # Core identification
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.MESSAGE_SEND
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Agent routing
    from_agent: str = ""
    to_agent: str = ""
    agent_group: Optional[str] = None
    
    # Message content
    payload: Any = None
    content_hash: Optional[str] = None
    
    # Message control
    priority: MessagePriority = MessagePriority.NORMAL
    metadata: MessageMetadata = field(default_factory=MessageMetadata)
    
    # Streaming support (inspired by Claude Code's streaming patterns)
    is_streaming: bool = False
    stream_id: Optional[str] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    
    # Progress tracking
    progress: Optional[float] = None  # 0.0 - 1.0
    progress_info: Dict[str, Any] = field(default_factory=dict)
    
    # Error handling
    error_info: Optional[Dict[str, Any]] = None
    recovery_suggestions: List[str] = field(default_factory=list)
    
    # Quality and validation
    confidence: Optional[float] = None
    validation_passed: bool = True
    quality_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp.isoformat(),
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "agent_group": self.agent_group,
            "payload": self.payload,
            "content_hash": self.content_hash,
            "priority": self.priority.value,
            "metadata": {
                "correlation_id": self.metadata.correlation_id,
                "sequence_number": self.metadata.sequence_number,
                "retry_count": self.metadata.retry_count,
                "max_retries": self.metadata.max_retries,
                "ttl_seconds": self.metadata.ttl_seconds,
                "routing_key": self.metadata.routing_key,
                "reply_to": self.metadata.reply_to,
                "content_type": self.metadata.content_type,
                "compression": self.metadata.compression,
                "created_at": self.metadata.created_at.isoformat(),
                "processed_at": self.metadata.processed_at.isoformat() if self.metadata.processed_at else None,
                "processing_time_ms": self.metadata.processing_time_ms,
                "headers": self.metadata.headers
            },
            "is_streaming": self.is_streaming,
            "stream_id": self.stream_id,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "progress": self.progress,
            "progress_info": self.progress_info,
            "error_info": self.error_info,
            "recovery_suggestions": self.recovery_suggestions,
            "confidence": self.confidence,
            "validation_passed": self.validation_passed,
            "quality_score": self.quality_score
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Create message from dictionary"""
        metadata_data = data.get("metadata", {})
        metadata = MessageMetadata(
            correlation_id=metadata_data.get("correlation_id", str(uuid.uuid4())),
            sequence_number=metadata_data.get("sequence_number", 0),
            retry_count=metadata_data.get("retry_count", 0),
            max_retries=metadata_data.get("max_retries", 3),
            ttl_seconds=metadata_data.get("ttl_seconds"),
            routing_key=metadata_data.get("routing_key"),
            reply_to=metadata_data.get("reply_to"),
            content_type=metadata_data.get("content_type", "application/json"),
            compression=metadata_data.get("compression"),
            created_at=datetime.fromisoformat(metadata_data["created_at"]) if "created_at" in metadata_data else datetime.utcnow(),
            headers=metadata_data.get("headers", {})
        )
        
        if "processed_at" in metadata_data and metadata_data["processed_at"]:
            metadata.processed_at = datetime.fromisoformat(metadata_data["processed_at"])
        if "processing_time_ms" in metadata_data:
            metadata.processing_time_ms = metadata_data["processing_time_ms"]
        
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            message_type=MessageType(data.get("message_type", MessageType.MESSAGE_SEND.value)),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            from_agent=data.get("from_agent", ""),
            to_agent=data.get("to_agent", ""),
            agent_group=data.get("agent_group"),
            payload=data.get("payload"),
            content_hash=data.get("content_hash"),
            priority=MessagePriority(data.get("priority", MessagePriority.NORMAL.value)),
            metadata=metadata,
            is_streaming=data.get("is_streaming", False),
            stream_id=data.get("stream_id"),
            chunk_index=data.get("chunk_index"),
            total_chunks=data.get("total_chunks"),
            progress=data.get("progress"),
            progress_info=data.get("progress_info", {}),
            error_info=data.get("error_info"),
            recovery_suggestions=data.get("recovery_suggestions", []),
            confidence=data.get("confidence"),
            validation_passed=data.get("validation_passed", True),
            quality_score=data.get("quality_score")
        )

    def create_reply(self, payload: Any = None, message_type: MessageType = MessageType.MESSAGE_REPLY) -> 'AgentMessage':
        """Create a reply message"""
        return AgentMessage(
            message_type=message_type,
            from_agent=self.to_agent,  # Swap from/to
            to_agent=self.from_agent,
            payload=payload,
            metadata=MessageMetadata(
                correlation_id=self.metadata.correlation_id,
                reply_to=self.message_id
            )
        )

    def create_progress_update(self, progress: float, progress_info: Dict[str, Any] = None) -> 'AgentMessage':
        """Create a progress update message"""
        return AgentMessage(
            message_type=MessageType.TASK_PROGRESS,
            from_agent=self.to_agent,
            to_agent=self.from_agent,
            payload={"original_task": self.message_id},
            progress=progress,
            progress_info=progress_info or {},
            metadata=MessageMetadata(
                correlation_id=self.metadata.correlation_id
            )
        )

    def is_expired(self) -> bool:
        """Check if message has expired"""
        return self.metadata.is_expired()

    def should_retry(self) -> bool:
        """Check if message should be retried"""
        return self.metadata.should_retry()


@dataclass
class StreamingMessage:
    """
    Streaming message chunk - for large data streams
    Inspired by Claude Code's streaming JSON parser
    """
    stream_id: str
    chunk_index: int
    total_chunks: Optional[int] = None
    data: Any = None
    is_final: bool = False
    compression: Optional[str] = None
    checksum: Optional[str] = None
    
    def to_agent_message(self, from_agent: str, to_agent: str) -> AgentMessage:
        """Convert to AgentMessage"""
        return AgentMessage(
            message_type=MessageType.STREAM_CHUNK if not self.is_final else MessageType.STREAM_END,
            from_agent=from_agent,
            to_agent=to_agent,
            payload=self.data,
            is_streaming=True,
            stream_id=self.stream_id,
            chunk_index=self.chunk_index,
            total_chunks=self.total_chunks,
            metadata=MessageMetadata(compression=self.compression)
        )


class MessagePattern:
    """
    Message pattern matching for routing and filtering
    Inspired by Claude Code's permission rule compilation
    """
    
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.compiled_pattern = self._compile_pattern(pattern)
    
    def _compile_pattern(self, pattern: str) -> Dict[str, Any]:
        """Compile pattern for efficient matching"""
        # Pattern format: "type:from_agent->to_agent[priority]"
        # Examples:
        # - "task_request:*->agent1" (any agent to agent1 for task requests)
        # - "message_send:agent1->*[HIGH]" (agent1 to any agent with high priority)
        # - "*:*->group1" (any message to group1)
        
        parts = pattern.split('[')
        main_pattern = parts[0]
        priority_filter = parts[1].rstrip(']') if len(parts) > 1 else None
        
        type_and_route = main_pattern.split(':')
        msg_type = type_and_route[0] if len(type_and_route) > 0 else '*'
        route = type_and_route[1] if len(type_and_route) > 1 else '*->*'
        
        route_parts = route.split('->')
        from_pattern = route_parts[0] if len(route_parts) > 0 else '*'
        to_pattern = route_parts[1] if len(route_parts) > 1 else '*'
        
        return {
            'msg_type': msg_type,
            'from_pattern': from_pattern,
            'to_pattern': to_pattern,
            'priority_filter': priority_filter,
            'original_pattern': pattern
        }
    
    def matches(self, message: AgentMessage) -> bool:
        """Check if message matches this pattern"""
        compiled = self.compiled_pattern
        
        # Check message type
        if compiled['msg_type'] != '*' and compiled['msg_type'] != message.message_type.value:
            return False
        
        # Check from agent
        if compiled['from_pattern'] != '*' and not self._pattern_matches(compiled['from_pattern'], message.from_agent):
            return False
        
        # Check to agent
        if compiled['to_pattern'] != '*' and not self._pattern_matches(compiled['to_pattern'], message.to_agent):
            return False
        
        # Check priority
        if compiled['priority_filter'] and compiled['priority_filter'] != message.priority.name:
            return False
        
        return True
    
    def _pattern_matches(self, pattern: str, value: str) -> bool:
        """Check if value matches pattern (supports wildcards)"""
        if pattern == '*':
            return True
        if pattern == value:
            return True
        
        # Simple wildcard support
        if '*' in pattern:
            import re
            regex_pattern = pattern.replace('*', '.*')
            return bool(re.match(f'^{regex_pattern}$', value))
        
        return False


class MessageHandler:
    """Base class for message handlers"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.patterns: List[MessagePattern] = []
        self.is_active = True
    
    def add_pattern(self, pattern: str):
        """Add a message pattern to handle"""
        self.patterns.append(MessagePattern(pattern))
    
    def can_handle(self, message: AgentMessage) -> bool:
        """Check if this handler can handle the message"""
        if not self.is_active:
            return False
        
        if not self.patterns:
            return True  # Handle all messages if no patterns specified
        
        return any(pattern.matches(message) for pattern in self.patterns)
    
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle the message - override in subclasses"""
        raise NotImplementedError("Subclasses must implement handle_message")


# Convenience functions for creating common message types

def create_task_request(from_agent: str, to_agent: str, task_data: Any, priority: MessagePriority = MessagePriority.NORMAL) -> AgentMessage:
    """Create a task request message"""
    return AgentMessage(
        message_type=MessageType.TASK_REQUEST,
        from_agent=from_agent,
        to_agent=to_agent,
        payload=task_data,
        priority=priority
    )

def create_progress_message(from_agent: str, to_agent: str, progress: float, info: Dict[str, Any] = None) -> AgentMessage:
    """Create a progress update message"""
    return AgentMessage(
        message_type=MessageType.TASK_PROGRESS,
        from_agent=from_agent,
        to_agent=to_agent,
        progress=progress,
        progress_info=info or {}
    )

def create_result_message(from_agent: str, to_agent: str, result: Any, confidence: float = None) -> AgentMessage:
    """Create a task result message"""
    return AgentMessage(
        message_type=MessageType.TASK_RESULT,
        from_agent=from_agent,
        to_agent=to_agent,
        payload=result,
        confidence=confidence
    )

def create_error_message(from_agent: str, to_agent: str, error: str, recovery_suggestions: List[str] = None) -> AgentMessage:
    """Create an error message"""
    return AgentMessage(
        message_type=MessageType.TASK_ERROR,
        from_agent=from_agent,
        to_agent=to_agent,
        payload=error,
        error_info={"error": error},
        recovery_suggestions=recovery_suggestions or []
    )

def create_heartbeat(agent_id: str, status: Dict[str, Any] = None) -> AgentMessage:
    """Create a heartbeat message"""
    return AgentMessage(
        message_type=MessageType.HEARTBEAT,
        from_agent=agent_id,
        to_agent="system",
        payload=status or {}
    )

def create_broadcast(from_agent: str, group: str, payload: Any) -> AgentMessage:
    """Create a broadcast message"""
    return AgentMessage(
        message_type=MessageType.MESSAGE_BROADCAST,
        from_agent=from_agent,
        to_agent="",
        agent_group=group,
        payload=payload
    )


# Export main classes and functions
__all__ = [
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
]