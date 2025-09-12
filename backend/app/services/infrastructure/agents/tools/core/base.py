"""
Core Tool Base Classes and Interfaces
=====================================

Defines the fundamental interfaces and base classes for the agent tool system,
inspired by Claude Code's tool architecture.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator, Union, Callable, TypeVar, Generic
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
import json
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ToolCategory(Enum):
    """Tool categories for organization and filtering"""
    DATA = "data"
    SYSTEM = "system"
    AI = "ai"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    ORCHESTRATION = "orchestration"
    UTILITY = "utility"
    SECURITY = "security"


class ToolPriority(Enum):
    """Tool execution priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


class ToolPermission(Enum):
    """Tool permission levels"""
    READ_ONLY = "read_only"
    WRITE_LIMITED = "write_limited"
    WRITE_FULL = "write_full"
    SYSTEM_ACCESS = "system_access"
    NETWORK_ACCESS = "network_access"
    ADMIN = "admin"


class ToolError(Exception):
    """Base exception for tool-related errors"""
    
    def __init__(self, message: str, tool_name: str = None, error_code: str = None, context: Dict[str, Any] = None):
        super().__init__(message)
        self.tool_name = tool_name
        self.error_code = error_code
        self.context = context or {}
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'error': str(self),
            'tool_name': self.tool_name,
            'error_code': self.error_code,
            'context': self.context,
            'timestamp': self.timestamp.isoformat()
        }


class ValidationError(ToolError):
    """Input validation error"""
    pass


class PermissionError(ToolError):
    """Permission denied error"""
    pass


class ExecutionError(ToolError):
    """Tool execution error"""
    pass


class TimeoutError(ToolError):
    """Tool execution timeout error"""
    pass


@dataclass
class ToolExecutionContext:
    """Context for tool execution"""
    tool_use_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = "unknown"
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    
    # Execution environment
    working_directory: str = "."
    environment_variables: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    
    # Security context
    permissions: List[ToolPermission] = field(default_factory=list)
    allowed_paths: List[str] = field(default_factory=list)
    denied_patterns: List[str] = field(default_factory=list)
    
    # Shared state
    shared_data: Dict[str, Any] = field(default_factory=dict)
    file_cache: Dict[str, Any] = field(default_factory=dict)
    
    # Progress and cancellation
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    cancellation_token: Optional[asyncio.Event] = None
    
    # Metrics
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    execution_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def is_cancelled(self) -> bool:
        """Check if execution should be cancelled"""
        return self.cancellation_token and self.cancellation_token.is_set()
    
    def report_progress(self, progress_data: Dict[str, Any]):
        """Report execution progress"""
        if self.progress_callback:
            try:
                self.progress_callback({
                    'tool_use_id': self.tool_use_id,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    **progress_data
                })
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    def add_metric(self, key: str, value: Any):
        """Add execution metric"""
        self.execution_metrics[key] = value
    
    def get_elapsed_time(self) -> float:
        """Get elapsed execution time in seconds"""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()


