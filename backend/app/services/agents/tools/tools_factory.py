"""
工具工厂
负责创建和管理所有智能代理工具
"""

import logging
from typing import List, Dict, Any, Optional

from llama_index.core.tools import FunctionTool

from .placeholder_tools import PlaceholderToolsCollection
from .chart_tools import ChartToolsCollection
# Skip data_tools and core_tools temporarily due to disabled dependencies

logger = logging.getLogger(__name__)


class ToolsFactory:
    """工具工厂类"""
    
    def __init__(self):
        self.collections = {}
        self._initialized = False
    
    async def initialize(self):
        """初始化所有工具集合"""
        if self._initialized:
            return
        
        logger.info("初始化工具工厂...")
        
        try:
            # 初始化占位符工具集合
            self.collections["placeholder"] = PlaceholderToolsCollection()
            logger.info("✅ 占位符工具集合初始化完成")
            
            # 初始化图表工具集合
            self.collections["chart"] = ChartToolsCollection()
            logger.info("✅ 图表工具集合初始化完成")
            
            self._initialized = True
            logger.info("🎉 工具工厂初始化完成")
            
        except Exception as e:
            logger.error(f"工具工厂初始化失败: {e}")
            raise
    
    def get_all_tools(self) -> List[FunctionTool]:
        """获取所有工具"""
        if not self._initialized:
            raise RuntimeError("工具工厂未初始化")
        
        all_tools = []
        for collection in self.collections.values():
            all_tools.extend(collection.create_tools())
        
        return all_tools
    
    def get_tools_by_category(self, category: str) -> List[FunctionTool]:
        """根据分类获取工具"""
        if not self._initialized:
            raise RuntimeError("工具工厂未初始化")
        
        if category not in self.collections:
            logger.warning(f"未找到分类 {category} 的工具集合")
            return []
        
        return self.collections[category].create_tools()
    
    def get_tools_summary(self) -> Dict[str, Any]:
        """获取工具摘要信息"""
        if not self._initialized:
            return {"initialized": False, "collections": []}
        
        summary = {
            "initialized": True,
            "total_collections": len(self.collections),
            "collections": []
        }
        
        for name, collection in self.collections.items():
            tools = collection.create_tools()
            summary["collections"].append({
                "name": name,
                "category": collection.category,
                "tool_count": len(tools),
                "tools": [tool.metadata.name for tool in tools]
            })
        
        return summary
    
    async def reload_collections(self):
        """重新加载所有工具集合"""
        logger.info("重新加载工具集合...")
        self._initialized = False
        self.collections.clear()
        await self.initialize()


# 全局工具工厂实例
_global_factory = None

async def get_tools_factory() -> ToolsFactory:
    """获取全局工具工厂实例"""
    global _global_factory
    
    if _global_factory is None:
        _global_factory = ToolsFactory()
        await _global_factory.initialize()
    
    return _global_factory

def create_placeholder_tools() -> List[FunctionTool]:
    """创建占位符工具列表（兼容接口）"""
    collection = PlaceholderToolsCollection()
    return collection.create_tools()

def create_chart_tools() -> List[FunctionTool]:
    """创建图表工具列表（兼容接口）"""
    collection = ChartToolsCollection()
    return collection.create_tools()

async def create_all_tools() -> List[FunctionTool]:
    """创建所有可用工具"""
    factory = await get_tools_factory()
    return factory.get_all_tools()

async def get_tools_summary() -> Dict[str, Any]:
    """获取工具摘要信息（兼容接口）"""
    factory = await get_tools_factory()
    return factory.get_tools_summary()

def create_tool_combination(combination_name: str) -> List[FunctionTool]:
    """创建工具组合（简化版）"""
    if combination_name == "placeholder":
        return create_placeholder_tools()
    elif combination_name == "chart":
        return create_chart_tools()
    else:
        # 默认返回所有可用工具
        placeholder_tools = create_placeholder_tools()
        chart_tools = create_chart_tools()
        return placeholder_tools + chart_tools

def get_available_combinations() -> List[str]:
    """获取可用的工具组合"""
    return ["placeholder", "chart", "all"]

def create_tools_by_category(category: str) -> List[FunctionTool]:
    """根据分类创建工具"""
    if category == "placeholder":
        return create_placeholder_tools()
    elif category == "chart":
        return create_chart_tools()
    else:
        return []

class ToolsMonitor:
    """工具监控器（简化版）"""
    
    def __init__(self):
        self.usage_stats = {}
    
    def record_usage(self, tool_name: str, success: bool, response_time: float):
        """记录工具使用"""
        if tool_name not in self.usage_stats:
            self.usage_stats[tool_name] = {"calls": 0, "successes": 0, "total_time": 0.0}
        
        self.usage_stats[tool_name]["calls"] += 1
        if success:
            self.usage_stats[tool_name]["successes"] += 1
        self.usage_stats[tool_name]["total_time"] += response_time
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.usage_stats


# 全局工具监控器实例
_global_monitor = None

def get_tools_monitor() -> ToolsMonitor:
    """获取全局工具监控器"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = ToolsMonitor()
    return _global_monitor