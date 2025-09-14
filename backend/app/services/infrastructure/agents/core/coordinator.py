"""
Agent Coordinator - Clean Architecture
=====================================

核心Agent协调器，采用简洁的架构设计：
- 基于TT控制循环的统一编排
- 清晰的状态管理
- 标准化的消息传递
- 完整的生命周期管理
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from .message_bus import MessageBus
from .message_types import AgentMessage, MessageType
from .memory_manager import MemoryManager
from .progress_aggregator import ProgressAggregator
from .streaming_parser import StreamingMessageParser
from .error_formatter import ErrorFormatter
from .tt_controller import TTController, TTContext, TTLoopState, TTEvent, TTEventType

logger = logging.getLogger(__name__)


class AgentCoordinator:
    """
    Agent协调器 - 基于TT控制循环的统一架构
    
    核心职责：
    1. Agent生命周期管理
    2. TT控制循环编排
    3. 消息路由和状态管理
    4. 错误处理和恢复
    """
    
    def __init__(self):
        """初始化协调器"""
        # 核心组件
        self.message_bus: Optional[MessageBus] = None
        self.memory_manager: Optional[MemoryManager] = None  
        self.progress_aggregator: Optional[ProgressAggregator] = None
        self.streaming_parser = StreamingMessageParser()
        self.error_formatter = ErrorFormatter()
        
        # TT控制器 - 唯一的编排引擎
        self.tt_controller = TTController()
        
        # Agent注册表
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        
        # 活动任务跟踪
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        
        # 系统状态
        self.is_running = False
        
        logger.info("AgentCoordinator initialized with clean architecture")
    
    async def start(self) -> None:
        """启动协调器"""
        if self.is_running:
            logger.warning("AgentCoordinator already running")
            return
            
        try:
            # 初始化核心组件
            self.message_bus = MessageBus()
            await self.message_bus.start()
            
            self.memory_manager = MemoryManager()
            await self.memory_manager.start()
            
            self.progress_aggregator = ProgressAggregator()
            
            # 注册默认agents
            await self._register_default_agents()
            
            self.is_running = True
            logger.info("AgentCoordinator started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start AgentCoordinator: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """停止协调器"""
        if not self.is_running:
            return
            
        try:
            # 清理活动任务
            for task_id in list(self.active_tasks.keys()):
                await self._cleanup_task(task_id)
            
            # 停止组件
            if self.message_bus:
                await self.message_bus.stop()
            
            if self.memory_manager:
                self.memory_manager.stop()
            
            self.is_running = False
            logger.info("AgentCoordinator stopped")
            
        except Exception as e:
            logger.error(f"Error stopping AgentCoordinator: {e}")
    
    async def register_agent(
        self,
        agent_id: str,
        capabilities: List[str],
        groups: List[str] = None
    ) -> bool:
        """注册Agent"""
        if not self.message_bus:
            logger.error("Cannot register agent: coordinator not started")
            return False
            
        try:
            agent_info = {
                "agent_id": agent_id,
                "capabilities": capabilities,
                "groups": groups or [],
                "registered_at": datetime.now(),
                "status": "active"
            }
            
            # 注册到消息总线
            self.message_bus.register_agent(agent_id, capabilities, groups)
            
            # 记录到注册表
            self.registered_agents[agent_id] = agent_info
            
            logger.info(f"Successfully registered agent: {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False
    
    async def execute_task(
        self,
        task_description: str,
        context: Dict[str, Any] = None,
        target_agents: List[str] = None,
        timeout_seconds: int = 120,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行任务 - 使用TT控制循环
        
        Args:
            task_description: 任务描述
            context: 任务上下文
            target_agents: 目标agents
            timeout_seconds: 超时时间
            user_id: 用户ID
            
        Returns:
            执行结果
        """
        if not self.is_running:
            return {"success": False, "error": "Coordinator not running"}
        
        task_id = str(uuid.uuid4())
        
        try:
            # 记录任务开始
            self.active_tasks[task_id] = {
                "task_id": task_id,
                "description": task_description,
                "context": context or {},
                "target_agents": target_agents or ["sql_generation_agent"],
                "user_id": user_id,
                "started_at": datetime.now(),
                "status": "running"
            }
            
            # 创建TT上下文
            tt_context = TTContext(
                task_description=task_description,
                context_data=context or {},
                target_agents=target_agents or ["sql_generation_agent"],
                timeout_seconds=timeout_seconds,
                enable_streaming=True,
                user_id=user_id,
                memory_manager=self.memory_manager,
                progress_aggregator=self.progress_aggregator,
                streaming_parser=self.streaming_parser,
                error_formatter=self.error_formatter
            )
            
            # 创建TT循环状态
            loop_state = TTLoopState(
                turn_id=str(uuid.uuid4()),
                turn_counter=0,
                task_id=task_id,
                compacted=False,
                is_resuming=False
            )
            
            # 执行TT控制循环
            events = []
            final_result = None
            
            async for event in self.tt_controller.tt(tt_context, loop_state):
                events.append(event)
                
                # 记录重要事件
                if event.type == TTEventType.TASK_COMPLETE:
                    final_result = event.data
                    break
                elif event.type == TTEventType.SYSTEM_ERROR:
                    logger.error(f"Task {task_id} error: {event.data}")
            
            # 构建结果
            if final_result and final_result.get("success", False):
                result = {
                    "success": True,
                    "task_id": task_id,
                    "result": final_result.get("result", {}),
                    "llm_interactions": final_result.get("llm_interactions_count", 0),
                    "architecture": "tt_controlled",
                    "events_processed": len(events),
                    "execution_time": final_result.get("execution_time")
                }
                self.active_tasks[task_id]["status"] = "completed"
            else:
                error_events = [e for e in events if e.type == TTEventType.SYSTEM_ERROR]
                error_msg = error_events[-1].data.get("error", "Unknown error") if error_events else "Task failed"
                
                result = {
                    "success": False,
                    "task_id": task_id,
                    "error": error_msg,
                    "events_processed": len(events),
                    "architecture": "tt_controlled"
                }
                self.active_tasks[task_id]["status"] = "failed"
            
            return result
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = "failed"
            
            return {
                "success": False,
                "task_id": task_id,
                "error": str(e),
                "architecture": "tt_controlled"
            }
        
        finally:
            # 清理任务
            await self._cleanup_task(task_id)
    
    async def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "is_running": self.is_running,
            "registered_agents": len(self.registered_agents),
            "active_tasks": len([t for t in self.active_tasks.values() if t["status"] == "running"]),
            "total_tasks": len(self.active_tasks),
            "agents": list(self.registered_agents.keys()),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _register_default_agents(self) -> None:
        """注册默认agents"""
        default_agents = [
            {
                "agent_id": "data_analysis_agent",
                "capabilities": ["data_analysis", "statistical_analysis", "pattern_recognition"],
                "groups": ["analysis_agents", "data_agents"]
            },
            {
                "agent_id": "sql_generation_agent", 
                "capabilities": ["sql_generation", "query_optimization", "database_interaction"],
                "groups": ["data_agents", "sql_agents"]
            },
            {
                "agent_id": "report_generation_agent",
                "capabilities": ["report_generation", "data_visualization", "document_formatting"],
                "groups": ["presentation_agents", "report_agents"]
            }
        ]
        
        for agent in default_agents:
            await self.register_agent(
                agent["agent_id"],
                agent["capabilities"],
                agent["groups"]
            )
    
    async def _cleanup_task(self, task_id: str) -> None:
        """清理任务"""
        try:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                if task["status"] == "running":
                    task["status"] = "cancelled"
                    task["completed_at"] = datetime.now()
                
                # 移除长时间完成的任务
                if task.get("completed_at"):
                    elapsed = (datetime.now() - task["completed_at"]).seconds
                    if elapsed > 300:  # 5分钟后清理
                        del self.active_tasks[task_id]
                        
        except Exception as e:
            logger.error(f"Error cleaning up task {task_id}: {e}")


# 全局实例管理
_coordinator_instance: Optional[AgentCoordinator] = None


async def get_coordinator() -> AgentCoordinator:
    """获取全局协调器实例"""
    global _coordinator_instance
    
    if _coordinator_instance is None:
        _coordinator_instance = AgentCoordinator()
        await _coordinator_instance.start()
    
    return _coordinator_instance


async def shutdown_coordinator() -> None:
    """关闭全局协调器"""
    global _coordinator_instance
    
    if _coordinator_instance:
        await _coordinator_instance.stop()
        _coordinator_instance = None