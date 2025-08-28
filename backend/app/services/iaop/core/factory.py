"""
IAOP服务工厂 - 依赖注入和服务管理

提供统一的服务创建、配置和生命周期管理
"""

import logging
from typing import Dict, Any, Optional, Type, TypeVar, Generic, Callable
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class ServiceConfig:
    """服务配置"""
    name: str
    service_class: Type
    singleton: bool = True
    lazy_init: bool = True
    dependencies: list = field(default_factory=list)
    init_params: Dict[str, Any] = field(default_factory=dict)
    lifecycle_hooks: Dict[str, Callable] = field(default_factory=dict)


@dataclass
class ServiceInstance:
    """服务实例"""
    instance: Any
    config: ServiceConfig
    created_at: datetime
    initialized: bool = False
    active: bool = True


class ServiceFactory:
    """服务工厂类 - 实现依赖注入和服务管理"""
    
    def __init__(self):
        self._services: Dict[str, ServiceInstance] = {}
        self._configs: Dict[str, ServiceConfig] = {}
        self._initialization_lock = asyncio.Lock()
        self._startup_completed = False
        
        logger.info("服务工厂初始化完成")

    def register_service(self, config: ServiceConfig) -> None:
        """注册服务配置"""
        self._configs[config.name] = config
        logger.info(f"注册服务: {config.name}")

    def register(self, name: str, service_class: Type, 
                singleton: bool = True, lazy_init: bool = True,
                dependencies: list = None, **init_params) -> None:
        """便捷的服务注册方法"""
        config = ServiceConfig(
            name=name,
            service_class=service_class,
            singleton=singleton,
            lazy_init=lazy_init,
            dependencies=dependencies or [],
            init_params=init_params
        )
        self.register_service(config)

    async def get_service(self, name: str) -> Any:
        """获取服务实例"""
        if name in self._services:
            service_instance = self._services[name]
            if service_instance.active:
                return service_instance.instance
        
        config = self._configs.get(name)
        if not config:
            raise ValueError(f"服务未注册: {name}")
        
        return await self._create_service_instance(config)

    async def _create_service_instance(self, config: ServiceConfig) -> Any:
        """创建服务实例"""
        async with self._initialization_lock:
            # 双重检查锁定
            if config.name in self._services:
                service_instance = self._services[config.name]
                if service_instance.active:
                    return service_instance.instance
            
            logger.info(f"创建服务实例: {config.name}")
            
            # 解析依赖
            dependencies = await self._resolve_dependencies(config.dependencies)
            
            # 创建实例
            try:
                # 合并依赖和初始化参数
                init_kwargs = {**config.init_params}
                for dep_name, dep_instance in dependencies.items():
                    init_kwargs[dep_name] = dep_instance
                
                instance = config.service_class(**init_kwargs)
                
                # 执行初始化钩子
                if 'on_init' in config.lifecycle_hooks:
                    await config.lifecycle_hooks['on_init'](instance)
                
                service_instance = ServiceInstance(
                    instance=instance,
                    config=config,
                    created_at=datetime.utcnow(),
                    initialized=True,
                    active=True
                )
                
                if config.singleton:
                    self._services[config.name] = service_instance
                
                logger.info(f"服务实例创建成功: {config.name}")
                return instance
                
            except Exception as e:
                logger.error(f"创建服务实例失败: {config.name}, 错误: {e}")
                raise

    async def _resolve_dependencies(self, dependencies: list) -> Dict[str, Any]:
        """解析服务依赖"""
        resolved_deps = {}
        
        for dep_name in dependencies:
            if isinstance(dep_name, str):
                resolved_deps[dep_name] = await self.get_service(dep_name)
            elif isinstance(dep_name, tuple):
                # 支持 (service_name, param_name) 格式
                service_name, param_name = dep_name
                resolved_deps[param_name] = await self.get_service(service_name)
        
        return resolved_deps

    async def initialize_all_services(self) -> None:
        """初始化所有非懒加载服务"""
        logger.info("开始初始化所有服务...")
        
        for name, config in self._configs.items():
            if not config.lazy_init:
                try:
                    await self.get_service(name)
                except Exception as e:
                    logger.error(f"初始化服务失败: {name}, 错误: {e}")
                    if not config.init_params.get('optional', False):
                        raise
        
        self._startup_completed = True
        logger.info("服务初始化完成")

    async def shutdown_all_services(self) -> None:
        """关闭所有服务"""
        logger.info("开始关闭所有服务...")
        
        for name, service_instance in self._services.items():
            try:
                # 执行关闭钩子
                if 'on_shutdown' in service_instance.config.lifecycle_hooks:
                    await service_instance.config.lifecycle_hooks['on_shutdown'](
                        service_instance.instance
                    )
                
                # 如果服务有异步关闭方法，调用它
                if hasattr(service_instance.instance, 'shutdown'):
                    if asyncio.iscoroutinefunction(service_instance.instance.shutdown):
                        await service_instance.instance.shutdown()
                    else:
                        service_instance.instance.shutdown()
                
                service_instance.active = False
                logger.info(f"服务已关闭: {name}")
                
            except Exception as e:
                logger.error(f"关闭服务失败: {name}, 错误: {e}")
        
        self._services.clear()
        self._startup_completed = False
        logger.info("所有服务已关闭")

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "total_registered": len(self._configs),
            "total_instances": len(self._services),
            "startup_completed": self._startup_completed,
            "services": {
                name: {
                    "active": instance.active,
                    "initialized": instance.initialized,
                    "created_at": instance.created_at.isoformat(),
                    "singleton": instance.config.singleton,
                    "dependencies": instance.config.dependencies
                }
                for name, instance in self._services.items()
            }
        }

    @asynccontextmanager
    async def service_lifecycle(self):
        """服务生命周期上下文管理器"""
        try:
            await self.initialize_all_services()
            yield self
        finally:
            await self.shutdown_all_services()


