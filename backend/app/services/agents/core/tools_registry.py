"""
Function Tools 注册中心
统一管理和注册所有智能代理工具
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from llama_index.core.tools import FunctionTool

from ..tools.tools_factory import get_tools_factory, ToolsFactory

logger = logging.getLogger(__name__)


class FunctionToolsRegistry:
    """
    Function Tools 统一注册中心
    - 移除MCP依赖，直接将业务服务包装为FunctionTool
    - 支持工具分类和元数据管理
    - 提供工具发现和动态加载功能
    """
    
    def __init__(self):
        self.tools_by_category: Dict[str, List[FunctionTool]] = {
            "placeholder": [],    # 占位符处理工具
            "chart": [],         # 图表生成工具
            "data": [],          # 数据分析工具
            "core": [],          # 核心系统工具
            "custom": []         # 自定义工具
        }
        
        self.all_tools: List[FunctionTool] = []
        self.tools_factory: Optional[ToolsFactory] = None
        self.initialized = False
        self.initialization_time: Optional[datetime] = None
    
    async def initialize(self):
        """初始化工具注册中心"""
        if self.initialized:
            return
        
        logger.info("初始化Function Tools注册中心...")
        
        try:
            # 获取工具工厂
            self.tools_factory = await get_tools_factory()
            
            # 注册所有工具
            await self._register_all_tools()
            
            self.initialized = True
            self.initialization_time = datetime.utcnow()
            
            logger.info(f"Function Tools注册中心初始化完成 - 总工具数: {len(self.all_tools)}")
            
        except Exception as e:
            logger.error(f"Function Tools注册中心初始化失败: {e}")
            raise
    
    async def _register_all_tools(self):
        """注册所有工具"""
        # 获取所有工具
        all_tools = await self.tools_factory.get_all_tools()
        
        # 按分类组织工具
        for tool in all_tools:
            category = getattr(tool.metadata, 'category', 'custom') if hasattr(tool, 'metadata') else 'custom'
            
            if category in self.tools_by_category:
                self.tools_by_category[category].append(tool)
            else:
                self.tools_by_category["custom"].append(tool)
        
        # 更新总工具列表
        self.all_tools = all_tools
        
        logger.info(f"工具注册完成 - 分类分布: {self._get_category_counts()}")
    
    def _get_category_counts(self) -> Dict[str, int]:
        """获取各分类的工具数量"""
        return {
            category: len(tools) 
            for category, tools in self.tools_by_category.items()
        }
    
    def get_all_tools(self) -> List[FunctionTool]:
        """获取所有已注册的工具"""
        if not self.initialized:
            raise RuntimeError("工具注册中心未初始化，请先调用 initialize()")
        
        return self.all_tools.copy()
    
    def get_tools_by_category(self, category: str) -> List[FunctionTool]:
        """按分类获取工具"""
        if not self.initialized:
            raise RuntimeError("工具注册中心未初始化，请先调用 initialize()")
        
        if category not in self.tools_by_category:
            available_categories = list(self.tools_by_category.keys())
            raise ValueError(f"未知的工具分类: {category}. 可用分类: {available_categories}")
        
        return self.tools_by_category[category].copy()
    
    def get_tools_by_names(self, tool_names: List[str]) -> List[FunctionTool]:
        """根据工具名称获取工具"""
        if not self.initialized:
            raise RuntimeError("工具注册中心未初始化，请先调用 initialize()")
        
        found_tools = []
        for tool in self.all_tools:
            tool_name = getattr(tool.metadata, 'name', tool.fn.__name__) if hasattr(tool, 'metadata') else tool.fn.__name__
            if tool_name in tool_names:
                found_tools.append(tool)
        
        return found_tools
    
    def get_tool_by_name(self, tool_name: str) -> Optional[FunctionTool]:
        """根据名称获取单个工具"""
        tools = self.get_tools_by_names([tool_name])
        return tools[0] if tools else None
    
    def search_tools(self, query: str, categories: Optional[List[str]] = None) -> List[FunctionTool]:
        """搜索工具（根据名称和描述）"""
        if not self.initialized:
            raise RuntimeError("工具注册中心未初始化，请先调用 initialize()")
        
        query_lower = query.lower()
        matching_tools = []
        
        tools_to_search = self.all_tools
        if categories:
            tools_to_search = []
            for category in categories:
                if category in self.tools_by_category:
                    tools_to_search.extend(self.tools_by_category[category])
        
        for tool in tools_to_search:
            tool_name = getattr(tool.metadata, 'name', tool.fn.__name__) if hasattr(tool, 'metadata') else tool.fn.__name__
            tool_desc = getattr(tool.metadata, 'description', '') if hasattr(tool, 'metadata') else ''
            
            if (query_lower in tool_name.lower() or 
                query_lower in tool_desc.lower()):
                matching_tools.append(tool)
        
        return matching_tools
    
    def get_registry_info(self) -> Dict[str, Any]:
        """获取注册中心信息"""
        if not self.initialized:
            return {
                "status": "not_initialized",
                "message": "工具注册中心未初始化"
            }
        
        category_details = {}
        for category, tools in self.tools_by_category.items():
            category_details[category] = {
                "tool_count": len(tools),
                "tools": [
                    {
                        "name": getattr(tool.metadata, 'name', tool.fn.__name__) if hasattr(tool, 'metadata') else tool.fn.__name__,
                        "description": getattr(tool.metadata, 'description', '') if hasattr(tool, 'metadata') else '',
                        "complexity": getattr(tool.metadata, 'complexity', 'medium') if hasattr(tool, 'metadata') else 'medium'
                    }
                    for tool in tools
                ]
            }
        
        return {
            "status": "initialized",
            "initialization_time": self.initialization_time.isoformat() if self.initialization_time else None,
            "total_tools": len(self.all_tools),
            "categories": category_details,
            "summary": self.tools_factory.get_tools_summary() if self.tools_factory else {}
        }
    
    async def refresh_tools(self):
        """刷新工具注册（重新加载所有工具）"""
        logger.info("刷新工具注册...")
        
        try:
            # 清空现有工具
            self.tools_by_category = {category: [] for category in self.tools_by_category.keys()}
            self.all_tools = []
            
            # 重新注册工具
            await self._register_all_tools()
            
            logger.info(f"工具注册刷新完成 - 总工具数: {len(self.all_tools)}")
            
        except Exception as e:
            logger.error(f"工具注册刷新失败: {e}")
            raise
    
    def add_custom_tool(self, tool: FunctionTool, category: str = "custom"):
        """添加自定义工具"""
        if not self.initialized:
            raise RuntimeError("工具注册中心未初始化，请先调用 initialize()")
        
        if category not in self.tools_by_category:
            self.tools_by_category[category] = []
        
        self.tools_by_category[category].append(tool)
        self.all_tools.append(tool)
        
        logger.info(f"添加自定义工具: {tool.fn.__name__} 到分类: {category}")
    
    def remove_tool(self, tool_name: str) -> bool:
        """移除工具"""
        if not self.initialized:
            raise RuntimeError("工具注册中心未初始化，请先调用 initialize()")
        
        removed = False
        
        # 从所有分类中查找并移除
        for category, tools in self.tools_by_category.items():
            for i, tool in enumerate(tools):
                current_name = getattr(tool.metadata, 'name', tool.fn.__name__) if hasattr(tool, 'metadata') else tool.fn.__name__
                if current_name == tool_name:
                    tools.pop(i)
                    removed = True
                    break
        
        # 从总列表中移除
        for i, tool in enumerate(self.all_tools):
            current_name = getattr(tool.metadata, 'name', tool.fn.__name__) if hasattr(tool, 'metadata') else tool.fn.__name__
            if current_name == tool_name:
                self.all_tools.pop(i)
                break
        
        if removed:
            logger.info(f"工具已移除: {tool_name}")
        
        return removed
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            health_info = {
                "status": "healthy" if self.initialized else "not_initialized",
                "timestamp": datetime.utcnow().isoformat(),
                "registry_initialized": self.initialized,
                "total_tools": len(self.all_tools),
                "categories_count": len(self.tools_by_category),
                "tools_factory_status": "available" if self.tools_factory else "unavailable"
            }
            
            if self.initialized:
                health_info["category_distribution"] = self._get_category_counts()
            
            return health_info
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# 全局注册中心实例
_global_tools_registry: Optional[FunctionToolsRegistry] = None


async def get_tools_registry() -> FunctionToolsRegistry:
    """获取全局工具注册中心实例"""
    global _global_tools_registry
    if _global_tools_registry is None:
        _global_tools_registry = FunctionToolsRegistry()
        await _global_tools_registry.initialize()
    return _global_tools_registry


# 便捷函数
async def register_all_tools():
    """注册所有工具的便捷函数"""
    registry = await get_tools_registry()
    return registry.get_all_tools()


async def get_tools_by_category(category: str) -> List[FunctionTool]:
    """按分类获取工具的便捷函数"""
    registry = await get_tools_registry()
    return registry.get_tools_by_category(category)