"""
Agent工具系统

提供标准化的工具接口和注册机制
所有工具都继承自Tool基类并实现execute方法
"""

from .base import Tool
from .registry import ToolRegistry

__all__ = ["Tool", "ToolRegistry"]