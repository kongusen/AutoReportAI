"""
Tool Execution Engine
====================

Provides safe, monitored, and efficient execution of agent tools
with streaming support, timeout handling, and error recovery.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, AsyncGenerator, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import traceback
import signal
import sys

from .base import (
    AgentTool, ToolResult, ToolExecutionContext, ToolError, 
    ExecutionError, TimeoutError, ValidationError, PermissionError
)
from .registry import ToolRegistry, get_tool_registry

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Tool execution status"""
    PENDING = "pending"
    VALIDATING = "validating"
    CHECKING_PERMISSIONS = "checking_permissions"
    EXECUTING = "executing"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ExecutionProgress:
    """Progress information for tool execution"""
    tool_name: str
    tool_use_id: str
    status: ExecutionStatus
    progress_percent: float = 0.0
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'tool_name': self.tool_name,
            'tool_use_id': self.tool_use_id,
            'status': self.status.value,
            'progress_percent': self.progress_percent,
            'message': self.message,
            'data': self.data,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ExecutionResult:
    """Complete result of tool execution"""
    tool_name: str
    tool_use_id: str
    success: bool
    final_result: Optional[ToolResult] = None
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # Execution metadata
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    execution_time_ms: float = 0
    
    # Progress and streaming
    progress_updates: List[ExecutionProgress] = field(default_factory=list)
    partial_results: List[ToolResult] = field(default_factory=list)
    
    # Performance metrics
    memory_usage_mb: float = 0
    cpu_time_ms: float = 0
    
    def get_duration(self) -> float:
        """Get execution duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()
    
    def add_progress(self, progress: ExecutionProgress):
        """Add a progress update"""
        self.progress_updates.append(progress)
        self.status = progress.status
    
    def add_partial_result(self, result: ToolResult):
        """Add a partial result"""
        self.partial_results.append(result)
    
    def finalize(self, final_result: ToolResult = None, error: str = None):
        """Finalize the execution result"""
        self.end_time = datetime.now(timezone.utc)
        self.execution_time_ms = self.get_duration() * 1000
        
        if error:
            self.success = False
            self.error = error
            self.status = ExecutionStatus.FAILED
        elif final_result:
            self.success = final_result.success
            self.final_result = final_result
            self.status = ExecutionStatus.COMPLETED if final_result.success else ExecutionStatus.FAILED
            if not final_result.success:
                self.error = final_result.error
                self.error_details = final_result.error_details
        else:
            self.success = False
            self.error = "No result or error provided"
            self.status = ExecutionStatus.FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'tool_name': self.tool_name,
            'tool_use_id': self.tool_use_id,
            'success': self.success,
            'status': self.status.value,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'execution_time_ms': self.execution_time_ms,
            'error': self.error,
            'error_details': self.error_details,
            'progress_updates_count': len(self.progress_updates),
            'partial_results_count': len(self.partial_results),
            'final_result': self.final_result.to_dict() if self.final_result else None,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_time_ms': self.cpu_time_ms
        }


class ToolExecutor:
    """
    Tool execution engine with advanced monitoring and control
    
    Inspired by Claude Code's execution patterns with async generators,
    streaming progress, and comprehensive error handling.
    """
    
    def __init__(self, 
                 registry: Optional[ToolRegistry] = None,
                 max_concurrent_executions: int = 10,
                 default_timeout_seconds: int = 30):
        self.registry = registry or get_tool_registry()
        self.max_concurrent_executions = max_concurrent_executions
        self.default_timeout_seconds = default_timeout_seconds
        
        # Active executions tracking
        self._active_executions: Dict[str, ExecutionResult] = {}
        self._execution_semaphore = asyncio.Semaphore(max_concurrent_executions)
        
        # Global execution hooks
        self._pre_execution_hooks: List[Callable] = []
        self._post_execution_hooks: List[Callable] = []
        self._progress_hooks: List[Callable] = []
        
        # Metrics
        self._total_executions = 0
        self._successful_executions = 0
        self._failed_executions = 0
        self._cancelled_executions = 0
        
        logger.info(f"ToolExecutor initialized with max {max_concurrent_executions} concurrent executions")
    
    async def execute_tool(self,
                          tool_name: str,
                          input_data: Dict[str, Any],
                          context: Optional[ToolExecutionContext] = None,
                          progress_callback: Optional[Callable[[ExecutionProgress], None]] = None) -> AsyncGenerator[Union[ExecutionProgress, ToolResult], None]:
        """
        Execute a tool with streaming progress updates
        
        Args:
            tool_name: Name of tool to execute
            input_data: Input data for the tool
            context: Execution context (created if None)
            progress_callback: Optional callback for progress updates
            
        Yields:
            ExecutionProgress and ToolResult objects
        """
        # Initialize context if not provided
        if context is None:
            context = ToolExecutionContext(
                agent_id="system",
                timeout_seconds=self.default_timeout_seconds
            )
        
        # Create execution result tracker
        execution_result = ExecutionResult(
            tool_name=tool_name,
            tool_use_id=context.tool_use_id
        )
        
        try:
            # Acquire execution slot
            async with self._execution_semaphore:
                self._active_executions[context.tool_use_id] = execution_result
                self._total_executions += 1
                
                # Execute with timeout
                async with asyncio.timeout(context.timeout_seconds):
                    async for update in self._execute_tool_internal(
                        tool_name, input_data, context, execution_result, progress_callback
                    ):
                        yield update
        
        except asyncio.TimeoutError:
            error_msg = f"Tool execution timed out after {context.timeout_seconds} seconds"
            logger.error(f"Tool {tool_name} timed out: {error_msg}")
            
            execution_result.finalize(error=error_msg)
            execution_result.status = ExecutionStatus.TIMEOUT
            self._failed_executions += 1
            
            # Yield timeout error
            yield ToolResult(
                success=False,
                error=error_msg,
                tool_name=tool_name,
                tool_use_id=context.tool_use_id,
                execution_time_ms=execution_result.execution_time_ms
            )
        
        except asyncio.CancelledError:
            error_msg = "Tool execution was cancelled"
            logger.info(f"Tool {tool_name} cancelled")
            
            execution_result.finalize(error=error_msg)
            execution_result.status = ExecutionStatus.CANCELLED
            self._cancelled_executions += 1
            
            # Yield cancellation notice
            yield ToolResult(
                success=False,
                error=error_msg,
                tool_name=tool_name,
                tool_use_id=context.tool_use_id
            )
        
        finally:
            # Cleanup
            self._active_executions.pop(context.tool_use_id, None)
    
    async def _execute_tool_internal(self,
                                   tool_name: str,
                                   input_data: Dict[str, Any],
                                   context: ToolExecutionContext,
                                   execution_result: ExecutionResult,
                                   progress_callback: Optional[Callable]) -> AsyncGenerator[Union[ExecutionProgress, ToolResult], None]:
        """
        Internal tool execution with comprehensive error handling
        """
        try:
            # Phase 1: Tool lookup and validation
            yield await self._progress_update(
                ExecutionStatus.VALIDATING, "Looking up tool...", 
                context, execution_result, progress_callback
            )
            
            tool = self.registry.get_tool(tool_name)
            if not tool:
                raise ExecutionError(
                    f"Tool '{tool_name}' not found in registry",
                    tool_name=tool_name,
                    error_code="TOOL_NOT_FOUND"
                )
            
            # Execute pre-execution hooks
            await self._execute_hooks(self._pre_execution_hooks, tool, input_data, context)
            
            # Phase 2: Input validation
            yield await self._progress_update(
                ExecutionStatus.VALIDATING, "Validating input...", 
                context, execution_result, progress_callback, 10.0
            )
            
            try:
                validated_input = await tool.validate_input(input_data, context)
            except Exception as e:
                raise ValidationError(
                    f"Input validation failed: {e}",
                    tool_name=tool_name,
                    error_code="VALIDATION_FAILED",
                    context={'input': input_data, 'validation_error': str(e)}
                )
            
            # Phase 3: Permission check
            yield await self._progress_update(
                ExecutionStatus.CHECKING_PERMISSIONS, "Checking permissions...", 
                context, execution_result, progress_callback, 20.0
            )
            
            try:
                permission_granted = await tool.check_permissions(validated_input, context)
                if not permission_granted:
                    raise PermissionError(
                        f"Permission denied for tool '{tool_name}'",
                        tool_name=tool_name,
                        error_code="PERMISSION_DENIED"
                    )
            except PermissionError:
                raise
            except Exception as e:
                raise PermissionError(
                    f"Permission check failed: {e}",
                    tool_name=tool_name,
                    error_code="PERMISSION_CHECK_FAILED"
                )
            
            # Phase 4: Tool execution with streaming
            yield await self._progress_update(
                ExecutionStatus.EXECUTING, "Starting tool execution...", 
                context, execution_result, progress_callback, 30.0
            )
            
            final_result = None
            partial_count = 0
            
            try:
                async for tool_result in tool.execute(validated_input, context):
                    if tool_result.is_partial:
                        # Handle partial results and progress
                        execution_result.add_partial_result(tool_result)
                        partial_count += 1
                        
                        # Update status to streaming if we're getting partial results
                        if execution_result.status != ExecutionStatus.STREAMING:
                            yield await self._progress_update(
                                ExecutionStatus.STREAMING, "Streaming results...", 
                                context, execution_result, progress_callback, 50.0
                            )
                        
                        # Yield the partial result
                        yield tool_result
                    else:
                        # Final result
                        final_result = tool_result
                        execution_result.execution_time_ms = tool_result.execution_time_ms
                        break
                
                # Ensure we have a final result
                if final_result is None:
                    final_result = ToolResult(
                        success=True,
                        data=f"Tool completed with {partial_count} partial results",
                        tool_name=tool_name,
                        tool_use_id=context.tool_use_id,
                        execution_time_ms=context.get_elapsed_time() * 1000
                    )
                
            except Exception as e:
                logger.exception(f"Tool execution failed: {e}")
                raise ExecutionError(
                    f"Tool execution failed: {e}",
                    tool_name=tool_name,
                    error_code="EXECUTION_FAILED",
                    context={'error': str(e), 'traceback': traceback.format_exc()}
                )
            
            # Phase 5: Cleanup and finalization
            try:
                await tool.cleanup(context)
            except Exception as e:
                logger.warning(f"Tool cleanup failed: {e}")
            
            # Execute post-execution hooks
            await self._execute_hooks(self._post_execution_hooks, tool, final_result, context)
            
            # Finalize execution result
            execution_result.finalize(final_result)
            
            if final_result.success:
                self._successful_executions += 1
                yield await self._progress_update(
                    ExecutionStatus.COMPLETED, "Tool execution completed successfully", 
                    context, execution_result, progress_callback, 100.0
                )
            else:
                self._failed_executions += 1
                yield await self._progress_update(
                    ExecutionStatus.FAILED, f"Tool execution failed: {final_result.error}", 
                    context, execution_result, progress_callback, 100.0
                )
            
            # Yield final result
            yield final_result
            
        except (ValidationError, PermissionError, ExecutionError) as e:
            # Known tool errors
            execution_result.finalize(error=str(e))
            self._failed_executions += 1
            
            yield await self._progress_update(
                ExecutionStatus.FAILED, f"Tool failed: {e}", 
                context, execution_result, progress_callback, 100.0
            )
            
            yield ToolResult(
                success=False,
                error=str(e),
                error_details=e.to_dict() if hasattr(e, 'to_dict') else None,
                tool_name=tool_name,
                tool_use_id=context.tool_use_id,
                execution_time_ms=context.get_elapsed_time() * 1000
            )
            
        except Exception as e:
            # Unexpected errors
            logger.exception(f"Unexpected error in tool execution: {e}")
            execution_result.finalize(error=f"Unexpected error: {e}")
            self._failed_executions += 1
            
            yield await self._progress_update(
                ExecutionStatus.FAILED, f"Unexpected error: {e}", 
                context, execution_result, progress_callback, 100.0
            )
            
            yield ToolResult(
                success=False,
                error=f"Unexpected error: {e}",
                error_details={'traceback': traceback.format_exc()},
                tool_name=tool_name,
                tool_use_id=context.tool_use_id,
                execution_time_ms=context.get_elapsed_time() * 1000
            )
    
    async def _progress_update(self,
                             status: ExecutionStatus,
                             message: str,
                             context: ToolExecutionContext,
                             execution_result: ExecutionResult,
                             progress_callback: Optional[Callable],
                             progress_percent: float = None) -> ExecutionProgress:
        """Create and handle a progress update"""
        
        if progress_percent is None:
            # Auto-calculate based on status
            progress_map = {
                ExecutionStatus.VALIDATING: 10.0,
                ExecutionStatus.CHECKING_PERMISSIONS: 20.0,
                ExecutionStatus.EXECUTING: 30.0,
                ExecutionStatus.STREAMING: 70.0,
                ExecutionStatus.COMPLETED: 100.0,
                ExecutionStatus.FAILED: 100.0
            }
            progress_percent = progress_map.get(status, 0.0)
        
        progress = ExecutionProgress(
            tool_name=execution_result.tool_name,
            tool_use_id=context.tool_use_id,
            status=status,
            progress_percent=progress_percent,
            message=message
        )
        
        execution_result.add_progress(progress)
        
        # Call progress callback if provided
        if progress_callback:
            try:
                progress_callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
        
        # Call global progress hooks
        await self._execute_hooks(self._progress_hooks, progress)
        
        return progress
    
    async def _execute_hooks(self, hooks: List[Callable], *args):
        """Execute a list of hooks safely"""
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(*args)
                else:
                    hook(*args)
            except Exception as e:
                logger.warning(f"Hook execution failed: {e}")
    
    def add_pre_execution_hook(self, hook: Callable):
        """Add a pre-execution hook"""
        self._pre_execution_hooks.append(hook)
    
    def add_post_execution_hook(self, hook: Callable):
        """Add a post-execution hook"""
        self._post_execution_hooks.append(hook)
    
    def add_progress_hook(self, hook: Callable):
        """Add a progress update hook"""
        self._progress_hooks.append(hook)
    
    def get_active_executions(self) -> Dict[str, ExecutionResult]:
        """Get currently active executions"""
        return self._active_executions.copy()
    
    def cancel_execution(self, tool_use_id: str) -> bool:
        """
        Cancel an active execution
        
        Args:
            tool_use_id: ID of execution to cancel
            
        Returns:
            True if cancellation was requested
        """
        if tool_use_id in self._active_executions:
            execution = self._active_executions[tool_use_id]
            # Set cancellation token if available
            # Note: Actual cancellation depends on tool implementation checking context.is_cancelled()
            logger.info(f"Cancellation requested for tool execution {tool_use_id}")
            return True
        return False
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return {
            'total_executions': self._total_executions,
            'successful_executions': self._successful_executions,
            'failed_executions': self._failed_executions,
            'cancelled_executions': self._cancelled_executions,
            'active_executions': len(self._active_executions),
            'max_concurrent': self.max_concurrent_executions,
            'success_rate': self._successful_executions / max(self._total_executions, 1),
            'failure_rate': self._failed_executions / max(self._total_executions, 1)
        }


# Convenience functions

def create_tool_executor(max_concurrent: int = 10, 
                        timeout_seconds: int = 30) -> ToolExecutor:
    """
    Create a tool executor with specified parameters
    
    Args:
        max_concurrent: Maximum concurrent executions
        timeout_seconds: Default timeout
        
    Returns:
        ToolExecutor instance
    """
    return ToolExecutor(
        max_concurrent_executions=max_concurrent,
        default_timeout_seconds=timeout_seconds
    )


async def execute_tool_safely(tool_name: str,
                             input_data: Dict[str, Any],
                             context: Optional[ToolExecutionContext] = None) -> ToolResult:
    """
    Execute a single tool and return only the final result
    
    Args:
        tool_name: Name of tool to execute
        input_data: Input data
        context: Optional execution context
        
    Returns:
        Final ToolResult
    """
    executor = create_tool_executor()
    final_result = None
    
    async for result in executor.execute_tool(tool_name, input_data, context):
        if isinstance(result, ToolResult) and not result.is_partial:
            final_result = result
            break
    
    return final_result or ToolResult(
        success=False,
        error="No final result received from tool",
        tool_name=tool_name
    )


__all__ = [
    "ExecutionStatus", "ExecutionProgress", "ExecutionResult",
    "ToolExecutor", "create_tool_executor", "execute_tool_safely"
]