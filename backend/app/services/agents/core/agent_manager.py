"""
智能代理管理器
负责协调多个专业化代理的工作流程
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum

from .react_agent import ReactIntelligentAgent
from .tools_registry import get_tools_registry, FunctionToolsRegistry
from ..tools.tools_factory import create_tool_combination, get_available_combinations

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """代理类型枚举"""
    GENERAL = "general"
    PLACEHOLDER_EXPERT = "placeholder_expert"
    CHART_SPECIALIST = "chart_specialist"
    DATA_ANALYST = "data_analyst"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    URGENT = "urgent"


class AgentStatus(Enum):
    """代理状态枚举"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class IntelligentAgentManager:
    """
    智能代理管理器
    - 管理多个专业化代理实例
    - 根据任务类型智能路由
    - 负载均衡和故障恢复
    - 统计和监控
    """
    
    def __init__(self, max_concurrent_tasks: int = 5):
        self.agents: Dict[AgentType, List[ReactIntelligentAgent]] = {}
        self.agent_status: Dict[str, AgentStatus] = {}
        self.task_queue = asyncio.Queue()
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.tools_registry: Optional[FunctionToolsRegistry] = None
        
        # 统计信息
        self.stats = {
            "total_tasks_processed": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "agent_usage": {},
            "average_response_time": 0.0
        }
        
        self.initialized = False
        self._shutdown_event = asyncio.Event()
    
    async def initialize(self):
        """初始化代理管理器"""
        if self.initialized:
            return
        
        logger.info("初始化智能代理管理器...")
        
        try:
            # 初始化工具注册中心
            self.tools_registry = await get_tools_registry()
            
            # 创建专业化代理
            await self._create_specialized_agents()
            
            # 启动任务处理循环
            asyncio.create_task(self._task_processing_loop())
            
            self.initialized = True
            logger.info(f"代理管理器初始化完成 - 总代理数: {sum(len(agents) for agents in self.agents.values())}")
            
        except Exception as e:
            logger.error(f"代理管理器初始化失败: {e}")
            raise
    
    async def _create_specialized_agents(self):
        """创建专业化代理"""
        agent_configs = {
            AgentType.GENERAL: {
                "count": 2,
                "tool_combination": "complete_workflow",
                "system_prompt": "你是一个通用智能助手，能够处理各种分析和数据处理任务。"
            },
            AgentType.PLACEHOLDER_EXPERT: {
                "count": 2,
                "tool_combination": "placeholder_processing",
                "system_prompt": "你是占位符分析专家，专门负责模板占位符的提取、分析和替换。"
            },
            AgentType.CHART_SPECIALIST: {
                "count": 1,
                "tool_combination": "visualization",
                "system_prompt": "你是数据可视化专家，专门负责图表生成、优化和推荐。"
            },
            AgentType.DATA_ANALYST: {
                "count": 2,
                "tool_combination": "data_analysis",
                "system_prompt": "你是数据分析专家，专门负责数据源分析、SQL生成和质量评估。"
            }
        }
        
        for agent_type, config in agent_configs.items():
            agents = []
            
            for i in range(config["count"]):
                try:
                    # 获取专门工具集合
                    tools = await create_tool_combination(config["tool_combination"])
                    
                    # 创建代理实例
                    agent_id = f"{agent_type.value}_{i+1}"
                    agent = ReactIntelligentAgent(
                        agent_id=agent_id,
                        system_prompt=config["system_prompt"],
                        tools=tools,
                        max_iterations=10,
                        verbose=True
                    )
                    
                    await agent.initialize()
                    agents.append(agent)
                    self.agent_status[agent_id] = AgentStatus.IDLE
                    
                    logger.info(f"创建代理: {agent_id}")
                    
                except Exception as e:
                    logger.error(f"创建代理 {agent_type.value}_{i+1} 失败: {e}")
                    continue
            
            self.agents[agent_type] = agents
            
            # 初始化使用统计
            self.stats["agent_usage"][agent_type.value] = {
                "total_tasks": 0,
                "successful_tasks": 0,
                "failed_tasks": 0,
                "average_response_time": 0.0
            }
    
    async def execute_task(
        self,
        task_content: str,
        task_type: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            task_content: 任务内容
            task_type: 任务类型，用于智能路由
            priority: 任务优先级
            context: 任务上下文
            
        Returns:
            任务执行结果
        """
        if not self.initialized:
            await self.initialize()
        
        task_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        logger.info(f"接收任务 {task_id}: {task_type or 'auto'}")
        
        try:
            # 选择合适的代理
            selected_agent = await self._select_agent(task_content, task_type)
            
            if not selected_agent:
                raise RuntimeError("没有可用的代理处理此任务")
            
            # 记录任务开始
            self.active_tasks[task_id] = {
                "agent_id": selected_agent.agent_id,
                "start_time": start_time,
                "task_type": task_type,
                "priority": priority.value,
                "status": "executing"
            }
            
            # 更新代理状态
            self.agent_status[selected_agent.agent_id] = AgentStatus.BUSY
            
            # 执行任务
            result = await selected_agent.execute_task(
                task_description=task_content,
                context=context or {}
            )
            
            # 计算执行时间
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 更新统计信息
            await self._update_task_stats(selected_agent.agent_id, True, execution_time)
            
            # 清理任务记录
            self.agent_status[selected_agent.agent_id] = AgentStatus.IDLE
            del self.active_tasks[task_id]
            
            logger.info(f"任务 {task_id} 执行完成，耗时: {execution_time:.2f}s")
            
            return {
                "task_id": task_id,
                "success": True,
                "result": result,
                "execution_time": execution_time,
                "agent_used": selected_agent.agent_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"任务 {task_id} 执行失败: {e}")
            
            # 更新失败统计
            if task_id in self.active_tasks:
                agent_id = self.active_tasks[task_id]["agent_id"]
                await self._update_task_stats(agent_id, False, 0)
                self.agent_status[agent_id] = AgentStatus.IDLE
                del self.active_tasks[task_id]
            
            return {
                "task_id": task_id,
                "success": False,
                "error": str(e),
                "execution_time": (datetime.utcnow() - start_time).total_seconds(),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _select_agent(
        self,
        task_content: str,
        task_type: Optional[str] = None
    ) -> Optional[ReactIntelligentAgent]:
        """智能选择最适合的代理"""
        
        # 如果指定了任务类型，优先选择对应专业代理
        if task_type:
            agent_type_mapping = {
                "placeholder": AgentType.PLACEHOLDER_EXPERT,
                "chart": AgentType.CHART_SPECIALIST,
                "visualization": AgentType.CHART_SPECIALIST,
                "data": AgentType.DATA_ANALYST,
                "sql": AgentType.DATA_ANALYST,
                "analysis": AgentType.DATA_ANALYST
            }
            
            preferred_type = agent_type_mapping.get(task_type.lower(), AgentType.GENERAL)
        else:
            # 基于任务内容智能推断类型
            preferred_type = self._infer_agent_type(task_content)
        
        # 查找可用的对应类型代理
        available_agents = []
        for agent in self.agents.get(preferred_type, []):
            if self.agent_status[agent.agent_id] == AgentStatus.IDLE:
                available_agents.append(agent)
        
        # 如果专业代理不可用，回退到通用代理
        if not available_agents and preferred_type != AgentType.GENERAL:
            for agent in self.agents.get(AgentType.GENERAL, []):
                if self.agent_status[agent.agent_id] == AgentStatus.IDLE:
                    available_agents.append(agent)
        
        # 选择负载最低的代理
        if available_agents:
            return min(
                available_agents,
                key=lambda a: self.stats["agent_usage"].get(
                    a.agent_id.split('_')[0], {}
                ).get("total_tasks", 0)
            )
        
        return None
    
    def _infer_agent_type(self, task_content: str) -> AgentType:
        """基于任务内容推断代理类型"""
        content_lower = task_content.lower()
        
        # 占位符相关关键词
        placeholder_keywords = ["占位符", "placeholder", "模板", "template", "替换", "replace"]
        if any(keyword in content_lower for keyword in placeholder_keywords):
            return AgentType.PLACEHOLDER_EXPERT
        
        # 图表相关关键词
        chart_keywords = ["图表", "chart", "可视化", "visualization", "绘图", "plot"]
        if any(keyword in content_lower for keyword in chart_keywords):
            return AgentType.CHART_SPECIALIST
        
        # 数据分析相关关键词
        data_keywords = ["数据", "data", "sql", "查询", "query", "分析", "analysis"]
        if any(keyword in content_lower for keyword in data_keywords):
            return AgentType.DATA_ANALYST
        
        return AgentType.GENERAL
    
    async def _update_task_stats(self, agent_id: str, success: bool, execution_time: float):
        """更新任务统计信息"""
        agent_type = agent_id.split('_')[0]
        
        # 更新总体统计
        self.stats["total_tasks_processed"] += 1
        if success:
            self.stats["successful_tasks"] += 1
        else:
            self.stats["failed_tasks"] += 1
        
        # 更新平均响应时间
        total_time = self.stats["average_response_time"] * (self.stats["total_tasks_processed"] - 1)
        self.stats["average_response_time"] = (total_time + execution_time) / self.stats["total_tasks_processed"]
        
        # 更新代理使用统计
        if agent_type in self.stats["agent_usage"]:
            agent_stats = self.stats["agent_usage"][agent_type]
            agent_stats["total_tasks"] += 1
            
            if success:
                agent_stats["successful_tasks"] += 1
            else:
                agent_stats["failed_tasks"] += 1
            
            # 更新代理平均响应时间
            if agent_stats["total_tasks"] > 0:
                total_agent_time = agent_stats["average_response_time"] * (agent_stats["total_tasks"] - 1)
                agent_stats["average_response_time"] = (total_agent_time + execution_time) / agent_stats["total_tasks"]
    
    async def _task_processing_loop(self):
        """任务处理循环（预留用于队列模式）"""
        while not self._shutdown_event.is_set():
            try:
                # 这里可以实现基于队列的任务处理
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"任务处理循环错误: {e}")
    
    async def get_manager_status(self) -> Dict[str, Any]:
        """获取管理器状态"""
        agent_status_summary = {}
        for agent_type, agents in self.agents.items():
            agent_status_summary[agent_type.value] = {
                "total_agents": len(agents),
                "idle_agents": sum(1 for agent in agents if self.agent_status[agent.agent_id] == AgentStatus.IDLE),
                "busy_agents": sum(1 for agent in agents if self.agent_status[agent.agent_id] == AgentStatus.BUSY),
                "error_agents": sum(1 for agent in agents if self.agent_status[agent.agent_id] == AgentStatus.ERROR)
            }
        
        return {
            "manager_status": "running" if self.initialized else "not_initialized",
            "total_agents": sum(len(agents) for agents in self.agents.values()),
            "active_tasks": len(self.active_tasks),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "agent_status_summary": agent_status_summary,
            "performance_stats": self.stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_agent_health(self) -> Dict[str, Any]:
        """获取所有代理健康状态"""
        health_results = {}
        
        for agent_type, agents in self.agents.items():
            health_results[agent_type.value] = []
            
            for agent in agents:
                try:
                    health = await agent.health_check()
                    health_results[agent_type.value].append({
                        "agent_id": agent.agent_id,
                        "status": self.agent_status[agent.agent_id].value,
                        "health": health
                    })
                except Exception as e:
                    health_results[agent_type.value].append({
                        "agent_id": agent.agent_id,
                        "status": "error",
                        "error": str(e)
                    })
        
        return health_results
    
    async def restart_agent(self, agent_id: str) -> bool:
        """重启指定代理"""
        try:
            # 查找代理
            target_agent = None
            agent_type = None
            
            for atype, agents in self.agents.items():
                for agent in agents:
                    if agent.agent_id == agent_id:
                        target_agent = agent
                        agent_type = atype
                        break
                if target_agent:
                    break
            
            if not target_agent:
                logger.error(f"未找到代理: {agent_id}")
                return False
            
            # 标记维护状态
            self.agent_status[agent_id] = AgentStatus.MAINTENANCE
            
            # 重新初始化代理
            await target_agent.initialize()
            
            # 恢复空闲状态
            self.agent_status[agent_id] = AgentStatus.IDLE
            
            logger.info(f"代理 {agent_id} 重启成功")
            return True
            
        except Exception as e:
            logger.error(f"代理 {agent_id} 重启失败: {e}")
            self.agent_status[agent_id] = AgentStatus.ERROR
            return False
    
    async def shutdown(self):
        """关闭代理管理器"""
        logger.info("正在关闭代理管理器...")
        
        self._shutdown_event.set()
        
        # 等待所有活跃任务完成
        while self.active_tasks:
            logger.info(f"等待 {len(self.active_tasks)} 个任务完成...")
            await asyncio.sleep(1)
        
        # 关闭所有代理
        for agents in self.agents.values():
            for agent in agents:
                try:
                    # 这里可以添加代理特定的清理逻辑
                    pass
                except Exception as e:
                    logger.error(f"关闭代理 {agent.agent_id} 时出错: {e}")
        
        logger.info("代理管理器已关闭")


# 全局代理管理器实例
_global_agent_manager: Optional[IntelligentAgentManager] = None


async def get_agent_manager() -> IntelligentAgentManager:
    """获取全局代理管理器实例"""
    global _global_agent_manager
    if _global_agent_manager is None:
        _global_agent_manager = IntelligentAgentManager()
        await _global_agent_manager.initialize()
    return _global_agent_manager


# 便捷函数
async def execute_agent_task(
    task_content: str,
    task_type: Optional[str] = None,
    priority: str = "medium",
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """执行代理任务的便捷函数"""
    manager = await get_agent_manager()
    priority_enum = TaskPriority(priority.lower())
    return await manager.execute_task(task_content, task_type, priority_enum, context)


async def get_agents_status() -> Dict[str, Any]:
    """获取代理状态的便捷函数"""
    manager = await get_agent_manager()
    return await manager.get_manager_status()


async def get_agents_health() -> Dict[str, Any]:
    """获取代理健康状态的便捷函数"""
    manager = await get_agent_manager()
    return await manager.get_agent_health()