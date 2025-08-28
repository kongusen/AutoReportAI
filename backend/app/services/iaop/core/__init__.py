"""
IAOP核心模块 - 服务工厂、配置管理、中间件系统

提供IAOP架构的核心基础设施
"""

from .factory import (
    ServiceFactory, 
    IAOPServiceFactory, 
    ServiceConfig,
    get_service_factory,
    initialize_iaop_services,
    shutdown_iaop_services,
    inject_service,
    register_service
)

# IAOP作为核心平台直接使用系统统一配置
from app.core.config import settings

# 简化的配置获取函数
def get_config():
    """获取系统配置"""
    return settings

def get_config_manager():
    """获取配置管理器（简化版）"""
    return settings

def load_default_config():
    """加载默认配置（使用系统配置）"""
    return settings

def config_required(func):
    """配置装饰器（简化版）"""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

from .middleware import (
    MiddlewareManager,
    BaseMiddleware,
    MiddlewareType,
    MiddlewareContext,
    get_middleware_manager
)

from .hooks import (
    HookManager,
    Hook,
    HookType,
    HookContext,
    get_hook_manager,
    setup_common_hooks
)

__all__ = [
    # 服务工厂
    'ServiceFactory',
    'IAOPServiceFactory', 
    'ServiceConfig',
    'get_service_factory',
    'initialize_iaop_services',
    'shutdown_iaop_services',
    'inject_service',
    'register_service',
    
    # 配置管理（简化版 - 直接使用系统配置）
    'settings',
    'get_config_manager', 
    'get_config',
    'load_default_config',
    'config_required',
    
    # 中间件
    'MiddlewareManager',
    'BaseMiddleware',
    'MiddlewareType',
    'MiddlewareContext',
    'get_middleware_manager',
    
    # 钩子系统
    'HookManager',
    'Hook',
    'HookType',
    'HookContext',
    'get_hook_manager',
    'setup_common_hooks'
]