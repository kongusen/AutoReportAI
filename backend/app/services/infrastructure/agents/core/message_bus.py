"""
Message Bus and Orchestration System
===================================

Central message broker for agent coordination and communication.
Inspired by Claude Code's message routing and coordination patterns.
"""

import asyncio
import logging
import uuid
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, AsyncGenerator, Any, Callable, Set, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from collections import defaultdict, deque
import threading
import json
import heapq
from abc import ABC, abstractmethod

from .message_types import (
    AgentMessage, MessageType, MessagePriority, MessagePattern, 
    MessageHandler, create_error_message
)
from .streaming_parser import StreamingMessageParser, parse_single_message
from .progress_aggregator import ProgressAggregator, create_simple_aggregator
from .error_formatter import ErrorFormatter, create_error_message

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """Message routing strategies"""
    DIRECT = "direct"               # Direct agent-to-agent
    BROADCAST = "broadcast"         # Broadcast to group
    ROUND_ROBIN = "round_robin"     # Round-robin to group members
    LOAD_BALANCED = "load_balanced" # Based on agent load
    PRIORITY_BASED = "priority_based" # Based on message priority


class DeliveryGuarantee(Enum):
    """Message delivery guarantees"""
    AT_MOST_ONCE = "at_most_once"     # Fire and forget
    AT_LEAST_ONCE = "at_least_once"   # Guaranteed delivery with possible duplicates
    EXACTLY_ONCE = "exactly_once"     # Guaranteed single delivery


@dataclass
class RoutingRule:
    """Message routing rule configuration"""
    pattern: MessagePattern
    strategy: RoutingStrategy = RoutingStrategy.DIRECT
    target_group: Optional[str] = None
    priority: int = 100
    enabled: bool = True
    
    # Advanced routing options
    load_balancing_key: Optional[str] = None
    sticky_sessions: bool = False
    retry_policy: Optional[Dict[str, Any]] = None
    
    def matches(self, message: AgentMessage) -> bool:
        """Check if message matches this routing rule"""
        return self.enabled and self.pattern.matches(message)


@dataclass
class MessageQueue:
    """Priority queue for messages"""
    queue: List[Tuple[int, datetime, AgentMessage]] = field(default_factory=list)
    max_size: int = 10000
    
    def put(self, message: AgentMessage):
        """Add message to queue with priority ordering"""
        if len(self.queue) >= self.max_size:
            # Remove lowest priority message if queue is full
            if self.queue:
                heapq.heappop(self.queue)
            logger.warning("Message queue full, dropping lowest priority message")
        
        # Higher priority values = higher urgency (reverse for heapq)
        priority_value = -message.priority.value
        timestamp = message.timestamp
        
        heapq.heappush(self.queue, (priority_value, timestamp, message))
    
    def get(self) -> Optional[AgentMessage]:
        """Get highest priority message from queue"""
        if self.queue:
            _, _, message = heapq.heappop(self.queue)
            return message
        return None
    
    def size(self) -> int:
        """Get queue size"""
        return len(self.queue)
    
    def clear(self):
        """Clear all messages"""
        self.queue.clear()


