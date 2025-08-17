"""
Agent工厂模式
提供智能的Agent创建和依赖注入管理
"""

import logging
from typing import Dict, Type, Optional, Any, TypeVar, Generic
from sqlalchemy.orm import Session
from enum import Enum
from dataclasses import dataclass

from .core_types import BaseAgent, AgentType, AgentConfig
from .core.session_manager import session_manager, ensure_session
from .base.base_analysis_agent import BaseAnalysisAgent

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseAgent)


class AgentCreationMode(Enum):
    """Agent创建模式"""
    STATELESS = "stateless"  # 无状态，每次创建新实例
    SINGLETON = "singleton"   # 单例模式，复用实例
    SESSION_SCOPED = "session_scoped"  # 会话范围，同一会话复用


@dataclass
class AgentFactoryConfig:
    """Agent工厂配置"""
    creation_mode: AgentCreationMode = AgentCreationMode.STATELESS
    enable_health_check: bool = True
    auto_session_management: bool = True
    default_timeout: int = 300
    enable_metrics: bool = True


class AgentFactory:
    """智能Agent工厂"""
    
    def __init__(self, config: Optional[AgentFactoryConfig] = None):
        self.config = config or AgentFactoryConfig()
        self.logger = logging.getLogger(__name__)
        
        # Agent类型注册表
        self._agent_classes: Dict[AgentType, Type[BaseAgent]] = {}
        
        # 单例实例缓存
        self._singleton_instances: Dict[str, BaseAgent] = {}
        
        # 会话范围实例缓存
        self._session_scoped_instances: Dict[str, Dict[str, BaseAgent]] = {}
        
        # 注册内置Agent类型
        self._register_builtin_agents()
    
    def _register_builtin_agents(self):
        """注册内置Agent类型"""
        try:
            # 基础分析Agent
            self._agent_classes[AgentType.ANALYSIS] = BaseAnalysisAgent
            
            # 导入其他专门的Agent类
            from .specialized.schema_analysis_agent import SchemaAnalysisAgent
            from .specialized.data_query_agent import DataQueryAgent
            from .specialized.content_generation_agent import ContentGenerationAgent
            from .specialized.visualization_agent import VisualizationAgent
            
            self._agent_classes[AgentType.SCHEMA_ANALYSIS] = SchemaAnalysisAgent
            self._agent_classes[AgentType.DATA_QUERY] = DataQueryAgent
            self._agent_classes[AgentType.CONTENT_GENERATION] = ContentGenerationAgent
            self._agent_classes[AgentType.VISUALIZATION] = VisualizationAgent
            
            self.logger.info(f"Registered {len(self._agent_classes)} agent types")
            
        except ImportError as e:
            self.logger.warning(f"Some agent types could not be imported: {e}")
    
    def register_agent_class(self, agent_type: AgentType, agent_class: Type[BaseAgent]):
        """注册新的Agent类型"""
        self._agent_classes[agent_type] = agent_class
        self.logger.info(f"Registered agent class: {agent_type.value} -> {agent_class.__name__}")
    
    def create_agent(
        self,
        agent_type: AgentType,
        db_session: Optional[Session] = None,
        config: Optional[AgentConfig] = None,
        creation_mode: Optional[AgentCreationMode] = None,
        **kwargs
    ) -> BaseAgent:
        """
        创建Agent实例
        
        Args:
            agent_type: Agent类型
            db_session: 数据库会话
            config: Agent配置
            creation_mode: 创建模式
            **kwargs: 其他参数
            
        Returns:
            Agent实例
        """
        if agent_type not in self._agent_classes:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        # 确定创建模式
        mode = creation_mode or self.config.creation_mode
        
        # 生成实例键
        instance_key = self._generate_instance_key(agent_type, config, kwargs)
        
        # 根据创建模式获取或创建实例
        if mode == AgentCreationMode.SINGLETON:
            return self._get_or_create_singleton(instance_key, agent_type, db_session, config, **kwargs)
        elif mode == AgentCreationMode.SESSION_SCOPED:
            session_id = id(db_session) if db_session else "default"
            return self._get_or_create_session_scoped(session_id, instance_key, agent_type, db_session, config, **kwargs)
        else:
            return self._create_new_instance(agent_type, db_session, config, **kwargs)
    
    def _generate_instance_key(self, agent_type: AgentType, config: Optional[AgentConfig], kwargs: Dict[str, Any]) -> str:
        """生成实例键"""
        key_parts = [agent_type.value]
        
        if config:
            key_parts.append(f"config_{config.agent_id}")
        
        # 添加关键参数到键中
        for key, value in sorted(kwargs.items()):
            if key not in ['db_session']:  # 排除会话相关参数
                key_parts.append(f"{key}_{hash(str(value))}")
        
        return "_".join(key_parts)
    
    def _get_or_create_singleton(
        self,
        instance_key: str,
        agent_type: AgentType,
        db_session: Optional[Session],
        config: Optional[AgentConfig],
        **kwargs
    ) -> BaseAgent:
        """获取或创建单例实例"""
        if instance_key not in self._singleton_instances:
            self._singleton_instances[instance_key] = self._create_new_instance(
                agent_type, db_session, config, **kwargs
            )
            self.logger.debug(f"Created singleton agent: {instance_key}")
        else:
            self.logger.debug(f"Reusing singleton agent: {instance_key}")
        
        return self._singleton_instances[instance_key]
    
    def _get_or_create_session_scoped(
        self,
        session_id: str,
        instance_key: str,
        agent_type: AgentType,
        db_session: Optional[Session],
        config: Optional[AgentConfig],
        **kwargs
    ) -> BaseAgent:
        """获取或创建会话范围实例"""
        if session_id not in self._session_scoped_instances:
            self._session_scoped_instances[session_id] = {}
        
        session_cache = self._session_scoped_instances[session_id]
        
        if instance_key not in session_cache:
            session_cache[instance_key] = self._create_new_instance(
                agent_type, db_session, config, **kwargs
            )
            self.logger.debug(f"Created session-scoped agent: {session_id}/{instance_key}")
        else:
            self.logger.debug(f"Reusing session-scoped agent: {session_id}/{instance_key}")
        
        return session_cache[instance_key]
    
    def _create_new_instance(
        self,
        agent_type: AgentType,
        db_session: Optional[Session],
        config: Optional[AgentConfig],
        **kwargs
    ) -> BaseAgent:
        """创建新的Agent实例"""
        agent_class = self._agent_classes[agent_type]
        
        # 智能会话管理
        if self.config.auto_session_management:
            db_session = ensure_session(db_session)
        
        # 创建实例
        try:
            # 检查构造函数参数
            import inspect
            sig = inspect.signature(agent_class.__init__)
            params = sig.parameters
            
            # 构建参数字典
            init_kwargs = kwargs.copy()
            
            if 'db_session' in params:
                init_kwargs['db_session'] = db_session
            if 'config' in params and config:
                init_kwargs['config'] = config
            if 'suppress_ai_warning' in params:
                init_kwargs['suppress_ai_warning'] = db_session is None
            
            # 过滤不支持的参数
            filtered_kwargs = {
                k: v for k, v in init_kwargs.items() 
                if k in params or params.get(list(params.keys())[-1], None) and params[list(params.keys())[-1]].kind == inspect.Parameter.VAR_KEYWORD
            }
            
            agent = agent_class(**filtered_kwargs)
            
            self.logger.debug(f"Created new agent instance: {agent_type.value}")
            
            # 健康检查
            if self.config.enable_health_check:
                self._perform_health_check(agent)
            
            return agent
            
        except Exception as e:
            self.logger.error(f"Failed to create agent {agent_type.value}: {e}")
            raise
    
    def _perform_health_check(self, agent: BaseAgent):
        """执行Agent健康检查"""
        try:
            import asyncio
            
            # 对于同步上下文，我们只做基本检查
            if hasattr(agent, 'health_check'):
                # 这里我们不能直接调用异步方法，所以只记录
                self.logger.debug(f"Agent {agent.agent_id} created successfully")
            
        except Exception as e:
            self.logger.warning(f"Health check failed for agent {agent.agent_id}: {e}")
    
    def cleanup_session_cache(self, session_id: str):
        """清理会话缓存"""
        if session_id in self._session_scoped_instances:
            del self._session_scoped_instances[session_id]
            self.logger.debug(f"Cleaned up session cache: {session_id}")
    
    def get_factory_stats(self) -> Dict[str, Any]:
        """获取工厂统计信息"""
        return {
            "registered_agent_types": list(self._agent_classes.keys()),
            "singleton_instances": len(self._singleton_instances),
            "session_scoped_sessions": len(self._session_scoped_instances),
            "total_session_scoped_instances": sum(
                len(instances) for instances in self._session_scoped_instances.values()
            ),
            "config": {
                "creation_mode": self.config.creation_mode.value,
                "auto_session_management": self.config.auto_session_management,
                "enable_health_check": self.config.enable_health_check,
            }
        }


# 全局Agent工厂实例
_global_factory: Optional[AgentFactory] = None


def get_agent_factory(config: Optional[AgentFactoryConfig] = None) -> AgentFactory:
    """获取全局Agent工厂实例"""
    global _global_factory
    if _global_factory is None:
        _global_factory = AgentFactory(config)
    return _global_factory


def create_agent(
    agent_type: AgentType,
    db_session: Optional[Session] = None,
    config: Optional[AgentConfig] = None,
    **kwargs
) -> BaseAgent:
    """便捷的Agent创建函数"""
    factory = get_agent_factory()
    return factory.create_agent(agent_type, db_session, config, **kwargs)


def create_analysis_agent(
    db_session: Optional[Session] = None,
    **kwargs
) -> BaseAnalysisAgent:
    """创建分析Agent的便捷函数"""
    agent = create_agent(AgentType.ANALYSIS, db_session, **kwargs)
    return agent  # type: ignore