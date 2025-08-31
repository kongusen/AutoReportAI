"""
Intelligent Result Storage

智能结果存储系统，负责高效存储、检索和管理各类分析结果
支持智能索引、压缩存储、过期清理等功能
"""

import asyncio
import gzip
import json
import logging
import pickle
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from contextlib import asynccontextmanager
import hashlib
import threading

from .file_storage_service import file_storage_service
from ...llm_agents.monitoring.performance_monitor import get_performance_monitor, monitor_performance

logger = logging.getLogger(__name__)


class ResultType(Enum):
    """结果类型"""
    PLACEHOLDER_ANALYSIS = "placeholder_analysis"
    SQL_GENERATION = "sql_generation"
    QUALITY_ASSESSMENT = "quality_assessment"
    TEMPLATE_ANALYSIS = "template_analysis"
    CONTEXT_ANALYSIS = "context_analysis"
    REPORT_GENERATION = "report_generation"


class StoragePolicy(Enum):
    """存储策略"""
    MEMORY_ONLY = "memory_only"      # 仅内存
    PERSISTENT = "persistent"        # 持久化
    COMPRESSED = "compressed"        # 压缩存储
    DISTRIBUTED = "distributed"     # 分布式存储


class CompressionType(Enum):
    """压缩类型"""
    NONE = "none"
    GZIP = "gzip"
    PICKLE = "pickle"
    JSON = "json"


@dataclass
class StorageMetadata:
    """存储元数据"""
    result_id: str
    result_type: ResultType
    context_id: str
    storage_policy: StoragePolicy = StoragePolicy.PERSISTENT
    compression: CompressionType = CompressionType.GZIP
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    size_bytes: int = 0
    checksum: str = ""
    tags: List[str] = field(default_factory=list)
    priority: int = 1  # 1-10, 10为最高优先级


@dataclass
class StorageResult:
    """存储结果"""
    result_id: str
    data: Any
    metadata: StorageMetadata
    storage_location: Optional[str] = None
    cached: bool = False


