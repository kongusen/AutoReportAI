"""
Agent Registry and Capability Discovery System

Agent注册和能力发现系统，支持：
1. 动态Agent注册和发现
2. 能力匹配和路由
3. Agent生命周期管理
4. 性能监控和负载均衡
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Set, Type, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod

from .context_manager import ContextAwareAgent, AgentContext, ContextManager

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent状态"""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class AgentCapability:
    """Agent能力描述"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    requirements: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def matches_requirements(self, available_resources: Set[str]) -> bool:
        """检查是否满足能力要求"""
        required_set = set(self.requirements)
        return required_set.issubset(available_resources)
    
    def has_tag(self, tag: str) -> bool:
        """检查是否有指定标签"""
        return tag in self.tags


@dataclass 
class AgentInstance:
    """Agent实例信息"""
    agent_id: str
    agent_class: str
    agent: ContextAwareAgent
    status: AgentStatus = AgentStatus.INITIALIZING
    capabilities: Dict[str, AgentCapability] = field(default_factory=dict)
    
    # 性能指标
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_activity: Optional[datetime] = None
    
    # 配置
    max_concurrent_requests: int = 10
    current_concurrent_requests: int = 0
    priority: int = 0  # 0为最高优先级
    
    def update_metrics(self, success: bool, response_time: float):
        """更新性能指标"""
        self.total_requests += 1
        self.last_activity = datetime.now()
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # 更新平均响应时间（指数移动平均）
        alpha = 0.1
        self.average_response_time = (
            alpha * response_time + 
            (1 - alpha) * self.average_response_time
        )
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    def can_accept_request(self) -> bool:
        """检查是否可以接受新请求"""
        return (
            self.status == AgentStatus.READY and
            self.current_concurrent_requests < self.max_concurrent_requests
        )


class AgentMatcher:
    """Agent匹配器"""
    
    def __init__(self):
        self.matching_strategies: Dict[str, Callable] = {
            'exact': self._exact_match,
            'fuzzy': self._fuzzy_match,
            'best_fit': self._best_fit_match
        }
    
    def find_matching_agents(self, 
                           agents: Dict[str, AgentInstance],
                           capability_name: str,
                           requirements: Dict[str, Any] = None,
                           strategy: str = 'best_fit') -> List[AgentInstance]:
        """查找匹配的Agent"""
        if strategy not in self.matching_strategies:
            strategy = 'best_fit'
        
        matcher = self.matching_strategies[strategy]
        return matcher(agents, capability_name, requirements or {})
    
    def _exact_match(self, agents: Dict[str, AgentInstance], 
                    capability_name: str, requirements: Dict[str, Any]) -> List[AgentInstance]:
        """精确匹配"""
        matches = []
        for agent_instance in agents.values():
            if capability_name in agent_instance.capabilities:
                capability = agent_instance.capabilities[capability_name]
                if capability.matches_requirements(set(requirements.get('resources', []))):
                    matches.append(agent_instance)
        return matches
    
    def _fuzzy_match(self, agents: Dict[str, AgentInstance],
                    capability_name: str, requirements: Dict[str, Any]) -> List[AgentInstance]:
        """模糊匹配"""
        matches = []
        keywords = capability_name.lower().split('_')
        
        for agent_instance in agents.values():
            for cap_name, capability in agent_instance.capabilities.items():
                # 检查能力名称相似度
                cap_keywords = cap_name.lower().split('_')
                if any(keyword in cap_keywords for keyword in keywords):
                    matches.append(agent_instance)
                    break
                
                # 检查标签匹配
                if any(keyword in capability.tags for keyword in keywords):
                    matches.append(agent_instance)
                    break
        
        return matches
    
    def _best_fit_match(self, agents: Dict[str, AgentInstance],
                       capability_name: str, requirements: Dict[str, Any]) -> List[AgentInstance]:
        """最佳匹配"""
        # 首先尝试精确匹配
        exact_matches = self._exact_match(agents, capability_name, requirements)
        if exact_matches:
            # 按性能指标排序
            return sorted(exact_matches, key=self._calculate_agent_score, reverse=True)
        
        # 如果没有精确匹配，尝试模糊匹配
        fuzzy_matches = self._fuzzy_match(agents, capability_name, requirements)
        return sorted(fuzzy_matches, key=self._calculate_agent_score, reverse=True)
    
    def _calculate_agent_score(self, agent_instance: AgentInstance) -> float:
        """计算Agent评分"""
        if not agent_instance.can_accept_request():
            return 0.0
        
        # 综合考虑成功率、响应时间、负载等因素
        success_rate = agent_instance.get_success_rate()
        load_factor = 1.0 - (agent_instance.current_concurrent_requests / 
                           max(agent_instance.max_concurrent_requests, 1))
        response_time_factor = 1.0 / (1.0 + agent_instance.average_response_time)
        
        # 优先级权重
        priority_factor = 1.0 / (agent_instance.priority + 1)
        
        score = (
            success_rate * 0.4 +
            load_factor * 0.3 + 
            response_time_factor * 0.2 +
            priority_factor * 0.1
        )
        
        return score


class AgentRegistry:
    """Agent注册表"""
    
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
        self.agents: Dict[str, AgentInstance] = {}
        self.matcher = AgentMatcher()
        self._health_check_interval = 30  # 秒
        self._health_check_task = None
        self._event_handlers: Dict[str, List[Callable]] = {}
        
        # 启动健康检查
        self._start_health_check()
    
    def register_agent(self, agent: ContextAwareAgent, 
                      agent_id: str = None,
                      priority: int = 0,
                      max_concurrent: int = 10) -> str:
        """注册Agent"""
        if agent_id is None:
            agent_id = f"{agent.name}_{datetime.now().timestamp()}"
        
        # 创建Agent实例
        instance = AgentInstance(
            agent_id=agent_id,
            agent_class=agent.__class__.__name__,
            agent=agent,
            priority=priority,
            max_concurrent_requests=max_concurrent
        )
        
        # 注册Agent的能力
        agent_capabilities = agent.get_capabilities()
        for cap_name, cap_info in agent_capabilities.items():
            capability = AgentCapability(
                name=cap_name,
                description=cap_info.get('description', ''),
                input_schema=cap_info.get('input_schema', {}),
                output_schema=cap_info.get('output_schema', {}),
                requirements=cap_info.get('requirements', []),
                tags=set(cap_info.get('tags', [])),
                metadata=cap_info.get('metadata', {})
            )
            instance.capabilities[cap_name] = capability
        
        self.agents[agent_id] = instance
        instance.status = AgentStatus.READY
        
        # 触发注册事件
        self._emit_event('agent_registered', {
            'agent_id': agent_id,
            'agent_class': instance.agent_class,
            'capabilities': list(instance.capabilities.keys())
        })
        
        logger.info(f"Agent registered: {agent_id} with capabilities: {list(instance.capabilities.keys())}")
        return agent_id
    
    def unregister_agent(self, agent_id: str):
        """注销Agent"""
        if agent_id in self.agents:
            instance = self.agents[agent_id]
            instance.status = AgentStatus.SHUTDOWN
            del self.agents[agent_id]
            
            # 触发注销事件
            self._emit_event('agent_unregistered', {'agent_id': agent_id})
            logger.info(f"Agent unregistered: {agent_id}")
    
    def find_agent(self, capability_name: str, 
                  requirements: Dict[str, Any] = None,
                  strategy: str = 'best_fit') -> Optional[AgentInstance]:
        """查找能提供指定能力的Agent"""
        matches = self.matcher.find_matching_agents(
            self.agents, capability_name, requirements, strategy
        )
        
        if matches:
            # 返回最佳匹配的可用Agent
            for agent_instance in matches:
                if agent_instance.can_accept_request():
                    return agent_instance
        
        return None
    
    def get_available_capabilities(self) -> Dict[str, List[str]]:
        """获取所有可用能力"""
        capabilities = {}
        for agent_id, instance in self.agents.items():
            if instance.status == AgentStatus.READY:
                for cap_name in instance.capabilities:
                    if cap_name not in capabilities:
                        capabilities[cap_name] = []
                    capabilities[cap_name].append(agent_id)
        return capabilities
    
    async def execute_capability(self, capability_name: str,
                               session_id: str,
                               parameters: Dict[str, Any] = None,
                               requirements: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行指定能力"""
        # 查找合适的Agent
        agent_instance = self.find_agent(capability_name, requirements)
        if not agent_instance:
            raise ValueError(f"No available agent found for capability: {capability_name}")
        
        # 确保上下文存在
        context = self.context_manager.get_context(session_id)
        if not context:
            # 创建新的上下文
            context = self.context_manager.create_context(
                session_id=session_id,
                task_id=f"capability_{capability_name}",
                user_id=parameters.get('user_id') if parameters else None
            )
        
        # 更新并发计数
        agent_instance.current_concurrent_requests += 1
        agent_instance.status = AgentStatus.BUSY
        
        start_time = datetime.now()
        success = False
        
        try:
            # 执行Agent操作
            result = await agent_instance.agent.execute_with_context(
                session_id, capability_name, parameters
            )
            success = True
            return result
            
        except Exception as e:
            logger.error(f"Agent execution failed: {agent_instance.agent_id}, error: {e}")
            raise
            
        finally:
            # 更新指标
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            agent_instance.update_metrics(success, response_time)
            
            # 恢复状态
            agent_instance.current_concurrent_requests -= 1
            if agent_instance.current_concurrent_requests == 0:
                agent_instance.status = AgentStatus.READY
    
    def get_agent_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有Agent状态"""
        status = {}
        for agent_id, instance in self.agents.items():
            status[agent_id] = {
                'status': instance.status.value,
                'capabilities': list(instance.capabilities.keys()),
                'total_requests': instance.total_requests,
                'success_rate': instance.get_success_rate(),
                'average_response_time': instance.average_response_time,
                'current_load': instance.current_concurrent_requests,
                'max_concurrent': instance.max_concurrent_requests,
                'last_activity': instance.last_activity.isoformat() if instance.last_activity else None
            }
        return status
    
    def on_event(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """触发事件"""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.warning(f"Event handler failed: {event_type}, error: {e}")
    
    def _start_health_check(self):
        """启动健康检查任务"""
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._perform_health_check()
            except Exception as e:
                logger.error(f"Health check failed: {e}")
    
    async def _perform_health_check(self):
        """执行健康检查"""
        current_time = datetime.now()
        inactive_threshold = timedelta(minutes=30)
        
        inactive_agents = []
        for agent_id, instance in self.agents.items():
            # 检查长时间无活动的Agent
            if (instance.last_activity and 
                current_time - instance.last_activity > inactive_threshold):
                inactive_agents.append(agent_id)
            
            # 检查错误率过高的Agent
            if (instance.total_requests > 10 and 
                instance.get_success_rate() < 0.5):
                logger.warning(f"Agent {agent_id} has low success rate: {instance.get_success_rate()}")
        
        # 记录非活跃Agent
        if inactive_agents:
            logger.info(f"Inactive agents detected: {inactive_agents}")
    
    def shutdown(self):
        """关闭注册表"""
        if self._health_check_task:
            self._health_check_task.cancel()
        
        # 关闭所有Agent
        for agent_id in list(self.agents.keys()):
            self.unregister_agent(agent_id)


# 全局Agent注册表实例
_global_agent_registry = None

def get_agent_registry(context_manager: ContextManager = None) -> AgentRegistry:
    """获取全局Agent注册表"""
    global _global_agent_registry
    if _global_agent_registry is None:
        if context_manager is None:
            from .context_manager import get_context_manager
            context_manager = get_context_manager()
        _global_agent_registry = AgentRegistry(context_manager)
    return _global_agent_registry