"""
通用Agent协调器
===================

轻量级的通用Agent协调器，专注于生命周期管理和任务路由。
集成所有核心组件，提供统一的智能任务执行接口。
遵循TT控制循环设计原则，实现Prompt + TT + 工具生态的完整协作。
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum

from .intelligent_prompt_orchestrator import IntelligentPromptOrchestrator, SmartContext, ExecutionStrategy
from .unified_tool_ecosystem import UnifiedToolEcosystem, SelectedTool, ToolExecutionResult
from .smart_context_processor import SmartContextProcessor
from .tt_controller import TTController, TTContext

logger = logging.getLogger(__name__)


class CoordinationMode(Enum):
    """协调模式枚举"""
    INTELLIGENT = "intelligent"     # 智能模式：全面使用所有组件
    STANDARD = "standard"          # 标准模式：使用TT控制循环 + 基础工具
    SIMPLE = "simple"             # 简单模式：直接执行，最小化开销


class ExecutionPhase(Enum):
    """执行阶段枚举"""
    INITIALIZATION = "initialization"
    CONTEXT_BUILDING = "context_building"
    STRATEGY_GENERATION = "strategy_generation"
    TOOL_SELECTION = "tool_selection"
    TT_EXECUTION = "tt_execution"
    RESULT_SYNTHESIS = "result_synthesis"
    COMPLETION = "completion"


@dataclass
class CoordinationResult:
    """协调执行结果"""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    phases_completed: List[ExecutionPhase] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskRouter:
    """任务路由器"""
    active_tasks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    task_history: List[Dict[str, Any]] = field(default_factory=list)
    route_cache: Dict[str, str] = field(default_factory=dict)
    
    def register_task(self, task_id: str, task_data: Dict[str, Any]):
        """注册任务"""
        self.active_tasks[task_id] = {
            "data": task_data,
            "status": "registered",
            "created_at": datetime.utcnow(),
            "phases": []
        }
    
    def update_task_phase(self, task_id: str, phase: ExecutionPhase):
        """更新任务阶段"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["phases"].append({
                "phase": phase,
                "timestamp": datetime.utcnow()
            })
    
    def complete_task(self, task_id: str, result: CoordinationResult):
        """完成任务"""
        if task_id in self.active_tasks:
            task_data = self.active_tasks.pop(task_id)
            self.task_history.append({
                "task_id": task_id,
                "data": task_data,
                "result": result,
                "completed_at": datetime.utcnow()
            })


