"""
Agent工具基础框架

定义了Agent系统中工具的基础接口和通用功能。
所有具体工具都应该继承自BaseTool类。

Features:
- 统一的工具接口
- 工具注册和发现机制
- 工具执行监控和日志
- 工具权限管理
- 工具依赖管理
"""

import asyncio
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union, Callable
import logging


class ToolCategory(Enum):
    """工具分类"""
    DATA_PROCESSING = "data_processing"      # 数据处理工具
    ANALYSIS = "analysis"                    # 分析工具
    VISUALIZATION = "visualization"          # 可视化工具
    CONTENT_GENERATION = "content_generation" # 内容生成工具
    SECURITY = "security"                    # 安全工具
    OPTIMIZATION = "optimization"            # 优化工具
    INTEGRATION = "integration"              # 集成工具


class ToolPriority(Enum):
    """工具优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ToolConfig:
    """工具配置"""
    enabled: bool = True
    timeout_seconds: int = 30
    retry_count: int = 3
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    log_enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolDependency:
    """工具依赖"""
    tool_id: str
    required: bool = True
    version: Optional[str] = None


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolMetadata:
    """工具元数据"""
    tool_id: str
    name: str
    description: str
    version: str
    category: ToolCategory
    priority: ToolPriority = ToolPriority.MEDIUM
    dependencies: List[ToolDependency] = field(default_factory=list)
    config: ToolConfig = field(default_factory=ToolConfig)
    tags: List[str] = field(default_factory=list)
    author: str = "AutoReport AI"
    created_at: Optional[float] = None
    updated_at: Optional[float] = None


class BaseTool(ABC):
    """工具基础类"""
    
    def __init__(self, metadata: ToolMetadata, logger: Optional[logging.Logger] = None):
        self.metadata = metadata
        self.logger = logger or logging.getLogger(f"tool.{metadata.tool_id}")
        self.config = metadata.config
        self._execution_count = 0
        self._error_count = 0
        self._total_execution_time = 0.0
        self._cache = {}
        
        # 设置创建时间
        if not self.metadata.created_at:
            self.metadata.created_at = time.time()
        self.metadata.updated_at = time.time()
    
    @abstractmethod
    async def execute(self, input_data: Any, context: Dict[str, Any] = None) -> ToolResult:
        """
        执行工具主要功能
        
        Args:
            input_data: 输入数据
            context: 执行上下文
            
        Returns:
            ToolResult: 工具执行结果
        """
        pass
    
    @abstractmethod
    async def validate_input(self, input_data: Any) -> bool:
        """
        验证输入数据
        
        Args:
            input_data: 待验证的输入数据
            
        Returns:
            bool: 验证是否通过
        """
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            Dict: 健康状态信息
        """
        return {
            "tool_id": self.metadata.tool_id,
            "healthy": True,
            "execution_count": self._execution_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(1, self._execution_count),
            "average_execution_time": self._total_execution_time / max(1, self._execution_count),
            "cache_size": len(self._cache),
            "config": {
                "enabled": self.config.enabled,
                "timeout": self.config.timeout_seconds,
                "cache_enabled": self.config.cache_enabled
            }
        }
    
    async def cleanup(self):
        """清理资源"""
        self._cache.clear()
        self.logger.info(f"工具 {self.metadata.tool_id} 已清理资源")
    
    async def run_with_monitoring(self, input_data: Any, context: Dict[str, Any] = None) -> ToolResult:
        """
        带监控的执行方法
        
        Args:
            input_data: 输入数据
            context: 执行上下文
            
        Returns:
            ToolResult: 执行结果
        """
        if not self.config.enabled:
            return ToolResult(
                success=False,
                error_message=f"工具 {self.metadata.tool_id} 已禁用"
            )
        
        # 检查缓存
        cache_key = self._generate_cache_key(input_data, context)
        if self.config.cache_enabled and cache_key in self._cache:
            cached_result = self._cache[cache_key]
            if time.time() - cached_result['timestamp'] < self.config.cache_ttl_seconds:
                self.logger.debug(f"工具 {self.metadata.tool_id} 使用缓存结果")
                return cached_result['result']
        
        start_time = time.time()
        
        try:
            # 输入验证
            if not await self.validate_input(input_data):
                return ToolResult(
                    success=False,
                    error_message="输入数据验证失败"
                )
            
            # 执行工具
            result = await asyncio.wait_for(
                self.execute(input_data, context),
                timeout=self.config.timeout_seconds
            )
            
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            
            # 更新统计信息
            self._execution_count += 1
            self._total_execution_time += execution_time
            
            # 缓存结果
            if self.config.cache_enabled and result.success:
                self._cache[cache_key] = {
                    'result': result,
                    'timestamp': time.time()
                }
                
                # 清理过期缓存
                self._cleanup_cache()
            
            if self.config.log_enabled:
                self.logger.info(
                    f"工具 {self.metadata.tool_id} 执行完成",
                    extra={
                        "execution_time": execution_time,
                        "success": result.success,
                        "input_size": len(str(input_data))
                    }
                )
            
            return result
            
        except asyncio.TimeoutError:
            self._error_count += 1
            error_msg = f"工具 {self.metadata.tool_id} 执行超时 ({self.config.timeout_seconds}s)"
            self.logger.error(error_msg)
            
            return ToolResult(
                success=False,
                error_message=error_msg,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            self._error_count += 1
            error_msg = f"工具 {self.metadata.tool_id} 执行失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return ToolResult(
                success=False,
                error_message=error_msg,
                execution_time=time.time() - start_time,
                metadata={"exception": str(e), "traceback": traceback.format_exc()}
            )
    
    def _generate_cache_key(self, input_data: Any, context: Dict[str, Any] = None) -> str:
        """生成缓存键"""
        import hashlib
        
        key_data = {
            "tool_id": self.metadata.tool_id,
            "input": str(input_data),
            "context": str(context) if context else ""
        }
        
        key_str = str(key_data)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _cleanup_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []
        
        for key, cached_item in self._cache.items():
            if current_time - cached_item['timestamp'] > self.config.cache_ttl_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        # 限制缓存大小
        if len(self._cache) > 100:
            # 删除最老的缓存项
            sorted_items = sorted(
                self._cache.items(),
                key=lambda x: x[1]['timestamp']
            )
            for key, _ in sorted_items[:len(self._cache) - 80]:
                del self._cache[key]