class MessageBroker:
    """Message broker for handling delivery and routing"""
    
    def __init__(self, delivery_guarantee: DeliveryGuarantee = DeliveryGuarantee.AT_LEAST_ONCE):
        self.delivery_guarantee = delivery_guarantee
        self.pending_messages: Dict[str, AgentMessage] = {}  # For at-least-once delivery
        self.delivered_messages: Set[str] = set()  # For exactly-once delivery
        self.retry_counts: Dict[str, int] = {}
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        
        # Delivery confirmation tracking
        self.awaiting_confirmation: Dict[str, datetime] = {}
        self.confirmation_timeout = 30.0  # seconds
        
        logger.debug(f"MessageBroker initialized with {delivery_guarantee.value} delivery guarantee")
    
    async def deliver_message(self, message: AgentMessage, target_handler: Callable) -> bool:
        """Deliver message to target with appropriate guarantee"""
        
        message_id = message.message_id
        
        # Check for duplicate delivery (exactly-once)
        if (self.delivery_guarantee == DeliveryGuarantee.EXACTLY_ONCE and 
            message_id in self.delivered_messages):
            logger.debug(f"Skipping duplicate message delivery: {message_id}")
            return True
        
        try:
            # Attempt delivery
            await target_handler(message)
            
            # Mark as delivered
            if self.delivery_guarantee == DeliveryGuarantee.EXACTLY_ONCE:
                self.delivered_messages.add(message_id)
            
            # Remove from pending if successful
            self.pending_messages.pop(message_id, None)
            self.retry_counts.pop(message_id, None)
            
            logger.debug(f"Message {message_id} delivered successfully")
            return True
            
        except Exception as e:
            logger.warning(f"Message delivery failed: {e}")
            
            # Handle retry for at-least-once delivery
            if self.delivery_guarantee == DeliveryGuarantee.AT_LEAST_ONCE:
                return await self._handle_retry(message, target_handler, e)
            
            return False
    
    async def _handle_retry(self, message: AgentMessage, target_handler: Callable, error: Exception) -> bool:
        """Handle message retry logic"""
        
        message_id = message.message_id
        retry_count = self.retry_counts.get(message_id, 0)
        
        if retry_count < self.max_retries:
            self.retry_counts[message_id] = retry_count + 1
            self.pending_messages[message_id] = message
            
            # Schedule retry with exponential backoff
            delay = self.retry_delay * (2 ** retry_count)
            logger.info(f"Scheduling retry {retry_count + 1} for message {message_id} in {delay}s")
            
            asyncio.create_task(self._retry_after_delay(message, target_handler, delay))
            return True
        else:
            logger.error(f"Message {message_id} failed after {self.max_retries} retries")
            self.pending_messages.pop(message_id, None)
            self.retry_counts.pop(message_id, None)
            return False
    
    async def _retry_after_delay(self, message: AgentMessage, target_handler: Callable, delay: float):
        """Retry message delivery after delay"""
        await asyncio.sleep(delay)
        await self.deliver_message(message, target_handler)
    
    def get_pending_count(self) -> int:
        """Get number of pending messages"""
        return len(self.pending_messages)
    
    def cleanup_delivered_messages(self, max_age_hours: int = 24):
        """Clean up old delivered message IDs"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        # This is simplified - in production you'd track delivery timestamps
        if len(self.delivered_messages) > 10000:
            # Keep only the most recent half
            delivered_list = list(self.delivered_messages)
            self.delivered_messages = set(delivered_list[-5000:])
            logger.debug("Cleaned up old delivered message IDs")


class AgentRegistry:
    """Registry for managing agent lifecycle and capabilities"""
    
    def __init__(self):
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.agent_groups: Dict[str, Set[str]] = defaultdict(set)
        self.agent_load: Dict[str, float] = defaultdict(float)  # 0.0 - 1.0
        self.agent_handlers: Dict[str, List[MessageHandler]] = defaultdict(list)
        
        # Performance tracking
        self.message_counts: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)
        
        # Health monitoring
        self.last_heartbeat: Dict[str, datetime] = {}
        self.heartbeat_timeout = 60.0  # seconds
        
        logger.debug("AgentRegistry initialized")
    
    def register_agent(self, agent_id: str, capabilities: List[str] = None, 
                      groups: List[str] = None, metadata: Dict[str, Any] = None):
        """Register a new agent"""
        
        self.agents[agent_id] = {
            'capabilities': capabilities or [],
            'groups': groups or [],
            'metadata': metadata or {},
            'registered_at': datetime.now(timezone.utc),
            'status': 'active'
        }
        
        # Add to groups
        for group in (groups or []):
            self.agent_groups[group].add(agent_id)
        
        # Initialize metrics
        self.agent_load[agent_id] = 0.0
        self.message_counts[agent_id] = 0
        self.error_counts[agent_id] = 0
        self.last_heartbeat[agent_id] = datetime.now(timezone.utc)
        
        logger.info(f"Registered agent {agent_id} with capabilities: {capabilities}")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        
        if agent_id in self.agents:
            # Remove from groups
            agent_info = self.agents[agent_id]
            for group in agent_info.get('groups', []):
                self.agent_groups[group].discard(agent_id)
            
            # Clean up all data
            del self.agents[agent_id]
            self.agent_load.pop(agent_id, None)
            self.message_counts.pop(agent_id, None)
            self.error_counts.pop(agent_id, None)
            self.last_heartbeat.pop(agent_id, None)
            self.agent_handlers.pop(agent_id, None)
            
            logger.info(f"Unregistered agent {agent_id}")
    
    def add_handler(self, agent_id: str, handler: MessageHandler):
        """Add message handler for agent"""
        self.agent_handlers[agent_id].append(handler)
        logger.debug(f"Added handler for agent {agent_id}")
    
    def get_handlers(self, agent_id: str) -> List[MessageHandler]:
        """Get handlers for agent"""
        return self.agent_handlers.get(agent_id, [])
    
    def update_agent_load(self, agent_id: str, load: float):
        """Update agent load metric"""
        self.agent_load[agent_id] = max(0.0, min(1.0, load))
    
    def record_heartbeat(self, agent_id: str):
        """Record heartbeat from agent"""
        self.last_heartbeat[agent_id] = datetime.now(timezone.utc)
    
    def get_healthy_agents(self, group: str = None) -> List[str]:
        """Get list of healthy agents, optionally filtered by group"""
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.heartbeat_timeout)
        healthy_agents = []
        
        agents_to_check = self.agent_groups.get(group, self.agents.keys()) if group else self.agents.keys()
        
        for agent_id in agents_to_check:
            last_hb = self.last_heartbeat.get(agent_id)
            if last_hb and last_hb > cutoff_time:
                healthy_agents.append(agent_id)
        
        return healthy_agents
    
    def get_least_loaded_agent(self, group: str = None) -> Optional[str]:
        """Get the least loaded healthy agent"""
        
        healthy_agents = self.get_healthy_agents(group)
        if not healthy_agents:
            return None
        
        return min(healthy_agents, key=lambda aid: self.agent_load.get(aid, 0.0))
    
    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get statistics for an agent"""
        
        if agent_id not in self.agents:
            return {}
        
        return {
            'load': self.agent_load.get(agent_id, 0.0),
            'message_count': self.message_counts.get(agent_id, 0),
            'error_count': self.error_counts.get(agent_id, 0),
            'last_heartbeat': self.last_heartbeat.get(agent_id),
            'groups': self.agents[agent_id].get('groups', []),
            'capabilities': self.agents[agent_id].get('capabilities', [])
        }


