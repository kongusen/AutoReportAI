"""
Base Agent Framework

Defines the core interfaces and base classes for the AI Agent system.
All agents inherit from BaseAgent and follow consistent patterns for
initialization, execution, and result handling.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from app.core.logging_config import get_module_logger

logger = get_module_logger('agents.base')


class AgentType(Enum):
    """Agent type enumeration"""
    DATA_QUERY = "data_query"
    CONTENT_GENERATION = "content_generation" 
    ANALYSIS = "analysis"
    VISUALIZATION = "visualization"
    ORCHESTRATOR = "orchestrator"


class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentConfig:
    """Agent configuration"""
    agent_id: str
    agent_type: AgentType
    name: str
    description: str = ""
    max_retries: int = 3
    timeout_seconds: int = 30
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    custom_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Agent execution result"""
    success: bool
    agent_id: str
    agent_type: AgentType
    data: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time: float = 0.0
    timestamp: float = field(default_factory=time.time)


class AgentError(Exception):
    """Base exception for agent errors"""
    
    def __init__(
        self, 
        message: str, 
        agent_id: str = "", 
        error_code: str = "AGENT_ERROR",
        details: Dict[str, Any] = None
    ):
        super().__init__(message)
        self.agent_id = agent_id
        self.error_code = error_code
        self.details = details or {}


