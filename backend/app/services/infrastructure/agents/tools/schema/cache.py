from __future__ import annotations


from loom.interfaces.tool import BaseTool
"""
Schema 缓存工具

用于缓存和管理 Schema 信息
支持智能缓存策略和缓存优化
"""

import logging
import time
import json
from typing import Any, Dict, List, Optional, Union, Literal
from dataclasses import dataclass, asdict
from collections import OrderedDict
from pydantic import BaseModel, Field


from ...types import ToolCategory, ContextInfo

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    data: Any
    created_at: float
    accessed_at: float
    access_count: int = 0
    ttl: Optional[float] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def touch(self):
        """更新访问时间"""
        self.accessed_at = time.time()
        self.access_count += 1


@dataclass
class CacheStats:
    """缓存统计"""
    total_entries: int
    hit_count: int
    miss_count: int
    hit_rate: float
    memory_usage_bytes: int
    oldest_entry_age: float
    newest_entry_age: float
    most_accessed_entry: Optional[str] = None


class SchemaCacheTool(BaseTool):
    """Schema 缓存工具"""
    
    def __init__(self, container: Any, max_size: int = 1000, default_ttl: float = 3600):
        """
        Args:
            container: 服务容器
            max_size: 最大缓存条目数
            default_ttl: 默认TTL（秒）
        """
        super().__init__()

        self.name = "schema_cache"

        self.category = ToolCategory.SCHEMA

        self.description = "缓存和管理 Schema 信息" 
        self.container = container
        self.max_size = max_size
        self.default_ttl = default_ttl
        
        # 使用 OrderedDict 实现 LRU 缓存
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = {
            "hit_count": 0,
            "miss_count": 0,
            "total_entries": 0
        }
        
        # 使用 Pydantic 定义参数模式（args_schema）
        class SchemaCacheArgs(BaseModel):
            action: Literal["get", "set", "delete", "clear", "stats", "list"] = Field(
                description="缓存操作"
            )
            key: Optional[str] = Field(default=None, description="缓存键")
            data: Optional[Any] = Field(default=None, description="要缓存的数据（仅用于 set 操作）")
            ttl: Optional[float] = Field(default=None, description="TTL时间（秒），默认3600")
            pattern: Optional[str] = Field(default=None, description="键模式（用于 list 操作）")

        self.args_schema = SchemaCacheArgs
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数模式（基于 args_schema 生成）"""
        try:
            parameters = self.args_schema.model_json_schema()
        except Exception:
            parameters = self.args_schema.schema()  # type: ignore[attr-defined]
        return {
            "type": "function",
            "function": {
                "name": "schema_cache",
                "description": "缓存和管理 Schema 信息",
                "parameters": parameters,
            },
        }
    
    async def run(
        self,
        action: str,
        key: Optional[str] = None,
        data: Optional[Any] = None,
        ttl: Optional[float] = None,
        pattern: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行缓存操作

        Args:
            action: 缓存操作
            key: 缓存键
            data: 要缓存的数据
            ttl: TTL时间
            pattern: 键模式

        Returns:
            Dict[str, Any]: 操作结果
        """
        logger.info(f"🗄️ [SchemaCacheTool] 执行操作: {action}")

        try:
            if action == "get":
                return await self._get(key)
            elif action == "set":
                return await self._set(key, data, ttl)
            elif action == "delete":
                return await self._delete(key)
            elif action == "clear":
                return await self._clear()
            elif action == "stats":
                return await self._get_stats()
            elif action == "list":
                return await self._list(pattern)
            else:
                return {
                    "success": False,
                    "error": f"不支持的操作: {action}"
                }

        except Exception as e:
            logger.error(f"❌ [SchemaCacheTool] 操作失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """向后兼容的execute方法"""
        return await self.run(**kwargs)
    
    async def _get(self, key: str) -> Dict[str, Any]:
        """获取缓存数据"""
        if not key:
            return {
                "success": False,
                "error": "缺少缓存键"
            }
        
        # 检查缓存
        if key in self._cache:
            entry = self._cache[key]
            
            # 检查是否过期
            if entry.is_expired():
                # 删除过期条目
                del self._cache[key]
                self._stats["miss_count"] += 1
                return {
                    "success": False,
                    "error": "缓存已过期",
                    "data": None
                }
            
            # 更新访问信息
            entry.touch()
            # 移动到末尾（LRU）
            self._cache.move_to_end(key)
            
            self._stats["hit_count"] += 1
            
            return {
                "success": True,
                "data": entry.data,
                "metadata": {
                    "created_at": entry.created_at,
                    "accessed_at": entry.accessed_at,
                    "access_count": entry.access_count,
                    "ttl": entry.ttl
                }
            }
        else:
            self._stats["miss_count"] += 1
            return {
                "success": False,
                "error": "缓存未命中",
                "data": None
            }
    
    async def _set(self, key: str, data: Any, ttl: Optional[float]) -> Dict[str, Any]:
        """设置缓存数据"""
        if not key:
            return {
                "success": False,
                "error": "缺少缓存键"
            }
        
        if data is None:
            return {
                "success": False,
                "error": "缺少缓存数据"
            }
        
        # 使用默认TTL
        if ttl is None:
            ttl = self.default_ttl
        
        # 创建缓存条目
        entry = CacheEntry(
            key=key,
            data=data,
            created_at=time.time(),
            accessed_at=time.time(),
            ttl=ttl
        )
        
        # 检查缓存大小
        if len(self._cache) >= self.max_size:
            # 删除最旧的条目（LRU）
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.info(f"🗑️ 删除最旧缓存条目: {oldest_key}")
        
        # 设置缓存
        self._cache[key] = entry
        self._stats["total_entries"] += 1
        
        logger.info(f"✅ 设置缓存: {key}")
        
        return {
            "success": True,
            "metadata": {
                "key": key,
                "ttl": ttl,
                "created_at": entry.created_at,
                "cache_size": len(self._cache)
            }
        }
    
    async def _delete(self, key: str) -> Dict[str, Any]:
        """删除缓存数据"""
        if not key:
            return {
                "success": False,
                "error": "缺少缓存键"
            }
        
        if key in self._cache:
            del self._cache[key]
            self._stats["total_entries"] -= 1
            
            logger.info(f"🗑️ 删除缓存: {key}")
            
            return {
                "success": True,
                "metadata": {
                    "deleted_key": key,
                    "cache_size": len(self._cache)
                }
            }
        else:
            return {
                "success": False,
                "error": "缓存键不存在"
            }
    
    async def _clear(self) -> Dict[str, Any]:
        """清空缓存"""
        cleared_count = len(self._cache)
        self._cache.clear()
        self._stats["total_entries"] = 0
        
        logger.info(f"🧹 清空缓存: {cleared_count} 个条目")
        
        return {
            "success": True,
            "metadata": {
                "cleared_count": cleared_count,
                "cache_size": 0
            }
        }
    
    async def _get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        current_time = time.time()
        
        # 计算命中率
        total_requests = self._stats["hit_count"] + self._stats["miss_count"]
        hit_rate = self._stats["hit_count"] / total_requests if total_requests > 0 else 0
        
        # 计算内存使用（粗略估算）
        memory_usage = sum(
            len(json.dumps(entry.data, default=str)) + len(entry.key)
            for entry in self._cache.values()
        )
        
        # 计算条目年龄
        ages = [current_time - entry.created_at for entry in self._cache.values()]
        oldest_age = max(ages) if ages else 0
        newest_age = min(ages) if ages else 0
        
        # 找到访问次数最多的条目
        most_accessed = None
        if self._cache:
            most_accessed_entry = max(self._cache.values(), key=lambda e: e.access_count)
            most_accessed = most_accessed_entry.key
        
        stats = CacheStats(
            total_entries=len(self._cache),
            hit_count=self._stats["hit_count"],
            miss_count=self._stats["miss_count"],
            hit_rate=hit_rate,
            memory_usage_bytes=memory_usage,
            oldest_entry_age=oldest_age,
            newest_entry_age=newest_age,
            most_accessed_entry=most_accessed
        )
        
        return {
            "success": True,
            "stats": asdict(stats)
        }
    
    async def _list(self, pattern: Optional[str]) -> Dict[str, Any]:
        """列出缓存条目"""
        keys = list(self._cache.keys())
        
        # 应用模式过滤
        if pattern:
            import re
            regex_pattern = pattern.replace("*", ".*").replace("?", ".")
            keys = [key for key in keys if re.match(regex_pattern, key)]
        
        # 获取条目信息
        entries = []
        for key in keys:
            entry = self._cache[key]
            entries.append({
                "key": key,
                "created_at": entry.created_at,
                "accessed_at": entry.accessed_at,
                "access_count": entry.access_count,
                "ttl": entry.ttl,
                "is_expired": entry.is_expired()
            })
        
        return {
            "success": True,
            "entries": entries,
            "metadata": {
                "total_entries": len(entries),
                "pattern": pattern,
                "cache_size": len(self._cache)
            }
        }
    
    def cleanup_expired(self) -> int:
        """清理过期条目"""
        expired_keys = []
        current_time = time.time()
        
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        # 删除过期条目
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            self._stats["total_entries"] -= len(expired_keys)
            logger.info(f"🧹 清理过期缓存: {len(expired_keys)} 个条目")
        
        return len(expired_keys)
    
    def get_cache_size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)
    
    def get_memory_usage(self) -> int:
        """获取内存使用量（字节）"""
        return sum(
            len(json.dumps(entry.data, default=str)) + len(entry.key)
            for entry in self._cache.values()
        )


class SchemaCacheManager:
    """Schema 缓存管理器"""
    
    def __init__(self, container: Any, max_size: int = 1000):
        """
        Args:
            container: 服务容器
            max_size: 最大缓存大小
        """
        self.container = container
        self.cache_tool = SchemaCacheTool(container, max_size)
        self._cache_prefixes = {
            "table": "table:",
            "column": "column:",
            "relationship": "rel:",
            "constraint": "constraint:",
            "index": "index:"
        }
    
    def _build_key(self, prefix: str, identifier: str) -> str:
        """构建缓存键"""
        return f"{prefix}{identifier}"
    
    async def cache_table_info(self, table_name: str, table_info: Dict[str, Any], ttl: float = 3600):
        """缓存表信息"""
        key = self._build_key(self._cache_prefixes["table"], table_name)
        return await self.cache_tool.execute("set", key, table_info, ttl)
    
    async def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取表信息"""
        key = self._build_key(self._cache_prefixes["table"], table_name)
        result = await self.cache_tool.execute("get", key)
        return result.get("data") if result.get("success") else None
    
    async def cache_column_info(self, table_name: str, column_info: List[Dict[str, Any]], ttl: float = 3600):
        """缓存列信息"""
        key = self._build_key(self._cache_prefixes["column"], table_name)
        return await self.cache_tool.execute("set", key, column_info, ttl)
    
    async def get_column_info(self, table_name: str) -> Optional[List[Dict[str, Any]]]:
        """获取列信息"""
        key = self._build_key(self._cache_prefixes["column"], table_name)
        result = await self.cache_tool.execute("get", key)
        return result.get("data") if result.get("success") else None
    
    async def cache_relationships(self, table_name: str, relationships: List[Dict[str, Any]], ttl: float = 3600):
        """缓存关系信息"""
        key = self._build_key(self._cache_prefixes["relationship"], table_name)
        return await self.cache_tool.execute("set", key, relationships, ttl)
    
    async def get_relationships(self, table_name: str) -> Optional[List[Dict[str, Any]]]:
        """获取关系信息"""
        key = self._build_key(self._cache_prefixes["relationship"], table_name)
        result = await self.cache_tool.execute("get", key)
        return result.get("data") if result.get("success") else None
    
    async def cache_schema_summary(self, data_source_id: str, schema_summary: Dict[str, Any], ttl: float = 7200):
        """缓存 Schema 摘要"""
        key = f"schema_summary:{data_source_id}"
        return await self.cache_tool.execute("set", key, schema_summary, ttl)
    
    async def get_schema_summary(self, data_source_id: str) -> Optional[Dict[str, Any]]:
        """获取 Schema 摘要"""
        key = f"schema_summary:{data_source_id}"
        result = await self.cache_tool.execute("get", key)
        return result.get("data") if result.get("success") else None
    
    async def clear_table_cache(self, table_name: str):
        """清除表相关缓存"""
        patterns = [
            f"{self._cache_prefixes['table']}{table_name}",
            f"{self._cache_prefixes['column']}{table_name}",
            f"{self._cache_prefixes['relationship']}{table_name}",
            f"{self._cache_prefixes['constraint']}{table_name}",
            f"{self._cache_prefixes['index']}{table_name}"
        ]
        
        for pattern in patterns:
            result = await self.cache_tool.execute("list", pattern=pattern)
            if result.get("success"):
                entries = result.get("entries", [])
                for entry in entries:
                    await self.cache_tool.execute("delete", entry["key"])
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return await self.cache_tool.execute("stats")
    
    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        return self.cache_tool.cleanup_expired()


def create_schema_cache_tool(container: Any, max_size: int = 1000) -> SchemaCacheTool:
    """
    创建 Schema 缓存工具
    
    Args:
        container: 服务容器
        max_size: 最大缓存大小
        
    Returns:
        SchemaCacheTool 实例
    """
    return SchemaCacheTool(container, max_size)


def create_schema_cache_manager(container: Any, max_size: int = 1000) -> SchemaCacheManager:
    """
    创建 Schema 缓存管理器
    
    Args:
        container: 服务容器
        max_size: 最大缓存大小
        
    Returns:
        SchemaCacheManager 实例
    """
    return SchemaCacheManager(container, max_size)


# 导出
__all__ = [
    "SchemaCacheTool",
    "SchemaCacheManager",
    "CacheEntry",
    "CacheStats",
    "create_schema_cache_tool",
    "create_schema_cache_manager",
]