class MessageBus:
    """
    Central message bus for agent coordination
    
    Provides:
    1. Message routing and delivery
    2. Agent lifecycle management
    3. Load balancing and failover
    4. Progress aggregation
    5. Error handling and recovery
    """
    
    def __init__(self, 
                 delivery_guarantee: DeliveryGuarantee = DeliveryGuarantee.AT_LEAST_ONCE,
                 max_queue_size: int = 10000):
        
        # Core components
        self.agent_registry = AgentRegistry()
        self.message_broker = MessageBroker(delivery_guarantee)
        self.error_formatter = ErrorFormatter()
        self.progress_aggregator = create_simple_aggregator()
        self.streaming_parser = StreamingMessageParser()
        
        # Message queues per agent
        self.agent_queues: Dict[str, MessageQueue] = defaultdict(
            lambda: MessageQueue(max_size=max_queue_size)
        )
        
        # Routing configuration
        self.routing_rules: List[RoutingRule] = []
        self.default_routing_strategy = RoutingStrategy.DIRECT
        
        # Global message handlers
        self.global_handlers: List[MessageHandler] = []
        self.middleware: List[Callable[[AgentMessage], AgentMessage]] = []
        
        # Processing control
        self._running = False
        self._processing_tasks: Set[asyncio.Task] = set()
        self._executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="MessageBus")
        
        # Statistics
        self.total_messages_processed = 0
        self.total_messages_failed = 0
        self.routing_stats: Dict[str, int] = defaultdict(int)
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("MessageBus initialized")
    
    async def start(self):
        """Start the message bus"""
        
        if self._running:
            return
        
        self._running = True
        
        # Start message processing tasks for each agent
        await self._start_processing_tasks()
        
        # Start periodic cleanup task
        asyncio.create_task(self._periodic_cleanup())
        
        logger.info("MessageBus started")
    
    async def stop(self):
        """Stop the message bus"""
        
        self._running = False
        
        # Cancel all processing tasks
        for task in self._processing_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._processing_tasks:
            await asyncio.gather(*self._processing_tasks, return_exceptions=True)
        
        self._processing_tasks.clear()
        self._executor.shutdown(wait=True)
        
        logger.info("MessageBus stopped")
    
    def register_agent(self, agent_id: str, capabilities: List[str] = None,
                      groups: List[str] = None, handlers: List[MessageHandler] = None):
        """Register an agent with the message bus"""
        
        self.agent_registry.register_agent(agent_id, capabilities, groups)
        
        # Add handlers
        if handlers:
            for handler in handlers:
                self.agent_registry.add_handler(agent_id, handler)
        
        # Start processing task for this agent if bus is running
        if self._running:
            task = asyncio.create_task(self._process_agent_messages(agent_id))
            self._processing_tasks.add(task)
            task.add_done_callback(self._processing_tasks.discard)
        
        logger.info(f"Agent {agent_id} registered with message bus")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent from the message bus"""
        
        # Clear agent queue
        if agent_id in self.agent_queues:
            self.agent_queues[agent_id].clear()
            del self.agent_queues[agent_id]
        
        self.agent_registry.unregister_agent(agent_id)
        
        logger.info(f"Agent {agent_id} unregistered from message bus")
    
    async def send_message(self, message: AgentMessage) -> bool:
        """Send a message through the bus"""
        
        # Apply middleware
        processed_message = message
        for middleware in self.middleware:
            try:
                processed_message = middleware(processed_message)
            except Exception as e:
                logger.error(f"Middleware error: {e}")
        
        # Route the message
        targets = await self._route_message(processed_message)
        
        if not targets:
            logger.warning(f"No targets found for message {message.message_id}")
            return False
        
        # Deliver to all targets
        delivery_results = []
        for target_agent in targets:
            success = await self._deliver_to_agent(processed_message, target_agent)
            delivery_results.append(success)
        
        # Update statistics
        self.total_messages_processed += 1
        if not any(delivery_results):
            self.total_messages_failed += 1
        
        return any(delivery_results)
    
    async def broadcast_message(self, message: AgentMessage, group: str = None) -> int:
        """Broadcast message to all agents in group (or all agents)"""
        
        targets = self.agent_registry.get_healthy_agents(group)
        if not targets:
            return 0
        
        success_count = 0
        for target_agent in targets:
            # Create copy of message for each target
            target_message = AgentMessage.from_dict(message.to_dict())
            target_message.to_agent = target_agent
            target_message.message_id = str(uuid.uuid4())  # New ID for each copy
            
            if await self._deliver_to_agent(target_message, target_agent):
                success_count += 1
        
        logger.info(f"Broadcast message delivered to {success_count}/{len(targets)} agents")
        return success_count
    
    def add_routing_rule(self, pattern_str: str, strategy: RoutingStrategy = RoutingStrategy.DIRECT,
                        target_group: str = None, priority: int = 100):
        """Add a message routing rule"""
        
        pattern = MessagePattern(pattern_str)
        rule = RoutingRule(
            pattern=pattern,
            strategy=strategy,
            target_group=target_group,
            priority=priority
        )
        
        # Insert in priority order
        inserted = False
        for i, existing_rule in enumerate(self.routing_rules):
            if rule.priority < existing_rule.priority:
                self.routing_rules.insert(i, rule)
                inserted = True
                break
        
        if not inserted:
            self.routing_rules.append(rule)
        
        logger.info(f"Added routing rule: {pattern_str} -> {strategy.value}")
    
    def add_global_handler(self, handler: MessageHandler):
        """Add a global message handler"""
        self.global_handlers.append(handler)
    
    def add_middleware(self, middleware: Callable[[AgentMessage], AgentMessage]):
        """Add message processing middleware"""
        self.middleware.append(middleware)
    
    async def _route_message(self, message: AgentMessage) -> List[str]:
        """Route message to target agents based on rules"""
        
        # Try routing rules first
        for rule in self.routing_rules:
            if rule.matches(message):
                targets = await self._apply_routing_strategy(message, rule)
                if targets:
                    self.routing_stats[rule.strategy.value] += 1
                    return targets
        
        # Fall back to direct routing
        if message.to_agent and message.to_agent != "*":
            if message.to_agent in self.agent_registry.agents:
                return [message.to_agent]
        
        # Group targeting
        if message.agent_group:
            return self.agent_registry.get_healthy_agents(message.agent_group)
        
        logger.warning(f"No route found for message {message.message_id}")
        return []
    
    async def _apply_routing_strategy(self, message: AgentMessage, rule: RoutingRule) -> List[str]:
        """Apply specific routing strategy"""
        
        if rule.strategy == RoutingStrategy.DIRECT:
            if message.to_agent and message.to_agent != "*":
                return [message.to_agent] if message.to_agent in self.agent_registry.agents else []
        
        elif rule.strategy == RoutingStrategy.BROADCAST:
            return self.agent_registry.get_healthy_agents(rule.target_group)
        
        elif rule.strategy == RoutingStrategy.ROUND_ROBIN:
            # Simple round-robin implementation
            agents = self.agent_registry.get_healthy_agents(rule.target_group)
            if agents:
                # Use message hash for consistent selection
                index = hash(message.message_id) % len(agents)
                return [agents[index]]
        
        elif rule.strategy == RoutingStrategy.LOAD_BALANCED:
            agent = self.agent_registry.get_least_loaded_agent(rule.target_group)
            return [agent] if agent else []
        
        elif rule.strategy == RoutingStrategy.PRIORITY_BASED:
            # Route high priority messages to least loaded agents
            agents = self.agent_registry.get_healthy_agents(rule.target_group)
            if agents and message.priority.value >= 3:  # HIGH or above
                agent = min(agents, key=lambda a: self.agent_registry.agent_load.get(a, 0.0))
                return [agent]
            elif agents:
                return [agents[0]]  # Just pick first for lower priority
        
        return []
    
    async def _deliver_to_agent(self, message: AgentMessage, target_agent: str) -> bool:
        """Deliver message to specific agent"""
        
        if target_agent not in self.agent_registry.agents:
            logger.warning(f"Target agent {target_agent} not found")
            return False
        
        # Add to agent's queue
        self.agent_queues[target_agent].put(message)
        
        # Update agent message count
        self.agent_registry.message_counts[target_agent] += 1
        
        logger.debug(f"Message {message.message_id} queued for agent {target_agent}")
        return True
    
    async def _start_processing_tasks(self):
        """Start message processing tasks for all registered agents"""
        
        for agent_id in self.agent_registry.agents.keys():
            task = asyncio.create_task(self._process_agent_messages(agent_id))
            self._processing_tasks.add(task)
            task.add_done_callback(self._processing_tasks.discard)
    
    async def _process_agent_messages(self, agent_id: str):
        """Process messages for a specific agent"""
        
        logger.debug(f"Started message processing for agent {agent_id}")
        
        try:
            while self._running:
                queue = self.agent_queues.get(agent_id)
                if not queue:
                    await asyncio.sleep(0.1)
                    continue
                
                message = queue.get()
                if not message:
                    await asyncio.sleep(0.1)
                    continue
                
                # Check if message is expired
                if message.is_expired():
                    logger.warning(f"Message {message.message_id} expired, dropping")
                    continue
                
                # Process the message
                await self._handle_agent_message(agent_id, message)
                
        except asyncio.CancelledError:
            logger.debug(f"Message processing cancelled for agent {agent_id}")
        except Exception as e:
            logger.error(f"Error processing messages for agent {agent_id}: {e}", exc_info=True)
    
    async def _handle_agent_message(self, agent_id: str, message: AgentMessage):
        """Handle a message for a specific agent"""
        
        try:
            # Get agent handlers
            handlers = self.agent_registry.get_handlers(agent_id)
            
            # Add global handlers
            all_handlers = handlers + self.global_handlers
            
            # Find matching handlers
            matching_handlers = [h for h in all_handlers if h.can_handle(message)]
            
            if not matching_handlers:
                logger.warning(f"No handlers found for message {message.message_id} to agent {agent_id}")
                return
            
            # Execute handlers
            for handler in matching_handlers:
                try:
                    response = await handler.handle_message(message)
                    
                    # If handler returns a response message, route it
                    if response:
                        await self.send_message(response)
                        
                except Exception as e:
                    logger.error(f"Handler error for agent {agent_id}: {e}")
                    self.agent_registry.error_counts[agent_id] += 1
                    
                    # Create error message
                    error_msg = create_error_message(e, agent_id, message.from_agent)
                    await self.send_message(error_msg)
        
        except Exception as e:
            logger.error(f"Error handling message for agent {agent_id}: {e}", exc_info=True)
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old data"""
        
        while self._running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Clean up delivered messages
                self.message_broker.cleanup_delivered_messages()
                
                # Clean up expired progress aggregations
                self.progress_aggregator._cleanup_old_aggregations()
                
                logger.debug("Periodic cleanup completed")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get message bus statistics"""
        
        queue_sizes = {aid: queue.size() for aid, queue in self.agent_queues.items()}
        
        return {
            'total_messages_processed': self.total_messages_processed,
            'total_messages_failed': self.total_messages_failed,
            'success_rate': (self.total_messages_processed - self.total_messages_failed) / max(self.total_messages_processed, 1),
            'registered_agents': len(self.agent_registry.agents),
            'active_processing_tasks': len(self._processing_tasks),
            'queue_sizes': queue_sizes,
            'total_queued_messages': sum(queue_sizes.values()),
            'routing_stats': dict(self.routing_stats),
            'pending_deliveries': self.message_broker.get_pending_count(),
            'agent_registry_stats': {
                aid: self.agent_registry.get_agent_stats(aid)
                for aid in self.agent_registry.agents.keys()
            }
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the message bus"""
        
        healthy_agents = self.agent_registry.get_healthy_agents()
        total_agents = len(self.agent_registry.agents)
        
        return {
            'status': 'healthy' if self._running else 'stopped',
            'healthy_agents': len(healthy_agents),
            'total_agents': total_agents,
            'health_ratio': len(healthy_agents) / max(total_agents, 1),
            'processing_tasks_active': len(self._processing_tasks),
            'queue_health': {
                aid: {
                    'size': queue.size(),
                    'status': 'ok' if queue.size() < queue.max_size * 0.8 else 'warning'
                }
                for aid, queue in self.agent_queues.items()
            }
        }


# Convenience functions

async def create_message_bus(delivery_guarantee: DeliveryGuarantee = DeliveryGuarantee.AT_LEAST_ONCE) -> MessageBus:
    """Create and start a message bus"""
    bus = MessageBus(delivery_guarantee=delivery_guarantee)
    await bus.start()
    return bus

def create_simple_handler(agent_id: str, handler_func: Callable[[AgentMessage], Any]) -> MessageHandler:
    """Create a simple message handler"""
    
    class SimpleHandler(MessageHandler):
        def __init__(self, agent_id: str, func: Callable):
            super().__init__(agent_id)
            self.func = func
        
        async def handle_message(self, message: AgentMessage):
            if asyncio.iscoroutinefunction(self.func):
                return await self.func(message)
            else:
                return self.func(message)
    
    return SimpleHandler(agent_id, handler_func)


__all__ = [
    "RoutingStrategy",
    "DeliveryGuarantee", 
    "RoutingRule",
    "MessageQueue",
    "MessageBroker",
    "AgentRegistry",
    "MessageBus",
    "create_message_bus",
    "create_simple_handler",
]