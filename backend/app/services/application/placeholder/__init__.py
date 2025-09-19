"""
占位符应用层模块

提供占位符相关的应用服务和业务流程编排
"""

from .placeholder_service import (
    PlaceholderApplicationService,
    get_placeholder_service,
    shutdown_placeholder_service,
    
    # 兼容性函数
    analyze_placeholder,
    update_placeholder,
    complete_placeholder,
    analyze_placeholder_simple,
    update_placeholder_simple,
    complete_placeholder_simple
)

__all__ = [
    "PlaceholderApplicationService",
    "get_placeholder_service", 
    "shutdown_placeholder_service",
    
    # 兼容性函数
    "analyze_placeholder",
    "update_placeholder", 
    "complete_placeholder",
    "analyze_placeholder_simple",
    "update_placeholder_simple",
    "complete_placeholder_simple"
]