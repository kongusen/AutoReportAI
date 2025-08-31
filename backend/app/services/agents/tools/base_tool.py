"""
基础工具类
提供工具创建的标准化接口和公共功能
"""

import json
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from functools import wraps

from llama_index.core.tools import FunctionTool

logger = logging.getLogger(__name__)


class ToolMetadata:
    """工具元数据"""
    
    def __init__(
        self,
        name: str,
        description: str,
        category: str = "general",
        complexity: str = "medium",
        cache_enabled: bool = True,
        timeout: int = 60,
        requires_auth: bool = False
    ):
        self.name = name
        self.description = description
        self.category = category
        self.complexity = complexity
        self.cache_enabled = cache_enabled
        self.timeout = timeout
        self.requires_auth = requires_auth


class ToolsCollection:
    """工具集合基类"""
    
    def __init__(self, category: str = "general"):
        self.category = category
        self.tools: List[FunctionTool] = []
        self.metadata: Dict[str, ToolMetadata] = {}
    
    def add_tool(self, tool: FunctionTool, metadata: ToolMetadata = None):
        """添加工具到集合"""
        self.tools.append(tool)
        if metadata:
            self.metadata[tool.metadata.name] = metadata
    
    def get_tools(self) -> List[FunctionTool]:
        """获取所有工具"""
        return self.tools
    
    def get_tools_summary(self) -> Dict[str, Any]:
        """获取工具摘要信息"""
        return {
            "category": self.category,
            "count": len(self.tools),
            "tools": [
                {
                    "name": tool.metadata.name,
                    "description": tool.metadata.description,
                    "category": self.metadata.get(tool.metadata.name, ToolMetadata("", "")).category
                }
                for tool in self.tools
            ]
        }


def create_standard_tool(
    func: Callable,
    name: str,
    description: str,
    category: str = "general",
    complexity: str = "medium",
    cache_enabled: bool = True,
    timeout: int = 60,
    return_direct: bool = False
) -> FunctionTool:
    """
    创建标准化的Function Tool
    
    Args:
        func: 要包装的函数
        name: 工具名称
        description: 工具描述
        category: 工具分类
        complexity: 复杂度等级 (low/medium/high/very_high)
        cache_enabled: 是否启用缓存
        timeout: 超时时间（秒）
        return_direct: 是否直接返回结果
        
    Returns:
        标准化的FunctionTool
    """
    
    @wraps(func)
    async def wrapped_tool(*args, **kwargs) -> str:
        """包装后的工具函数"""
        start_time = datetime.utcnow()
        
        try:
            # 记录工具调用
            logger.info(f"工具调用开始: {name}")
            
            # 执行原函数
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # 处理返回值
            if isinstance(result, dict):
                output = json.dumps(result, ensure_ascii=False, indent=2)
            elif isinstance(result, (list, tuple)):
                output = json.dumps(result, ensure_ascii=False, indent=2)
            else:
                output = str(result)
            
            # 记录执行时间
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"工具调用完成: {name}, 耗时: {execution_time:.2f}s")
            
            return output
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"工具调用失败: {name}, 耗时: {execution_time:.2f}s, 错误: {e}")
            
            error_result = {
                "error": str(e),
                "tool": name,
                "category": category,
                "execution_time": execution_time
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)
    
    # 创建FunctionTool
    return FunctionTool.from_defaults(
        async_fn=wrapped_tool,
        name=name,
        description=f"[{category}] {description}",
        return_direct=return_direct
    )


def create_tool_with_validation(
    func: Callable,
    name: str,
    description: str,
    input_schema: Dict[str, Any] = None,
    **kwargs
) -> FunctionTool:
    """
    创建带输入验证的工具
    
    Args:
        func: 要包装的函数
        name: 工具名称
        description: 工具描述
        input_schema: 输入参数验证schema
        **kwargs: 传递给create_standard_tool的其他参数
    """
    
    @wraps(func)
    async def validated_func(*args, **kwargs):
        """带验证的函数包装"""
        # 这里可以添加输入验证逻辑
        if input_schema:
            # TODO: 实现schema验证
            pass
        
        return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
    
    return create_standard_tool(
        validated_func,
        name,
        description,
        **kwargs
    )


# 添加缺失的导入
import asyncio