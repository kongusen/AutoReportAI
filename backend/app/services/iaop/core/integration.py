"""
IAOP配置集成模块 - 连接配置系统与其他模块

提供配置驱动的服务初始化和管理
"""

import logging
from typing import Optional
from contextlib import asynccontextmanager

# 使用系统配置替代
from app.core.config import settings
from .factory import IAOPServiceFactory, get_service_factory
from .middleware import get_middleware_manager
from .hooks import get_hook_manager, setup_common_hooks

logger = logging.getLogger(__name__)


class IAOPIntegrator:
    """IAOP集成器 - 统一管理配置、服务、中间件和钩子"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager or settings
        self.service_factory: Optional[IAOPServiceFactory] = None
        self.middleware_manager = None
        self.hook_manager = None
        self._initialized = False
        
        logger.info("IAOP集成器初始化完成")
    
    async def initialize(self) -> None:
        """初始化所有组件"""
        if self._initialized:
            logger.warning("IAOP集成器已经初始化")
            return
        
        try:
            # 初始化服务工厂
            self.service_factory = IAOPServiceFactory(self.config_manager)
            
            # 初始化中间件管理器
            self.middleware_manager = get_middleware_manager()
            
            # 初始化钩子管理器
            self.hook_manager = get_hook_manager()
            setup_common_hooks()
            
            # 应用配置到各个组件
            await self._apply_configuration()
            
            # 初始化服务
            await self.service_factory.initialize_all_services()
            
            self._initialized = True
            logger.info("IAOP集成器初始化完成")
            
        except Exception as e:
            logger.error(f"IAOP集成器初始化失败: {e}")
            raise
    
    async def _apply_configuration(self) -> None:
        """应用配置到各个组件"""
        config = self.config_manager.config
        
        # 应用系统配置
        if config.system.performance_monitoring:
            logger.info("启用性能监控")
        
        if config.system.metrics_collection:
            logger.info("启用指标收集")
        
        # 应用Agent配置
        logger.info(f"Agent配置应用完成，最大并发: {config.agent.max_concurrent_agents}")
        
        # 应用API配置
        logger.info(f"API配置应用完成，端口: {config.api.port}")
    
    async def shutdown(self) -> None:
        """关闭所有组件"""
        if not self._initialized:
            return
        
        try:
            if self.service_factory:
                await self.service_factory.shutdown_all_services()
            
            self._initialized = False
            logger.info("IAOP集成器已关闭")
            
        except Exception as e:
            logger.error(f"IAOP集成器关闭失败: {e}")
            raise
    
    def get_config(self):
        """获取配置"""
        return self.config_manager.config
    
    def get_service_factory(self):
        """获取服务工厂"""
        return self.service_factory
    
    def get_middleware_manager(self):
        """获取中间件管理器"""
        return self.middleware_manager
    
    def get_hook_manager(self):
        """获取钩子管理器"""
        return self.hook_manager
    
    def get_system_status(self):
        """获取系统状态"""
        if not self._initialized:
            return {
                "status": "not_initialized",
                "components": {}
            }
        
        status = {
            "status": "running",
            "initialized": self._initialized,
            "components": {
                "config_manager": {
                    "loaded_files": self.config_manager._loaded_files,
                    "config_entries": len(self.config_manager.config_entries)
                }
            }
        }
        
        if self.service_factory:
            status["components"]["service_factory"] = self.service_factory.get_service_status()
        
        if self.middleware_manager:
            status["components"]["middleware_manager"] = self.middleware_manager.get_middleware_status()
        
        if self.hook_manager:
            status["components"]["hook_manager"] = self.hook_manager.get_hook_stats()
        
        return status
    
    @asynccontextmanager
    async def lifecycle(self):
        """生命周期上下文管理器"""
        try:
            await self.initialize()
            yield self
        finally:
            await self.shutdown()


# 全局集成器实例
_global_integrator = None

def get_iaop_integrator() -> IAOPIntegrator:
    """获取全局IAOP集成器"""
    global _global_integrator
    if _global_integrator is None:
        _global_integrator = IAOPIntegrator()
    return _global_integrator


async def initialize_iaop_system(config_path: Optional[str] = None) -> IAOPIntegrator:
    """初始化完整的IAOP系统"""
    # 简化配置处理，直接使用系统配置
    integrator = IAOPIntegrator(settings)
    if False:  # 保持原有逻辑结构
        integrator = get_iaop_integrator()
    
    await integrator.initialize()
    return integrator


async def shutdown_iaop_system():
    """关闭IAOP系统"""
    integrator = get_iaop_integrator()
    await integrator.shutdown()


# 配置更新通知
async def notify_config_updated(config_key: str, new_value):
    """通知配置已更新"""
    integrator = get_iaop_integrator()
    if integrator.hook_manager:
        await integrator.hook_manager.trigger_hook(
            hook_type=integrator.hook_manager.HookType.CONTEXT_UPDATE,
            source="config_manager",
            data={
                "config_key": config_key,
                "new_value": new_value,
                "event_type": "config_updated"
            }
        )


# 便捷装饰器
def with_iaop_context(func):
    """IAOP上下文装饰器"""
    async def wrapper(*args, **kwargs):
        integrator = get_iaop_integrator()
        if not integrator._initialized:
            await integrator.initialize()
        
        return await func(integrator, *args, **kwargs)
    
    return wrapper