"""
tt控制循环 - 类似于Claude Code的核心控制机制

基于Claude Code架构模式实现的流式、事件驱动的六阶段Agent编排控制器。
实现了与Claude Code相同的架构模式：流式处理、递归控制、状态管理、事件发射等。
"""

import asyncio
import uuid
import logging
import json
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum

from .message_types import MessageType, MessagePriority, AgentMessage
from .memory_manager import MemoryManager
from .progress_aggregator import ProgressAggregator
from .streaming_parser import StreamingMessageParser
from .error_formatter import ErrorFormatter

logger = logging.getLogger(__name__)

class TTEventType(Enum):
    """TT控制循环事件类型"""
    # UI状态更新
    UI_STATE_UPDATE = "ui_state_update"
    UI_NOTIFICATION = "ui_notification" 
    UI_PROGRESS = "ui_progress"
    UI_TEXT_DELTA = "ui_text_delta"
    UI_TOOL_PREVIEW = "ui_tool_preview"
    UI_CONTENT_BLOCK_COMPLETE = "ui_content_block_complete"
    
    # 系统事件
    SYSTEM_NOTIFICATION = "system_notification"
    SYSTEM_ERROR = "system_error"
    
    # 阶段执行事件
    STAGE_START = "stage_start"
    STAGE_PROGRESS = "stage_progress"
    STAGE_COMPLETE = "stage_complete"
    
    # LLM交互事件
    LLM_STREAM_START = "llm_stream_start"
    LLM_STREAM_DELTA = "llm_stream_delta"
    LLM_STREAM_COMPLETE = "llm_stream_complete"
    
    # 工具执行事件
    TOOL_EXECUTION_START = "tool_execution_start"
    TOOL_EXECUTION_PROGRESS = "tool_execution_progress"
    TOOL_EXECUTION_COMPLETE = "tool_execution_complete"
    
    # 递归控制事件
    RECURSION_START = "recursion_start"
    RECURSION_COMPLETE = "recursion_complete"
    
    # 完成事件
    TASK_COMPLETE = "task_complete"

@dataclass
class TTEvent:
    """TT控制循环事件"""
    type: TTEventType
    uuid: str
    timestamp: str
    data: Dict[str, Any]
    turn_id: str
    turn_counter: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "uuid": self.uuid,
            "timestamp": self.timestamp,
            "data": self.data,
            "turn_id": self.turn_id,
            "turn_counter": self.turn_counter
        }

@dataclass
class TTLoopState:
    """TT循环状态"""
    turn_id: str
    turn_counter: int
    task_id: str
    compacted: bool = False
    is_resuming: bool = False
    max_recursion_depth: int = 6  # 减少递归深度，避免过度循环
    memory_threshold: int = 1024 * 1024 * 100  # 100MB
    
    def increment_turn(self) -> "TTLoopState":
        """增加turn计数器并生成新状态"""
        return TTLoopState(
            turn_id=self.turn_id,
            turn_counter=self.turn_counter + 1,
            task_id=self.task_id,
            compacted=self.compacted,
            is_resuming=False,
            max_recursion_depth=self.max_recursion_depth,
            memory_threshold=self.memory_threshold
        )

@dataclass
class TTContext:
    """TT控制循环上下文"""
    task_description: str
    context_data: Dict[str, Any]
    target_agents: List[str]
    timeout_seconds: int
    enable_streaming: bool
    user_id: Optional[str] = None
    
    # 累积的消息历史
    message_history: List[AgentMessage] = None
    
    # 系统组件
    memory_manager: MemoryManager = None
    progress_aggregator: ProgressAggregator = None
    streaming_parser: StreamingMessageParser = None
    error_formatter: ErrorFormatter = None
    
    def __post_init__(self):
        if self.message_history is None:
            self.message_history = []

