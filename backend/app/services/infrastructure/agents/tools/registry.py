"""
工具注册表

管理所有可用的Agent工具
提供工具注册、查找和管理功能
"""

from typing import Dict, Optional
import logging

from .base import Tool


class ToolRegistry:
    """工具注册表"""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}
        self._logger = logging.getLogger(self.__class__.__name__)

    def register(self, tool: Tool) -> None:
        """
        注册工具

        Args:
            tool: 要注册的工具实例
        """
        if not isinstance(tool, Tool):
            raise ValueError(f"Tool must be instance of Tool, got {type(tool)}")

        if not tool.name:
            raise ValueError(f"Tool name cannot be empty: {tool}")

        self._tools[tool.name] = tool
        self._logger.debug(f"注册工具: {tool.name}")

    def get(self, name: str) -> Optional[Tool]:
        """
        获取工具

        Args:
            name: 工具名称

        Returns:
            Tool: 工具实例，如果不存在返回None
        """
        return self._tools.get(name)

    def unregister(self, name: str) -> bool:
        """
        取消注册工具

        Args:
            name: 工具名称

        Returns:
            bool: 是否成功取消注册
        """
        if name in self._tools:
            del self._tools[name]
            self._logger.debug(f"取消注册工具: {name}")
            return True
        return False

    def list_tools(self) -> Dict[str, str]:
        """
        列出所有工具

        Returns:
            Dict: 工具名称到描述的映射
        """
        return {name: tool.description for name, tool in self._tools.items()}

    def exists(self, name: str) -> bool:
        """
        检查工具是否存在

        Args:
            name: 工具名称

        Returns:
            bool: 工具是否存在
        """
        return name in self._tools

    def count(self) -> int:
        """
        获取注册工具数量

        Returns:
            int: 工具数量
        """
        return len(self._tools)

    def clear(self) -> None:
        """清空所有工具"""
        self._tools.clear()
        self._logger.debug("清空所有工具")

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __iter__(self):
        return iter(self._tools)

    def __repr__(self) -> str:
        return f"ToolRegistry({len(self._tools)} tools: {list(self._tools.keys())})"