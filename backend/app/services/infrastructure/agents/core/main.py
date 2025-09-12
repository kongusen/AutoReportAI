"""
Main Agent Infrastructure Integration
====================================

Main integration point and usage examples for the agent message passing system.
Demonstrates how to use all components together in a cohesive system.
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .message_bus import (
    MessageBus, create_message_bus, create_simple_handler,
    RoutingStrategy, DeliveryGuarantee
)
from .message_types import (
    AgentMessage, MessageType, MessagePriority,
    create_task_request, create_progress_message, create_result_message,
    create_error_message, create_heartbeat
)
from .streaming_parser import StreamingMessageParser, parse_single_message
from .progress_aggregator import (
    ProgressAggregator, create_simple_aggregator, 
    AggregationStrategy, AgentProgress
)
from .error_formatter import ErrorFormatter, create_error_message as format_error
from .memory_manager import MemoryManager, create_memory_manager

logger = logging.getLogger(__name__)


class AgentCoordinator:
    """
    Main coordinator for agent infrastructure - inspired by Claude Code's tt function
    
    Implements sophisticated orchestration patterns:
    - Six-stage async generator workflow (validation -> readonly -> write -> compress -> reason -> synthesize)
    - Streaming state machine for complex control flow
    - Hierarchical agent management with sub-agents
    - Memory-efficient message handling with backpressure
    - Real-time progress aggregation and ANR detection
    - Advanced error recovery with context preservation
    
    This is the 'tt' equivalent for our agent system - the main orchestration function
    that coordinates all agent activities with sophisticated control flow patterns.
    """
    
    def __init__(self):
        self.message_bus: Optional[MessageBus] = None
        self.progress_aggregator: Optional[ProgressAggregator] = None
        self.error_formatter = ErrorFormatter()
        self.memory_manager: Optional[MemoryManager] = None
        self.streaming_parser = StreamingMessageParser()
        
        # Agent registry - enhanced with hierarchical support
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_hierarchy: Dict[str, List[str]] = {}  # parent -> [children]
        self.sub_agents: Dict[str, str] = {}  # child -> parent
        
        # Active tasks with enhanced state tracking
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_pipelines: Dict[str, asyncio.Queue] = {}  # streaming task pipelines
        
        # Six-stage orchestration state
        self.orchestration_stages = [
            "validation", "readonly_parallel", "write_sequential", 
            "context_compression", "llm_reasoning", "result_synthesis"
        ]
        self.stage_handlers: Dict[str, callable] = {}
        
        # Streaming state machine
        self.state_machine_active = False
        self.current_state = "idle"
        self.state_transitions: Dict[str, List[str]] = {
            "idle": ["initializing", "error"],
            "initializing": ["validation", "error"],
            "validation": ["readonly_parallel", "error"], 
            "readonly_parallel": ["write_sequential", "error"],
            "write_sequential": ["context_compression", "error"],
            "context_compression": ["llm_reasoning", "error"],
            "llm_reasoning": ["result_synthesis", "error"],
            "result_synthesis": ["completed", "error"],
            "completed": ["idle"],
            "error": ["recovery", "idle"],
            "recovery": ["validation", "idle"]
        }
        
        # Task execution context preservation
        self.execution_contexts: Dict[str, Dict[str, Any]] = {}
        
        # Performance and monitoring
        self.orchestration_metrics: Dict[str, Any] = {
            "total_orchestrations": 0,
            "successful_orchestrations": 0,
            "failed_orchestrations": 0,
            "stage_performance": {stage: [] for stage in self.orchestration_stages}
        }
        
        logger.info("AgentCoordinator initialized with Claude Code orchestration patterns")
    
    async def start(self):
        """Start the coordinator and all subsystems"""
        
        # Initialize message bus
        self.message_bus = await create_message_bus(DeliveryGuarantee.AT_LEAST_ONCE)
        
        # Initialize progress aggregator
        self.progress_aggregator = create_simple_aggregator()
        
        # Initialize memory manager
        self.memory_manager = create_memory_manager(max_cache_mb=256)
        await self.memory_manager.start()
        
        # Set up routing rules
        self._setup_routing_rules()
        
        # Set up global error handling
        self._setup_error_handling()
        
        logger.info("AgentCoordinator started successfully")
    
    async def stop(self):
        """Stop the coordinator and cleanup resources"""
        
        if self.message_bus:
            await self.message_bus.stop()
        
        if self.progress_aggregator:
            self.progress_aggregator.shutdown()
        
        if self.memory_manager:
            self.memory_manager.stop()
        
        logger.info("AgentCoordinator stopped")
    
    def _setup_routing_rules(self):
        """Setup message routing rules"""
        
        if not self.message_bus:
            return
        
        # Route task requests to appropriate agents
        self.message_bus.add_routing_rule(
            "task_request:*->*",
            RoutingStrategy.LOAD_BALANCED,
            priority=1
        )
        
        # Route progress updates directly
        self.message_bus.add_routing_rule(
            "task_progress:*->*",
            RoutingStrategy.DIRECT,
            priority=2
        )
        
        # Broadcast heartbeats to system
        self.message_bus.add_routing_rule(
            "heartbeat:*->system",
            RoutingStrategy.BROADCAST,
            target_group="monitors",
            priority=10
        )
        
        # Route errors to error handlers
        self.message_bus.add_routing_rule(
            "task_error:*->*",
            RoutingStrategy.BROADCAST,
            target_group="error_handlers",
            priority=1
        )
    
    def _setup_error_handling(self):
        """Setup global error handling"""
        
        if not self.message_bus:
            return
        
        async def global_error_handler(message: AgentMessage):
            """Handle all error messages globally"""
            if message.message_type == MessageType.TASK_ERROR:
                logger.error(f"Task error from {message.from_agent}: {message.payload}")
                
                # Format error for better reporting
                if isinstance(message.payload, dict) and 'exception' in message.payload:
                    try:
                        exception = Exception(message.payload['exception'])
                        formatted_error = format_error(exception, message.from_agent)
                        logger.error(f"Formatted error: {formatted_error}")
                    except Exception as e:
                        logger.warning(f"Failed to format error: {e}")
        
        error_handler = create_simple_handler("global_error_handler", global_error_handler)
        error_handler.add_pattern("task_error:*->*")
        
        self.message_bus.add_global_handler(error_handler)
    
    async def register_agent(self, 
                           agent_id: str, 
                           capabilities: List[str] = None,
                           groups: List[str] = None,
                           handler_func: callable = None) -> bool:
        """Register a new agent with the system"""
        
        if not self.message_bus:
            logger.error("Message bus not initialized")
            return False
        
        try:
            # Create default handler if none provided
            if not handler_func:
                handler_func = self._create_default_handler(agent_id)
            
            handler = create_simple_handler(agent_id, handler_func)
            
            # Register with message bus
            self.message_bus.register_agent(
                agent_id=agent_id,
                capabilities=capabilities or [],
                groups=groups or [],
                handlers=[handler]
            )
            
            # Store in local registry
            self.registered_agents[agent_id] = {
                'capabilities': capabilities or [],
                'groups': groups or [],
                'registered_at': datetime.now(timezone.utc),
                'status': 'active'
            }
            
            logger.info(f"Successfully registered agent: {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False
    
    def _create_default_handler(self, agent_id: str):
        """Create a default message handler for an agent"""
        
        async def default_handler(message: AgentMessage) -> Optional[AgentMessage]:
            """Default message handler - just logs and acknowledges"""
            
            logger.info(f"Agent {agent_id} received message: {message.message_type.value}")
            
            # Handle different message types
            if message.message_type == MessageType.TASK_REQUEST:
                # Simulate task processing
                await asyncio.sleep(0.1)  # Simulate work
                
                # Send progress update
                progress_msg = create_progress_message(
                    from_agent=agent_id,
                    to_agent=message.from_agent,
                    progress=0.5,
                    info={'step': 'processing', 'details': 'Task in progress'}
                )
                
                if self.message_bus:
                    await self.message_bus.send_message(progress_msg)
                
                # Send completion
                result_msg = create_result_message(
                    from_agent=agent_id,
                    to_agent=message.from_agent,
                    result={'status': 'completed', 'data': 'Task completed successfully'},
                    confidence=0.9
                )
                
                return result_msg
            
            elif message.message_type == MessageType.HEARTBEAT:
                # Respond to heartbeat
                return create_heartbeat(
                    agent_id=agent_id,
                    status={'load': 0.3, 'memory_usage': 0.2, 'status': 'healthy'}
                )
            
            return None
        
        return default_handler
    
    async def execute_task(self, 
                         task_description: str,
                         target_agents: List[str] = None,
                         timeout_seconds: int = 30,
                         use_six_stage_orchestration: bool = True,
                         enable_streaming: bool = True) -> Dict[str, Any]:
        """Execute a task using Claude Code's sophisticated orchestration patterns"""
        
        if not self.message_bus or not self.progress_aggregator:
            return {'error': 'Coordinator not properly initialized'}
        
        task_id = str(uuid.uuid4())
        
        # Use six-stage orchestration or fallback to simple execution
        if use_six_stage_orchestration:
            return await self._execute_six_stage_orchestration(
                task_id, task_description, target_agents, timeout_seconds, enable_streaming
            )
        else:
            return await self._execute_simple_task(
                task_id, task_description, target_agents, timeout_seconds
            )
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        
        status = {
            'coordinator_status': 'running' if self.message_bus else 'stopped',
            'registered_agents': len(self.registered_agents),
            'active_tasks': len([t for t in self.active_tasks.values() if t['status'] == 'running']),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Message bus statistics
        if self.message_bus:
            status['message_bus'] = self.message_bus.get_statistics()
            status['health'] = self.message_bus.get_health_status()
        
        # Progress aggregator statistics
        if self.progress_aggregator:
            status['progress_aggregator'] = self.progress_aggregator.get_performance_metrics()
        
        # Memory management statistics
        if self.memory_manager:
            status['memory_manager'] = self.memory_manager.get_memory_stats()
        
        # Agent details
        status['agents'] = {}
        for agent_id, agent_info in self.registered_agents.items():
            if self.message_bus:
                agent_stats = self.message_bus.agent_registry.get_agent_stats(agent_id)
                status['agents'][agent_id] = {
                    **agent_info,
                    **agent_stats
                }
            else:
                status['agents'][agent_id] = agent_info
        
        # Add orchestration metrics
        status['orchestration_metrics'] = self.orchestration_metrics
        status['current_state'] = self.current_state
        status['state_machine_active'] = self.state_machine_active
        status['active_pipelines'] = len(self.task_pipelines)
        
        return status
    
    async def demonstrate_streaming_parsing(self, message_stream: str) -> Dict[str, Any]:
        """Demonstrate streaming message parsing capabilities"""
        
        # Simulate streaming data
        async def simulate_stream():
            chunks = [message_stream[i:i+10] for i in range(0, len(message_stream), 10)]
            for chunk in chunks:
                yield chunk.encode('utf-8')
                await asyncio.sleep(0.01)  # Simulate network latency
        
        results = []
        
        # Parse the stream
        async for parsed_result in self.streaming_parser.parse_stream(simulate_stream()):
            results.append({
                'result_type': parsed_result.result_type.value,
                'confidence': parsed_result.confidence,
                'message_available': parsed_result.message is not None,
                'partial_data_available': parsed_result.partial_data is not None,
                'parse_time_ms': parsed_result.parse_time_ms,
                'validation_passed': parsed_result.validation_passed
            })
        
        return {
            'total_results': len(results),
            'results': results,
            'parser_stats': self.streaming_parser.get_performance_metrics()
        }


# Usage examples and demonstrations

async def basic_usage_example():
    """Basic usage example of the agent infrastructure"""
    
    print("=== Basic Agent Infrastructure Usage Example ===")
    
    # Create coordinator
    coordinator = AgentCoordinator()
    
    try:
        # Start the system
        await coordinator.start()
        
        # Register some agents
        await coordinator.register_agent("data_processor", capabilities=["data_processing", "analysis"])
        await coordinator.register_agent("report_generator", capabilities=["reporting", "visualization"])
        await coordinator.register_agent("validator", capabilities=["validation", "quality_check"])
        
        # Get system status
        status = await coordinator.get_system_status()
        print(f"System started with {status['registered_agents']} agents")
        
        # Execute a task
        task_result = await coordinator.execute_task(
            task_description="Process data and generate report",
            target_agents=["data_processor", "report_generator"],
            timeout_seconds=10
        )
        
        print(f"Task execution result: {task_result}")
        
        # Demonstrate streaming parsing
        sample_message = """
        {
            "message_type": "task_request",
            "from_agent": "user",
            "to_agent": "processor",
            "payload": {
                "task": "analyze_data",
                "parameters": {"format": "json"}
            }
        }
        """
        
        parsing_result = await coordinator.demonstrate_streaming_parsing(sample_message)
        print(f"Streaming parsing demonstration: {parsing_result}")
        
    finally:
        # Clean up
        await coordinator.stop()


async def advanced_usage_example():
    """Advanced usage example with Claude Code six-stage orchestration"""
    
    print("=== Advanced Agent Infrastructure Usage Example (Claude Code Style) ===")
    
    coordinator = AgentCoordinator()
    
    # Custom agent handler
    async def custom_ai_agent_handler(message: AgentMessage) -> Optional[AgentMessage]:
        """Custom handler for AI processing agent"""
        
        print(f"AI Agent received: {message.message_type.value}")
        
        if message.message_type == MessageType.TASK_REQUEST:
            # Simulate AI processing with progress updates
            task_data = message.payload
            
            # Send multiple progress updates
            progress_steps = [
                (0.1, "Initializing AI model"),
                (0.3, "Processing input data"),
                (0.6, "Running inference"), 
                (0.9, "Formatting results"),
                (1.0, "Task completed")
            ]
            
            for progress, step in progress_steps:
                progress_msg = create_progress_message(
                    from_agent="ai_processor",
                    to_agent=message.from_agent,
                    progress=progress,
                    info={'step': step, 'task_id': task_data.get('task_id')}
                )
                
                # Send progress update
                if coordinator.message_bus:
                    await coordinator.message_bus.send_message(progress_msg)
                
                await asyncio.sleep(0.2)  # Simulate processing time
            
            # Return final result
            return create_result_message(
                from_agent="ai_processor",
                to_agent=message.from_agent,
                result={
                    'task_id': task_data.get('task_id'),
                    'result': 'AI processing completed successfully',
                    'confidence': 0.95,
                    'processing_time': 1.0
                },
                confidence=0.95
            )
        
        return None
    
    try:
        await coordinator.start()
        
        # Register custom agent
        await coordinator.register_agent(
            "ai_processor",
            capabilities=["artificial_intelligence", "machine_learning", "nlp"],
            groups=["ai_agents", "processors"],
            handler_func=custom_ai_agent_handler
        )
        
        # Execute complex task using tt function (Claude Code style)
        print("\n🧠 Executing task with tt function (six-stage orchestration)...")
        result = await coordinator.tt(
            "Analyze customer sentiment and generate insights",
            target_agents=["ai_processor"],
            timeout_seconds=15,
            enable_streaming=True,
            memory_optimization=True
        )
        
        print(f"✅ tt function result: {result.get('success', False)}")
        print(f"📊 Orchestration method: {result.get('orchestration_method', 'unknown')}")
        
        # Show stage results if available
        stage_results = result.get('stage_results', {})
        if stage_results:
            print("\n📋 Stage-by-stage results:")
            for stage, stage_result in stage_results.items():
                success_indicator = "✅" if stage_result.get('success', True) else "❌"
                print(f"  {success_indicator} {stage}: {stage_result.get('success', True)}")
        
        # Demonstrate hierarchical agents if available
        print("\n🔗 Testing hierarchical agent management...")
        sub_success = await coordinator.register_sub_agent(
            parent_agent_id="ai_processor",
            sub_agent_id="nlp_sub_processor", 
            capabilities=["sentiment_analysis", "entity_extraction"]
        )
        
        if sub_success:
            hierarchy = coordinator.get_agent_hierarchy("ai_processor")
            print(f"✅ Sub-agent registered. Hierarchy: {hierarchy}")
        else:
            print("❌ Failed to register sub-agent")
        
        # Show final system status
        final_status = await coordinator.get_system_status()
        print(f"Final system status: {final_status}")
        
    except Exception as e:
        print(f"Error in advanced example: {e}")
        # The error formatter will handle this
        
    finally:
        await coordinator.stop()


async def performance_demonstration():
    """Demonstrate performance characteristics with six-stage orchestration"""
    
    print("=== Performance Demonstration (Six-Stage Orchestration) ===")
    
    coordinator = AgentCoordinator()
    
    try:
        await coordinator.start()
        
        # Register multiple agents for load testing
        agent_count = 5
        for i in range(agent_count):
            await coordinator.register_agent(
                f"worker_{i}",
                capabilities=["processing"],
                groups=["workers"]
            )
        
        # Test both orchestration methods
        import time
        
        print("\n🚀 Testing Six-Stage Orchestration Performance...")
        start_time = time.time()
        
        # Use tt function for sophisticated orchestration
        tasks = []
        for i in range(5):  # Fewer concurrent tasks for six-stage due to complexity
            task = coordinator.tt(
                f"Complex orchestrated task {i}",
                target_agents=[f"worker_{i % agent_count}"],
                timeout_seconds=8,
                enable_streaming=True
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        six_stage_time = time.time() - start_time
        successful_six_stage = sum(1 for r in results if r.get('success', False))
        
        print(f"Six-stage orchestration: {successful_six_stage}/{len(tasks)} successful")
        print(f"Six-stage execution time: {six_stage_time:.2f} seconds")
        
        # Compare with simple execution
        print("\n⚡ Testing Simple Execution Performance...")
        start_time = time.time()
        
        simple_tasks = []
        for i in range(10):  # More tasks for simple execution
            task = coordinator.execute_task(
                f"Simple task {i}",
                target_agents=[f"worker_{i % agent_count}"],
                timeout_seconds=5,
                use_six_stage_orchestration=False
            )
            simple_tasks.append(task)
        
        simple_results = await asyncio.gather(*simple_tasks)
        simple_time = time.time() - start_time
        successful_simple = sum(1 for r in simple_results if r.get('success', False))
        
        print(f"Simple execution: {successful_simple}/{len(simple_tasks)} successful")
        print(f"Simple execution time: {simple_time:.2f} seconds")
        
        # Show comparative analysis
        print("\n📊 Performance Comparison:")
        print(f"Six-stage avg per task: {six_stage_time / len(tasks):.2f}s")
        print(f"Simple avg per task: {simple_time / len(simple_tasks):.2f}s")
        print(f"Six-stage success rate: {successful_six_stage / len(tasks):.1%}")
        print(f"Simple success rate: {successful_simple / len(simple_tasks):.1%}")
        
        # Show orchestration metrics
        final_status = await coordinator.get_system_status()
        orchestration_metrics = final_status.get('orchestration_metrics', {})
        
        print(f"\n🎯 Orchestration Metrics:")
        print(f"Total orchestrations: {orchestration_metrics.get('total_orchestrations', 0)}")
        print(f"Successful orchestrations: {orchestration_metrics.get('successful_orchestrations', 0)}")
        print(f"Failed orchestrations: {orchestration_metrics.get('failed_orchestrations', 0)}")
        
        # Show stage performance if available
        stage_performance = orchestration_metrics.get('stage_performance', {})
        if stage_performance:
            print(f"\n⏱️  Average Stage Performance:")
            for stage, times in stage_performance.items():
                if times:
                    avg_time = sum(times) / len(times)
                    print(f"  {stage}: {avg_time:.1f}ms")
        
    finally:
        await coordinator.stop()


if __name__ == "__main__":
    # Run all examples
    async def main():
        await basic_usage_example()
        print("\n" + "="*50 + "\n")
        
        await advanced_usage_example() 
        print("\n" + "="*50 + "\n")
        
        await performance_demonstration()
    
    asyncio.run(main())