class IAOPServiceFactory(ServiceFactory):
    """IAOP专用服务工厂"""
    
    def __init__(self, config_manager=None):
        super().__init__()
        self.config_manager = config_manager
        if self.config_manager is None:
            from .config import get_config_manager, load_default_config
            self.config_manager = load_default_config()
        self._register_core_services()
        
    def _register_core_services(self):
        """注册核心服务"""
        from ..context.context_manager import IAOPContextManager
        from ..registry.agent_registry import IAOPAgentRegistry
        from ..orchestration.engine import OrchestrationEngine
        from ..api.services import IAOPService
        
        # 注册上下文管理器
        self.register(
            name="context_manager",
            service_class=IAOPContextManager,
            singleton=True,
            lazy_init=False
        )
        
        # 注册Agent注册器
        self.register(
            name="agent_registry",
            service_class=IAOPAgentRegistry,
            singleton=True,
            lazy_init=False
        )
        
        # 注册编排引擎
        self.register(
            name="orchestration_engine",
            service_class=OrchestrationEngine,
            singleton=True,
            lazy_init=True,
            dependencies=[
                ("context_manager", "context_manager"),
                ("agent_registry", "agent_registry")
            ]
        )
        
        # 注册IAOP服务
        self.register(
            name="iaop_service",
            service_class=IAOPService,
            singleton=True,
            lazy_init=True
        )
        
        logger.info("核心服务注册完成")

    async def setup_specialized_agents(self):
        """设置专业Agent"""
        try:
            from ..agents.specialized import register_all_specialized_agents
            registry = await self.get_service("agent_registry")
            
            # 确保Agent注册器已准备好
            if not hasattr(registry, 'register_agent'):
                raise RuntimeError("Agent注册器未正确初始化")
            
            # 注册专业Agent
            register_all_specialized_agents()
            logger.info("专业Agent设置完成")
            
        except Exception as e:
            logger.error(f"设置专业Agent失败: {e}")
            raise

    async def get_iaop_service(self):
        """获取IAOP主服务"""
        return await self.get_service("iaop_service")

    async def get_context_manager(self):
        """获取上下文管理器"""
        return await self.get_service("context_manager")

    async def get_agent_registry(self):
        """获取Agent注册器"""
        return await self.get_service("agent_registry")

    async def get_orchestration_engine(self):
        """获取编排引擎"""
        return await self.get_service("orchestration_engine")


# 全局服务工厂实例
_global_service_factory = None

def get_service_factory() -> IAOPServiceFactory:
    """获取全局服务工厂"""
    global _global_service_factory
    if _global_service_factory is None:
        _global_service_factory = IAOPServiceFactory()
    return _global_service_factory


async def initialize_iaop_services():
    """初始化IAOP服务"""
    factory = get_service_factory()
    
    try:
        # 初始化核心服务
        await factory.initialize_all_services()
        
        # 设置专业Agent
        await factory.setup_specialized_agents()
        
        logger.info("IAOP服务初始化完成")
        return factory
        
    except Exception as e:
        logger.error(f"IAOP服务初始化失败: {e}")
        raise


async def shutdown_iaop_services():
    """关闭IAOP服务"""
    factory = get_service_factory()
    await factory.shutdown_all_services()
    logger.info("IAOP服务已关闭")


# 便捷的依赖注入装饰器
def inject_service(service_name: str):
    """服务注入装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            factory = get_service_factory()
            service = await factory.get_service(service_name)
            return await func(service, *args, **kwargs)
        return wrapper
    return decorator


# 服务注册装饰器
def register_service(name: str, **config_kwargs):
    """服务注册装饰器"""
    def decorator(cls):
        factory = get_service_factory()
        factory.register(name=name, service_class=cls, **config_kwargs)
        return cls
    return decorator