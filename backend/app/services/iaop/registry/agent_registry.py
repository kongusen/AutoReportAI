"""
IAOP Agent注册器 - 管理所有智能体的注册和调度
"""

import logging
from typing import Dict, List, Optional, Type, Any
from dataclasses import dataclass

from ..agents.base import BaseAgent
from ..context.execution_context import EnhancedExecutionContext

logger = logging.getLogger(__name__)


@dataclass
class AgentRegistration:
    """Agent注册信息"""
    agent: BaseAgent
    priority: int = 50
    capabilities: List[str] = None
    requirements: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = getattr(self.agent, 'capabilities', [])
        if self.requirements is None:
            self.requirements = getattr(self.agent, '_context_requirements', [])
        if self.metadata is None:
            self.metadata = {}


class IAOPAgentRegistry:
    """IAOP架构的Agent注册器"""
    
    def __init__(self):
        self._agents: Dict[str, AgentRegistration] = {}
        self._capability_map: Dict[str, List[str]] = {}  # capability -> agent_names
        self._agent_chains: Dict[str, List[str]] = {}  # chain_name -> agent_names
        
    def register_agent(self, agent: BaseAgent, priority: int = 50, 
                      capabilities: List[str] = None, 
                      requirements: List[str] = None,
                      metadata: Dict[str, Any] = None) -> None:
        """注册Agent"""
        registration = AgentRegistration(
            agent=agent,
            priority=priority,
            capabilities=capabilities,
            requirements=requirements,
            metadata=metadata
        )
        
        self._agents[agent.name] = registration
        
        # 更新能力映射
        for capability in registration.capabilities:
            if capability not in self._capability_map:
                self._capability_map[capability] = []
            if agent.name not in self._capability_map[capability]:
                self._capability_map[capability].append(agent.name)
        
        logger.info(f"Registered agent: {agent.name} with capabilities: {registration.capabilities}")
    
    def unregister_agent(self, agent_name: str) -> None:
        """注销Agent"""
        if agent_name not in self._agents:
            return
        
        registration = self._agents[agent_name]
        
        # 从能力映射中移除
        for capability in registration.capabilities:
            if capability in self._capability_map:
                if agent_name in self._capability_map[capability]:
                    self._capability_map[capability].remove(agent_name)
                if not self._capability_map[capability]:
                    del self._capability_map[capability]
        
        # 从Agent链中移除
        for chain_name in list(self._agent_chains.keys()):
            if agent_name in self._agent_chains[chain_name]:
                self._agent_chains[chain_name].remove(agent_name)
                if not self._agent_chains[chain_name]:
                    del self._agent_chains[chain_name]
        
        del self._agents[agent_name]
        logger.info(f"Unregistered agent: {agent_name}")
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """获取Agent实例"""
        registration = self._agents.get(agent_name)
        return registration.agent if registration else None
    
    def get_agents_by_capability(self, capability: str) -> List[BaseAgent]:
        """根据能力获取Agent列表"""
        agent_names = self._capability_map.get(capability, [])
        agents = []
        
        for name in agent_names:
            registration = self._agents.get(name)
            if registration:
                agents.append(registration.agent)
        
        # 按优先级排序
        agents.sort(key=lambda a: self._agents[a.name].priority, reverse=True)
        return agents
    
    def can_handle_task(self, agent_name: str, context: EnhancedExecutionContext) -> bool:
        """检查Agent是否能处理任务"""
        registration = self._agents.get(agent_name)
        if not registration:
            return False
        
        # 检查前置条件
        try:
            # 这里是同步检查，实际的异步检查在执行时进行
            missing_requirements = [
                req for req in registration.requirements
                if context.get_context(req) is None
            ]
            return len(missing_requirements) == 0
        except Exception as e:
            logger.error(f"Error checking task compatibility for {agent_name}: {e}")
            return False
    
    def find_suitable_agents(self, required_capabilities: List[str], 
                           context: EnhancedExecutionContext) -> List[BaseAgent]:
        """查找适合的Agent列表"""
        suitable_agents = []
        
        for capability in required_capabilities:
            agents = self.get_agents_by_capability(capability)
            for agent in agents:
                if (agent not in suitable_agents and 
                    self.can_handle_task(agent.name, context)):
                    suitable_agents.append(agent)
        
        return suitable_agents
    
    def register_agent_chain(self, chain_name: str, agent_names: List[str]) -> None:
        """注册Agent执行链"""
        # 验证所有Agent都已注册
        missing_agents = [name for name in agent_names if name not in self._agents]
        if missing_agents:
            raise ValueError(f"Agents not registered: {missing_agents}")
        
        self._agent_chains[chain_name] = agent_names.copy()
        logger.info(f"Registered agent chain '{chain_name}': {agent_names}")
    
    def get_agent_chain(self, chain_name: str) -> List[BaseAgent]:
        """获取Agent执行链"""
        agent_names = self._agent_chains.get(chain_name, [])
        return [self.get_agent(name) for name in agent_names if self.get_agent(name)]
    
    def execute_agent_chain(self, chain_name: str, context: EnhancedExecutionContext) -> List[Dict[str, Any]]:
        """执行Agent链 - 同步版本，异步执行在各Agent内部处理"""
        agents = self.get_agent_chain(chain_name)
        if not agents:
            raise ValueError(f"Agent chain not found: {chain_name}")
        
        results = []
        for agent in agents:
            try:
                # 这里返回的是协程，需要在外部await
                results.append({
                    'agent': agent.name,
                    'execution_coroutine': agent.execute_with_tracking(context)
                })
            except Exception as e:
                logger.error(f"Error preparing execution for agent {agent.name}: {e}")
                results.append({
                    'agent': agent.name,
                    'error': str(e)
                })
        
        return results
    
    def get_registered_agents(self) -> List[str]:
        """获取所有已注册的Agent名称"""
        return list(self._agents.keys())
    
    def get_agent_info(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """获取Agent详细信息"""
        registration = self._agents.get(agent_name)
        if not registration:
            return None
        
        return {
            'name': agent_name,
            'priority': registration.priority,
            'capabilities': registration.capabilities,
            'requirements': registration.requirements,
            'metadata': registration.metadata,
            'class': type(registration.agent).__name__
        }
    
    def get_registry_status(self) -> Dict[str, Any]:
        """获取注册器状态"""
        return {
            'total_agents': len(self._agents),
            'agents': list(self._agents.keys()),
            'capabilities': list(self._capability_map.keys()),
            'chains': list(self._agent_chains.keys()),
            'capability_coverage': {
                cap: len(agents) for cap, agents in self._capability_map.items()
            }
        }


# 全局注册器实例
_global_iaop_registry = None

def get_iaop_agent_registry() -> IAOPAgentRegistry:
    """获取全局IAOP Agent注册器"""
    global _global_iaop_registry
    if _global_iaop_registry is None:
        _global_iaop_registry = IAOPAgentRegistry()
    return _global_iaop_registry


def register_default_agents():
    """注册默认的Agent集合"""
    registry = get_iaop_agent_registry()
    
    # 这里会在实际部署时注册所有Agent
    # 示例：
    # from ..agents.specialized.sql_generation_agent import SQLGenerationAgent
    # from ..agents.specialized.semantic_analyzer_agent import PlaceholderSemanticAnalyzerAgent
    # from ..agents.specialized.sql_quality_assessor_agent import SQLQualityAssessorAgent
    
    # registry.register_agent(
    #     SQLGenerationAgent("sql_generator"),
    #     priority=80,
    #     capabilities=["sql_generation", "placeholder_analysis"]
    # )
    
    logger.info("Default agents registration completed")


# 在模块导入时自动注册默认Agent
# register_default_agents()