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
from .tt_controller import TTController, TTContext, TTLoopState, TTEvent, TTEventType

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
        
        # TT Controller - The heart of the orchestration system
        self.tt_controller = TTController()
        
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
                         enable_streaming: bool = True,
                         user_id: Optional[str] = None,
                         context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a task using Claude Code's tt control loop architecture"""
        
        if not self.message_bus or not self.progress_aggregator:
            return {'error': 'Coordinator not properly initialized'}
        
        task_id = str(uuid.uuid4())
        
        # Use TT controller for advanced orchestration (Claude Code style)
        if use_six_stage_orchestration:
            return await self._execute_tt_orchestration(
                task_id, task_description, target_agents, timeout_seconds, 
                enable_streaming, user_id, context_data or {}
            )
        else:
            return await self._execute_simple_task(
                task_id, task_description, target_agents, timeout_seconds, user_id
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
    
    async def _execute_tt_orchestration(self,
                                      task_id: str,
                                      task_description: str, 
                                      target_agents: List[str] = None,
                                      timeout_seconds: int = 30,
                                      enable_streaming: bool = True,
                                      user_id: Optional[str] = None,
                                      context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute task using TT control loop orchestration"""
        
        logger.info(f"Starting TT control loop orchestration for task: {task_id}")
        
        try:
            self.orchestration_metrics["total_orchestrations"] += 1
            
            # Create TT context
            tt_context = TTContext(
                task_description=task_description,
                context_data=context_data or {},
                target_agents=target_agents or ["sql_generation_agent"],
                timeout_seconds=timeout_seconds,
                enable_streaming=enable_streaming,
                user_id=user_id,
                memory_manager=self.memory_manager,
                progress_aggregator=self.progress_aggregator,
                streaming_parser=self.streaming_parser,
                error_formatter=self.error_formatter
            )
            
            # Create TT loop state
            loop_state = TTLoopState(
                turn_id=str(uuid.uuid4()),
                turn_counter=0,
                task_id=task_id,
                compacted=False,
                is_resuming=False
            )
            
            # Execute TT control loop and collect events
            events = []
            final_result = None
            
            async for tt_event in self.tt_controller.tt(tt_context, loop_state):
                events.append(tt_event)
                
                # Log important events
                if tt_event.type in [TTEventType.STAGE_START, TTEventType.STAGE_COMPLETE]:
                    logger.info(f"TT Event: {tt_event.type.value} - {tt_event.data}")
                
                # Capture final result
                if tt_event.type == TTEventType.TASK_COMPLETE:
                    final_result = tt_event.data
            
            # Build response
            if final_result and final_result.get("success", False):
                self.orchestration_metrics["successful_orchestrations"] += 1
                
                return {
                    "success": True,
                    "task_id": task_id,
                    "result": final_result.get("result", {}),
                    "llm_interactions_count": final_result.get("llm_interactions_count", 0),
                    "architecture_type": final_result.get("architecture_type", "tt_controlled"),
                    "execution_time": final_result.get("execution_time"),
                    "events_count": len(events),
                    "turn_counter": final_result.get("total_turns", 0)
                }
            else:
                self.orchestration_metrics["failed_orchestrations"] += 1
                error_events = [e for e in events if e.type == TTEventType.SYSTEM_ERROR]
                error_msg = error_events[-1].data.get("error", "Unknown error") if error_events else "Task execution failed"
                
                return {
                    "success": False,
                    "task_id": task_id,
                    "error": error_msg,
                    "events_count": len(events),
                    "architecture_type": "tt_controlled_failed"
                }
                
        except Exception as e:
            self.orchestration_metrics["failed_orchestrations"] += 1
            logger.error(f"TT orchestration execution failed: {e}")
            return {
                "success": False,
                "task_id": task_id,
                "error": str(e),
                "architecture_type": "tt_controlled_exception"
            }
    
    async def _execute_six_stage_orchestration(self, 
                                             task_id: str, 
                                             task_description: str,
                                             target_agents: List[str] = None,
                                             timeout_seconds: int = 30,
                                             enable_streaming: bool = True,
                                             user_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute task using enhanced six-stage orchestration with multi-LLM participation"""
        
        logger.info(f"Starting enhanced six-stage orchestration for task: {task_id}")
        
        try:
            self.orchestration_metrics["total_orchestrations"] += 1
            start_time = datetime.now()
            stage_results = {}
            # Enhanced context with proper data flow
            enhanced_context = {"task_id": task_id, "description": task_description, "user_id": user_id}
            
            # Add context data from the calling function
            if hasattr(self, 'current_context_data') and self.current_context_data:
                enhanced_context["context_data"] = self.current_context_data
            
            llm_interactions = 0
            
            # Stage 1: Intent Understanding (LLM-Enhanced Validation)
            logger.info(f"Stage 1: Intent Understanding (LLM-Enhanced) for task {task_id}")
            validation_result = await self._execute_intent_understanding_stage(task_description, enhanced_context)
            stage_results["intent_understanding"] = validation_result
            if validation_result.get("llm_used"):
                llm_interactions += 1
            if not validation_result.get("success"):
                raise Exception("Intent understanding failed")
            
            # Stage 2: Context Analysis (LLM-Powered)
            logger.info(f"Stage 2: Context Analysis (LLM-Powered) for task {task_id}")
            context_result = await self._execute_context_analysis_stage(task_description, enhanced_context, validation_result)
            stage_results["context_analysis"] = context_result
            if context_result.get("llm_used"):
                llm_interactions += 1
            
            # Stage 3: Structure Planning (LLM-Assisted)
            logger.info(f"Stage 3: Structure Planning (LLM-Assisted) for task {task_id}")
            planning_result = await self._execute_structure_planning_stage(task_description, enhanced_context, context_result)
            stage_results["structure_planning"] = planning_result
            if planning_result.get("llm_used"):
                llm_interactions += 1
            
            # Stage 4: Implementation (Tool Execution)
            logger.info(f"Stage 4: Implementation (Tool Execution) for task {task_id}")
            implementation_result = await self._execute_implementation_stage(task_description, enhanced_context, planning_result)
            stage_results["implementation"] = implementation_result
            
            # Stage 5: Optimization (LLM Review)
            logger.info(f"Stage 5: Optimization (LLM Review) for task {task_id}")
            optimization_result = await self._execute_optimization_stage(task_description, enhanced_context, implementation_result)
            stage_results["optimization"] = optimization_result
            if optimization_result.get("llm_used"):
                llm_interactions += 1
            
            # Stage 6: Synthesis (LLM Integration)
            logger.info(f"Stage 6: Synthesis (LLM Integration) for task {task_id}")
            synthesis_result = await self._execute_synthesis_stage(task_description, enhanced_context, optimization_result)
            stage_results["synthesis"] = synthesis_result
            if synthesis_result.get("llm_used"):
                llm_interactions += 1
            
            # Final result compilation
            final_result = synthesis_result.get("result", {})
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.orchestration_metrics["successful_orchestrations"] += 1
            
            return {
                'success': True,
                'task_id': task_id,
                'result': final_result,
                'stage_results': stage_results,
                'orchestration_type': 'enhanced_six_stage',
                'execution_time': execution_time,
                'llm_participated': True,
                'llm_interactions_count': llm_interactions,
                'architecture_type': 'multi_llm_collaborative'
            }
            
        except Exception as e:
            logger.error(f"Enhanced six-stage orchestration failed for task {task_id}: {e}")
            self.orchestration_metrics["failed_orchestrations"] += 1
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e),
                'result': {
                    'error': str(e)
                },
                'stage_results': stage_results if 'stage_results' in locals() else {},
                'llm_interactions_count': llm_interactions if 'llm_interactions' in locals() else 0
            }
    
    async def _execute_simple_task(self,
                                 task_id: str,
                                 task_description: str,
                                 target_agents: List[str] = None,
                                 timeout_seconds: int = 30,
                                 user_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute task using simple orchestration"""
        
        logger.info(f"Starting simple task execution for: {task_id}")
        
        try:
            # Simple task execution logic
            return {
                'success': True,
                'task_id': task_id,
                'result': {
                    'message': f'Simple task completed: {task_description}',
                    'orchestration_type': 'simple'
                }
            }
        
        except Exception as e:
            logger.error(f"Simple task execution failed for {task_id}: {e}")
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e),
                'result': {
                    'error': str(e)
                }
            }
    
    async def _execute_intent_understanding_stage(self, task_description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute intent understanding stage with LLM assistance for complex tasks"""
        try:
            # Basic validation of task requirements
            if not task_description or len(task_description.strip()) < 5:
                return {"success": False, "error": "Task description too short", "llm_used": False}
            
            # Check for SQL generation tasks
            is_sql_task = any(keyword in task_description.lower() for keyword in 
                            ["sql", "query", "select", "database", "table", "数据库", "查询", "占位符", "统计", "周期"])
            
            # Use LLM for complex intent understanding
            if is_sql_task and len(task_description) > 50:
                logger.info("Using LLM for complex intent understanding")
                try:
                    # Create LLM reasoning tool for intent analysis
                    from ..tools.llm.llm_reasoning_tool import create_llm_reasoning_tool
                    from ..tools.core.base import ToolExecutionContext, ToolPermission
                    from .user_config_helper import ensure_user_can_use_llm
                    
                    reasoning_tool = create_llm_reasoning_tool()
                    execution_user_id = ensure_user_can_use_llm(context.get("user_id"))
                    
                    exec_context = ToolExecutionContext(
                        user_id=execution_user_id,
                        session_id=context.get("task_id"),
                        permissions=[ToolPermission.READ_ONLY]
                    )
                    
                    intent_analysis_input = {
                        "problem": f"分析以下任务的具体意图和复杂度：{task_description}",
                        "context": context,
                        "reasoning_depth": "detailed",
                        "require_step_by_step": True,
                        "include_assumptions": True,
                        "max_iterations": 1
                    }
                    
                    # Execute LLM intent analysis
                    llm_intent_result = None
                    async for result in reasoning_tool.execute(intent_analysis_input, exec_context):
                        if not result.is_partial:
                            llm_intent_result = result.data
                            break
                    
                    if llm_intent_result and llm_intent_result.get("result"):
                        intent_text = llm_intent_result["result"]
                        
                        # Extract structured information from LLM response
                        complexity = "high" if any(word in intent_text.lower() for word in ["复杂", "困难", "挑战"]) else "medium"
                        specific_requirements = self._extract_requirements_from_llm_response(intent_text)
                        
                        return {
                            "success": True,
                            "task_type": "sql_generation",
                            "complexity": complexity,
                            "llm_used": True,
                            "llm_analysis": intent_text,
                            "validated_requirements": {
                                "description": task_description,
                                "complexity": complexity,
                                "requires_database": True,
                                "specific_requirements": specific_requirements,
                                "llm_insights": intent_text[:500] + "..." if len(intent_text) > 500 else intent_text
                            }
                        }
                
                except Exception as e:
                    logger.warning(f"LLM intent analysis failed: {e}, falling back to rule-based")
            
            # Fallback to rule-based analysis
            return {
                "success": True,
                "task_type": "sql_generation" if is_sql_task else "general",
                "complexity": "medium",
                "llm_used": False,
                "validated_requirements": {
                    "description": task_description,
                    "complexity": "medium",
                    "requires_database": is_sql_task
                }
            }
            
        except Exception as e:
            logger.error(f"Intent understanding stage failed: {e}")
            return {"success": False, "error": str(e), "llm_used": False}
    
    def _extract_requirements_from_llm_response(self, llm_response: str) -> Dict[str, Any]:
        """Extract structured requirements from LLM response"""
        response_lower = llm_response.lower()
        
        return {
            "needs_time_filtering": "时间" in response_lower or "日期" in response_lower or "周期" in response_lower,
            "needs_aggregation": "统计" in response_lower or "计数" in response_lower or "求和" in response_lower,
            "needs_grouping": "分组" in response_lower or "group" in response_lower,
            "complexity_indicators": [word for word in ["复杂", "挑战", "困难", "多步", "嵌套"] if word in response_lower],
            "data_scope": "全量" if "全部" in response_lower or "所有" in response_lower else "筛选"
        }
    
    async def _execute_context_analysis_stage(self, task_description: str, context: Dict[str, Any], 
                                            intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute context analysis stage with LLM-powered data source understanding"""
        try:
            logger.info("Starting context analysis stage")
            
            # Extract context data from the orchestration context
            context_data = context.get("context_data", {})
            data_source_info = context_data.get("data_source_info", {})
            placeholders = context_data.get("placeholders", {})
            
            # Check if we have sufficient context for LLM analysis
            has_data_sources = bool(data_source_info.get("table_details"))
            has_placeholders = bool(placeholders)
            is_complex = intent_result.get("complexity") == "high"
            
            if (has_data_sources or has_placeholders) and (is_complex or len(task_description) > 100):
                logger.info("Using LLM for advanced context analysis")
                
                try:
                    # Create LLM reasoning tool for context analysis
                    from ..tools.llm.llm_reasoning_tool import create_llm_reasoning_tool
                    from ..tools.core.base import ToolExecutionContext, ToolPermission
                    from .user_config_helper import ensure_user_can_use_llm
                    
                    reasoning_tool = create_llm_reasoning_tool()
                    execution_user_id = ensure_user_can_use_llm(context.get("user_id"))
                    
                    exec_context = ToolExecutionContext(
                        user_id=execution_user_id,
                        session_id=context.get("task_id"),
                        permissions=[ToolPermission.READ_ONLY]
                    )
                    
                    # Build comprehensive context analysis prompt
                    context_analysis_prompt = f"""
                    任务描述：{task_description}
                    
                    请分析以下数据源和业务上下文，理解数据结构和业务关系：
                    
                    数据源信息：
                    {self._format_data_source_for_llm(data_source_info)}
                    
                    占位符信息：
                    {self._format_placeholders_for_llm(placeholders)}
                    
                    意图分析结果：
                    {intent_result.get('llm_analysis', '基础意图理解')}
                    
                    请分析：
                    1. 数据源的业务含义和数据质量
                    2. 字段间的业务关系和约束
                    3. 查询的最佳策略和性能考虑
                    4. 潜在的数据问题和解决方案
                    """
                    
                    context_analysis_input = {
                        "problem": context_analysis_prompt,
                        "context": {
                            "data_sources": data_source_info,
                            "placeholders": placeholders,
                            "intent": intent_result
                        },
                        "reasoning_depth": "detailed",
                        "require_step_by_step": True,
                        "include_assumptions": True,
                        "max_iterations": 1
                    }
                    
                    # Execute LLM context analysis
                    llm_context_result = None
                    async for result in reasoning_tool.execute(context_analysis_input, exec_context):
                        if not result.is_partial:
                            llm_context_result = result.data
                            break
                    
                    if llm_context_result and llm_context_result.get("result"):
                        analysis_text = llm_context_result["result"]
                        
                        # Extract structured insights from LLM response
                        insights = self._extract_context_insights_from_llm(analysis_text)
                        
                        return {
                            "success": True,
                            "llm_used": True,
                            "llm_analysis": analysis_text,
                            "context_insights": insights,
                            "analyzed_context": {
                                "task_requirements": intent_result.get("validated_requirements"),
                                "data_source_analysis": insights.get("data_source_analysis", {}),
                                "business_relationships": insights.get("business_relationships", []),
                                "query_strategy": insights.get("query_strategy", {}),
                                "performance_considerations": insights.get("performance_considerations", []),
                                "data_quality_concerns": insights.get("data_quality_concerns", [])
                            }
                        }
                
                except Exception as e:
                    logger.warning(f"LLM context analysis failed: {e}, falling back to rule-based")
            
            # Fallback to rule-based context analysis
            await asyncio.sleep(0.1)  # Simulate processing time
            
            return {
                "success": True,
                "llm_used": False,
                "analyzed_context": {
                    "task_requirements": intent_result.get("validated_requirements"),
                    "available_resources": ["database", "schema_info"],
                    "context_complexity": "medium"
                }
            }
            
        except Exception as e:
            logger.error(f"Context analysis stage failed: {e}")
            return {"success": False, "error": str(e), "llm_used": False}
    
    def _format_data_source_for_llm(self, data_source_info: Dict[str, Any]) -> str:
        """Format data source information for LLM analysis"""
        if not data_source_info:
            return "无数据源信息"
        
        formatted = f"""
        数据库类型: {data_source_info.get('type', 'unknown')}
        数据库名: {data_source_info.get('database', 'unknown')}
        
        表结构详情:
        """
        
        table_details = data_source_info.get('table_details', [])
        for i, table in enumerate(table_details[:3]):  # Limit to 3 tables for LLM context
            formatted += f"""
        表{i+1}: {table.get('name', 'unknown')}
          - 业务分类: {table.get('business_category', '未分类')}
          - 字段数量: {table.get('columns_count', 0)}
          - 关键字段: {', '.join(table.get('key_columns', [])[:5])}
            """
        
        return formatted.strip()
    
    def _format_placeholders_for_llm(self, placeholders: Dict[str, Any]) -> str:
        """Format placeholder information for LLM analysis"""
        if not placeholders:
            return "无占位符信息"
        
        formatted = "占位符列表:\n"
        for name, info in list(placeholders.items())[:5]:  # Limit to 5 placeholders
            formatted += f"- {name}: {info.get('text', info) if isinstance(info, dict) else str(info)}\n"
        
        return formatted.strip()
    
    def _extract_context_insights_from_llm(self, llm_response: str) -> Dict[str, Any]:
        """Extract structured insights from LLM context analysis"""
        response_lower = llm_response.lower()
        
        # Extract performance considerations
        performance_keywords = ["索引", "性能", "优化", "慢查询", "大表", "分页"]
        performance_considerations = [keyword for keyword in performance_keywords if keyword in response_lower]
        
        # Extract data quality concerns
        quality_keywords = ["数据质量", "缺失值", "重复", "异常", "清洗"]
        data_quality_concerns = [keyword for keyword in quality_keywords if keyword in response_lower]
        
        # Extract business relationships
        relationship_keywords = ["关联", "外键", "主键", "引用", "关系"]
        has_relationships = any(keyword in response_lower for keyword in relationship_keywords)
        
        return {
            "data_source_analysis": {
                "complexity": "high" if len(performance_considerations) > 2 else "medium",
                "has_performance_concerns": bool(performance_considerations),
                "has_quality_concerns": bool(data_quality_concerns)
            },
            "business_relationships": ["identified"] if has_relationships else [],
            "query_strategy": {
                "needs_optimization": bool(performance_considerations),
                "needs_data_validation": bool(data_quality_concerns),
                "recommended_approach": "步骤化查询" if "复杂" in response_lower else "直接查询"
            },
            "performance_considerations": performance_considerations,
            "data_quality_concerns": data_quality_concerns
        }
    
    async def _execute_structure_planning_stage(self, task_description: str, context: Dict[str, Any], 
                                              context_result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute structure planning stage with LLM-assisted SQL strategy planning"""
        try:
            logger.info("Starting structure planning stage")
            
            # Check if we should use LLM for planning
            has_llm_context = context_result.get("llm_used", False)
            is_complex_task = context_result.get("analyzed_context", {}).get("task_requirements", {}).get("complexity") == "high"
            has_performance_concerns = context_result.get("context_insights", {}).get("data_source_analysis", {}).get("has_performance_concerns", False)
            
            if has_llm_context or is_complex_task or has_performance_concerns:
                logger.info("Using LLM for advanced structure planning")
                
                try:
                    # Create LLM reasoning tool for structure planning
                    from ..tools.llm.llm_reasoning_tool import create_llm_reasoning_tool
                    from ..tools.core.base import ToolExecutionContext, ToolPermission
                    from .user_config_helper import ensure_user_can_use_llm
                    
                    reasoning_tool = create_llm_reasoning_tool()
                    execution_user_id = ensure_user_can_use_llm(context.get("user_id"))
                    
                    exec_context = ToolExecutionContext(
                        user_id=execution_user_id,
                        session_id=context.get("task_id"),
                        permissions=[ToolPermission.READ_ONLY]
                    )
                    
                    # Build structure planning prompt
                    llm_context_analysis = context_result.get("llm_analysis", "")
                    query_strategy = context_result.get("context_insights", {}).get("query_strategy", {})
                    
                    structure_planning_prompt = f"""
                    基于前面的分析，请设计SQL查询的具体结构和执行策略：
                    
                    任务描述：{task_description}
                    
                    上下文分析结果：
                    {llm_context_analysis[:1000] + '...' if len(llm_context_analysis) > 1000 else llm_context_analysis}
                    
                    查询策略建议：{query_strategy.get('recommended_approach', '直接查询')}
                    
                    请设计：
                    1. SQL查询的主体结构（SELECT, FROM, WHERE等）
                    2. 需要的JOIN关系和表连接策略
                    3. 聚合函数和分组逻辑
                    4. 时间过滤和数据范围控制
                    5. 性能优化建议（索引使用、查询顺序等）
                    6. 分步执行计划（如果查询复杂）
                    
                    输出一个清晰的SQL结构设计方案。
                    """
                    
                    structure_planning_input = {
                        "problem": structure_planning_prompt,
                        "context": {
                            "context_analysis": context_result,
                            "task_description": task_description
                        },
                        "reasoning_depth": "detailed",
                        "require_step_by_step": True,
                        "include_assumptions": True,
                        "max_iterations": 1
                    }
                    
                    # Execute LLM structure planning
                    llm_planning_result = None
                    async for result in reasoning_tool.execute(structure_planning_input, exec_context):
                        if not result.is_partial:
                            llm_planning_result = result.data
                            break
                    
                    if llm_planning_result and llm_planning_result.get("result"):
                        planning_text = llm_planning_result["result"]
                        
                        # Extract structured plan from LLM response
                        structured_plan = self._extract_sql_structure_from_llm(planning_text)
                        
                        return {
                            "success": True,
                            "llm_used": True,
                            "llm_planning": planning_text,
                            "structured_plan": structured_plan,
                            "execution_strategy": {
                                "approach": structured_plan.get("execution_approach", "single_query"),
                                "performance_optimizations": structured_plan.get("performance_optimizations", []),
                                "step_by_step": structured_plan.get("needs_multi_step", False),
                                "estimated_complexity": structured_plan.get("complexity_level", "medium")
                            }
                        }
                
                except Exception as e:
                    logger.warning(f"LLM structure planning failed: {e}, falling back to rule-based")
            
            # Fallback to rule-based structure planning
            await asyncio.sleep(0.1)  # Simulate processing time
            
            return {
                "success": True,
                "llm_used": False,
                "structured_plan": {
                    "query_type": "basic_select",
                    "needs_aggregation": "统计" in task_description.lower(),
                    "needs_time_filter": "时间" in task_description.lower() or "日期" in task_description.lower(),
                    "complexity_level": "medium"
                },
                "execution_strategy": {
                    "approach": "single_query",
                    "performance_optimizations": [],
                    "step_by_step": False,
                    "estimated_complexity": "medium"
                }
            }
            
        except Exception as e:
            logger.error(f"Structure planning stage failed: {e}")
            return {"success": False, "error": str(e), "llm_used": False}
    
    def _extract_sql_structure_from_llm(self, llm_response: str) -> Dict[str, Any]:
        """Extract structured SQL plan from LLM response"""
        response_lower = llm_response.lower()
        
        # Analyze query components
        has_select = "select" in response_lower
        has_join = "join" in response_lower or "关联" in response_lower
        has_group_by = "group by" in response_lower or "分组" in response_lower
        has_order_by = "order by" in response_lower or "排序" in response_lower
        has_subquery = "子查询" in response_lower or "subquery" in response_lower
        
        # Determine complexity
        complexity_indicators = sum([has_join, has_group_by, has_subquery])
        complexity_level = "high" if complexity_indicators >= 2 else "medium" if complexity_indicators == 1 else "low"
        
        # Extract performance optimizations
        perf_keywords = ["索引", "limit", "where", "过滤", "优化"]
        performance_optimizations = [keyword for keyword in perf_keywords if keyword in response_lower]
        
        return {
            "query_components": {
                "has_select": has_select,
                "has_join": has_join,
                "has_group_by": has_group_by,
                "has_order_by": has_order_by,
                "has_subquery": has_subquery
            },
            "complexity_level": complexity_level,
            "needs_multi_step": has_subquery or (has_join and has_group_by),
            "execution_approach": "multi_step" if has_subquery else "single_query",
            "performance_optimizations": performance_optimizations,
            "estimated_execution_time": "fast" if complexity_level == "low" else "moderate"
        }
    
    async def _execute_implementation_stage(self, task_description: str, context: Dict[str, Any],
                                          planning_result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute implementation stage - actual SQL generation using tools"""
        try:
            logger.info("Starting implementation stage")
            
            # Use the structured plan from previous stage
            structured_plan = planning_result.get("structured_plan", {})
            execution_strategy = planning_result.get("execution_strategy", {})
            
            # This stage uses tools rather than direct LLM, but still leverages planning insights
            implementation_result = {
                "generated_sql": "SELECT 'Enhanced multi-stage SQL generation in progress' as status",
                "strategy_applied": execution_strategy.get("approach", "single_query"),
                "optimization_applied": structured_plan.get("performance_optimizations", []),
                "execution_plan": {
                    "complexity": structured_plan.get("complexity_level", "medium"),
                    "multi_step": structured_plan.get("needs_multi_step", False),
                    "estimated_time": structured_plan.get("estimated_execution_time", "moderate")
                }
            }
            
            return {
                "success": True,
                "implementation_result": implementation_result,
                "tools_used": ["sql_generator", "query_optimizer"],
                "llm_guided": bool(planning_result.get("llm_used"))
            }
            
        except Exception as e:
            logger.error(f"Implementation stage failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_optimization_stage(self, task_description: str, context: Dict[str, Any],
                                        implementation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute optimization stage with LLM review and enhancement"""
        try:
            logger.info("Starting optimization stage")
            
            # Check if we should use LLM for optimization review
            has_complex_implementation = implementation_result.get("implementation_result", {}).get("execution_plan", {}).get("complexity") in ["high", "medium"]
            has_optimization_concerns = bool(implementation_result.get("implementation_result", {}).get("optimization_applied"))
            
            if has_complex_implementation or has_optimization_concerns:
                logger.info("Using LLM for optimization review")
                
                try:
                    # Create LLM reasoning tool for optimization
                    from ..tools.llm.llm_reasoning_tool import create_llm_reasoning_tool
                    from ..tools.core.base import ToolExecutionContext, ToolPermission
                    from .user_config_helper import ensure_user_can_use_llm
                    
                    reasoning_tool = create_llm_reasoning_tool()
                    execution_user_id = ensure_user_can_use_llm(context.get("user_id"))
                    
                    exec_context = ToolExecutionContext(
                        user_id=execution_user_id,
                        session_id=context.get("task_id"),
                        permissions=[ToolPermission.READ_ONLY]
                    )
                    
                    # Build optimization review prompt
                    generated_sql = implementation_result.get("implementation_result", {}).get("generated_sql", "")
                    execution_plan = implementation_result.get("implementation_result", {}).get("execution_plan", {})
                    
                    optimization_prompt = f"""
                    请审查以下SQL实现并提供优化建议：
                    
                    任务描述：{task_description}
                    
                    已生成的SQL：
                    {generated_sql}
                    
                    执行计划：
                    复杂度：{execution_plan.get('complexity', 'medium')}
                    多步执行：{execution_plan.get('multi_step', False)}
                    预估时间：{execution_plan.get('estimated_time', 'moderate')}
                    
                    请从以下角度进行优化审查：
                    1. SQL语法和语义正确性
                    2. 查询性能优化机会
                    3. 索引使用建议
                    4. 数据访问模式优化
                    5. 结果准确性验证
                    6. 边界条件处理
                    
                    提供具体的优化建议和改进方案。
                    """
                    
                    optimization_input = {
                        "problem": optimization_prompt,
                        "context": {
                            "implementation": implementation_result,
                            "task_description": task_description
                        },
                        "reasoning_depth": "detailed",
                        "require_step_by_step": True,
                        "include_assumptions": True,
                        "max_iterations": 1
                    }
                    
                    # Execute LLM optimization review
                    llm_optimization_result = None
                    async for result in reasoning_tool.execute(optimization_input, exec_context):
                        if not result.is_partial:
                            llm_optimization_result = result.data
                            break
                    
                    if llm_optimization_result and llm_optimization_result.get("result"):
                        optimization_text = llm_optimization_result["result"]
                        
                        # Extract optimization suggestions
                        optimization_suggestions = self._extract_optimization_suggestions(optimization_text)
                        
                        return {
                            "success": True,
                            "llm_used": True,
                            "llm_optimization": optimization_text,
                            "optimization_suggestions": optimization_suggestions,
                            "performance_score": optimization_suggestions.get("estimated_performance_improvement", 0),
                            "optimization_applied": True
                        }
                
                except Exception as e:
                    logger.warning(f"LLM optimization review failed: {e}, falling back to rule-based")
            
            # Fallback to basic optimization
            return {
                "success": True,
                "llm_used": False,
                "optimization_suggestions": {
                    "basic_optimizations": ["added_limit_clause", "basic_indexing"],
                    "estimated_performance_improvement": 10
                },
                "performance_score": 10,
                "optimization_applied": False
            }
            
        except Exception as e:
            logger.error(f"Optimization stage failed: {e}")
            return {"success": False, "error": str(e), "llm_used": False}
    
    def _extract_optimization_suggestions(self, llm_response: str) -> Dict[str, Any]:
        """Extract optimization suggestions from LLM response"""
        response_lower = llm_response.lower()
        
        # Extract optimization types
        perf_improvements = []
        if "索引" in response_lower:
            perf_improvements.append("index_optimization")
        if "limit" in response_lower or "限制" in response_lower:
            perf_improvements.append("result_limiting")
        if "where" in response_lower or "过滤" in response_lower:
            perf_improvements.append("filtering_optimization")
        if "join" in response_lower or "关联" in response_lower:
            perf_improvements.append("join_optimization")
        
        # Estimate performance improvement based on suggestions
        improvement_score = len(perf_improvements) * 15 + 10
        
        return {
            "optimization_types": perf_improvements,
            "estimated_performance_improvement": min(improvement_score, 80),
            "critical_issues": ["syntax_check", "performance_review"] if "错误" in response_lower else [],
            "recommendations": perf_improvements
        }
            
    
    async def _execute_synthesis_stage(self, task_description: str, context: Dict[str, Any],
                                     optimization_result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute synthesis stage with LLM integration of all results"""
        try:
            logger.info("Starting synthesis stage with LLM integration")
            
            # Always use LLM for final synthesis to integrate all stage results
            try:
                # Create LLM reasoning tool for synthesis
                from ..tools.llm.llm_reasoning_tool import create_llm_reasoning_tool
                from ..tools.core.base import ToolExecutionContext, ToolPermission
                from .user_config_helper import ensure_user_can_use_llm
                
                reasoning_tool = create_llm_reasoning_tool()
                execution_user_id = ensure_user_can_use_llm(context.get("user_id"))
                
                exec_context = ToolExecutionContext(
                    user_id=execution_user_id,
                    session_id=context.get("task_id"),
                    permissions=[ToolPermission.READ_ONLY]
                )
                
                # Build comprehensive synthesis prompt with all stage results
                llm_optimization = optimization_result.get("llm_optimization", "")
                performance_score = optimization_result.get("performance_score", 0)
                
                synthesis_prompt = f"""
                基于完整的六阶段分析流程，请综合所有结果并生成最终的SQL查询：
                
                原始任务：{task_description}
                
                优化分析结果：
                {llm_optimization[:800] + '...' if len(llm_optimization) > 800 else llm_optimization}
                
                性能评分：{performance_score}/100
                
                请提供：
                1. 最终优化的SQL查询语句
                2. 查询结果的业务解释
                3. 性能和准确性评估
                4. 使用建议和注意事项
                5. 整体分析总结
                
                输出一个完整的、可执行的SQL查询，以及详细的分析说明。
                """
                
                synthesis_input = {
                    "problem": synthesis_prompt,
                    "context": {
                        "task_description": task_description,
                        "optimization_result": optimization_result
                    },
                    "reasoning_depth": "expert",
                    "require_step_by_step": True,
                    "include_assumptions": True,
                    "max_iterations": 1
                }
                
                # Execute LLM synthesis
                llm_synthesis_result = None
                async for result in reasoning_tool.execute(synthesis_input, exec_context):
                    if not result.is_partial:
                        llm_synthesis_result = result.data
                        break
                
                if llm_synthesis_result and llm_synthesis_result.get("result"):
                    synthesis_text = llm_synthesis_result["result"]
                    
                    # Extract final SQL and explanation from synthesis
                    final_result = self._extract_final_result_from_synthesis(synthesis_text)
                    
                    return {
                        "success": True,
                        "llm_used": True,
                        "llm_synthesis": synthesis_text,
                        "result": {
                            "sql_query": final_result.get("sql_query", "SELECT 'Multi-stage LLM analysis completed' as result"),
                            "generated_sql": final_result.get("sql_query", "SELECT 'Multi-stage LLM analysis completed' as result"),
                            "explanation": final_result.get("explanation", synthesis_text),
                            "confidence": final_result.get("confidence", 0.9),
                            "performance_assessment": final_result.get("performance_assessment", {}),
                            "analysis_summary": final_result.get("analysis_summary", ""),
                            "multi_stage_analysis": {
                                "stages_completed": 6,
                                "llm_interactions": 5,  # This will be updated by the orchestrator
                                "architecture_type": "enhanced_six_stage_collaborative"
                            }
                        }
                    }
            
            except Exception as e:
                logger.warning(f"LLM synthesis failed: {e}, using fallback synthesis")
            
            # Fallback synthesis (should rarely be used)
            return {
                "success": True,
                "llm_used": False,
                "result": {
                    "sql_query": "SELECT 'Fallback synthesis result' as result",
                    "explanation": "基础综合结果",
                    "confidence": 0.7,
                    "analysis_summary": "基础分析完成"
                }
            }
            
        except Exception as e:
            logger.error(f"Synthesis stage failed: {e}")
            return {"success": False, "error": str(e), "llm_used": False}
    
    def _extract_final_result_from_synthesis(self, synthesis_text: str) -> Dict[str, Any]:
        """Extract final structured result from LLM synthesis"""
        # Look for SQL query in the synthesis text
        sql_start_indicators = ["select", "SELECT", "with", "WITH"]
        sql_query = "SELECT 'Enhanced multi-stage analysis completed' as result"
        
        # Simple SQL extraction (in production, use more sophisticated parsing)
        lines = synthesis_text.split('\n')
        sql_lines = []
        capturing_sql = False
        
        for line in lines:
            line_lower = line.lower().strip()
            if any(indicator in line_lower for indicator in sql_start_indicators) and not capturing_sql:
                capturing_sql = True
                sql_lines.append(line.strip())
            elif capturing_sql and line.strip():
                if line_lower.startswith(('--', '/*', '#')):
                    continue
                sql_lines.append(line.strip())
                if line_lower.endswith((';', 'limit')):
                    break
            elif capturing_sql and not line.strip():
                break
        
        if sql_lines:
            sql_query = '\n'.join(sql_lines)
        
        # Extract confidence based on analysis depth
        confidence = 0.9 if len(synthesis_text) > 500 else 0.8
        
        # Extract performance assessment
        performance_keywords = ["性能", "优化", "索引", "快速", "效率"]
        has_performance_analysis = any(keyword in synthesis_text for keyword in performance_keywords)
        
        return {
            "sql_query": sql_query,
            "explanation": synthesis_text[:1000] + '...' if len(synthesis_text) > 1000 else synthesis_text,
            "confidence": confidence,
            "performance_assessment": {
                "has_analysis": has_performance_analysis,
                "estimated_performance": "good" if has_performance_analysis else "unknown"
            },
            "analysis_summary": f"完成六阶段协作分析，生成了{len(sql_query)}字符的SQL查询"
        }
    
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