@dataclass
class ToolResult:
    """Result of tool execution"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # Metadata
    tool_name: str = ""
    tool_use_id: str = ""
    execution_time_ms: float = 0
    tokens_used: int = 0
    
    # Output formatting
    content_type: str = "text"
    formatted_output: Optional[str] = None
    
    # Streaming support
    is_partial: bool = False
    sequence_number: int = 0
    
    # Metrics and diagnostics
    metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'error_details': self.error_details,
            'tool_name': self.tool_name,
            'tool_use_id': self.tool_use_id,
            'execution_time_ms': self.execution_time_ms,
            'tokens_used': self.tokens_used,
            'content_type': self.content_type,
            'formatted_output': self.formatted_output,
            'is_partial': self.is_partial,
            'sequence_number': self.sequence_number,
            'metrics': self.metrics,
            'warnings': self.warnings
        }
    
    def add_warning(self, message: str):
        """Add a warning message"""
        self.warnings.append(message)
        logger.warning(f"Tool {self.tool_name}: {message}")


class ToolInputSchema(BaseModel):
    """Base class for tool input validation schemas"""
    
    class Config:
        extra = "forbid"  # Strict input validation
        validate_assignment = True


class ToolDefinition(BaseModel):
    """Definition of a tool with metadata and validation"""
    
    # Basic info
    name: str = Field(..., description="Unique tool name")
    description: str = Field(..., description="Tool description for LLM")
    version: str = Field(default="1.0.0", description="Tool version")
    
    # Categorization
    category: ToolCategory = Field(..., description="Tool category")
    priority: ToolPriority = Field(default=ToolPriority.NORMAL, description="Default priority")
    permissions: List[ToolPermission] = Field(default_factory=list, description="Required permissions")
    
    # Input/Output
    input_schema: Optional[type] = Field(None, description="Pydantic input schema class")
    output_description: str = Field(default="", description="Description of tool output")
    
    # Execution properties
    is_read_only: bool = Field(default=True, description="Whether tool only reads data")
    supports_streaming: bool = Field(default=False, description="Whether tool supports streaming")
    supports_cancellation: bool = Field(default=True, description="Whether tool supports cancellation")
    
    # Performance hints
    typical_execution_time_ms: int = Field(default=1000, description="Typical execution time")
    memory_intensive: bool = Field(default=False, description="Whether tool uses significant memory")
    cpu_intensive: bool = Field(default=False, description="Whether tool is CPU intensive")
    
    # Documentation
    examples: List[Dict[str, Any]] = Field(default_factory=list, description="Usage examples")
    limitations: List[str] = Field(default_factory=list, description="Known limitations")
    see_also: List[str] = Field(default_factory=list, description="Related tools")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Tool name must be alphanumeric with underscores/hyphens')
        return v
    
    def to_llm_description(self) -> str:
        """Generate description for LLM consumption"""
        desc = [f"# {self.name}"]
        desc.append(f"**Category**: {self.category.value}")
        desc.append(f"**Description**: {self.description}")
        
        if self.permissions:
            perms = [p.value for p in self.permissions]
            desc.append(f"**Permissions Required**: {', '.join(perms)}")
        
        if self.is_read_only:
            desc.append("**Read-only**: This tool does not modify data")
        
        if self.supports_streaming:
            desc.append("**Streaming**: This tool supports progress updates")
        
        if self.limitations:
            desc.append("**Limitations**:")
            for limitation in self.limitations:
                desc.append(f"- {limitation}")
        
        if self.examples:
            desc.append("**Examples**:")
            for i, example in enumerate(self.examples[:3], 1):  # Limit to 3 examples
                desc.append(f"{i}. {json.dumps(example, indent=2)}")
        
        return "\n".join(desc)


class AgentTool(ABC):
    """
    Abstract base class for all agent tools
    
    Inspired by Claude Code's tool architecture with async generators
    for streaming progress and results.
    """
    
    def __init__(self, definition: ToolDefinition):
        self.definition = definition
        self.logger = logging.getLogger(f"tool.{definition.name}")
    
    @property
    def name(self) -> str:
        return self.definition.name
    
    @property
    def category(self) -> ToolCategory:
        return self.definition.category
    
    @property
    def permissions(self) -> List[ToolPermission]:
        return self.definition.permissions
    
    @abstractmethod
    async def validate_input(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        """
        Validate and normalize input data
        
        Args:
            input_data: Raw input data
            context: Execution context
            
        Returns:
            Validated and normalized input data
            
        Raises:
            ValidationError: If input is invalid
        """
        pass
    
    @abstractmethod
    async def check_permissions(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> bool:
        """
        Check if the tool can be executed with given permissions
        
        Args:
            input_data: Validated input data
            context: Execution context
            
        Returns:
            True if execution is allowed
            
        Raises:
            PermissionError: If permission is denied
        """
        pass
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """
        Execute the tool with streaming progress updates
        
        Args:
            input_data: Validated input data
            context: Execution context
            
        Yields:
            ToolResult objects for progress updates and final result
            
        Raises:
            ExecutionError: If execution fails
            TimeoutError: If execution times out
        """
        pass
    
    async def cleanup(self, context: ToolExecutionContext):
        """
        Cleanup resources after execution (optional)
        
        Args:
            context: Execution context
        """
        pass
    
    def get_input_schema(self) -> Optional[type]:
        """Get the Pydantic input schema class"""
        return self.definition.input_schema
    
    def format_result(self, result: ToolResult) -> str:
        """
        Format tool result for display
        
        Args:
            result: Tool execution result
            
        Returns:
            Formatted string representation
        """
        if not result.success:
            return f"❌ {self.name} failed: {result.error}"
        
        if result.formatted_output:
            return result.formatted_output
        
        if isinstance(result.data, str):
            return result.data
        elif isinstance(result.data, dict):
            return json.dumps(result.data, indent=2)
        else:
            return str(result.data)
    
    def estimate_execution_time(self, input_data: Dict[str, Any]) -> int:
        """
        Estimate execution time in milliseconds
        
        Args:
            input_data: Input data for estimation
            
        Returns:
            Estimated execution time in ms
        """
        return self.definition.typical_execution_time_ms
    
    def get_resource_requirements(self) -> Dict[str, Any]:
        """Get resource requirements for this tool"""
        return {
            'memory_intensive': self.definition.memory_intensive,
            'cpu_intensive': self.definition.cpu_intensive,
            'permissions': [p.value for p in self.definition.permissions],
            'estimated_time_ms': self.definition.typical_execution_time_ms
        }


class StreamingAgentTool(AgentTool):
    """
    Base class for tools that support streaming execution
    
    Provides helper methods for streaming progress updates.
    """
    
    def __init__(self, definition: ToolDefinition):
        if not definition.supports_streaming:
            definition.supports_streaming = True
        super().__init__(definition)
    
    async def stream_progress(self, progress_data: Dict[str, Any], context: ToolExecutionContext) -> ToolResult:
        """
        Create a progress update result
        
        Args:
            progress_data: Progress information
            context: Execution context
            
        Returns:
            ToolResult for progress update
        """
        result = ToolResult(
            success=True,
            data=progress_data,
            tool_name=self.name,
            tool_use_id=context.tool_use_id,
            is_partial=True,
            content_type="progress"
        )
        
        # Report to context callback
        context.report_progress(progress_data)
        
        return result
    
    async def stream_partial_result(self, partial_data: Any, context: ToolExecutionContext, sequence: int = 0) -> ToolResult:
        """
        Create a partial result update
        
        Args:
            partial_data: Partial result data
            context: Execution context
            sequence: Sequence number for ordering
            
        Returns:
            ToolResult for partial result
        """
        return ToolResult(
            success=True,
            data=partial_data,
            tool_name=self.name,
            tool_use_id=context.tool_use_id,
            is_partial=True,
            sequence_number=sequence,
            content_type="partial_result"
        )
    
    async def stream_final_result(self, final_data: Any, context: ToolExecutionContext) -> ToolResult:
        """
        Create the final result
        
        Args:
            final_data: Final result data
            context: Execution context
            
        Returns:
            ToolResult for final result
        """
        execution_time = context.get_elapsed_time() * 1000  # Convert to ms
        
        return ToolResult(
            success=True,
            data=final_data,
            tool_name=self.name,
            tool_use_id=context.tool_use_id,
            execution_time_ms=execution_time,
            is_partial=False,
            content_type="final_result",
            metrics=context.execution_metrics.copy()
        )


# Utility functions for tool development

def create_tool_definition(
    name: str,
    description: str,
    category: ToolCategory,
    **kwargs
) -> ToolDefinition:
    """
    Create a tool definition with defaults
    
    Args:
        name: Tool name
        description: Tool description
        category: Tool category
        **kwargs: Additional definition parameters
        
    Returns:
        ToolDefinition instance
    """
    return ToolDefinition(
        name=name,
        description=description,
        category=category,
        **kwargs
    )


def create_execution_context(
    agent_id: str = "system",
    **kwargs
) -> ToolExecutionContext:
    """
    Create an execution context with defaults
    
    Args:
        agent_id: ID of the executing agent
        **kwargs: Additional context parameters
        
    Returns:
        ToolExecutionContext instance
    """
    return ToolExecutionContext(
        agent_id=agent_id,
        **kwargs
    )


__all__ = [
    "ToolCategory", "ToolPriority", "ToolPermission",
    "ToolError", "ValidationError", "PermissionError", "ExecutionError", "TimeoutError",
    "ToolExecutionContext", "ToolResult", "ToolInputSchema", "ToolDefinition",
    "AgentTool", "StreamingAgentTool",
    "create_tool_definition", "create_execution_context"
]