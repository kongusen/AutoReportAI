"""
Infrastructure层AI工具注册表

负责工具的注册、发现和管理

核心职责：
- 提供工具注册和发现机制
- 管理工具元数据和分类
- 支持动态工具加载和卸载
- 为上层Agent提供工具注册服务

技术职责：
- 纯技术实现，不包含业务逻辑
- 可被Application/Domain层的Agent使用
- 提供稳定的工具管理服务
"""

import logging
from typing import Any, Dict, List, Optional, Callable, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """工具类别"""
    DATA_PROCESSING = "data_processing"
    PLACEHOLDER = "placeholder"
    CHART_GENERATION = "chart_generation"
    SQL_GENERATION = "sql_generation"
    BUSINESS_LOGIC = "business_logic"
    VALIDATION = "validation"
    FORMATTING = "formatting"
    CORE = "core"
    GENERAL = "general"


class ToolComplexity(Enum):
    """工具复杂度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    description: str
    category: ToolCategory = ToolCategory.GENERAL
    complexity: ToolComplexity = ToolComplexity.MEDIUM
    cache_enabled: bool = True
    timeout: int = 60
    requires_auth: bool = False
    version: str = "1.0.0"
    author: str = "system"
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


@dataclass
class RegisteredTool:
    """已注册的工具"""
    tool: Any  # 实际的工具对象
    metadata: ToolMetadata
    is_active: bool = True
    usage_count: int = 0
    last_used: Optional[datetime] = None
    registration_time: datetime = field(default_factory=datetime.utcnow)


class AIToolsRegistry:
    """
    Infrastructure层AI工具注册表
    
    核心职责：
    1. 管理工具的注册和发现
    2. 提供工具元数据管理
    3. 支持工具分类和搜索
    4. 监控工具使用统计
    
    技术定位：
    - Infrastructure层技术基础设施
    - 为上层Agent提供工具注册能力
    - 不包含具体业务逻辑
    """
    
    def __init__(self):
        self.tools: Dict[str, RegisteredTool] = {}
        self.categories: Dict[ToolCategory, Set[str]] = {category: set() for category in ToolCategory}
        self.tags_index: Dict[str, Set[str]] = {}
        
        # 统计信息
        self.total_registrations = 0
        self.total_usage = 0
        self.start_time = datetime.utcnow()
        
        logger.info("AI工具注册表初始化完成")
    
    def register_tool(
        self,
        tool: Any,
        metadata: ToolMetadata,
        overwrite: bool = False
    ) -> bool:
        """
        注册工具
        
        Args:
            tool: 工具对象
            metadata: 工具元数据
            overwrite: 是否覆盖已存在的工具
            
        Returns:
            是否注册成功
        """
        try:
            tool_name = metadata.name
            
            # 检查是否已存在
            if tool_name in self.tools and not overwrite:
                logger.warning(f"工具 {tool_name} 已存在，跳过注册")
                return False
            
            # 创建已注册工具
            registered_tool = RegisteredTool(
                tool=tool,
                metadata=metadata
            )
            
            # 注册工具
            self.tools[tool_name] = registered_tool
            
            # 更新分类索引
            self.categories[metadata.category].add(tool_name)
            
            # 更新标签索引
            for tag in metadata.tags:
                if tag not in self.tags_index:
                    self.tags_index[tag] = set()
                self.tags_index[tag].add(tool_name)
            
            self.total_registrations += 1
            
            logger.info(f"工具注册成功: {tool_name} ({metadata.category.value})")
            return True
            
        except Exception as e:
            logger.error(f"工具注册失败: {metadata.name}, 错误: {e}")
            return False
    
    def get_tool(self, name: str) -> Optional[Any]:
        """
        获取工具
        
        Args:
            name: 工具名称
            
        Returns:
            工具对象，如果不存在返回None
        """
        if name in self.tools:
            registered_tool = self.tools[name]
            
            if registered_tool.is_active:
                # 更新使用统计
                registered_tool.usage_count += 1
                registered_tool.last_used = datetime.utcnow()
                self.total_usage += 1
                
                return registered_tool.tool
            else:
                logger.warning(f"工具 {name} 已禁用")
                return None
        
        logger.warning(f"工具 {name} 不存在")
        return None
    
    def get_tools_by_category(self, category: ToolCategory) -> List[Any]:
        """
        根据类别获取工具
        
        Args:
            category: 工具类别
            
        Returns:
            工具列表
        """
        tools = []
        for tool_name in self.categories.get(category, set()):
            tool = self.get_tool(tool_name)
            if tool:
                tools.append(tool)
        
        return tools
    
    def get_tools_by_tag(self, tag: str) -> List[Any]:
        """
        根据标签获取工具
        
        Args:
            tag: 标签
            
        Returns:
            工具列表
        """
        tools = []
        for tool_name in self.tags_index.get(tag, set()):
            tool = self.get_tool(tool_name)
            if tool:
                tools.append(tool)
        
        return tools
    
    def search_tools(
        self,
        query: str,
        category: Optional[ToolCategory] = None,
        tags: Optional[List[str]] = None,
        complexity: Optional[ToolComplexity] = None
    ) -> List[Any]:
        """
        搜索工具
        
        Args:
            query: 搜索查询
            category: 类别过滤
            tags: 标签过滤
            complexity: 复杂度过滤
            
        Returns:
            匹配的工具列表
        """
        matching_tools = []
        query_lower = query.lower()
        
        for tool_name, registered_tool in self.tools.items():
            if not registered_tool.is_active:
                continue
            
            metadata = registered_tool.metadata
            
            # 文本匹配
            text_match = (
                query_lower in metadata.name.lower() or
                query_lower in metadata.description.lower() or
                any(query_lower in tag.lower() for tag in metadata.tags)
            )
            
            if not text_match:
                continue
            
            # 类别过滤
            if category and metadata.category != category:
                continue
            
            # 标签过滤
            if tags and not any(tag in metadata.tags for tag in tags):
                continue
            
            # 复杂度过滤
            if complexity and metadata.complexity != complexity:
                continue
            
            matching_tools.append(registered_tool.tool)
        
        logger.debug(f"搜索工具 '{query}' 找到 {len(matching_tools)} 个结果")
        return matching_tools
    
    def get_all_tools(self, active_only: bool = True) -> List[Any]:
        """
        获取所有工具
        
        Args:
            active_only: 是否只返回激活的工具
            
        Returns:
            工具列表
        """
        tools = []
        for registered_tool in self.tools.values():
            if not active_only or registered_tool.is_active:
                tools.append(registered_tool.tool)
        
        return tools
    
    def deactivate_tool(self, name: str) -> bool:
        """
        禁用工具
        
        Args:
            name: 工具名称
            
        Returns:
            是否成功
        """
        if name in self.tools:
            self.tools[name].is_active = False
            logger.info(f"工具 {name} 已禁用")
            return True
        
        return False
    
    def activate_tool(self, name: str) -> bool:
        """
        启用工具
        
        Args:
            name: 工具名称
            
        Returns:
            是否成功
        """
        if name in self.tools:
            self.tools[name].is_active = True
            logger.info(f"工具 {name} 已启用")
            return True
        
        return False
    
    def unregister_tool(self, name: str) -> bool:
        """
        注销工具
        
        Args:
            name: 工具名称
            
        Returns:
            是否成功
        """
        if name not in self.tools:
            return False
        
        try:
            registered_tool = self.tools[name]
            metadata = registered_tool.metadata
            
            # 从主索引移除
            del self.tools[name]
            
            # 从分类索引移除
            self.categories[metadata.category].discard(name)
            
            # 从标签索引移除
            for tag in metadata.tags:
                if tag in self.tags_index:
                    self.tags_index[tag].discard(name)
                    if not self.tags_index[tag]:
                        del self.tags_index[tag]
            
            logger.info(f"工具 {name} 已注销")
            return True
            
        except Exception as e:
            logger.error(f"注销工具失败: {name}, 错误: {e}")
            return False
    
    def get_tool_metadata(self, name: str) -> Optional[ToolMetadata]:
        """
        获取工具元数据
        
        Args:
            name: 工具名称
            
        Returns:
            工具元数据，如果不存在返回None
        """
        if name in self.tools:
            return self.tools[name].metadata
        
        return None
    
    def update_tool_metadata(self, name: str, metadata: ToolMetadata) -> bool:
        """
        更新工具元数据
        
        Args:
            name: 工具名称
            metadata: 新的元数据
            
        Returns:
            是否成功
        """
        if name not in self.tools:
            return False
        
        try:
            old_metadata = self.tools[name].metadata
            
            # 更新元数据
            metadata.updated_at = datetime.utcnow()
            self.tools[name].metadata = metadata
            
            # 更新分类索引
            self.categories[old_metadata.category].discard(name)
            self.categories[metadata.category].add(name)
            
            # 更新标签索引
            for tag in old_metadata.tags:
                if tag in self.tags_index:
                    self.tags_index[tag].discard(name)
                    if not self.tags_index[tag]:
                        del self.tags_index[tag]
            
            for tag in metadata.tags:
                if tag not in self.tags_index:
                    self.tags_index[tag] = set()
                self.tags_index[tag].add(name)
            
            logger.info(f"工具元数据已更新: {name}")
            return True
            
        except Exception as e:
            logger.error(f"更新工具元数据失败: {name}, 错误: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        # 按类别统计
        category_stats = {}
        for category in ToolCategory:
            tools_in_category = len(self.categories[category])
            active_tools_in_category = sum(
                1 for name in self.categories[category]
                if name in self.tools and self.tools[name].is_active
            )
            category_stats[category.value] = {
                "total": tools_in_category,
                "active": active_tools_in_category
            }
        
        # 使用统计
        usage_stats = {}
        for name, registered_tool in self.tools.items():
            if registered_tool.usage_count > 0:
                usage_stats[name] = {
                    "usage_count": registered_tool.usage_count,
                    "last_used": registered_tool.last_used.isoformat() if registered_tool.last_used else None
                }
        
        return {
            "total_tools": len(self.tools),
            "active_tools": sum(1 for rt in self.tools.values() if rt.is_active),
            "total_registrations": self.total_registrations,
            "total_usage": self.total_usage,
            "uptime_seconds": uptime,
            "category_stats": category_stats,
            "total_tags": len(self.tags_index),
            "usage_stats": usage_stats
        }
    
    def get_registry_info(self) -> Dict[str, Any]:
        """获取注册表信息"""
        tools_info = []
        for name, registered_tool in self.tools.items():
            metadata = registered_tool.metadata
            tools_info.append({
                "name": name,
                "description": metadata.description,
                "category": metadata.category.value,
                "complexity": metadata.complexity.value,
                "version": metadata.version,
                "author": metadata.author,
                "tags": metadata.tags,
                "is_active": registered_tool.is_active,
                "usage_count": registered_tool.usage_count,
                "registration_time": registered_tool.registration_time.isoformat(),
                "last_used": registered_tool.last_used.isoformat() if registered_tool.last_used else None
            })
        
        return {
            "registry_name": "Infrastructure AI Tools Registry",
            "version": "2.0.0-ddd",
            "architecture": "DDD Infrastructure Layer",
            "tools": tools_info,
            "statistics": self.get_statistics()
        }