class BaseAgent(ABC):
    """
    Base class for all AI agents
    
    Provides common functionality for:
    - Configuration management
    - Logging and metrics
    - Error handling and retries
    - Result caching
    - Lifecycle management
    """
    
    def __init__(self, config: AgentConfig):
        """Initialize the agent with configuration"""
        self.config = config
        self.status = AgentStatus.IDLE
        self.logger = get_module_logger(f'agents.{config.agent_type.value}')
        self._cache = {}
        self._metrics = {
            "executions": 0,
            "successes": 0,
            "failures": 0,
            "total_execution_time": 0.0
        }
    
    @property
    def agent_id(self) -> str:
        """Get agent ID"""
        return self.config.agent_id
    
    @property
    def agent_type(self) -> AgentType:
        """Get agent type"""
        return self.config.agent_type
    
    @abstractmethod
    async def execute(
        self, 
        input_data: Any, 
        context: Dict[str, Any] = None
    ) -> AgentResult:
        """
        Execute the agent's main functionality
        
        Args:
            input_data: Input data for processing
            context: Additional context information
            
        Returns:
            AgentResult containing execution results
        """
        pass
    
    async def run(
        self, 
        input_data: Any, 
        context: Dict[str, Any] = None
    ) -> AgentResult:
        """
        Run the agent with error handling and retries
        
        Args:
            input_data: Input data for processing
            context: Additional context information
            
        Returns:
            AgentResult containing execution results
        """
        context = context or {}
        start_time = time.time()
        
        self.logger.info(f"Starting agent execution", agent_id=self.agent_id)
        self.status = AgentStatus.RUNNING
        self._metrics["executions"] += 1
        
        try:
            # Check cache if enabled
            if self.config.enable_caching:
                cache_key = self._generate_cache_key(input_data, context)
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    self.logger.info("Returning cached result", agent_id=self.agent_id)
                    self.status = AgentStatus.COMPLETED
                    return cached_result
            
            # Execute with retries
            result = await self._execute_with_retries(input_data, context)
            
            # Cache successful results
            if result.success and self.config.enable_caching:
                self._cache_result(cache_key, result)
            
            # Update metrics
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            self._metrics["total_execution_time"] += execution_time
            
            if result.success:
                self.status = AgentStatus.COMPLETED
                self._metrics["successes"] += 1
                self.logger.info(
                    "Agent execution completed successfully", 
                    agent_id=self.agent_id,
                    execution_time=execution_time
                )
            else:
                self.status = AgentStatus.FAILED
                self._metrics["failures"] += 1
                self.logger.error(
                    "Agent execution failed", 
                    agent_id=self.agent_id,
                    error=result.error_message,
                    execution_time=execution_time
                )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.status = AgentStatus.FAILED
            self._metrics["failures"] += 1
            self._metrics["total_execution_time"] += execution_time
            
            error_message = str(e)
            self.logger.error(
                "Agent execution failed with exception",
                agent_id=self.agent_id,
                error=error_message,
                execution_time=execution_time,
                exc_info=True
            )
            
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=error_message,
                execution_time=execution_time
            )
    
    async def _execute_with_retries(
        self, 
        input_data: Any, 
        context: Dict[str, Any]
    ) -> AgentResult:
        """Execute with retry logic"""
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # Set timeout
                result = await asyncio.wait_for(
                    self.execute(input_data, context),
                    timeout=self.config.timeout_seconds
                )
                
                if result.success:
                    return result
                else:
                    last_error = result.error_message
                    if attempt < self.config.max_retries:
                        self.logger.warning(
                            f"Agent execution failed, retrying (attempt {attempt + 1})",
                            agent_id=self.agent_id,
                            error=last_error
                        )
                        await asyncio.sleep(min(2 ** attempt, 10))  # Exponential backoff
                    
            except asyncio.TimeoutError:
                last_error = f"Agent execution timed out after {self.config.timeout_seconds} seconds"
                if attempt < self.config.max_retries:
                    self.logger.warning(
                        f"Agent execution timed out, retrying (attempt {attempt + 1})",
                        agent_id=self.agent_id
                    )
                    await asyncio.sleep(min(2 ** attempt, 10))
                    
            except Exception as e:
                last_error = str(e)
                if attempt < self.config.max_retries:
                    self.logger.warning(
                        f"Agent execution failed with exception, retrying (attempt {attempt + 1})",
                        agent_id=self.agent_id,
                        error=last_error
                    )
                    await asyncio.sleep(min(2 ** attempt, 10))
        
        # All retries failed
        return AgentResult(
            success=False,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            error_message=f"Agent failed after {self.config.max_retries + 1} attempts. Last error: {last_error}"
        )
    
    def _generate_cache_key(self, input_data: Any, context: Dict[str, Any]) -> str:
        """Generate a cache key for the given input"""
        import hashlib
        import json
        
        try:
            # Create a deterministic string representation
            cache_data = {
                "agent_id": self.agent_id,
                "input_data": str(input_data),
                "context": json.dumps(context, sort_keys=True, default=str)
            }
            cache_string = json.dumps(cache_data, sort_keys=True)
            return hashlib.md5(cache_string.encode()).hexdigest()
        except Exception:
            # Fallback to a simple key
            return f"{self.agent_id}_{hash(str(input_data))}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[AgentResult]:
        """Get cached result if available and not expired"""
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self.config.cache_ttl_seconds:
                return cached_data
            else:
                # Remove expired cache entry
                del self._cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: AgentResult) -> None:
        """Cache the execution result"""
        self._cache[cache_key] = (result, time.time())
        
        # Simple cache size management
        if len(self._cache) > 100:
            # Remove oldest entries
            sorted_cache = sorted(
                self._cache.items(), 
                key=lambda x: x[1][1]  # Sort by timestamp
            )
            # Keep only the newest 50 entries
            self._cache = dict(sorted_cache[-50:])
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        avg_execution_time = (
            self._metrics["total_execution_time"] / max(self._metrics["executions"], 1)
        )
        success_rate = (
            self._metrics["successes"] / max(self._metrics["executions"], 1)
        )
        
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "status": self.status.value,
            "executions": self._metrics["executions"],
            "successes": self._metrics["successes"],
            "failures": self._metrics["failures"],
            "success_rate": success_rate,
            "average_execution_time": avg_execution_time,
            "total_execution_time": self._metrics["total_execution_time"],
            "cache_entries": len(self._cache)
        }
    
    def clear_cache(self) -> None:
        """Clear the agent's cache"""
        self._cache.clear()
        self.logger.info("Agent cache cleared", agent_id=self.agent_id)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform agent health check"""
        try:
            # Basic health check - can be overridden by subclasses
            return {
                "healthy": True,
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "status": self.status.value,
                "last_check": time.time()
            }
        except Exception as e:
            return {
                "healthy": False,
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "status": self.status.value,
                "error": str(e),
                "last_check": time.time()
            }


class AgentRegistry:
    """Registry for managing agent instances"""
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent instance"""
        self._agents[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.agent_id} ({agent.agent_type.value})")
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent instance"""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID"""
        return self._agents.get(agent_id)
    
    def list_agents(self, agent_type: AgentType = None) -> List[BaseAgent]:
        """List all agents or agents of a specific type"""
        if agent_type:
            return [agent for agent in self._agents.values() if agent.agent_type == agent_type]
        return list(self._agents.values())
    
    def get_agent_metrics(self) -> Dict[str, Any]:
        """Get metrics for all registered agents"""
        return {
            agent_id: agent.get_metrics()
            for agent_id, agent in self._agents.items()
        }


# Global agent registry instance
agent_registry = AgentRegistry()