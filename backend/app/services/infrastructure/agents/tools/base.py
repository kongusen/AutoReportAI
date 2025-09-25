"""
工具基类定义

定义所有Agent工具的统一接口
确保一致的输入输出格式
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class Tool(ABC):
    """Agent工具基类"""

    def __init__(self) -> None:
        self.name: str = ""
        self.description: str = ""

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具逻辑

        Args:
            input_data: 工具输入数据

        Returns:
            Dict: 标准格式的工具输出
            {
                "success": bool,  # 执行是否成功
                "result": Any,    # 主要结果
                "error": str,     # 错误信息 (如果失败)
                ...               # 其他工具特定的输出
            }
        """
        raise NotImplementedError

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def __repr__(self) -> str:
        return self.__str__()