class InMemoryStorage:
    """内存存储管理器"""
    
    def __init__(self, max_memory_mb: int = 500):
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.storage: Dict[str, Any] = {}
        self.metadata_cache: Dict[str, StorageMetadata] = {}
        self.access_times: Dict[str, float] = {}
        self.lock = threading.RLock()
        self._current_size = 0
    
    def get_current_size(self) -> int:
        """获取当前使用的内存大小"""
        return self._current_size
    
    def store(self, result_id: str, data: Any, metadata: StorageMetadata) -> bool:
        """存储到内存"""
        try:
            with self.lock:
                # 序列化数据以计算大小
                serialized_data = pickle.dumps(data)
                data_size = len(serialized_data)
                
                # 检查是否需要清理内存
                if self._current_size + data_size > self.max_memory_bytes:
                    self._evict_lru_items(data_size)
                
                # 如果仍然超过限制，拒绝存储
                if self._current_size + data_size > self.max_memory_bytes:
                    logger.warning(f"内存不足，无法存储结果: {result_id}")
                    return False
                
                # 存储数据
                self.storage[result_id] = data
                self.metadata_cache[result_id] = metadata
                self.access_times[result_id] = time.time()
                self._current_size += data_size
                
                logger.debug(f"结果存储到内存: {result_id}, 大小: {data_size} bytes")
                return True
                
        except Exception as e:
            logger.error(f"内存存储失败: {e}")
            return False
    
    def retrieve(self, result_id: str) -> Optional[Tuple[Any, StorageMetadata]]:
        """从内存检索"""
        try:
            with self.lock:
                if result_id not in self.storage:
                    return None
                
                # 更新访问时间和计数
                self.access_times[result_id] = time.time()
                if result_id in self.metadata_cache:
                    self.metadata_cache[result_id].accessed_at = datetime.now()
                    self.metadata_cache[result_id].access_count += 1
                
                data = self.storage[result_id]
                metadata = self.metadata_cache.get(result_id)
                
                return data, metadata
                
        except Exception as e:
            logger.error(f"内存检索失败: {e}")
            return None
    
    def remove(self, result_id: str) -> bool:
        """从内存删除"""
        try:
            with self.lock:
                if result_id not in self.storage:
                    return False
                
                # 计算释放的大小
                data = self.storage[result_id]
                data_size = len(pickle.dumps(data))
                
                # 删除数据
                del self.storage[result_id]
                if result_id in self.metadata_cache:
                    del self.metadata_cache[result_id]
                if result_id in self.access_times:
                    del self.access_times[result_id]
                
                self._current_size -= data_size
                
                logger.debug(f"从内存删除结果: {result_id}")
                return True
                
        except Exception as e:
            logger.error(f"内存删除失败: {e}")
            return False
    
    def _evict_lru_items(self, needed_size: int):
        """清理最少使用的项目"""
        # 按访问时间排序，最旧的在前
        sorted_items = sorted(self.access_times.items(), key=lambda x: x[1])
        
        freed_size = 0
        for result_id, _ in sorted_items:
            if freed_size >= needed_size:
                break
                
            if result_id in self.storage:
                data = self.storage[result_id]
                data_size = len(pickle.dumps(data))
                
                del self.storage[result_id]
                if result_id in self.metadata_cache:
                    del self.metadata_cache[result_id]
                del self.access_times[result_id]
                
                self._current_size -= data_size
                freed_size += data_size
                
                logger.debug(f"LRU清理: {result_id}, 释放: {data_size} bytes")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计"""
        with self.lock:
            return {
                "total_items": len(self.storage),
                "current_size_bytes": self._current_size,
                "current_size_mb": self._current_size / 1024 / 1024,
                "max_size_mb": self.max_memory_bytes / 1024 / 1024,
                "usage_percentage": (self._current_size / self.max_memory_bytes) * 100
            }


class ResultDatabase:
    """结果数据库管理器"""
    
    def __init__(self, db_path: str = "intelligent_results.db"):
        self.db_path = Path(db_path)
        self._connection_pool = {}
        self._lock = asyncio.Lock()
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS result_metadata (
                    result_id TEXT PRIMARY KEY,
                    result_type TEXT NOT NULL,
                    context_id TEXT NOT NULL,
                    storage_policy TEXT NOT NULL,
                    compression TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    accessed_at TEXT NOT NULL,
                    expires_at TEXT,
                    access_count INTEGER DEFAULT 0,
                    size_bytes INTEGER DEFAULT 0,
                    checksum TEXT,
                    tags TEXT,  -- JSON array
                    priority INTEGER DEFAULT 1,
                    storage_location TEXT,
                    is_cached BOOLEAN DEFAULT FALSE
                );
                
                CREATE TABLE IF NOT EXISTS result_data (
                    result_id TEXT PRIMARY KEY,
                    compressed_data BLOB,
                    FOREIGN KEY (result_id) REFERENCES result_metadata (result_id)
                );
                
                CREATE TABLE IF NOT EXISTS result_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    result_id TEXT NOT NULL,
                    index_key TEXT NOT NULL,
                    index_value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (result_id) REFERENCES result_metadata (result_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_result_type ON result_metadata (result_type);
                CREATE INDEX IF NOT EXISTS idx_context_id ON result_metadata (context_id);
                CREATE INDEX IF NOT EXISTS idx_created_at ON result_metadata (created_at);
                CREATE INDEX IF NOT EXISTS idx_expires_at ON result_metadata (expires_at);
                CREATE INDEX IF NOT EXISTS idx_access_count ON result_metadata (access_count);
                CREATE INDEX IF NOT EXISTS idx_index_key ON result_index (index_key, index_value);
            """)
            conn.commit()
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接"""
        async with self._lock:
            thread_id = asyncio.current_task()
            if thread_id not in self._connection_pool:
                self._connection_pool[thread_id] = sqlite3.connect(self.db_path)
                self._connection_pool[thread_id].row_factory = sqlite3.Row
            
            conn = self._connection_pool[thread_id]
            try:
                yield conn
            finally:
                conn.commit()
    
    async def save_metadata(self, metadata: StorageMetadata, storage_location: Optional[str] = None, is_cached: bool = False):
        """保存元数据"""
        async with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO result_metadata (
                    result_id, result_type, context_id, storage_policy, compression,
                    created_at, updated_at, accessed_at, expires_at, access_count,
                    size_bytes, checksum, tags, priority, storage_location, is_cached
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.result_id,
                metadata.result_type.value,
                metadata.context_id,
                metadata.storage_policy.value,
                metadata.compression.value,
                metadata.created_at.isoformat(),
                metadata.updated_at.isoformat(),
                metadata.accessed_at.isoformat(),
                metadata.expires_at.isoformat() if metadata.expires_at else None,
                metadata.access_count,
                metadata.size_bytes,
                metadata.checksum,
                json.dumps(metadata.tags),
                metadata.priority,
                storage_location,
                is_cached
            ))
    
    async def get_metadata(self, result_id: str) -> Optional[StorageMetadata]:
        """获取元数据"""
        async with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM result_metadata WHERE result_id = ?
            """, (result_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return StorageMetadata(
                result_id=row['result_id'],
                result_type=ResultType(row['result_type']),
                context_id=row['context_id'],
                storage_policy=StoragePolicy(row['storage_policy']),
                compression=CompressionType(row['compression']),
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                accessed_at=datetime.fromisoformat(row['accessed_at']),
                expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                access_count=row['access_count'],
                size_bytes=row['size_bytes'],
                checksum=row['checksum'] or "",
                tags=json.loads(row['tags']) if row['tags'] else [],
                priority=row['priority']
            )
    
    async def save_data(self, result_id: str, compressed_data: bytes):
        """保存压缩数据"""
        async with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO result_data (result_id, compressed_data)
                VALUES (?, ?)
            """, (result_id, compressed_data))
    
    async def get_data(self, result_id: str) -> Optional[bytes]:
        """获取压缩数据"""
        async with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT compressed_data FROM result_data WHERE result_id = ?
            """, (result_id,))
            
            row = cursor.fetchone()
            if row:
                return row['compressed_data']
            return None
    
    async def update_access(self, result_id: str):
        """更新访问信息"""
        async with self.get_connection() as conn:
            conn.execute("""
                UPDATE result_metadata 
                SET accessed_at = ?, access_count = access_count + 1
                WHERE result_id = ?
            """, (datetime.now().isoformat(), result_id))
    
    async def create_index(self, result_id: str, index_key: str, index_value: str):
        """创建索引"""
        async with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO result_index (result_id, index_key, index_value, created_at)
                VALUES (?, ?, ?, ?)
            """, (result_id, index_key, index_value, datetime.now().isoformat()))
    
    async def search_by_index(self, index_key: str, index_value: str, limit: int = 50) -> List[str]:
        """根据索引搜索"""
        async with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT DISTINCT ri.result_id 
                FROM result_index ri
                JOIN result_metadata rm ON ri.result_id = rm.result_id
                WHERE ri.index_key = ? AND ri.index_value = ?
                ORDER BY rm.created_at DESC
                LIMIT ?
            """, (index_key, index_value, limit))
            
            return [row['result_id'] for row in cursor.fetchall()]
    
    async def cleanup_expired(self) -> int:
        """清理过期结果"""
        now = datetime.now().isoformat()
        
        async with self.get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM result_data 
                WHERE result_id IN (
                    SELECT result_id FROM result_metadata 
                    WHERE expires_at IS NOT NULL AND expires_at < ?
                )
            """, (now,))
            
            deleted_data = cursor.rowcount
            
            cursor = conn.execute("""
                DELETE FROM result_index 
                WHERE result_id IN (
                    SELECT result_id FROM result_metadata 
                    WHERE expires_at IS NOT NULL AND expires_at < ?
                )
            """, (now,))
            
            cursor = conn.execute("""
                DELETE FROM result_metadata 
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (now,))
            
            deleted_metadata = cursor.rowcount
            
            return deleted_metadata
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计"""
        async with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_results,
                    SUM(size_bytes) as total_size_bytes,
                    AVG(access_count) as avg_access_count,
                    result_type,
                    COUNT(*) as type_count
                FROM result_metadata
                GROUP BY result_type
            """)
            
            type_stats = {}
            total_results = 0
            total_size = 0
            total_access = 0
            
            for row in cursor.fetchall():
                if row['result_type']:
                    type_stats[row['result_type']] = row['type_count']
                if row['total_results']:
                    total_results = row['total_results']
                if row['total_size_bytes']:
                    total_size = row['total_size_bytes']
                if row['avg_access_count']:
                    total_access = row['avg_access_count']
            
            # 获取过期统计
            cursor = conn.execute("""
                SELECT COUNT(*) as expired_count
                FROM result_metadata 
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (datetime.now().isoformat(),))
            
            expired_count = cursor.fetchone()['expired_count']
            
            return {
                "total_results": total_results,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / 1024 / 1024 if total_size else 0,
                "average_access_count": total_access,
                "type_distribution": type_stats,
                "expired_count": expired_count
            }


class IntelligentResultStorage:
    """智能结果存储系统主类"""
    
    def __init__(self, max_memory_mb: int = 500, db_path: str = "intelligent_results.db"):
        self.memory_storage = InMemoryStorage(max_memory_mb)
        self.database = ResultDatabase(db_path)
        self.performance_monitor = get_performance_monitor()
        self.compression_engines = {
            CompressionType.GZIP: self._gzip_compress,
            CompressionType.PICKLE: self._pickle_compress,
            CompressionType.JSON: self._json_compress,
            CompressionType.NONE: self._no_compress
        }
        self.decompression_engines = {
            CompressionType.GZIP: self._gzip_decompress,
            CompressionType.PICKLE: self._pickle_decompress,
            CompressionType.JSON: self._json_decompress,
            CompressionType.NONE: self._no_decompress
        }
    
    @monitor_performance("intelligent_result_storage", "store_result")
    async def store_result(
        self,
        result_id: str,
        data: Any,
        result_type: ResultType,
        context_id: str,
        storage_policy: StoragePolicy = StoragePolicy.PERSISTENT,
        compression: CompressionType = CompressionType.GZIP,
        expires_in_hours: Optional[int] = None,
        tags: List[str] = None,
        priority: int = 1
    ) -> bool:
        """
        存储结果
        
        Args:
            result_id: 结果ID
            data: 要存储的数据
            result_type: 结果类型
            context_id: 上下文ID
            storage_policy: 存储策略
            compression: 压缩类型
            expires_in_hours: 过期时间（小时）
            tags: 标签列表
            priority: 优先级
            
        Returns:
            存储是否成功
        """
        try:
            logger.info(f"存储结果: {result_id}, 类型: {result_type.value}")
            
            # 创建元数据
            expires_at = None
            if expires_in_hours:
                expires_at = datetime.now() + timedelta(hours=expires_in_hours)
            
            metadata = StorageMetadata(
                result_id=result_id,
                result_type=result_type,
                context_id=context_id,
                storage_policy=storage_policy,
                compression=compression,
                expires_at=expires_at,
                tags=tags or [],
                priority=priority
            )
            
            # 压缩数据
            compressed_data = await self._compress_data(data, compression)
            metadata.size_bytes = len(compressed_data)
            metadata.checksum = hashlib.sha256(compressed_data).hexdigest()
            
            storage_location = None
            is_cached = False
            
            # 根据存储策略选择存储位置
            if storage_policy == StoragePolicy.MEMORY_ONLY:
                # 仅内存存储
                success = self.memory_storage.store(result_id, data, metadata)
                is_cached = success
                
            elif storage_policy == StoragePolicy.PERSISTENT:
                # 持久化存储
                await self.database.save_data(result_id, compressed_data)
                
                # 同时尝试缓存到内存
                if self._should_cache_to_memory(metadata):
                    is_cached = self.memory_storage.store(result_id, data, metadata)
                    
            elif storage_policy == StoragePolicy.COMPRESSED:
                # 压缩持久化存储
                await self.database.save_data(result_id, compressed_data)
                
            elif storage_policy == StoragePolicy.DISTRIBUTED:
                # 分布式存储（使用文件存储服务）
                from io import BytesIO
                storage_result = file_storage_service.upload_file(
                    file_data=BytesIO(compressed_data),
                    original_filename=f"{result_id}.dat",
                    file_type="intelligent_results",
                    content_type="application/octet-stream"
                )
                storage_location = storage_result["file_path"]
            
            # 保存元数据
            await self.database.save_metadata(metadata, storage_location, is_cached)
            
            # 创建索引
            await self._create_indexes(result_id, data, metadata)
            
            logger.info(f"结果存储成功: {result_id}")
            return True
            
        except Exception as e:
            logger.error(f"存储结果失败: {e}")
            return False
    
    @monitor_performance("intelligent_result_storage", "retrieve_result")
    async def retrieve_result(self, result_id: str) -> Optional[StorageResult]:
        """
        检索结果
        
        Args:
            result_id: 结果ID
            
        Returns:
            存储结果对象或None
        """
        try:
            logger.debug(f"检索结果: {result_id}")
            
            # 获取元数据
            metadata = await self.database.get_metadata(result_id)
            if not metadata:
                logger.warning(f"结果不存在: {result_id}")
                return None
            
            # 检查是否过期
            if metadata.expires_at and datetime.now() > metadata.expires_at:
                logger.warning(f"结果已过期: {result_id}")
                await self._delete_result(result_id)
                return None
            
            data = None
            cached = False
            
            # 首先尝试从内存获取
            memory_result = self.memory_storage.retrieve(result_id)
            if memory_result:
                data, _ = memory_result
                cached = True
                logger.debug(f"从内存获取结果: {result_id}")
                
            else:
                # 根据存储策略从不同位置获取
                if metadata.storage_policy == StoragePolicy.DISTRIBUTED:
                    # 从分布式存储获取
                    async with self.database.get_connection() as conn:
                        cursor = conn.execute("""
                            SELECT storage_location FROM result_metadata WHERE result_id = ?
                        """, (result_id,))
                        row = cursor.fetchone()
                        
                        if row and row['storage_location']:
                            file_data, _ = file_storage_service.download_file(row['storage_location'])
                            data = await self._decompress_data(file_data, metadata.compression)
                
                else:
                    # 从数据库获取
                    compressed_data = await self.database.get_data(result_id)
                    if compressed_data:
                        data = await self._decompress_data(compressed_data, metadata.compression)
                
                # 如果获取成功且符合缓存条件，缓存到内存
                if data and self._should_cache_to_memory(metadata):
                    self.memory_storage.store(result_id, data, metadata)
                    cached = True
            
            if data is None:
                logger.error(f"无法获取结果数据: {result_id}")
                return None
            
            # 更新访问信息
            await self.database.update_access(result_id)
            
            return StorageResult(
                result_id=result_id,
                data=data,
                metadata=metadata,
                cached=cached
            )
            
        except Exception as e:
            logger.error(f"检索结果失败: {e}")
            return None
    
    async def _delete_result(self, result_id: str) -> bool:
        """删除结果"""
        try:
            # 从内存删除
            self.memory_storage.remove(result_id)
            
            # 从数据库删除
            async with self.database.get_connection() as conn:
                # 获取存储位置信息
                cursor = conn.execute("""
                    SELECT storage_location FROM result_metadata WHERE result_id = ?
                """, (result_id,))
                row = cursor.fetchone()
                
                if row and row['storage_location']:
                    # 删除分布式存储文件
                    file_storage_service.delete_file(row['storage_location'])
                
                # 删除数据库记录
                conn.execute("DELETE FROM result_data WHERE result_id = ?", (result_id,))
                conn.execute("DELETE FROM result_index WHERE result_id = ?", (result_id,))
                conn.execute("DELETE FROM result_metadata WHERE result_id = ?", (result_id,))
            
            return True
            
        except Exception as e:
            logger.error(f"删除结果失败: {e}")
            return False
    
    async def search_results(
        self,
        result_type: Optional[ResultType] = None,
        context_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        index_filters: Optional[Dict[str, str]] = None,
        limit: int = 50
    ) -> List[StorageResult]:
        """
        搜索结果
        
        Args:
            result_type: 结果类型过滤
            context_id: 上下文ID过滤
            tags: 标签过滤
            index_filters: 索引过滤
            limit: 返回数量限制
            
        Returns:
            搜索结果列表
        """
        try:
            result_ids = set()
            
            # 基于索引搜索
            if index_filters:
                for index_key, index_value in index_filters.items():
                    ids = await self.database.search_by_index(index_key, index_value, limit)
                    if result_ids:
                        result_ids &= set(ids)  # 交集
                    else:
                        result_ids = set(ids)
            
            # 基于元数据搜索
            async with self.database.get_connection() as conn:
                conditions = []
                params = []
                
                if result_type:
                    conditions.append("result_type = ?")
                    params.append(result_type.value)
                
                if context_id:
                    conditions.append("context_id = ?")
                    params.append(context_id)
                
                if tags:
                    # 简单的标签匹配
                    tag_conditions = []
                    for tag in tags:
                        tag_conditions.append("tags LIKE ?")
                        params.append(f'%"{tag}"%')
                    
                    if tag_conditions:
                        conditions.append(f"({' OR '.join(tag_conditions)})")
                
                where_clause = ""
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)
                
                # 如果有索引过滤结果，限制搜索范围
                if result_ids:
                    id_placeholders = ",".join("?" for _ in result_ids)
                    if where_clause:
                        where_clause += f" AND result_id IN ({id_placeholders})"
                    else:
                        where_clause = f"WHERE result_id IN ({id_placeholders})"
                    params.extend(list(result_ids))
                
                params.append(limit)
                
                cursor = conn.execute(f"""
                    SELECT result_id FROM result_metadata {where_clause}
                    ORDER BY priority DESC, created_at DESC
                    LIMIT ?
                """, params)
                
                found_ids = [row['result_id'] for row in cursor.fetchall()]
            
            # 检索结果数据
            results = []
            for result_id in found_ids:
                result = await self.retrieve_result(result_id)
                if result:
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"搜索结果失败: {e}")
            return []
    
    def _should_cache_to_memory(self, metadata: StorageMetadata) -> bool:
        """判断是否应该缓存到内存"""
        # 基于优先级、访问频率、大小等决策
        if metadata.priority >= 8:  # 高优先级
            return True
        
        if metadata.size_bytes > 10 * 1024 * 1024:  # 大于10MB不缓存
            return False
        
        if metadata.access_count > 5:  # 访问频繁
            return True
        
        if metadata.result_type in [ResultType.PLACEHOLDER_ANALYSIS, ResultType.TEMPLATE_ANALYSIS]:
            return True  # 常用类型
        
        return False
    
    async def _create_indexes(self, result_id: str, data: Any, metadata: StorageMetadata):
        """创建智能索引"""
        try:
            # 基于结果类型创建索引
            await self.database.create_index(result_id, "result_type", metadata.result_type.value)
            await self.database.create_index(result_id, "context_id", metadata.context_id)
            
            # 基于标签创建索引
            for tag in metadata.tags:
                await self.database.create_index(result_id, "tag", tag)
            
            # 基于数据内容创建索引
            if isinstance(data, dict):
                # 为字典类型数据的关键字段创建索引
                for key, value in data.items():
                    if isinstance(value, (str, int, float)) and len(str(value)) < 100:
                        await self.database.create_index(result_id, f"data.{key}", str(value))
                        
        except Exception as e:
            logger.warning(f"创建索引失败: {e}")
    
    async def _compress_data(self, data: Any, compression: CompressionType) -> bytes:
        """压缩数据"""
        compress_func = self.compression_engines.get(compression)
        if compress_func:
            return await compress_func(data)
        else:
            raise ValueError(f"不支持的压缩类型: {compression}")
    
    async def _decompress_data(self, compressed_data: bytes, compression: CompressionType) -> Any:
        """解压缩数据"""
        decompress_func = self.decompression_engines.get(compression)
        if decompress_func:
            return await decompress_func(compressed_data)
        else:
            raise ValueError(f"不支持的压缩类型: {compression}")
    
    async def _gzip_compress(self, data: Any) -> bytes:
        """GZIP压缩"""
        serialized = pickle.dumps(data)
        return gzip.compress(serialized)
    
    async def _gzip_decompress(self, compressed_data: bytes) -> Any:
        """GZIP解压缩"""
        decompressed = gzip.decompress(compressed_data)
        return pickle.loads(decompressed)
    
    async def _pickle_compress(self, data: Any) -> bytes:
        """Pickle序列化"""
        return pickle.dumps(data)
    
    async def _pickle_decompress(self, compressed_data: bytes) -> Any:
        """Pickle反序列化"""
        return pickle.loads(compressed_data)
    
    async def _json_compress(self, data: Any) -> bytes:
        """JSON序列化"""
        json_str = json.dumps(data, ensure_ascii=False, default=str)
        return gzip.compress(json_str.encode('utf-8'))
    
    async def _json_decompress(self, compressed_data: bytes) -> Any:
        """JSON反序列化"""
        decompressed = gzip.decompress(compressed_data)
        json_str = decompressed.decode('utf-8')
        return json.loads(json_str)
    
    async def _no_compress(self, data: Any) -> bytes:
        """无压缩"""
        return pickle.dumps(data)
    
    async def _no_decompress(self, compressed_data: bytes) -> Any:
        """无解压"""
        return pickle.loads(compressed_data)
    
    async def cleanup_expired_results(self) -> Dict[str, Any]:
        """清理过期结果"""
        try:
            deleted_count = await self.database.cleanup_expired()
            
            # 也清理内存中的过期项
            expired_memory_items = []
            current_time = datetime.now()
            
            for result_id, metadata in self.memory_storage.metadata_cache.items():
                if metadata.expires_at and current_time > metadata.expires_at:
                    expired_memory_items.append(result_id)
            
            for result_id in expired_memory_items:
                self.memory_storage.remove(result_id)
            
            return {
                "database_deleted": deleted_count,
                "memory_deleted": len(expired_memory_items),
                "cleanup_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"清理过期结果失败: {e}")
            raise
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            db_stats = await self.database.get_statistics()
            memory_stats = self.memory_storage.get_stats()
            
            return {
                "database": db_stats,
                "memory": memory_stats,
                "total_size_mb": db_stats.get("total_size_mb", 0) + memory_stats.get("current_size_mb", 0),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取存储统计失败: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 测试存储和检索
            test_data = {"test": "health_check", "timestamp": datetime.now().isoformat()}
            test_id = f"health_check_{int(time.time())}"
            
            # 存储测试
            store_success = await self.store_result(
                result_id=test_id,
                data=test_data,
                result_type=ResultType.QUALITY_ASSESSMENT,
                context_id="health_check",
                storage_policy=StoragePolicy.MEMORY_ONLY,
                expires_in_hours=1
            )
            
            # 检索测试
            retrieve_success = False
            if store_success:
                result = await self.retrieve_result(test_id)
                retrieve_success = result is not None and result.data == test_data
            
            # 清理测试数据
            await self._delete_result(test_id)
            
            return {
                "status": "healthy" if store_success and retrieve_success else "degraded",
                "store_test": store_success,
                "retrieve_test": retrieve_success,
                "memory_storage": self.memory_storage.get_stats(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# 全局智能结果存储实例
_intelligent_result_storage: Optional[IntelligentResultStorage] = None

def get_intelligent_result_storage() -> IntelligentResultStorage:
    """获取全局智能结果存储实例"""
    global _intelligent_result_storage
    if _intelligent_result_storage is None:
        _intelligent_result_storage = IntelligentResultStorage()
    return _intelligent_result_storage