class ToolRegistry:
    """工具注册中心"""
    
    def __init__(self):
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._instances: Dict[str, BaseTool] = {}
        self._categories: Dict[ToolCategory, List[str]] = {}
        self.logger = logging.getLogger("tool_registry")
    
    def register_tool(self, tool_class: Type[BaseTool], metadata: ToolMetadata):
        """注册工具"""
        tool_id = metadata.tool_id
        
        if tool_id in self._tools:
            self.logger.warning(f"工具 {tool_id} 已存在，将被覆盖")
        
        self._tools[tool_id] = tool_class
        
        # 按分类组织工具
        if metadata.category not in self._categories:
            self._categories[metadata.category] = []
        
        if tool_id not in self._categories[metadata.category]:
            self._categories[metadata.category].append(tool_id)
        
        self.logger.info(f"工具 {tool_id} 已注册")
    
    def get_tool(self, tool_id: str) -> Optional[BaseTool]:
        """获取工具实例"""
        if tool_id not in self._tools:
            return None
        
        if tool_id not in self._instances:
            tool_class = self._tools[tool_id]
            # 假设工具类有default_metadata类方法
            if hasattr(tool_class, 'default_metadata'):
                metadata = tool_class.default_metadata()
            else:
                # 创建默认元数据
                metadata = ToolMetadata(
                    tool_id=tool_id,
                    name=tool_id,
                    description=f"工具 {tool_id}",
                    version="1.0.0",
                    category=ToolCategory.DATA_PROCESSING
                )
            
            self._instances[tool_id] = tool_class(metadata)
        
        return self._instances[tool_id]
    
    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """根据分类获取工具"""
        tool_ids = self._categories.get(category, [])
        return [self.get_tool(tool_id) for tool_id in tool_ids if self.get_tool(tool_id)]
    
    def list_tools(self) -> List[ToolMetadata]:
        """列出所有工具的元数据"""
        tools = []
        for tool_id in self._tools:
            tool_instance = self.get_tool(tool_id)
            if tool_instance:
                tools.append(tool_instance.metadata)
        return tools
    
    def search_tools(
        self, 
        query: str = None,
        category: ToolCategory = None,
        tags: List[str] = None
    ) -> List[BaseTool]:
        """搜索工具"""
        results = []
        
        for tool_id in self._tools:
            tool_instance = self.get_tool(tool_id)
            if not tool_instance:
                continue
            
            metadata = tool_instance.metadata
            
            # 按查询字符串过滤
            if query:
                if (query.lower() not in metadata.name.lower() and 
                    query.lower() not in metadata.description.lower()):
                    continue
            
            # 按分类过滤
            if category and metadata.category != category:
                continue
            
            # 按标签过滤
            if tags:
                if not any(tag in metadata.tags for tag in tags):
                    continue
            
            results.append(tool_instance)
        
        return results
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """检查所有工具的健康状态"""
        results = {}
        
        for tool_id in self._tools:
            tool_instance = self.get_tool(tool_id)
            if tool_instance:
                try:
                    results[tool_id] = await tool_instance.health_check()
                except Exception as e:
                    results[tool_id] = {
                        "tool_id": tool_id,
                        "healthy": False,
                        "error": str(e)
                    }
        
        return results
    
    async def cleanup_all(self):
        """清理所有工具资源"""
        for tool_instance in self._instances.values():
            try:
                await tool_instance.cleanup()
            except Exception as e:
                self.logger.error(f"清理工具 {tool_instance.metadata.tool_id} 失败: {str(e)}")
        
        self._instances.clear()


# 全局工具注册中心
tool_registry = ToolRegistry()