class UniversalAgentCoordinator:
    """
    通用Agent协调器
    
    核心功能：
    1. 轻量级任务协调和生命周期管理
    2. 智能组件集成和统一接口
    3. TT控制循环编排和执行监控
    4. 性能优化和错误处理
    """
    
    def __init__(self, coordination_mode: CoordinationMode = CoordinationMode.INTELLIGENT):
        # 协调模式
        self.coordination_mode = coordination_mode
        
        # 核心组件集成 - 单一职责原则
        self.context_processor = SmartContextProcessor()
        self.prompt_orchestrator = IntelligentPromptOrchestrator()
        self.tool_ecosystem = UnifiedToolEcosystem()
        self.tt_controller = TTController()  # 唯一编排引擎
        
        # 轻量级状态管理
        self.task_router = TaskRouter()
        self.agent_registry = {}
        self.performance_monitor = PerformanceMonitor()
        
        # 配置
        self.config = {
            "max_concurrent_tasks": 10,
            "default_timeout": 300,
            "enable_caching": True,
            "enable_streaming": True,
            "enable_performance_monitoring": True
        }
        
        logger.info(f"UniversalAgentCoordinator initialized in {coordination_mode.value} mode")
    
    async def execute_intelligent_task(
        self,
        task_description: str,
        context_data: Dict[str, Any] = None,
        user_id: str = None,
        coordination_mode: Optional[CoordinationMode] = None
    ) -> CoordinationResult:
        """
        智能任务执行 - 统一入口
        
        Args:
            task_description: 任务描述
            context_data: 上下文数据
            user_id: 用户ID
            coordination_mode: 协调模式（覆盖默认模式）
        
        Returns:
            CoordinationResult: 协调执行结果
        """
        
        # 生成任务ID
        task_id = str(uuid.uuid4())[:8]
        start_time = datetime.utcnow()
        
        # 使用指定的协调模式或默认模式
        mode = coordination_mode or self.coordination_mode
        
        try:
            logger.info(f"Starting intelligent task execution [Task: {task_id}, Mode: {mode.value}]")
            
            # 注册任务
            self.task_router.register_task(task_id, {
                "description": task_description,
                "context_data": context_data,
                "user_id": user_id,
                "mode": mode.value
            })
            
            # 选择执行策略
            if mode == CoordinationMode.INTELLIGENT:
                result = await self._execute_intelligent_mode(task_id, task_description, context_data, user_id)
            elif mode == CoordinationMode.STANDARD:
                result = await self._execute_standard_mode(task_id, task_description, context_data, user_id)
            else:  # SIMPLE
                result = await self._execute_simple_mode(task_id, task_description, context_data, user_id)
            
            # 计算执行时间
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            result.execution_time = execution_time
            
            # 更新性能指标
            await self.performance_monitor.record_task_completion(task_id, result, execution_time)
            
            # 完成任务
            self.task_router.complete_task(task_id, result)
            
            logger.info(f"Task {task_id} completed successfully in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Task {task_id} failed after {execution_time:.2f}s: {e}")
            
            error_result = CoordinationResult(
                task_id=task_id,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
            
            self.task_router.complete_task(task_id, error_result)
            return error_result
    
    async def _execute_intelligent_mode(
        self,
        task_id: str,
        task_description: str,
        context_data: Dict[str, Any],
        user_id: str
    ) -> CoordinationResult:
        """智能模式执行 - 全面使用所有组件"""
        
        phases_completed = []
        performance_metrics = {}
        
        try:
            # Phase 1: 智能上下文构建
            self.task_router.update_task_phase(task_id, ExecutionPhase.CONTEXT_BUILDING)
            
            phase_start = datetime.utcnow()
            smart_context = await self.context_processor.build_intelligent_context(
                task_description, context_data, user_id
            )
            performance_metrics["context_building_time"] = (datetime.utcnow() - phase_start).total_seconds()
            phases_completed.append(ExecutionPhase.CONTEXT_BUILDING)
            
            logger.debug(f"Task {task_id}: Context built - Scenario: {smart_context.scenario}, "
                        f"Complexity: {smart_context.complexity_level.value}, "
                        f"Agent: {smart_context.optimal_agent_type}")
            
            # Phase 2: Prompt策略生成
            self.task_router.update_task_phase(task_id, ExecutionPhase.STRATEGY_GENERATION)
            
            phase_start = datetime.utcnow()
            execution_strategy = await self.prompt_orchestrator.generate_execution_strategy(smart_context)
            performance_metrics["strategy_generation_time"] = (datetime.utcnow() - phase_start).total_seconds()
            phases_completed.append(ExecutionPhase.STRATEGY_GENERATION)
            
            logger.debug(f"Task {task_id}: Strategy generated with confidence {execution_strategy.confidence_score}")
            
            # Phase 3: 智能工具选择
            self.task_router.update_task_phase(task_id, ExecutionPhase.TOOL_SELECTION)
            
            phase_start = datetime.utcnow()
            selected_tools = await self.tool_ecosystem.discover_and_select_tools(
                smart_context, execution_strategy
            )
            performance_metrics["tool_selection_time"] = (datetime.utcnow() - phase_start).total_seconds()
            phases_completed.append(ExecutionPhase.TOOL_SELECTION)
            
            logger.debug(f"Task {task_id}: Selected {len(selected_tools)} tools")
            
            # Phase 4: TT控制循环执行 (唯一编排引擎)
            self.task_router.update_task_phase(task_id, ExecutionPhase.TT_EXECUTION)
            
            phase_start = datetime.utcnow()
            tt_result = await self._execute_tt_with_strategy(
                smart_context, execution_strategy, selected_tools
            )
            performance_metrics["tt_execution_time"] = (datetime.utcnow() - phase_start).total_seconds()
            phases_completed.append(ExecutionPhase.TT_EXECUTION)
            
            logger.debug(f"Task {task_id}: TT execution completed")
            
            # Phase 5: 结果综合
            self.task_router.update_task_phase(task_id, ExecutionPhase.RESULT_SYNTHESIS)
            
            phase_start = datetime.utcnow()
            final_result = await self._synthesize_results(
                tt_result, smart_context, execution_strategy, selected_tools
            )
            performance_metrics["result_synthesis_time"] = (datetime.utcnow() - phase_start).total_seconds()
            phases_completed.append(ExecutionPhase.RESULT_SYNTHESIS)
            
            phases_completed.append(ExecutionPhase.COMPLETION)
            
            return CoordinationResult(
                task_id=task_id,
                success=True,
                result=final_result,
                phases_completed=phases_completed,
                performance_metrics=performance_metrics,
                metadata={
                    "mode": "intelligent",
                    "scenario": smart_context.scenario,
                    "complexity": smart_context.complexity_level.value,
                    "agent_type": smart_context.optimal_agent_type,
                    "tools_used": [tool.definition.name for tool in selected_tools],
                    "strategy_confidence": execution_strategy.confidence_score
                }
            )
            
        except Exception as e:
            logger.error(f"Intelligent mode execution failed for task {task_id}: {e}")
            raise e
    
    async def _execute_standard_mode(
        self,
        task_id: str,
        task_description: str,
        context_data: Dict[str, Any],
        user_id: str
    ) -> CoordinationResult:
        """标准模式执行 - 使用TT控制循环 + 基础工具"""
        
        phases_completed = []
        
        try:
            # 简化的上下文构建
            self.task_router.update_task_phase(task_id, ExecutionPhase.CONTEXT_BUILDING)
            
            smart_context = SmartContext(
                task_description=task_description,
                context_data=context_data or {},
                user_id=user_id,
                scenario="general",
                available_tools=["reasoning_tool", "data_analyzer"]
            )
            phases_completed.append(ExecutionPhase.CONTEXT_BUILDING)
            
            # 基础策略
            execution_strategy = ExecutionStrategy(
                tool_selection=smart_context.available_tools,
                optimization_hints=["Use standard processing approach"]
            )
            phases_completed.append(ExecutionPhase.STRATEGY_GENERATION)
            
            # TT控制循环执行
            self.task_router.update_task_phase(task_id, ExecutionPhase.TT_EXECUTION)
            
            tt_result = await self._execute_tt_basic(smart_context, execution_strategy)
            phases_completed.append(ExecutionPhase.TT_EXECUTION)
            
            phases_completed.append(ExecutionPhase.COMPLETION)
            
            return CoordinationResult(
                task_id=task_id,
                success=True,
                result=tt_result,
                phases_completed=phases_completed,
                metadata={"mode": "standard"}
            )
            
        except Exception as e:
            logger.error(f"Standard mode execution failed for task {task_id}: {e}")
            raise e
    
    async def _execute_simple_mode(
        self,
        task_id: str,
        task_description: str,
        context_data: Dict[str, Any],
        user_id: str
    ) -> CoordinationResult:
        """简单模式执行 - 直接执行，最小化开销"""
        
        try:
            # 最基础的TT控制循环执行
            basic_context = TTContext(
                task_description=task_description,
                context_data=context_data or {},
                target_agents=["data_analysis"],  # 默认目标Agent
                timeout_seconds=300,             # 默认超时5分钟
                enable_streaming=True,           # 启用流式处理
                user_id=user_id or "anonymous"
            )
            
            result = await self.tt_controller.execute(basic_context)
            
            return CoordinationResult(
                task_id=task_id,
                success=True,
                result=result,
                phases_completed=[ExecutionPhase.TT_EXECUTION, ExecutionPhase.COMPLETION],
                metadata={"mode": "simple"}
            )
            
        except Exception as e:
            logger.error(f"Simple mode execution failed for task {task_id}: {e}")
            raise e
    
    async def _execute_tt_with_strategy(
        self,
        smart_context: SmartContext,
        execution_strategy: ExecutionStrategy,
        selected_tools: List[SelectedTool]
    ) -> Any:
        """使用策略执行TT控制循环"""
        
        # 构建增强的TTContext
        tt_context = TTContext(
            task_description=smart_context.task_description,
            context_data=smart_context.context_data,
            target_agents=[smart_context.optimal_agent_type],
            timeout_seconds=600,  # 智能模式需要更长时间
            enable_streaming=True,
            user_id=smart_context.user_id or "anonymous"
        )
        
        # 添加策略和工具信息到上下文
        tt_context.context_data.update({
            "execution_strategy": execution_strategy,
            "selected_tools": [
                {
                    "name": tool.definition.name,
                    "parameters": tool.parameters,
                    "confidence": tool.confidence_score
                }
                for tool in selected_tools
            ],
            "scenario": smart_context.scenario,
            "complexity_level": smart_context.complexity_level.value,
            "optimal_agent_type": smart_context.optimal_agent_type
        })
        
        # 执行工具
        tool_results = await self.tool_ecosystem.execute_tools_with_strategy(
            selected_tools, tt_context
        )
        
        # 将工具结果添加到上下文
        tt_context.context_data["tool_results"] = [
            {
                "tool": result.tool_name,
                "success": result.success,
                "result": result.result,
                "error": result.error
            }
            for result in tool_results
        ]
        
        # 执行TT控制循环
        return await self.tt_controller.execute(tt_context)
    
    async def _execute_tt_basic(
        self,
        smart_context: SmartContext,
        execution_strategy: ExecutionStrategy
    ) -> Any:
        """基础TT控制循环执行"""
        
        tt_context = TTContext(
            task_description=smart_context.task_description,
            context_data=smart_context.context_data,
            target_agents=[smart_context.optimal_agent_type],
            timeout_seconds=300,
            enable_streaming=True,
            user_id=smart_context.user_id or "anonymous"
        )
        
        return await self.tt_controller.execute(tt_context)
    
    async def _synthesize_results(
        self,
        tt_result: Any,
        smart_context: SmartContext,
        execution_strategy: ExecutionStrategy,
        selected_tools: List[SelectedTool]
    ) -> Dict[str, Any]:
        """综合处理结果"""
        
        synthesis = {
            "primary_result": tt_result,
            "execution_summary": {
                "scenario": smart_context.scenario,
                "complexity": smart_context.complexity_level.value,
                "agent_type": smart_context.optimal_agent_type,
                "tools_used": len(selected_tools),
                "strategy_confidence": execution_strategy.confidence_score
            },
            "metadata": {
                "processing_mode": "intelligent",
                "optimization_hints_applied": execution_strategy.optimization_hints,
                "context_adaptations": execution_strategy.context_adaptations
            }
        }
        
        # 如果有工具结果，添加到综合结果中
        if isinstance(tt_result, dict) and "tool_results" in smart_context.context_data:
            synthesis["tool_results"] = smart_context.context_data["tool_results"]
        
        return synthesis
    
    # 管理接口
    
    def get_coordination_status(self) -> Dict[str, Any]:
        """获取协调器状态"""
        return {
            "mode": self.coordination_mode.value,
            "active_tasks": len(self.task_router.active_tasks),
            "completed_tasks": len(self.task_router.task_history),
            "performance_metrics": self.performance_monitor.get_summary(),
            "config": self.config
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取特定任务状态"""
        if task_id in self.task_router.active_tasks:
            return {
                "status": "active",
                "data": self.task_router.active_tasks[task_id]
            }
        
        for task in self.task_router.task_history:
            if task["task_id"] == task_id:
                return {
                    "status": "completed",
                    "data": task
                }
        
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.task_router.active_tasks:
            # 简单的取消逻辑 - 实际实现中可能需要更复杂的取消机制
            cancelled_task = self.task_router.active_tasks.pop(task_id)
            logger.info(f"Task {task_id} cancelled")
            return True
        return False
    
    def clear_task_history(self):
        """清空任务历史"""
        self.task_router.task_history.clear()
        logger.info("Task history cleared")
    
    def update_config(self, **kwargs):
        """更新配置"""
        self.config.update(kwargs)
        logger.info(f"Configuration updated: {kwargs}")


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "average_execution_time": 0.0,
            "total_execution_time": 0.0,
            "phase_metrics": {},
            "mode_metrics": {}
        }
    
    async def record_task_completion(
        self,
        task_id: str,
        result: CoordinationResult,
        execution_time: float
    ):
        """记录任务完成情况"""
        
        self.metrics["total_tasks"] += 1
        
        if result.success:
            self.metrics["successful_tasks"] += 1
        else:
            self.metrics["failed_tasks"] += 1
        
        # 更新时间指标
        self.metrics["total_execution_time"] += execution_time
        self.metrics["average_execution_time"] = (
            self.metrics["total_execution_time"] / self.metrics["total_tasks"]
        )
        
        # 更新阶段指标
        for phase in result.phases_completed:
            phase_name = phase.value
            if phase_name not in self.metrics["phase_metrics"]:
                self.metrics["phase_metrics"][phase_name] = 0
            self.metrics["phase_metrics"][phase_name] += 1
        
        # 更新模式指标
        mode = result.metadata.get("mode", "unknown")
        if mode not in self.metrics["mode_metrics"]:
            self.metrics["mode_metrics"][mode] = {"count": 0, "success_rate": 0}
        
        mode_stats = self.metrics["mode_metrics"][mode]
        mode_stats["count"] += 1
        if result.success:
            mode_stats["success_rate"] = (
                (mode_stats["success_rate"] * (mode_stats["count"] - 1) + 1) / mode_stats["count"]
            )
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        success_rate = (
            self.metrics["successful_tasks"] / self.metrics["total_tasks"]
            if self.metrics["total_tasks"] > 0 else 0
        )
        
        return {
            "total_tasks": self.metrics["total_tasks"],
            "success_rate": success_rate,
            "average_execution_time": self.metrics["average_execution_time"],
            "phase_completion_rates": self.metrics["phase_metrics"],
            "mode_performance": self.metrics["mode_metrics"]
        }


# 便利函数
def create_universal_coordinator(
    mode: CoordinationMode = CoordinationMode.INTELLIGENT
) -> UniversalAgentCoordinator:
    """快速创建通用协调器"""
    return UniversalAgentCoordinator(coordination_mode=mode)


async def execute_intelligent_task(
    task_description: str,
    context_data: Dict[str, Any] = None,
    user_id: str = None,
    mode: CoordinationMode = CoordinationMode.INTELLIGENT
) -> CoordinationResult:
    """快速执行智能任务"""
    coordinator = UniversalAgentCoordinator(coordination_mode=mode)
    return await coordinator.execute_intelligent_task(
        task_description, context_data, user_id
    )


__all__ = [
    "UniversalAgentCoordinator",
    "CoordinationResult",
    "CoordinationMode",
    "ExecutionPhase",
    "TaskRouter",
    "PerformanceMonitor",
    "create_universal_coordinator",
    "execute_intelligent_task"
]