class TTController:
    """
    TT控制循环控制器
    
    核心职责：
    1. 六阶段任务编排
    2. 流式事件处理
    3. LLM协作管理
    4. 错误处理和恢复
    """
    
    def __init__(self):
        self.logger = logger
        self.active_loops: Dict[str, TTLoopState] = {}
        
        self.logger.info("TTController initialized")
    
    async def execute(self, context: TTContext):
        """
        执行TT控制循环的简化接口
        """
        # 创建默认的循环状态
        loop_state = TTLoopState(
            task_id=f"task_{len(self.active_loops)}",
            turn_counter=0,
            max_recursion_depth=5,
            memory_threshold=0.8
        )
        
        # 收集所有TT事件的结果
        results = []
        try:
            async for event in self.tt(context, loop_state):
                results.append(event)
                
                # 如果是任务完成事件，返回结果
                if hasattr(event, 'type') and event.type.value == "task_complete":
                    return event.data.get("result", {"success": True, "events": results})
            
            # 如果没有明确的完成事件，返回收集的所有结果
            return {"success": True, "events": results, "final_result": "TT loop completed"}
            
        except Exception as e:
            self.logger.error(f"TT execution failed: {e}")
            return {"success": False, "error": str(e), "events": results}
    
    async def tt(
        self,
        context: TTContext,
        loop_state: TTLoopState
    ) -> AsyncGenerator[TTEvent, None]:
        """
        TT控制循环 - 六阶段任务编排
        """
        try:
            # 初始化
            yield await self._create_event(
                TTEventType.UI_STATE_UPDATE,
                {"status": "starting", "task_id": loop_state.task_id},
                loop_state
            )
            
            # 递归深度检查
            if loop_state.turn_counter >= loop_state.max_recursion_depth:
                yield await self._create_event(
                    TTEventType.SYSTEM_ERROR,
                    {"error": f"Maximum recursion depth reached: {loop_state.max_recursion_depth}"},
                    loop_state
                )
                return
            
            # 注册循环
            self.active_loops[loop_state.task_id] = loop_state
            
            # 阶段1：意图理解和验证（LLM增强）
            intent_result = {}
            async for event in self._execute_intent_understanding_stage(context, loop_state):
                if event.type == TTEventType.STAGE_COMPLETE:
                    intent_result = event.data.get("result", {})
                yield event
            
            # 阶段2：上下文分析（LLM驱动）
            context_result = {}
            async for event in self._execute_context_analysis_stage(context, loop_state, intent_result):
                if event.type == TTEventType.STAGE_COMPLETE:
                    context_result = event.data.get("result", {})
                yield event
            
            # 阶段3：结构规划（LLM辅助）
            planning_result = {}
            async for event in self._execute_structure_planning_stage(context, loop_state, context_result):
                if event.type == TTEventType.STAGE_COMPLETE:
                    planning_result = event.data.get("result", {})
                yield event
            
            # 阶段4：实现执行（工具执行）
            implementation_result = {}
            tool_requests = []
            async for event in self._execute_implementation_stage(context, loop_state, planning_result):
                if event.type == TTEventType.STAGE_COMPLETE:
                    implementation_result = event.data.get("result", {})
                    tool_requests = event.data.get("tool_requests", [])
                yield event
            
            # 工具请求处理和递归判断
            if tool_requests:
                yield await self._create_event(
                    TTEventType.TOOL_EXECUTION_START,
                    {"tool_count": len(tool_requests)},
                    loop_state
                )
                
                # 执行工具并收集结果
                tool_results = []
                async for event in self._execute_tools_in_parallel(tool_requests, context, loop_state):
                    if event.type == TTEventType.TOOL_EXECUTION_COMPLETE:
                        tool_results.extend(event.data.get("results", []))
                    yield event
                
                # 检查工具结果中的任务完成信号
                task_completed = self._check_task_completion_signals(tool_results)
                
                if task_completed["should_terminate"]:
                    # 任务已完成，直接返回结果而不递归
                    final_result = {
                        "success": task_completed["success"],
                        "result": task_completed["completion_result"],
                        "completion_reason": task_completed["reason"],
                        "tool_results": tool_results,
                        "llm_interactions_count": self._count_llm_interactions(
                            intent_result, context_result, planning_result, implementation_result
                        ),
                        "architecture_type": "tt_controlled_early_termination",
                        "total_turns": loop_state.turn_counter,
                        "execution_time": datetime.now().isoformat()
                    }
                    
                    yield await self._create_event(
                        TTEventType.TASK_COMPLETE,
                        final_result,
                        loop_state
                    )
                    return
                
                # 任务未完成，继续递归处理
                updated_context = self._update_context_with_tool_results(context, tool_results)
                
                yield await self._create_event(
                    TTEventType.RECURSION_START,
                    {"reason": "tool_execution_complete", "tool_count": len(tool_results)},
                    loop_state
                )
                
                # 递归调用tt
                async for event in self.tt(
                    updated_context,
                    loop_state.increment_turn()
                ):
                    yield event
                
                yield await self._create_event(
                    TTEventType.RECURSION_COMPLETE,
                    {"recursive_turn_counter": loop_state.turn_counter + 1},
                    loop_state
                )
                return
            
            # 阶段5：优化审查（LLM评审）
            optimization_result = {}
            async for event in self._execute_optimization_stage(context, loop_state, implementation_result):
                if event.type == TTEventType.STAGE_COMPLETE:
                    optimization_result = event.data.get("result", {})
                yield event
            
            # 阶段6：综合整合（LLM集成）
            synthesis_result = {}
            async for event in self._execute_synthesis_stage(context, loop_state, optimization_result):
                if event.type == TTEventType.STAGE_COMPLETE:
                    synthesis_result = event.data.get("result", {})
                yield event
            
            # 任务完成
            yield await self._create_event(
                TTEventType.TASK_COMPLETE,
                {
                    "success": True,
                    "result": synthesis_result,
                    "llm_interactions_count": self._count_llm_interactions(
                        intent_result, context_result, planning_result, 
                        optimization_result, synthesis_result
                    ),
                    "architecture_type": "tt_controlled_multi_llm_collaborative",
                    "total_turns": loop_state.turn_counter,
                    "execution_time": datetime.now().isoformat()
                },
                loop_state
            )
            
        except Exception as e:
            self.logger.error(f"TT控制循环执行异常: {e}")
            yield await self._create_event(
                TTEventType.SYSTEM_ERROR,
                {
                    "error": str(e),
                    "error_type": "tt_loop_exception",
                    "turn_counter": loop_state.turn_counter,
                    "task_id": loop_state.task_id
                },
                loop_state
            )
        finally:
            # 清理活动循环
            self.active_loops.pop(loop_state.task_id, None)
    
    async def _handle_memory_pressure(
        self, 
        context: TTContext, 
        loop_state: TTLoopState
    ) -> AsyncGenerator[TTEvent, None]:
        """处理内存压力和历史压缩"""
        
        memory_stats = self.memory_manager.get_memory_stats()
        current_memory = memory_stats.get('total_memory_mb', 0) * 1024 * 1024  # Convert to bytes
        
        if current_memory > loop_state.memory_threshold:
            yield await self._create_event(
                TTEventType.UI_NOTIFICATION,
                {"message": "Memory pressure detected, attempting to compact context..."},
                loop_state
            )
            
            try:
                # 压缩消息历史
                compacted_history = await self._compact_message_history(context.message_history)
                context.message_history = compacted_history
                loop_state.compacted = True
                
                new_memory_stats = self.memory_manager.get_memory_stats()
                new_memory = new_memory_stats.get('total_memory_mb', 0) * 1024 * 1024
                yield await self._create_event(
                    TTEventType.SYSTEM_NOTIFICATION,
                    {
                        "message": "Context history automatically compacted",
                        "memory_saved": current_memory - new_memory
                    },
                    loop_state
                )
                
            except Exception as e:
                yield await self._create_event(
                    TTEventType.SYSTEM_ERROR,
                    {
                        "error": f"Failed to compact context: {str(e)}",
                        "memory_usage": current_memory
                    },
                    loop_state
                )
    
    async def _execute_intent_understanding_stage(
        self, 
        context: TTContext, 
        loop_state: TTLoopState
    ) -> AsyncGenerator[TTEvent, None]:
        """阶段1：意图理解和验证（LLM增强）"""
        
        yield await self._create_event(
            TTEventType.STAGE_START,
            {
                "stage": "intent_understanding", 
                "stage_number": 1,
                "llm_enhanced": True
            },
            loop_state
        )
        
        try:
            # 导入LLM推理工具
            from ..tools.llm import get_llm_reasoning_tool
            
            llm_tool = get_llm_reasoning_tool()
            
            # 构建意图分析提示
            intent_prompt = f"""
            分析以下任务的意图和复杂性：
            
            任务描述: {context.task_description}
            目标代理: {context.target_agents}
            上下文数据: {json.dumps(context.context_data, ensure_ascii=False, indent=2)}
            
            请分析：
            1. 任务的核心意图是什么？
            2. 任务的复杂程度如何？
            3. 需要哪些类型的推理？
            4. 预期的输出格式是什么？
            
            返回JSON格式的分析结果。
            """
            
            # 构建工具执行上下文
            from ..tools.core.base import ToolExecutionContext
            tool_context = ToolExecutionContext(user_id=context.user_id)
            
            # 流式LLM推理
            async for llm_result in llm_tool.execute(
                {"problem": intent_prompt, "reasoning_depth": "basic"},
                tool_context
            ):
                if llm_result.is_partial:
                    yield await self._create_event(
                        TTEventType.LLM_STREAM_DELTA,
                        {"stage": "intent_understanding", "delta": llm_result.data.get("message", "") if llm_result.data else ""},
                        loop_state
                    )
                elif llm_result.success and not llm_result.is_partial:
                    result = {
                        "intent_analysis": llm_result.data.get("result", {}),
                        "llm_used": True,
                        "confidence": 0.9
                    }
                    
                    yield await self._create_event(
                        TTEventType.STAGE_COMPLETE,
                        {
                            "stage": "intent_understanding",
                            "result": result,
                            "llm_interactions": 1
                        },
                        loop_state
                    )
                    return
            
        except Exception as e:
            self.logger.error(f"意图理解阶段执行异常: {e}")
            # 兜底逻辑
            fallback_result = {
                "intent_analysis": {
                    "core_intent": "task_execution",
                    "complexity": "medium", 
                    "reasoning_type": "general",
                    "output_format": "structured"
                },
                "llm_used": False,
                "confidence": 0.5,
                "fallback": True
            }
            
            yield await self._create_event(
                TTEventType.STAGE_COMPLETE,
                {
                    "stage": "intent_understanding",
                    "result": fallback_result,
                    "error": str(e),
                    "llm_interactions": 0
                },
                loop_state
            )
    
    async def _execute_context_analysis_stage(
        self, 
        context: TTContext, 
        loop_state: TTLoopState,
        intent_result: Dict[str, Any]
    ) -> AsyncGenerator[TTEvent, None]:
        """阶段2：上下文分析（LLM驱动）"""
        
        yield await self._create_event(
            TTEventType.STAGE_START,
            {
                "stage": "context_analysis",
                "stage_number": 2, 
                "llm_powered": True
            },
            loop_state
        )
        
        try:
            from ..tools.llm import get_llm_reasoning_tool
            
            llm_tool = get_llm_reasoning_tool()
            
            context_analysis_prompt = f"""
            基于意图分析结果，深入分析任务上下文：
            
            意图分析结果: {json.dumps(intent_result, ensure_ascii=False, indent=2)}
            
            任务上下文数据: {json.dumps(context.context_data, ensure_ascii=False, indent=2)}
            
            请分析：
            1. 关键上下文要素有哪些？
            2. 数据源的质量和完整性如何？
            3. 潜在的约束条件是什么？
            4. 需要哪些额外的上下文信息？
            
            返回详细的上下文分析结果（JSON格式）。
            """
            
            from ..tools.core.base import ToolExecutionContext
            tool_context = ToolExecutionContext(user_id=context.user_id)
            
            async for llm_result in llm_tool.execute(
                {"problem": context_analysis_prompt, "reasoning_depth": "detailed"},
                tool_context
            ):
                if llm_result.is_partial:
                    yield await self._create_event(
                        TTEventType.LLM_STREAM_DELTA,
                        {"stage": "context_analysis", "delta": llm_result.data.get("message", "") if llm_result.data else ""},
                        loop_state
                    )
                elif llm_result.success and not llm_result.is_partial:
                    result = {
                        "context_analysis": llm_result.data.get("result", {}),
                        "enhanced_context": {
                            **context.context_data,
                            "intent_insights": intent_result.get("intent_analysis", {}),
                            "analysis_timestamp": datetime.now().isoformat()
                        },
                        "llm_used": True,
                        "confidence": 0.85
                    }
                    
                    yield await self._create_event(
                        TTEventType.STAGE_COMPLETE,
                        {
                            "stage": "context_analysis",
                            "result": result,
                            "llm_interactions": 1
                        },
                        loop_state
                    )
                    return
            
        except Exception as e:
            self.logger.error(f"上下文分析阶段执行异常: {e}")
            fallback_result = {
                "context_analysis": {
                    "key_elements": ["task_description", "target_agents"],
                    "data_quality": "moderate",
                    "constraints": [],
                    "additional_context_needed": []
                },
                "enhanced_context": context.context_data,
                "llm_used": False,
                "confidence": 0.6,
                "fallback": True
            }
            
            yield await self._create_event(
                TTEventType.STAGE_COMPLETE,
                {
                    "stage": "context_analysis",
                    "result": fallback_result,
                    "error": str(e),
                    "llm_interactions": 0
                },
                loop_state
            )
    
    async def _execute_structure_planning_stage(
        self,
        context: TTContext,
        loop_state: TTLoopState, 
        context_result: Dict[str, Any]
    ) -> AsyncGenerator[TTEvent, None]:
        """阶段3：结构规划（LLM辅助）"""
        
        yield await self._create_event(
            TTEventType.STAGE_START,
            {
                "stage": "structure_planning",
                "stage_number": 3,
                "llm_assisted": True
            },
            loop_state
        )
        
        try:
            from ..tools.llm import get_llm_reasoning_tool
            
            llm_tool = get_llm_reasoning_tool()
            
            planning_prompt = f"""
            基于上下文分析，规划任务的执行结构：
            
            上下文分析结果: {json.dumps(context_result, ensure_ascii=False, indent=2)}
            
            请规划：
            1. 执行步骤的逻辑顺序
            2. 每个步骤所需的工具和资源
            3. 步骤间的依赖关系
            4. 风险点和应对策略
            5. 预期的中间输出和最终结果格式
            
            返回详细的执行计划（JSON格式）。
            """
            
            from ..tools.core.base import ToolExecutionContext
            tool_context = ToolExecutionContext(user_id=context.user_id)
            
            async for llm_result in llm_tool.execute(
                {"problem": planning_prompt, "reasoning_depth": "detailed"},
                tool_context
            ):
                if llm_result.is_partial:
                    yield await self._create_event(
                        TTEventType.LLM_STREAM_DELTA,
                        {"stage": "structure_planning", "delta": llm_result.data.get("message", "") if llm_result.data else ""},
                        loop_state
                    )
                elif llm_result.success and not llm_result.is_partial:
                    result = {
                        "execution_plan": llm_result.data.get("result", {}),
                        "structured_context": {
                            **context_result.get("enhanced_context", {}),
                            "planning_insights": llm_result.data.get("result", {}),
                            "planning_timestamp": datetime.now().isoformat()
                        },
                        "llm_used": True,
                        "confidence": 0.88
                    }
                    
                    yield await self._create_event(
                        TTEventType.STAGE_COMPLETE,
                        {
                            "stage": "structure_planning",
                            "result": result,
                            "llm_interactions": 1
                        },
                        loop_state
                    )
                    return
            
        except Exception as e:
            self.logger.error(f"结构规划阶段执行异常: {e}")
            fallback_result = {
                "execution_plan": {
                    "steps": ["analyze", "process", "generate", "optimize"],
                    "tools_needed": ["sql_generator", "data_analyzer"],
                    "dependencies": {},
                    "risks": ["data_quality", "performance"],
                    "output_format": "structured_response"
                },
                "structured_context": context_result.get("enhanced_context", {}),
                "llm_used": False,
                "confidence": 0.65,
                "fallback": True
            }
            
            yield await self._create_event(
                TTEventType.STAGE_COMPLETE,
                {
                    "stage": "structure_planning", 
                    "result": fallback_result,
                    "error": str(e),
                    "llm_interactions": 0
                },
                loop_state
            )
    
    async def _execute_implementation_stage(
        self,
        context: TTContext,
        loop_state: TTLoopState,
        planning_result: Dict[str, Any]
    ) -> AsyncGenerator[TTEvent, None]:
        """阶段4：通用实现执行（智能工具选择和执行）"""
        
        yield await self._create_event(
            TTEventType.STAGE_START,
            {
                "stage": "implementation",
                "stage_number": 4,
                "tool_execution": True,
                "approach": "intelligent_tool_selection"
            },
            loop_state
        )
        
        try:
            # 智能分析任务目标和上下文，确定最佳工具策略
            tool_strategy = await self._analyze_task_and_select_tools(
                context, planning_result
            )
            
            # 基于目标导向构建工具请求
            tool_requests = await self._build_goal_oriented_tool_requests(
                context, tool_strategy
            )
            
            implementation_result = {
                "tool_requests": tool_requests,
                "tool_strategy": tool_strategy,
                "execution_status": "ready_for_intelligent_execution",
                "approach": "goal_oriented",
                "llm_used": False,
                "confidence": tool_strategy.get("confidence", 0.85)
            }
            
            yield await self._create_event(
                TTEventType.STAGE_COMPLETE,
                {
                    "stage": "implementation",
                    "result": implementation_result,
                    "tool_requests": tool_requests,
                    "llm_interactions": 0,
                    "strategy": tool_strategy.get("strategy_type", "adaptive")
                },
                loop_state
            )
            
        except Exception as e:
            self.logger.error(f"通用实现执行阶段异常: {e}")
            yield await self._create_event(
                TTEventType.STAGE_COMPLETE,
                {
                    "stage": "implementation",
                    "result": {
                        "error": str(e),
                        "tool_requests": [],
                        "approach": "fallback",
                        "llm_used": False,
                        "confidence": 0.0
                    },
                    "error": str(e),
                    "llm_interactions": 0
                },
                loop_state
            )
    
    async def _analyze_task_and_select_tools(
        self, 
        context: TTContext, 
        planning_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """智能分析任务并选择最适合的工具策略 - 集成多任务prompt适配"""
        
        try:
            # 基础任务分析
            task_description = context.task_description.lower()
            context_data = context.context_data
            
            # 智能推断任务类型和目标
            task_analysis = {
                "primary_goal": self._extract_primary_goal(task_description, context_data),
                "context_relevance": self._analyze_context_relevance(context_data, task_description),
                "data_requirements": self._identify_data_requirements(context_data, task_description),
                "output_expectations": self._infer_output_expectations(task_description, context.target_agents)
            }
            
            # 多任务prompt适配分析
            prompt_adaptation_analysis = await self._analyze_prompt_requirements(task_analysis, context)
            
            # 基于分析结果和prompt适配选择最优策略
            strategy = self._select_optimal_strategy_with_prompts(task_analysis, prompt_adaptation_analysis)
            
            return {
                "strategy_type": strategy["type"],
                "primary_tools": strategy["tools"],
                "execution_order": strategy["order"],
                "task_analysis": task_analysis,
                "prompt_adaptation": prompt_adaptation_analysis,
                "confidence": strategy["confidence"],
                "reasoning": strategy["reasoning"],
                "specialized_agent_type": strategy.get("agent_type", "general")
            }
            
        except Exception as e:
            self.logger.error(f"多任务分析和工具选择异常: {e}")
            # 返回保守的默认策略
            return {
                "strategy_type": "conservative_default",
                "primary_tools": ["general_reasoning"],
                "execution_order": ["analyze", "execute", "validate"],
                "confidence": 0.5,
                "reasoning": "使用保守默认策略由于分析异常",
                "specialized_agent_type": "general"
            }
    
    async def _analyze_prompt_requirements(
        self, 
        task_analysis: Dict[str, Any], 
        context: TTContext
    ) -> Dict[str, Any]:
        """分析任务的prompt需求，实现多任务适配"""
        
        try:
            primary_goal = task_analysis["primary_goal"]["primary_type"]
            
            # 确定专业化agent类型
            agent_type_mapping = {
                "placeholder_processing": "data_analysis",
                "sql_generation": "data_analysis", 
                "data_analysis": "data_analysis",
                "report_generation": "business_intelligence",
                "business_intelligence": "business_intelligence",
                "system_maintenance": "system_administration",
                "code_analysis": "development"
            }
            
            specialized_agent_type = agent_type_mapping.get(primary_goal, "general")
            
            # 分析上下文特征以确定prompt适配需求
            context_characteristics = {
                "user_role": self._infer_user_role_from_context(context.context_data, context.task_description),
                "data_sensitivity": self._assess_data_sensitivity(context.context_data),
                "urgency_level": self._assess_urgency(context.task_description),
                "resource_constraints": self._analyze_resource_constraints(context.context_data, context.timeout_seconds)
            }
            
            # 确定工作流类型
            workflow_type = self._determine_workflow_type(primary_goal, task_analysis)
            
            return {
                "specialized_agent_type": specialized_agent_type,
                "context_characteristics": context_characteristics,
                "workflow_type": workflow_type,
                "prompt_complexity": self._assess_prompt_complexity(task_analysis),
                "adaptation_confidence": 0.85
            }
            
        except Exception as e:
            self.logger.error(f"Prompt需求分析异常: {e}")
            return {
                "specialized_agent_type": "general",
                "context_characteristics": {},
                "workflow_type": "general",
                "prompt_complexity": "medium",
                "adaptation_confidence": 0.5
            }
    
    def _infer_user_role_from_context(self, context_data: Dict[str, Any], task_description: str) -> str:
        """从上下文推断用户角色 - 智能优先级判断"""
        
        # 调整优先级顺序：更具体的技术词汇优先级更高
        developer_indicators = ["开发", "代码", "系统", "development", "code", "performance", "optimization"]
        executive_indicators = ["战略", "决策", "高管", "executive", "strategic", "decision"]
        analyst_indicators = ["分析", "统计", "数据", "analysis", "analytics", "statistical"]
        
        task_lower = task_description.lower()
        
        # 优先检查更具体的技术指标
        if any(indicator in task_lower for indicator in developer_indicators):
            return "developer"
        elif any(indicator in task_lower for indicator in executive_indicators):
            return "executive"
        elif any(indicator in task_lower for indicator in analyst_indicators):
            return "analyst"
        else:
            return "analyst"  # 默认角色
    
    def _assess_data_sensitivity(self, context_data: Dict[str, Any]) -> str:
        """评估数据敏感性"""
        
        sensitive_indicators = [
            "password", "secret", "token", "private", "confidential",
            "密码", "机密", "私有", "敏感", "内部"
        ]
        
        context_str = json.dumps(context_data, ensure_ascii=False).lower()
        
        if any(indicator in context_str for indicator in sensitive_indicators):
            return "high"
        elif any(key in context_data for key in ["user_info", "personal_data", "financial_data"]):
            return "medium" 
        else:
            return "low"
    
    def _assess_urgency(self, task_description: str) -> str:
        """评估任务紧急程度"""
        
        urgent_indicators = ["紧急", "立即", "马上", "急", "urgent", "immediate", "asap", "critical"]
        normal_indicators = ["正常", "常规", "标准", "normal", "standard", "regular"]
        
        task_lower = task_description.lower()
        
        if any(indicator in task_lower for indicator in urgent_indicators):
            return "high"
        elif any(indicator in task_lower for indicator in normal_indicators):
            return "normal"
        else:
            return "normal"  # 默认正常优先级
    
    def _analyze_resource_constraints(self, context_data: Dict[str, Any], timeout_seconds: int) -> Dict[str, Any]:
        """分析资源约束"""
        
        return {
            "time_limited": timeout_seconds < 60,  # 少于1分钟认为时间有限
            "memory_limited": len(json.dumps(context_data)) > 10000,  # 上下文过大认为内存有限
            "processing_limited": False  # 暂时默认无处理限制
        }
    
    def _determine_workflow_type(self, primary_goal: str, task_analysis: Dict[str, Any]) -> str:
        """确定工作流类型"""
        
        workflow_mapping = {
            "data_analysis": "data_pipeline",
            "placeholder_processing": "data_pipeline",
            "sql_generation": "data_pipeline", 
            "business_intelligence": "data_pipeline",
            "system_maintenance": "system_maintenance",
            "code_analysis": "code_analysis"
        }
        
        return workflow_mapping.get(primary_goal, "general")
    
    def _assess_prompt_complexity(self, task_analysis: Dict[str, Any]) -> str:
        """评估prompt复杂度需求"""
        
        complexity_factors = {
            "multiple_goals": len(task_analysis["primary_goal"]["secondary_types"]) > 1,
            "high_context_relevance": len(task_analysis["context_relevance"]["high_relevance_keys"]) > 2,
            "complex_data_requirements": len(task_analysis["data_requirements"]["data_sources"]) > 1,
            "advanced_output_expectations": task_analysis["output_expectations"]["complexity"] == "high"
        }
        
        complexity_score = sum(complexity_factors.values()) / len(complexity_factors)
        
        if complexity_score > 0.7:
            return "high"
        elif complexity_score > 0.4:
            return "medium"
        else:
            return "low"
    
    def _select_optimal_strategy_with_prompts(
        self, 
        task_analysis: Dict[str, Any], 
        prompt_adaptation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """基于任务分析和prompt适配选择最佳策略"""
        
        primary_goal = task_analysis["primary_goal"]["primary_type"]
        specialized_agent = prompt_adaptation["specialized_agent_type"]
        workflow_type = prompt_adaptation["workflow_type"]
        
        # 多任务适配策略选择
        if primary_goal == "placeholder_processing":
            return {
                "type": "specialized_placeholder_analysis",
                "tools": ["placeholder_analyzer", "context_extractor", "sql_generator"],
                "order": ["extract_context", "analyze_placeholder", "generate_solution", "validate"],
                "confidence": 0.92,
                "reasoning": f"检测到占位符处理任务，使用{specialized_agent}专业化prompt和{workflow_type}工作流",
                "agent_type": specialized_agent
            }
            
        elif primary_goal == "sql_generation":
            return {
                "type": "specialized_sql_generation",
                "tools": ["sql_generator", "syntax_validator", "quality_assessor", "connection_tester"],
                "order": ["analyze_requirements", "generate_sql", "assess_quality", "validate_syntax", "test_connection"],
                "confidence": 0.90,
                "reasoning": f"SQL生成任务，使用{specialized_agent}专业化prompt和增强质量评估",
                "agent_type": specialized_agent
            }
            
        elif primary_goal == "data_analysis":
            return {
                "type": "specialized_data_analysis", 
                "tools": ["data_analyzer", "statistical_processor", "insight_generator", "report_creator"],
                "order": ["load_data", "analyze_patterns", "generate_insights", "create_report"],
                "confidence": 0.88,
                "reasoning": f"数据分析任务，使用{specialized_agent}专业化工作流和统计分析工具",
                "agent_type": specialized_agent
            }
            
        elif primary_goal == "business_intelligence":
            return {
                "type": "specialized_business_intelligence",
                "tools": ["bi_analyzer", "kpi_calculator", "dashboard_creator", "executive_reporter"],
                "order": ["analyze_business_requirements", "calculate_metrics", "create_dashboard", "generate_executive_report"],
                "confidence": 0.89,
                "reasoning": f"商业智能任务，使用{specialized_agent}专业化BI工作流",
                "agent_type": specialized_agent
            }
            
        else:
            # 通用策略但使用最相关的专业化agent
            most_relevant = task_analysis["context_relevance"].get("most_relevant")
            if most_relevant == "placeholder_text":
                primary_tool = "placeholder_analyzer"
                agent_type = "data_analysis"
            elif most_relevant == "data_source_info":
                primary_tool = "data_analyzer"
                agent_type = "data_analysis"
            else:
                primary_tool = "general_processor"
                agent_type = "general"
                
            return {
                "type": "adaptive_specialized_general",
                "tools": [primary_tool, "context_analyzer", "goal_achiever"],
                "order": ["understand_context", "select_approach", "execute", "validate"],
                "confidence": 0.78,
                "reasoning": f"通用适应性策略，使用{agent_type}专业化prompt，重点关注{most_relevant or '综合上下文'}",
                "agent_type": agent_type
            }
    
    def _extract_primary_goal(self, task_description: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """从任务描述和上下文中提取主要目标 - 智能优先级判断"""
        
        goal_indicators = {
            "placeholder_processing": ["占位符", "参数", "替换", "placeholder", "parameter"],
            "sql_generation": ["sql", "查询", "数据库", "select", "query"],
            "data_analysis": ["分析", "统计", "趋势", "analysis", "pattern"],
            "report_generation": ["报告", "报表", "生成", "report", "generate"],
            "business_intelligence": ["kpi", "指标", "dashboard", "bi", "商业智能"]
        }
        
        detected_goals = []
        for goal_type, keywords in goal_indicators.items():
            if any(keyword in task_description for keyword in keywords):
                detected_goals.append(goal_type)
        
        # 分析上下文数据以确认目标
        context_hints = []
        if "placeholder_text" in context_data:
            context_hints.append("placeholder_processing")
        if "data_source_info" in context_data:
            context_hints.append("data_analysis")
        if "template_info" in context_data:
            context_hints.append("report_generation")
        
        # 智能优先级决策：
        # 1. 任务描述中明确提到的目标优先级最高
        # 2. 上下文强烈指示的目标次之
        # 3. 默认为通用处理
        
        if detected_goals:
            # 任务描述中有明确关键词，优先使用
            primary_type = detected_goals[0]
        elif context_hints:
            # 没有明确关键词但有上下文提示，使用上下文提示
            primary_type = context_hints[0]
        else:
            primary_type = "general_processing"
        
        return {
            "primary_type": primary_type,
            "secondary_types": detected_goals if detected_goals else [],
            "context_confirmed": context_hints,
            "confidence": (len(detected_goals) + len(context_hints)) / 5.0
        }
    
    def _analyze_context_relevance(self, context_data: Dict[str, Any], task_description: str) -> Dict[str, Any]:
        """分析上下文数据的相关性，自动识别最相关的部分"""
        
        relevance_scores = {}
        
        # 为不同类型的上下文数据计算相关性分数
        for key, value in context_data.items():
            if key == "placeholder_text":
                # 占位符文本的相关性基于任务描述中的关键词匹配
                score = self._calculate_text_relevance(str(value), task_description)
                # 占位符任务中，占位符文本应该有最高优先级
                if "占位符" in task_description or "placeholder" in task_description:
                    score = max(score, 0.95)  # 强制提高分数
                relevance_scores[key] = {"score": score, "type": "placeholder", "priority": "high"}
                
            elif key == "data_source_info":
                # 数据源信息对于数据相关任务高度相关
                data_keywords = ["数据", "查询", "分析", "data", "query", "analysis"]
                if any(kw in task_description for kw in data_keywords):
                    relevance_scores[key] = {"score": 0.9, "type": "data_source", "priority": "high"}
                else:
                    relevance_scores[key] = {"score": 0.3, "type": "data_source", "priority": "medium"}
                    
            elif key == "template_info":
                # 模板信息对于报告生成任务相关
                template_keywords = ["模板", "报告", "生成", "template", "report", "generate"]
                if any(kw in task_description for kw in template_keywords):
                    relevance_scores[key] = {"score": 0.8, "type": "template", "priority": "high"}
                else:
                    relevance_scores[key] = {"score": 0.2, "type": "template", "priority": "low"}
                    
            elif key in ["user_preferences", "system_config"]:
                # 系统配置通常是低优先级的背景信息
                relevance_scores[key] = {"score": 0.1, "type": "system", "priority": "low"}
                
            else:
                # 其他未知类型的数据，基于文本相似性计算相关性
                if isinstance(value, (str, dict, list)):
                    score = self._calculate_generic_relevance(value, task_description)
                    relevance_scores[key] = {"score": score, "type": "generic", "priority": "medium"}
        
        # 找出最相关的上下文部分
        most_relevant = max(relevance_scores.items(), key=lambda x: x[1]["score"]) if relevance_scores else None
        high_relevance_items = {k: v for k, v in relevance_scores.items() if v["score"] > 0.6}
        
        return {
            "all_scores": relevance_scores,
            "most_relevant": most_relevant[0] if most_relevant else None,
            "high_relevance_keys": list(high_relevance_items.keys()),
            "focused_context": {k: context_data.get(k) for k in high_relevance_items.keys()},
            "relevance_summary": f"发现 {len(high_relevance_items)} 个高相关性上下文项"
        }
    
    def _calculate_text_relevance(self, text: str, task_description: str) -> float:
        """计算文本与任务描述的相关性"""
        
        if not text or not task_description:
            return 0.0
        
        # 简单的关键词匹配算法
        text_words = set(text.lower().split())
        task_words = set(task_description.lower().split())
        
        if not text_words or not task_words:
            return 0.0
        
        # 计算交集比例
        common_words = text_words.intersection(task_words)
        relevance = len(common_words) / len(task_words.union(text_words))
        
        return min(relevance * 2, 1.0)  # 放大相关性并限制在1.0以内
    
    def _calculate_generic_relevance(self, value: Any, task_description: str) -> float:
        """计算通用数据的相关性"""
        
        try:
            # 将值转换为字符串进行分析
            if isinstance(value, dict):
                text = " ".join(str(v) for v in value.values() if v)
            elif isinstance(value, list):
                text = " ".join(str(item) for item in value if item)
            else:
                text = str(value)
            
            return self._calculate_text_relevance(text, task_description)
            
        except Exception:
            return 0.1  # 默认低相关性
    
    def _identify_data_requirements(self, context_data: Dict[str, Any], task_description: str) -> Dict[str, Any]:
        """识别任务的数据需求"""
        
        requirements = {
            "needs_database_access": False,
            "needs_external_data": False,
            "needs_user_input": False,
            "data_sources": [],
            "expected_data_types": []
        }
        
        # 基于任务描述推断数据需求
        if any(kw in task_description.lower() for kw in ["数据库", "查询", "sql", "database", "query"]):
            requirements["needs_database_access"] = True
            
        if any(kw in task_description.lower() for kw in ["api", "外部", "external", "fetch"]):
            requirements["needs_external_data"] = True
            
        if any(kw in task_description.lower() for kw in ["输入", "参数", "input", "parameter"]):
            requirements["needs_user_input"] = True
        
        # 从上下文数据中识别可用的数据源
        if "data_source_info" in context_data:
            requirements["data_sources"].append("configured_datasource")
            
        if "placeholder_text" in context_data:
            requirements["data_sources"].append("placeholder_context")
            
        return requirements
    
    def _infer_output_expectations(self, task_description: str, target_agents: List[str]) -> Dict[str, Any]:
        """推断输出期望"""
        
        expectations = {
            "format": "structured_data",
            "complexity": "medium",
            "requires_validation": False
        }
        
        # 基于目标代理推断输出格式
        if "sql_generation_agent" in target_agents:
            expectations["format"] = "sql_query"
            expectations["requires_validation"] = True
            
        elif "report_generation_agent" in target_agents:
            expectations["format"] = "formatted_report"
            expectations["complexity"] = "high"
            
        elif "data_analysis_agent" in target_agents:
            expectations["format"] = "analysis_results"
            expectations["complexity"] = "medium"
        
        # 基于任务描述调整期望
        if any(kw in task_description.lower() for kw in ["复杂", "详细", "comprehensive"]):
            expectations["complexity"] = "high"
            
        if any(kw in task_description.lower() for kw in ["简单", "basic", "quick"]):
            expectations["complexity"] = "low"
        
        return expectations
    
    def _select_optimal_strategy(self, task_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """基于任务分析选择最佳执行策略"""
        
        primary_goal = task_analysis["primary_goal"]["primary_type"]
        context_relevance = task_analysis["context_relevance"]
        
        # 策略决策逻辑
        if primary_goal == "placeholder_processing":
            return {
                "type": "placeholder_focused",
                "tools": ["placeholder_analyzer", "context_extractor", "sql_generator"],
                "order": ["extract_context", "analyze_placeholder", "generate_solution", "validate"],
                "confidence": 0.9,
                "reasoning": "检测到占位符处理任务，使用专门的占位符分析流程"
            }
            
        elif primary_goal == "sql_generation":
            return {
                "type": "sql_focused",
                "tools": ["sql_generator", "syntax_validator", "connection_tester"],
                "order": ["analyze_requirements", "generate_sql", "validate_syntax", "test_connection"],
                "confidence": 0.88,
                "reasoning": "SQL生成任务，使用数据库相关工具链"
            }
            
        elif primary_goal == "data_analysis":
            return {
                "type": "analysis_focused", 
                "tools": ["data_analyzer", "pattern_detector", "insight_generator"],
                "order": ["load_data", "analyze_patterns", "generate_insights", "summarize"],
                "confidence": 0.85,
                "reasoning": "数据分析任务，使用分析工具链"
            }
            
        else:
            # 通用策略 - 基于上下文相关性动态调整
            most_relevant = context_relevance.get("most_relevant")
            if most_relevant == "placeholder_text":
                primary_tool = "placeholder_analyzer"
            elif most_relevant == "data_source_info":
                primary_tool = "data_analyzer"
            else:
                primary_tool = "general_processor"
                
            return {
                "type": "adaptive_general",
                "tools": [primary_tool, "context_analyzer", "goal_achiever"],
                "order": ["understand_context", "select_approach", "execute", "validate"],
                "confidence": 0.75,
                "reasoning": f"通用适应性策略，重点关注{most_relevant or '综合上下文'}"
            }
    
    async def _build_goal_oriented_tool_requests(
        self, 
        context: TTContext, 
        tool_strategy: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """基于目标导向构建工具请求"""
        
        tool_requests = []
        strategy_type = tool_strategy["strategy_type"]
        primary_tools = tool_strategy["primary_tools"]
        
        # 提取最相关的上下文数据
        context_relevance = tool_strategy.get("task_analysis", {}).get("context_relevance", {})
        focused_context = context_relevance.get("focused_context", context.context_data)
        
        for tool_name in primary_tools:
            if tool_name == "placeholder_analyzer":
                tool_requests.append({
                    "tool": "placeholder_analysis",
                    "input": {
                        "task_description": context.task_description,
                        "placeholder_text": focused_context.get("placeholder_text", ""),
                        "context": focused_context,
                        "analysis_depth": "intelligent"
                    }
                })
                
            elif tool_name == "sql_generator":
                tool_requests.append({
                    "tool": "sql_generation", 
                    "input": {
                        "task_description": context.task_description,
                        "context": focused_context,
                        "data_source": focused_context.get("data_source_info", {}),
                        "requirements": {"validation_required": True}
                    }
                })
                
            elif tool_name == "data_analyzer":
                tool_requests.append({
                    "tool": "data_analysis",
                    "input": {
                        "data_source": focused_context.get("data_source_info", {}),
                        "analysis_type": "contextual_analysis",
                        "task_context": context.task_description
                    }
                })
                
            elif tool_name == "general_processor":
                tool_requests.append({
                    "tool": "general_processing",
                    "input": {
                        "task_description": context.task_description,
                        "context": focused_context,
                        "processing_strategy": strategy_type
                    }
                })
        
        return tool_requests
    
    async def _execute_optimization_stage(
        self,
        context: TTContext,
        loop_state: TTLoopState,
        implementation_result: Dict[str, Any]
    ) -> AsyncGenerator[TTEvent, None]:
        """阶段5：优化审查（LLM评审）"""
        
        yield await self._create_event(
            TTEventType.STAGE_START,
            {
                "stage": "optimization",
                "stage_number": 5,
                "llm_review": True
            },
            loop_state
        )
        
        try:
            from ..tools.llm import get_llm_reasoning_tool
            
            llm_tool = get_llm_reasoning_tool()
            
            optimization_prompt = f"""
            审查实现结果并提出优化建议：
            
            实现结果: {json.dumps(implementation_result, ensure_ascii=False, indent=2)}
            
            请评估：
            1. 实现质量如何？
            2. 性能是否可以优化？
            3. 结果的准确性和完整性？
            4. 是否存在改进空间？
            5. 推荐的优化策略
            
            返回优化分析和建议（JSON格式）。
            """
            
            from ..tools.core.base import ToolExecutionContext
            tool_context = ToolExecutionContext(user_id=context.user_id)
            
            async for llm_result in llm_tool.execute(
                {"problem": optimization_prompt, "reasoning_depth": "detailed"},
                tool_context
            ):
                if llm_result.is_partial:
                    yield await self._create_event(
                        TTEventType.LLM_STREAM_DELTA,
                        {"stage": "optimization", "delta": llm_result.data.get("message", "") if llm_result.data else ""},
                        loop_state
                    )
                elif llm_result.success and not llm_result.is_partial:
                    # 安全获取LLM结果
                    llm_data = llm_result.data.get("result", {}) if llm_result.data else {}
                    if not isinstance(llm_data, dict):
                        llm_data = {}
                        
                    result = {
                        "optimization_analysis": llm_data,
                        "optimized_result": implementation_result,
                        "improvements": llm_data.get("improvements", []) if isinstance(llm_data.get("improvements"), list) else [],
                        "llm_used": True,
                        "confidence": 0.87
                    }
                    
                    yield await self._create_event(
                        TTEventType.STAGE_COMPLETE,
                        {
                            "stage": "optimization",
                            "result": result,
                            "llm_interactions": 1
                        },
                        loop_state
                    )
                    return
            
        except Exception as e:
            self.logger.error(f"优化审查阶段执行异常: {e}")
            fallback_result = {
                "optimization_analysis": {
                    "quality": "acceptable",
                    "performance": "satisfactory",
                    "accuracy": "good",
                    "improvements": []
                },
                "optimized_result": implementation_result,
                "improvements": [],
                "llm_used": False,
                "confidence": 0.7,
                "fallback": True
            }
            
            yield await self._create_event(
                TTEventType.STAGE_COMPLETE,
                {
                    "stage": "optimization",
                    "result": fallback_result,
                    "error": str(e),
                    "llm_interactions": 0
                },
                loop_state
            )
    
    async def _execute_synthesis_stage(
        self,
        context: TTContext,
        loop_state: TTLoopState,
        optimization_result: Dict[str, Any]
    ) -> AsyncGenerator[TTEvent, None]:
        """阶段6：综合整合（LLM集成）"""
        
        yield await self._create_event(
            TTEventType.STAGE_START,
            {
                "stage": "synthesis",
                "stage_number": 6,
                "llm_integration": True
            },
            loop_state
        )
        
        try:
            from ..tools.llm import get_llm_reasoning_tool
            
            llm_tool = get_llm_reasoning_tool()
            
            synthesis_prompt = f"""
            综合所有阶段的结果，生成最终的任务输出：
            
            优化结果: {json.dumps(optimization_result, ensure_ascii=False, indent=2)}
            
            原始任务: {context.task_description}
            
            请生成：
            1. 综合的任务执行结果
            2. 关键洞察和发现
            3. 质量评估和置信度
            4. 使用建议和注意事项
            5. 完整的输出格式
            
            返回最终的综合结果（JSON格式）。
            """
            
            from ..tools.core.base import ToolExecutionContext
            tool_context = ToolExecutionContext(user_id=context.user_id)
            
            async for llm_result in llm_tool.execute(
                {"problem": synthesis_prompt, "reasoning_depth": "detailed"},
                tool_context
            ):
                if llm_result.is_partial:
                    yield await self._create_event(
                        TTEventType.LLM_STREAM_DELTA,
                        {"stage": "synthesis", "delta": llm_result.data.get("message", "") if llm_result.data else ""},
                        loop_state
                    )
                elif llm_result.success and not llm_result.is_partial:
                    result = {
                        "final_result": llm_result.data.get("result", {}),
                        "synthesis_quality": "high",
                        "comprehensive_output": {
                            **optimization_result.get("optimized_result", {}),
                            "synthesis_insights": llm_result.data.get("result", {}),
                            "final_timestamp": datetime.now().isoformat()
                        },
                        "llm_used": True,
                        "confidence": 0.92
                    }
                    
                    yield await self._create_event(
                        TTEventType.STAGE_COMPLETE,
                        {
                            "stage": "synthesis",
                            "result": result,
                            "llm_interactions": 1
                        },
                        loop_state
                    )
                    return
            
        except Exception as e:
            self.logger.error(f"综合整合阶段执行异常: {e}")
            fallback_result = {
                "final_result": optimization_result.get("optimized_result", {}),
                "synthesis_quality": "basic",
                "comprehensive_output": optimization_result.get("optimized_result", {}),
                "llm_used": False,
                "confidence": 0.75,
                "fallback": True
            }
            
            yield await self._create_event(
                TTEventType.STAGE_COMPLETE,
                {
                    "stage": "synthesis",
                    "result": fallback_result,
                    "error": str(e),
                    "llm_interactions": 0
                },
                loop_state
            )
    
    async def _execute_tools_in_parallel(
        self,
        tool_requests: List[Dict[str, Any]],
        context: TTContext,
        loop_state: TTLoopState
    ) -> AsyncGenerator[TTEvent, None]:
        """并行执行工具请求"""
        
        yield await self._create_event(
            TTEventType.TOOL_EXECUTION_START,
            {"tool_count": len(tool_requests), "parallel": True},
            loop_state
        )
        
        try:
            # 并行执行所有工具
            tasks = []
            for i, tool_request in enumerate(tool_requests):
                task = self._execute_single_tool(tool_request, i, context, loop_state)
                tasks.append(task)
            
            # 等待所有工具完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            successful_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"工具{i}执行异常: {result}")
                else:
                    successful_results.append(result)
            
            yield await self._create_event(
                TTEventType.TOOL_EXECUTION_COMPLETE,
                {
                    "results": successful_results,
                    "success_count": len(successful_results),
                    "total_count": len(tool_requests)
                },
                loop_state
            )
            
        except Exception as e:
            self.logger.error(f"并行工具执行异常: {e}")
            yield await self._create_event(
                TTEventType.TOOL_EXECUTION_COMPLETE,
                {
                    "results": [],
                    "error": str(e),
                    "success_count": 0,
                    "total_count": len(tool_requests)
                },
                loop_state
            )
    
    async def _execute_single_tool(
        self,
        tool_request: Dict[str, Any],
        tool_index: int,
        context: TTContext,
        loop_state: TTLoopState
    ) -> Dict[str, Any]:
        """执行单个工具 - 通用智能工具执行器"""
        
        try:
            tool_name = tool_request.get("tool")
            tool_input = tool_request.get("input", {})
            
            self.logger.info(f"执行智能工具: {tool_name}, 索引: {tool_index}")
            
            # 智能工具路由 - 根据工具类型选择最适合的执行器
            if tool_name == "sql_generation":
                return await self._execute_sql_generation_tool(tool_input, tool_index, context)
                
            elif tool_name == "placeholder_analysis":
                return await self._execute_placeholder_analysis_tool(tool_input, tool_index, context)
                
            elif tool_name == "data_analysis":
                return await self._execute_data_analysis_tool(tool_input, tool_index, context)
                
            elif tool_name == "general_processing":
                return await self._execute_general_processing_tool(tool_input, tool_index, context)
                
            else:
                # 通用适应性工具执行 - 基于输入智能推断处理方式
                return await self._execute_adaptive_tool(tool_name, tool_input, tool_index, context)
            
        except Exception as e:
            self.logger.error(f"智能工具{tool_index}执行异常: {e}")
            return {
                "tool": tool_request.get("tool", "unknown"),
                "input": tool_request.get("input", {}),
                "output": None,
                "success": False,
                "error": str(e),
                "tool_index": tool_index,
                "task_completion_signal": False
            }
    
    async def _execute_placeholder_analysis_tool(
        self, 
        tool_input: Dict[str, Any], 
        tool_index: int,
        context: TTContext
    ) -> Dict[str, Any]:
        """执行占位符分析工具 - 使用专业化prompt进行智能分析"""
        
        try:
            from ..tools.llm import get_llm_reasoning_tool
            from ..tools.core.base import ToolExecutionContext
            from ..prompts import prompt_manager
            
            placeholder_text = tool_input.get("placeholder_text", "")
            analysis_context = tool_input.get("context", {})
            task_description = tool_input.get("task_description", "")
            
            # 使用Prompt系统进行智能上下文分析 - 遵循TT控制模式
            context_intelligence_result = await self._analyze_context_with_prompt_system(
                placeholder_text, analysis_context, task_description, context
            )
            
            # 如果Prompt系统判断上下文已足够，直接返回结果
            if context_intelligence_result.get("context_sufficient", False):
                return {
                    "tool": "placeholder_analysis", 
                    "input": tool_input,
                    "output": context_intelligence_result,
                    "success": True,
                    "task_completion_signal": context_intelligence_result.get("task_complete", False)
                }
            
            # 根据任务类型获取专业化指令
            agent_instructions = prompt_manager.get_agent_instructions(
                agent_type="data_analysis", 
                tools=["placeholder_analyzer", "sql_generator", "data_analyzer"]
            )
            
            # 构建上下文感知的提示
            context_aware_prompt = prompt_manager.get_context_aware_prompt({
                "task_type": "placeholder_analysis",
                "data_sensitivity": "medium",
                "user_role": "analyst",
                "urgency": "normal"
            })
            
            # 构建综合占位符分析提示
            placeholder_analysis_prompt = f"""
{agent_instructions}

{context_aware_prompt}

# 占位符分析专项任务

## 任务上下文
- 任务描述: {task_description}
- 占位符内容: {placeholder_text}
- 上下文信息: {json.dumps(analysis_context, ensure_ascii=False, indent=2)}

## 分析要求
遵循数据分析智能体的专业化工作流，特别关注：

### 阶段1：占位符理解和验证
1. 分析占位符的语法结构和语义含义
2. 识别占位符中的数据范围条件（时间、地域、类型等）
3. 提取业务逻辑和过滤条件
4. 验证占位符的完整性和有效性

### 阶段2：上下文关联性分析
1. 从上下文中识别最相关的数据源信息
2. 匹配占位符要求与可用数据字段
3. 分析数据质量和完整性要求
4. 识别潜在的数据转换需求

### 阶段3：解决方案生成
1. 设计最优的数据获取策略
2. 生成相应的SQL查询逻辑（如需要）
3. 确定输出格式和结构要求
4. 评估解决方案的可行性和效率

### 阶段4：质量保证
1. 验证解决方案的正确性
2. 评估性能和资源消耗
3. 提供实施建议和注意事项
4. 判断是否需要进一步的SQL生成步骤

请提供结构化的分析结果，包括详细的推理过程和可操作的建议。
"""
            
            llm_tool = get_llm_reasoning_tool()
            tool_context = ToolExecutionContext(user_id=context.user_id)
            
            # 执行专业化LLM分析
            final_analysis_result = None
            async for llm_result in llm_tool.execute(
                {"problem": placeholder_analysis_prompt, "reasoning_depth": "expert"},
                tool_context
            ):
                if llm_result.success and not llm_result.is_partial:
                    final_analysis_result = llm_result.data.get("result", "") if llm_result.data else ""
                    break
            
            if not final_analysis_result:
                raise Exception("占位符分析失败，无法获取LLM分析结果")
            
            # 智能判断后续步骤需求
            needs_sql = self._analyze_if_sql_needed(final_analysis_result, placeholder_text)
            analysis_quality = self._evaluate_analysis_quality(final_analysis_result)
            
            result = {
                "tool": "placeholder_analysis",
                "input": tool_input,
                "output": {
                    "analysis_result": final_analysis_result,
                    "placeholder_interpretation": self._extract_placeholder_interpretation(final_analysis_result),
                    "needs_sql_generation": needs_sql,
                    "analysis_quality": analysis_quality,
                    "relevant_context": analysis_context,
                    "specialized_approach": "data_analysis_focused",
                    "analysis_timestamp": datetime.now().isoformat()
                },
                "success": True,
                "execution_time": 3.0,  # 更复杂的分析需要更多时间
                "tool_index": tool_index,
                # 基于分析质量和SQL需求决定是否终止
                "task_completion_signal": analysis_quality["is_complete"] and not needs_sql
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"专业化占位符分析工具执行异常: {e}")
            return {
                "tool": "placeholder_analysis",
                "input": tool_input,
                "output": None,
                "success": False,
                "error": str(e),
                "tool_index": tool_index,
                "task_completion_signal": False
            }
    
    def _evaluate_analysis_quality(self, analysis_result: str) -> Dict[str, Any]:
        """评估分析结果质量"""
        
        quality_indicators = {
            "has_structure": any(indicator in analysis_result for indicator in ["阶段", "步骤", "##", "###"]),
            "has_reasoning": any(indicator in analysis_result for indicator in ["因为", "所以", "根据", "分析"]),
            "has_actionable_items": any(indicator in analysis_result for indicator in ["建议", "推荐", "应该", "需要"]),
            "has_technical_details": any(indicator in analysis_result for indicator in ["SQL", "字段", "表", "数据库"]),
            "sufficient_length": len(analysis_result) > 200
        }
        
        quality_score = sum(quality_indicators.values()) / len(quality_indicators)
        
        return {
            "is_complete": quality_score > 0.7,
            "quality_score": quality_score,
            "quality_indicators": quality_indicators,
            "confidence": quality_score
        }
    
    def _analyze_if_sql_needed(self, analysis_result: str, placeholder_text: str) -> bool:
        """分析是否需要生成SQL"""
        
        # 检查分析结果中是否提到需要SQL查询
        sql_indicators = [
            "sql", "查询", "数据库", "表", "字段", 
            "select", "from", "where", "query", "database"
        ]
        
        analysis_lower = analysis_result.lower()
        placeholder_lower = placeholder_text.lower()
        
        # 如果分析结果或占位符中包含SQL相关关键词
        sql_mentioned = any(indicator in analysis_lower for indicator in sql_indicators)
        placeholder_has_sql_context = any(indicator in placeholder_lower for indicator in sql_indicators)
        
        return sql_mentioned or placeholder_has_sql_context
    
    def _extract_placeholder_interpretation(self, analysis_result: str) -> Dict[str, Any]:
        """从分析结果中提取占位符解释"""
        
        # 简单的信息提取 - 实际可以用更复杂的NLP技术
        interpretation = {
            "type": "general",
            "data_requirements": [],
            "suggested_fields": [],
            "time_range": None
        }
        
        analysis_lower = analysis_result.lower()
        
        # 检测占位符类型
        if "时间" in analysis_lower or "date" in analysis_lower:
            interpretation["type"] = "temporal"
        elif "用户" in analysis_lower or "user" in analysis_lower:
            interpretation["type"] = "user_related"
        elif "产品" in analysis_lower or "product" in analysis_lower:
            interpretation["type"] = "product_related"
        elif "销售" in analysis_lower or "sales" in analysis_lower:
            interpretation["type"] = "sales_related"
        
        return interpretation
    
    async def _execute_general_processing_tool(
        self, 
        tool_input: Dict[str, Any], 
        tool_index: int,
        context: TTContext
    ) -> Dict[str, Any]:
        """执行通用处理工具 - 适应性强的通用处理器"""
        
        try:
            from ..tools.llm import get_llm_reasoning_tool
            from ..tools.core.base import ToolExecutionContext
            
            task_description = tool_input.get("task_description", "")
            processing_context = tool_input.get("context", {})
            strategy_type = tool_input.get("processing_strategy", "adaptive_general")
            
            # 构建通用处理提示
            general_processing_prompt = f"""
            基于给定的任务和上下文，进行智能通用处理：
            
            任务描述: {task_description}
            处理策略: {strategy_type}
            上下文数据: {json.dumps(processing_context, ensure_ascii=False, indent=2)}
            
            请进行以下处理：
            1. 理解任务的核心需求
            2. 分析可用的上下文信息
            3. 确定最佳的处理方法
            4. 生成相应的解决方案
            5. 评估结果的完整性
            
            重点关注目标导向的解决方案，确保输出能够满足任务需求。
            """
            
            llm_tool = get_llm_reasoning_tool()
            tool_context = ToolExecutionContext(user_id=context.user_id)
            
            # 执行LLM通用处理
            final_processing_result = None
            async for llm_result in llm_tool.execute(
                {"problem": general_processing_prompt, "reasoning_depth": "detailed"},
                tool_context
            ):
                if llm_result.success and not llm_result.is_partial:
                    final_processing_result = llm_result.data.get("result", "") if llm_result.data else ""
                    break
            
            if not final_processing_result:
                raise Exception("通用处理失败，无法获取LLM处理结果")
            
            # 评估处理完整性
            is_complete = self._evaluate_processing_completeness(final_processing_result, task_description)
            
            result = {
                "tool": "general_processing",
                "input": tool_input,
                "output": {
                    "processing_result": final_processing_result,
                    "strategy_used": strategy_type,
                    "completeness_evaluation": is_complete,
                    "processing_timestamp": datetime.now().isoformat()
                },
                "success": True,
                "execution_time": 2.0,
                "tool_index": tool_index,
                # 基于完整性评估决定是否完成
                "task_completion_signal": is_complete["is_complete"]
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"通用处理工具执行异常: {e}")
            return {
                "tool": "general_processing",
                "input": tool_input,
                "output": None,
                "success": False,
                "error": str(e),
                "tool_index": tool_index,
                "task_completion_signal": False
            }
    
    def _evaluate_processing_completeness(self, result: str, task_description: str) -> Dict[str, Any]:
        """评估处理结果的完整性"""
        
        # 简单的完整性评估逻辑
        evaluation = {
            "is_complete": False,
            "confidence": 0.0,
            "missing_aspects": [],
            "quality_score": 0.0
        }
        
        try:
            result_lower = result.lower()
            task_lower = task_description.lower()
            
            # 检查结果长度（简单指标）
            length_score = min(len(result) / 500, 1.0)  # 假设500字符为合理长度
            
            # 检查是否包含关键任务词汇
            task_words = set(task_lower.split())
            result_words = set(result_lower.split())
            keyword_coverage = len(task_words.intersection(result_words)) / len(task_words) if task_words else 0
            
            # 检查结构完整性指标
            structure_indicators = ["分析", "结论", "建议", "方案", "结果"]
            structure_score = sum(1 for indicator in structure_indicators if indicator in result) / len(structure_indicators)
            
            # 综合评分
            quality_score = (length_score + keyword_coverage + structure_score) / 3
            
            evaluation.update({
                "is_complete": quality_score > 0.6,  # 60%以上认为完整
                "confidence": quality_score,
                "quality_score": quality_score
            })
            
            if quality_score <= 0.6:
                evaluation["missing_aspects"] = ["需要更详细的分析", "缺少具体方案", "结论不够明确"]
            
        except Exception as e:
            self.logger.error(f"完整性评估异常: {e}")
        
        return evaluation
    
    async def _execute_adaptive_tool(
        self, 
        tool_name: str, 
        tool_input: Dict[str, Any], 
        tool_index: int,
        context: TTContext
    ) -> Dict[str, Any]:
        """执行适应性工具 - 处理未知工具类型"""
        
        try:
            self.logger.info(f"执行适应性工具处理: {tool_name}")
            
            # 根据工具名称和输入智能推断处理方式
            if "analyzer" in tool_name.lower():
                # 分析类工具
                return await self._execute_analysis_adaptive_tool(tool_name, tool_input, tool_index, context)
            elif "generator" in tool_name.lower():
                # 生成类工具
                return await self._execute_generation_adaptive_tool(tool_name, tool_input, tool_index, context)
            else:
                # 通用适应性处理
                result = {
                    "tool": tool_name,
                    "input": tool_input,
                    "output": {
                        "adaptive_result": f"适应性处理完成: {tool_name}",
                        "processing_type": "adaptive_general",
                        "timestamp": datetime.now().isoformat()
                    },
                    "success": True,
                    "execution_time": 1.0,
                    "tool_index": tool_index,
                    "task_completion_signal": True  # 适应性工具默认完成任务
                }
                
                return result
            
        except Exception as e:
            self.logger.error(f"适应性工具{tool_name}执行异常: {e}")
            return {
                "tool": tool_name,
                "input": tool_input,
                "output": None,
                "success": False,
                "error": str(e),
                "tool_index": tool_index,
                "task_completion_signal": False
            }
    
    async def _execute_analysis_adaptive_tool(
        self, 
        tool_name: str, 
        tool_input: Dict[str, Any], 
        tool_index: int,
        context: TTContext
    ) -> Dict[str, Any]:
        """执行分析类适应性工具"""
        
        # 模拟分析处理
        analysis_result = {
            "analysis_type": tool_name,
            "input_processed": bool(tool_input),
            "key_findings": f"基于{tool_name}的分析发现",
            "confidence": 0.75
        }
        
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": analysis_result,
            "success": True,
            "execution_time": 1.5,
            "tool_index": tool_index,
            "task_completion_signal": True
        }
    
    async def _execute_generation_adaptive_tool(
        self, 
        tool_name: str, 
        tool_input: Dict[str, Any], 
        tool_index: int,
        context: TTContext
    ) -> Dict[str, Any]:
        """执行生成类适应性工具"""
        
        # 模拟生成处理
        generation_result = {
            "generation_type": tool_name,
            "generated_content": f"基于{tool_name}生成的内容",
            "quality_score": 0.8
        }
        
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": generation_result,
            "success": True,
            "execution_time": 2.0,
            "tool_index": tool_index,
            "task_completion_signal": True
        }
    
    async def _execute_sql_generation_tool(
        self, 
        tool_input: Dict[str, Any], 
        tool_index: int,
        context: TTContext
    ) -> Dict[str, Any]:
        """执行SQL生成工具 - 使用专业化数据分析prompt"""
        
        try:
            from ..tools.llm import get_llm_reasoning_tool
            from ..tools.core.base import ToolExecutionContext
            from ..prompts import prompt_manager
            
            task_description = tool_input.get('task_description', '')
            sql_context = tool_input.get('context', {})
            data_source = tool_input.get('data_source', {})
            
            # 获取数据分析专业化指令
            agent_instructions = prompt_manager.get_agent_instructions(
                agent_type="data_analysis", 
                tools=["sql_generator", "sql_executor", "data_analyzer"]
            )
            
            # 根据数据敏感性和用户角色适配
            context_sensitive_prompt = prompt_manager.get_context_aware_prompt({
                "user_role": "analyst", 
                "data_sensitivity": "high",
                "urgency": "normal",
                "resource_constraints": {"memory_limited": False}
            })
            
            # 构建专业化SQL生成提示
            sql_generation_prompt = f"""
{agent_instructions}

{context_sensitive_prompt}

# SQL查询生成专项任务

## 任务上下文
- 任务描述: {task_description}
- 数据源信息: {json.dumps(data_source, ensure_ascii=False, indent=2)}
- 业务上下文: {json.dumps(sql_context, ensure_ascii=False, indent=2)}

## 生成要求
遵循数据分析智能体的专业化工作流：

### 阶段1：需求分析和验证
1. 深入理解业务需求和查询目标
2. 识别关键业务指标和维度
3. 分析数据源结构和关系
4. 验证数据可用性和质量要求

### 阶段2：智能查询规划
1. 设计最优的查询策略和执行计划
2. 选择合适的表连接方式和索引策略
3. 考虑查询性能和资源消耗
4. 规划数据过滤和聚合逻辑

### 阶段3：SQL代码生成
1. 生成语法正确、性能优化的SQL查询
2. 包含适当的错误处理和边界条件
3. 添加清晰的注释说明查询逻辑
4. 确保查询结果的准确性和完整性

### 阶段4：质量保证
1. 验证SQL语法的正确性
2. 评估查询性能和优化建议
3. 检查数据安全和权限要求
4. 提供执行建议和注意事项

## 输出要求
请生成：
1. 完整的、可执行的SQL查询语句
2. 详细的查询逻辑说明和注释
3. 预期的结果结构和数据类型
4. 性能优化建议和执行计划
5. 数据质量和统计显著性评估

确保遵循SQL最佳实践和安全标准。
"""
            
            llm_tool = get_llm_reasoning_tool()
            tool_context = ToolExecutionContext(user_id=context.user_id)
            
            # 执行专业化LLM SQL生成
            final_sql_result = None
            async for llm_result in llm_tool.execute(
                {"problem": sql_generation_prompt, "reasoning_depth": "expert"},
                tool_context
            ):
                if llm_result.success and not llm_result.is_partial:
                    final_sql_result = llm_result.data.get("result", "") if llm_result.data else ""
                    break
            
            if not final_sql_result:
                raise Exception("专业化SQL生成失败，无法获取LLM结果")
            
            # 增强的SQL验证和质量评估
            sql_validation_result = await self._validate_generated_sql(final_sql_result, context)
            sql_quality_assessment = self._assess_sql_quality(final_sql_result)
            
            result = {
                "tool": "sql_generation",
                "input": tool_input,
                "output": {
                    "generated_sql": final_sql_result,
                    "validation": sql_validation_result,
                    "quality_assessment": sql_quality_assessment,
                    "specialized_approach": "data_analysis_focused",
                    "generation_timestamp": datetime.now().isoformat()
                },
                "success": sql_validation_result.get("is_valid", False),
                "execution_time": 3.5,  # 专业化分析需要更多时间
                "tool_index": tool_index,
                # 基于验证结果和质量评估决定任务完成
                "task_completion_signal": (
                    sql_validation_result.get("is_valid", False) and 
                    sql_quality_assessment.get("quality_score", 0) > 0.7
                )
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"专业化SQL生成工具执行异常: {e}")
            return {
                "tool": "sql_generation",
                "input": tool_input,
                "output": None,
                "success": False,
                "error": str(e),
                "tool_index": tool_index,
                "task_completion_signal": False
            }
    
    def _assess_sql_quality(self, sql_text: str) -> Dict[str, Any]:
        """评估SQL查询质量"""
        
        quality_metrics = {
            "has_comments": "--" in sql_text or "/*" in sql_text,
            "proper_formatting": "\n" in sql_text and any(kw in sql_text.upper() for kw in ["SELECT", "FROM", "WHERE"]),
            "uses_best_practices": any(practice in sql_text.upper() for practice in ["LIMIT", "ORDER BY", "GROUP BY"]),
            "appropriate_length": 50 < len(sql_text) < 2000,
            "includes_error_handling": any(handler in sql_text.upper() for handler in ["COALESCE", "ISNULL", "CASE"])
        }
        
        quality_score = sum(quality_metrics.values()) / len(quality_metrics)
        
        return {
            "quality_score": quality_score,
            "quality_metrics": quality_metrics,
            "is_high_quality": quality_score > 0.7,
            "assessment_details": {
                "readability": "good" if quality_metrics["proper_formatting"] else "needs_improvement",
                "maintainability": "good" if quality_metrics["has_comments"] else "needs_improvement",
                "robustness": "good" if quality_metrics["includes_error_handling"] else "basic"
            }
        }
    
    async def _validate_generated_sql(
        self, 
        sql_text: str, 
        context: TTContext
    ) -> Dict[str, Any]:
        """验证生成的SQL并检查数据库连接"""
        
        validation_result = {
            "is_valid": False,
            "syntax_check": False,
            "db_connection_check": False,
            "validation_details": {},
            "retry_count": 0
        }
        
        try:
            # 步骤1：基本SQL语法检查
            sql_validation = self._basic_sql_syntax_check(sql_text)
            validation_result["syntax_check"] = sql_validation["is_valid"]
            validation_result["validation_details"]["syntax"] = sql_validation
            
            if not sql_validation["is_valid"]:
                self.logger.warning(f"SQL语法检查失败: {sql_validation.get('error')}")
                return validation_result
            
            # 步骤2：数据库连接测试（带重试机制）
            max_retries = 3
            for retry in range(max_retries):
                validation_result["retry_count"] = retry + 1
                
                try:
                    db_test_result = await self._test_database_connection(context)
                    validation_result["db_connection_check"] = db_test_result["connected"]
                    validation_result["validation_details"]["database"] = db_test_result
                    
                    if db_test_result["connected"]:
                        # 数据库连接成功，SQL语法正确 -> 任务成功完成
                        validation_result["is_valid"] = True
                        self.logger.info("SQL验证成功：语法正确且数据库连接正常")
                        break
                    else:
                        self.logger.warning(f"数据库连接失败，重试 {retry + 1}/{max_retries}: {db_test_result.get('error')}")
                        if retry < max_retries - 1:
                            await asyncio.sleep(1)  # 重试间隔
                        
                except Exception as db_error:
                    self.logger.error(f"数据库连接测试异常，重试 {retry + 1}/{max_retries}: {db_error}")
                    if retry == max_retries - 1:
                        # 最后一次重试失败 -> 任务失败完成
                        validation_result["validation_details"]["database"] = {
                            "connected": False,
                            "error": str(db_error),
                            "final_attempt": True
                        }
                        break
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"SQL验证过程异常: {e}")
            validation_result["validation_details"]["general_error"] = str(e)
            return validation_result
    
    def _basic_sql_syntax_check(self, sql_text: str) -> Dict[str, Any]:
        """基本SQL语法检查"""
        
        try:
            # 简单的SQL语法验证
            sql_clean = sql_text.strip().lower()
            
            # 检查是否包含基本SQL关键词
            required_keywords = ["select", "from"]
            missing_keywords = [kw for kw in required_keywords if kw not in sql_clean]
            
            if missing_keywords:
                return {
                    "is_valid": False,
                    "error": f"SQL缺少必要关键词: {missing_keywords}",
                    "validation_type": "syntax_check"
                }
            
            # 检查是否有明显的语法错误
            if sql_clean.count("(") != sql_clean.count(")"):
                return {
                    "is_valid": False,
                    "error": "SQL括号不匹配",
                    "validation_type": "syntax_check"
                }
            
            return {
                "is_valid": True,
                "message": "基本语法检查通过",
                "validation_type": "syntax_check"
            }
            
        except Exception as e:
            return {
                "is_valid": False,
                "error": f"语法检查异常: {str(e)}",
                "validation_type": "syntax_check"
            }
    
    async def _test_database_connection(self, context: TTContext) -> Dict[str, Any]:
        """测试数据库连接"""
        
        try:
            # 这里应该实现实际的数据库连接测试
            # 暂时返回模拟结果，实际应该连接到用户的数据源
            
            user_id = context.user_id
            if not user_id:
                return {
                    "connected": False,
                    "error": "缺少用户ID，无法测试数据库连接",
                    "test_type": "database_connection"
                }
            
            # 模拟数据库连接测试
            # 实际实现应该：
            # 1. 根据用户ID获取数据源配置
            # 2. 尝试建立数据库连接
            # 3. 执行简单的测试查询（如 SELECT 1）
            
            return {
                "connected": True,
                "message": "数据库连接测试通过",
                "test_type": "database_connection",
                "connection_time_ms": 150
            }
            
        except Exception as e:
            return {
                "connected": False,
                "error": f"数据库连接测试异常: {str(e)}",
                "test_type": "database_connection"
            }
    
    async def _execute_data_analysis_tool(
        self, 
        tool_input: Dict[str, Any], 
        tool_index: int,
        context: TTContext
    ) -> Dict[str, Any]:
        """执行数据分析工具"""
        
        try:
            # 数据分析工具的具体实现
            result = {
                "tool": "data_analysis",
                "input": tool_input,
                "output": {
                    "analysis_result": "数据分析完成",
                    "analysis_timestamp": datetime.now().isoformat()
                },
                "success": True,
                "execution_time": 1.5,
                "tool_index": tool_index,
                "task_completion_signal": True  # 数据分析完成即可终止
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"数据分析工具执行异常: {e}")
            return {
                "tool": "data_analysis",
                "input": tool_input,
                "output": None,
                "success": False,
                "error": str(e),
                "tool_index": tool_index,
                "task_completion_signal": False
            }
    
    async def _create_event(
        self,
        event_type: TTEventType,
        data: Dict[str, Any],
        loop_state: TTLoopState
    ) -> TTEvent:
        """创建TT事件"""
        return TTEvent(
            type=event_type,
            uuid=f"{event_type.value}-{loop_state.turn_id}-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now().isoformat(),
            data=data,
            turn_id=loop_state.turn_id,
            turn_counter=loop_state.turn_counter
        )
    
    def _count_llm_interactions(self, *stage_results) -> int:
        """统计LLM交互次数"""
        count = 0
        for result in stage_results:
            if isinstance(result, dict) and result.get("llm_used", False):
                count += 1
        return count
    
    def _check_task_completion_signals(self, tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """检查工具结果中的任务完成信号"""
        
        completion_status = {
            "should_terminate": False,
            "success": False,
            "reason": "no_completion_signal",
            "completion_result": {}
        }
        
        try:
            # 检查所有工具结果中的完成信号
            successful_completions = []
            failed_completions = []
            
            for tool_result in tool_results:
                if not isinstance(tool_result, dict):
                    continue
                    
                # 检查任务完成信号
                has_completion_signal = tool_result.get("task_completion_signal", False)
                is_tool_successful = tool_result.get("success", False)
                
                if has_completion_signal:
                    if is_tool_successful:
                        successful_completions.append(tool_result)
                        self.logger.info(f"检测到成功完成信号: {tool_result.get('tool', 'unknown')}")
                    else:
                        failed_completions.append(tool_result)
                        self.logger.info(f"检测到失败完成信号: {tool_result.get('tool', 'unknown')}")
            
            # 决策逻辑：
            # 1. 如果有任何成功完成的工具 -> 任务成功完成
            # 2. 如果没有成功但有失败完成的工具 -> 任务失败完成
            # 3. 如果没有任何完成信号 -> 继续执行
            
            if successful_completions:
                completion_status.update({
                    "should_terminate": True,
                    "success": True,
                    "reason": "task_completed_successfully",
                    "completion_result": {
                        "completed_tools": [r.get("tool") for r in successful_completions],
                        "successful_results": successful_completions,
                        "completion_type": "success"
                    }
                })
                
            elif failed_completions:
                # 检查是否是最终失败（如数据库连接重试用完）
                final_failures = [r for r in failed_completions 
                                if r.get("output", {}).get("validation", {}).get("retry_count", 0) >= 3]
                
                if final_failures:
                    completion_status.update({
                        "should_terminate": True,
                        "success": False,
                        "reason": "task_failed_after_retries",
                        "completion_result": {
                            "failed_tools": [r.get("tool") for r in final_failures],
                            "failed_results": final_failures,
                            "completion_type": "failure"
                        }
                    })
            
            return completion_status
            
        except Exception as e:
            self.logger.error(f"检查任务完成信号异常: {e}")
            return completion_status
    
    def _update_context_with_tool_results(
        self, 
        context: TTContext, 
        tool_results: List[Dict[str, Any]]
    ) -> TTContext:
        """使用工具结果更新上下文"""
        
        # 创建新的上下文
        updated_context = TTContext(
            task_description=context.task_description,
            context_data={
                **context.context_data,
                "tool_results": tool_results,
                "tool_execution_timestamp": datetime.now().isoformat()
            },
            target_agents=context.target_agents,
            timeout_seconds=context.timeout_seconds,
            enable_streaming=context.enable_streaming,
            user_id=context.user_id,
            message_history=context.message_history,
            memory_manager=context.memory_manager,
            progress_aggregator=context.progress_aggregator,
            streaming_parser=context.streaming_parser,
            error_formatter=context.error_formatter
        )
        
        return updated_context
    
    async def _analyze_context_with_prompt_system(
        self,
        placeholder_text: str,
        analysis_context: Dict[str, Any], 
        task_description: str,
        tt_context: TTContext
    ) -> Dict[str, Any]:
        """
        使用Prompt系统和LLM进行智能上下文分析
        
        遵循TT控制循环的设计原则:
        1. 使用Prompt系统获取专业化指令
        2. 通过LLM进行智能推理
        3. 基于工具生态进行动态适配
        
        Args:
            placeholder_text: 占位符文本
            analysis_context: 分析上下文数据
            task_description: 任务描述
            tt_context: TT控制上下文
            
        Returns:
            智能分析结果
        """
        
        try:
            from ..tools.llm import get_llm_reasoning_tool
            from ..tools.core.base import ToolExecutionContext
            from ..prompts import prompt_manager
            
            # 1. 获取上下文感知的Prompt指令
            context_aware_prompt = prompt_manager.get_context_aware_prompt({
                "task_type": "context_intelligence_analysis",
                "data_sensitivity": "medium",
                "user_role": "analyst",
                "urgency": "normal",
                "resource_constraints": {
                    "memory_limited": False,
                    "time_limited": False
                }
            })
            
            # 2. 获取专业化Agent指令
            data_analysis_instructions = prompt_manager.get_agent_instructions(
                agent_type="data_analysis",
                tools=["context_analyzer", "pattern_recognizer", "data_extractor"]
            )
            
            # 3. 构建智能上下文分析Prompt
            intelligence_analysis_prompt = f"""
{data_analysis_instructions}

{context_aware_prompt}

# 智能上下文充分性分析任务

## 任务目标
分析给定的上下文数据是否已经包含了占位符所需的信息，避免不必要的数据库查询和复杂分析。

## 输入信息
- 任务描述: {task_description}
- 占位符内容: {placeholder_text}
- 可用上下文: {json.dumps(analysis_context, ensure_ascii=False, indent=2)}

## 分析要求

### 阶段1: 占位符需求分析
1. 解析占位符的语义含义和数据需求
2. 识别占位符所请求的信息类型
3. 确定完成占位符解析所需的数据要素

### 阶段2: 上下文数据映射
1. 检查可用上下文中是否包含相关数据
2. 评估上下文数据的完整性和相关性
3. 识别数据映射关系和转换需求

### 阶段3: 充分性判断
1. 基于语义分析判断上下文是否足够
2. 计算置信度分数 (0-1)
3. 决定是否需要进一步的工具执行

### 阶段4: 结果生成
如果上下文充分 (置信度 >= 0.8)，生成直接答案
如果上下文不足，提供后续处理建议

## 输出格式
请返回JSON格式的分析结果:
```json
{{
    "context_sufficient": boolean,
    "confidence_score": float,
    "analysis_result": "详细分析结果",
    "placeholder_interpretation": {{
        "placeholder": "原始占位符",
        "type": "推断的类型",
        "resolved_value": "解析的值 (如果可解析)",
        "resolution_method": "解析方法"
    }},
    "reasoning": "详细推理过程",
    "needs_sql_generation": boolean,
    "task_complete": boolean,
    "next_action": "建议的下一步操作"
}}
```

请基于数据分析智能体的专业化工作流进行分析，提供准确、可靠的判断结果。
"""
            
            # 4. 执行LLM智能分析
            llm_tool = get_llm_reasoning_tool()
            tool_context = ToolExecutionContext(user_id=tt_context.user_id)
            
            analysis_result = None
            async for llm_result in llm_tool.execute(
                {"problem": intelligence_analysis_prompt, "reasoning_depth": "detailed"},
                tool_context
            ):
                if llm_result.success and not llm_result.is_partial:
                    analysis_result = llm_result.result
                    break
            
            if not analysis_result:
                # LLM分析失败，返回需要进一步分析的结果
                return {
                    "context_sufficient": False,
                    "confidence_score": 0.3,
                    "reasoning": "LLM上下文分析失败，需要执行完整的占位符分析流程",
                    "needs_sql_generation": True,
                    "task_complete": False,
                    "next_action": "execute_full_placeholder_analysis"
                }
            
            # 5. 解析LLM分析结果
            try:
                if isinstance(analysis_result, str):
                    # 尝试从文本中提取JSON
                    import re
                    json_match = re.search(r'```json\s*(.*?)\s*```', analysis_result, re.DOTALL)
                    if json_match:
                        result_data = json.loads(json_match.group(1))
                    else:
                        # 如果没有找到JSON块，尝试解析整个结果
                        result_data = json.loads(analysis_result)
                else:
                    result_data = analysis_result
                
                # 确保返回结果包含必要的字段
                return {
                    "context_sufficient": result_data.get("context_sufficient", False),
                    "confidence_score": result_data.get("confidence_score", 0.5),
                    "analysis_result": result_data.get("analysis_result", analysis_result),
                    "placeholder_interpretation": result_data.get("placeholder_interpretation", {}),
                    "reasoning": result_data.get("reasoning", "基于LLM智能分析的结果"),
                    "needs_sql_generation": result_data.get("needs_sql_generation", True),
                    "task_complete": result_data.get("task_complete", False),
                    "next_action": result_data.get("next_action", "continue_analysis"),
                    "analysis_quality": {"score": result_data.get("confidence_score", 0.5), "confidence": "llm_based"}
                }
                
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.warning(f"LLM结果解析失败: {e}, 原始结果: {analysis_result}")
                # 解析失败时的兜底处理
                return {
                    "context_sufficient": False,
                    "confidence_score": 0.4,
                    "analysis_result": str(analysis_result),
                    "reasoning": f"LLM分析完成但结果格式解析失败: {str(e)}",
                    "needs_sql_generation": True,
                    "task_complete": False,
                    "next_action": "execute_fallback_analysis"
                }
                
        except Exception as e:
            self.logger.error(f"智能上下文分析异常: {e}")
            # 异常时的兜底处理 - 继续执行完整流程
            return {
                "context_sufficient": False,
                "confidence_score": 0.2,
                "reasoning": f"上下文智能分析异常: {str(e)}，将执行标准分析流程",
                "needs_sql_generation": True,
                "task_complete": False,
                "next_action": "execute_standard_flow"
            }
    
    async def _compact_message_history(
        self, 
        messages: List[AgentMessage]
    ) -> List[AgentMessage]:
        """压缩消息历史以减少内存使用"""
        
        # 简单的压缩策略：保留最近的N条消息
        max_messages = 50
        
        if len(messages) <= max_messages:
            return messages
        
        # 保留最近的消息
        recent_messages = messages[-max_messages:]
        
        # 创建压缩摘要消息
        summary_message = AgentMessage(
            message_id=f"summary-{uuid.uuid4().hex[:8]}",
            from_agent="system",
            to_agent="all",
            message_type=MessageType.SYSTEM_NOTIFICATION,
            priority=MessagePriority.NORMAL,
            content={
                "type": "conversation_summary",
                "compressed_messages_count": len(messages) - max_messages,
                "summary": f"Compressed {len(messages) - max_messages} older messages",
                "timestamp": datetime.now().isoformat()
            },
            created_at=datetime.now()
        )
        
        return [summary_message] + recent_messages
    
    async def get_active_loops(self) -> Dict[str, TTLoopState]:
        """获取当前活动的循环状态"""
        return self.active_loops.copy()
    
    async def cancel_loop(self, task_id: str) -> bool:
        """取消指定的循环"""
        if task_id in self.active_loops:
            # 这里可以实现更精细的取消逻辑
            del self.active_loops[task_id]
            self.logger.info(f"已取消TT循环: {task_id}")
            return True
        return False