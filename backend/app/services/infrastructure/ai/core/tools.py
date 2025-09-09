"""
基础工具类定义 - 类似 Claude Code 的工具系统
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, AsyncGenerator, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ToolResultType(Enum):
    """工具结果类型"""
    PROGRESS = "progress"
    RESULT = "result" 
    ERROR = "error"
    STATUS = "status"


@dataclass
class ToolContext:
    """工具执行上下文"""
    user_id: str
    task_id: str
    session_id: str
    
    # 额外上下文数据
    context_data: Dict[str, Any]
    
    # 工具配置
    tool_config: Optional[Dict[str, Any]] = None


@dataclass
class ToolResult:
    """工具执行结果"""
    type: ToolResultType
    data: Any
    
    # 可选的进度信息
    progress_info: Optional[Dict[str, Any]] = None
    
    # 错误信息
    error_info: Optional[Dict[str, Any]] = None
    
    # 元数据
    metadata: Optional[Dict[str, Any]] = None


class BaseTool(ABC):
    """基础工具类，所有工具都继承此类"""
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.logger = logging.getLogger(f"{__name__}.{tool_name}")
    
    @abstractmethod
    async def execute(
        self, 
        input_data: Dict[str, Any],
        context: ToolContext
    ) -> AsyncGenerator[ToolResult, None]:
        """
        执行工具逻辑，支持流式进度反馈
        
        Args:
            input_data: 输入数据
            context: 执行上下文
            
        Yields:
            ToolResult: 可能是进度更新或最终结果
        """
        pass
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据格式"""
        return True
    
    def create_progress_result(
        self, 
        message: str, 
        step: Optional[str] = None,
        percentage: Optional[float] = None
    ) -> ToolResult:
        """创建进度结果"""
        return ToolResult(
            type=ToolResultType.PROGRESS,
            data=message,
            progress_info={
                "step": step,
                "percentage": percentage,
                "timestamp": self._get_timestamp()
            }
        )
    
    def create_success_result(
        self, 
        data: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """创建成功结果"""
        return ToolResult(
            type=ToolResultType.RESULT,
            data=data,
            metadata=metadata or {}
        )
    
    def create_error_result(
        self, 
        error_message: str,
        error_type: str = "tool_error",
        recoverable: bool = True
    ) -> ToolResult:
        """创建错误结果"""
        return ToolResult(
            type=ToolResultType.ERROR,
            data=None,
            error_info={
                "error_type": error_type,
                "error_message": error_message,
                "recoverable": recoverable,
                "tool_name": self.tool_name
            }
        )
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.utcnow().isoformat()


class ToolChain:
    """工具链管理器"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.logger = logging.getLogger(f"{__name__}.ToolChain")
    
    def register_tool(self, tool: BaseTool):
        """注册工具"""
        self.tools[tool.tool_name] = tool
        self.logger.info(f"工具已注册: {tool.tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> list:
        """列出所有已注册的工具"""
        return list(self.tools.keys())
    
    async def execute_tool(
        self,
        tool_name: str,
        input_data: Dict[str, Any],
        context: ToolContext
    ) -> AsyncGenerator[ToolResult, None]:
        """执行指定工具"""
        tool = self.get_tool(tool_name)
        if not tool:
            yield ToolResult(
                type=ToolResultType.ERROR,
                data=None,
                error_info={
                    "error_type": "tool_not_found",
                    "error_message": f"工具未找到: {tool_name}",
                    "recoverable": False
                }
            )
            return
        
        try:
            # 验证输入
            if not await tool.validate_input(input_data):
                yield tool.create_error_result(
                    f"输入数据验证失败: {tool_name}",
                    "input_validation_error"
                )
                return
            
            # 执行工具
            async for result in tool.execute(input_data, context):
                yield result
                
        except Exception as e:
            self.logger.error(f"工具执行失败: {tool_name} - {e}")
            yield ToolResult(
                type=ToolResultType.ERROR,
                data=None,
                error_info={
                    "error_type": "tool_execution_error",
                    "error_message": str(e),
                    "recoverable": True,
                    "tool_name": tool_name
                }
            )