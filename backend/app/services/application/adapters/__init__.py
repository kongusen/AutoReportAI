"""
应用层适配器模块

提供新旧系统之间的适配层，支持渐进式迁移
"""

from .template_adapter import TemplateContextAdapter
from .time_adapter import TimeContextAdapter

__all__ = [
    "TemplateContextAdapter",
    "TimeContextAdapter",
]
