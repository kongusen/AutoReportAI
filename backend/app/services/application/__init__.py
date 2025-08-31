"""
Application Layer - DAG Architecture Only

纯DAG架构应用层，只保留DAG核心组件：
- facades: 统一服务门面
- context: 上下文构建器（用于DAG）
"""

# 上下文构建器 - 用于DAG架构
from .context import (
    TimeContextBuilder,
    BusinessContextBuilder,
    DocumentContextBuilder
)

# 统一服务门面
from .facades.unified_service_facade import get_unified_facade

__all__ = [
    # 上下文构建器（DAG架构专用）
    "TimeContextBuilder",
    "BusinessContextBuilder", 
    "DocumentContextBuilder",
    
    # 统一门面
    "get_unified_facade",
]