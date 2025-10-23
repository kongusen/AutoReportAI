"""
Loom 兼容工具基类。

原始项目中的工具通过继承一个简单的 `Tool` 抽象类并暴露异步
`execute` 方法。为了在新的基础设施层复用这一模式，我们在此重建
相同的基类定义，供 `adapt_legacy_tool` 装饰器包装。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class Tool(ABC):
    """Agent 工具统一接口。"""

    def __init__(self) -> None:
        self.name: str = ""
        self.description: str = ""

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具逻辑并返回结构化结果。

        返回字典约定：
            {
                "success": bool,
                ...  # 具体工具可附带其他字段
            }
        """
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return f"{self.__class__.__name__}({self.name})"


__all__ = ["Tool"]

