"""
占位符结果存储

持久化存储占位符分析结果
"""

import logging
import json
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import aiofiles
import asyncio
import os

logger = logging.getLogger(__name__)

@dataclass
class StoredResult:
    """存储的结果"""
    placeholder_id: str
    content_hash: str
    context_hash: str
    result_data: Dict[str, Any]
    analysis_timestamp: datetime
    storage_timestamp: datetime
    version: str
    metadata: Dict[str, Any]
    file_path: str

class ResultStorage:
    """占位符结果存储"""
    
    def __init__(self, 
                 storage_directory: str = "data/placeholder_results",
                 max_versions_per_placeholder: int = 10,
                 retention_days: int = 90,
                 compression_enabled: bool = True):
        """
        初始化结果存储
        
        Args:
            storage_directory: 存储目录
            max_versions_per_placeholder: 每个占位符最大版本数
            retention_days: 数据保留天数
            compression_enabled: 是否启用压缩
        """
        self.storage_directory = Path(storage_directory)
        self.max_versions_per_placeholder = max_versions_per_placeholder
        self.retention_days = retention_days
        self.compression_enabled = compression_enabled
        
        # 创建存储目录
        self.storage_directory.mkdir(parents=True, exist_ok=True)
        
        # 索引文件
        self.index_file = self.storage_directory / "index.json"
        
        # 内存索引
        self._index: Dict[str, List[StoredResult]] = {}
        self._lock = asyncio.Lock()
        
        # 统计信息
        self.stats = {
            'total_results': 0,
            'total_placeholders': 0,
            'storage_size_bytes': 0,
            'last_cleanup': datetime.now()
        }
        
        # 初始化时加载索引
        asyncio.create_task(self._load_index())
        
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _load_index(self):
        """加载索引文件"""
        try:
            if self.index_file.exists():
                async with aiofiles.open(self.index_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    index_data = json.loads(content)
                
                # 重建内存索引
                for placeholder_id, results_data in index_data.items():
                    self._index[placeholder_id] = [
                        StoredResult(
                            placeholder_id=r['placeholder_id'],
                            content_hash=r['content_hash'],
                            context_hash=r['context_hash'],
                            result_data=r['result_data'],
                            analysis_timestamp=datetime.fromisoformat(r['analysis_timestamp']),
                            storage_timestamp=datetime.fromisoformat(r['storage_timestamp']),
                            version=r['version'],
                            metadata=r['metadata'],
                            file_path=r['file_path']
                        )
                        for r in results_data
                    ]
                
                # 更新统计信息
                await self._update_stats()
                
                logger.info(f"加载了 {len(self._index)} 个占位符的存储索引")
        
        except Exception as e:
            logger.error(f"加载索引失败: {e}")
            self._index = {}
    
    async def _save_index(self):
        """保存索引文件"""
        try:
            # 转换为可序列化的格式
            index_data = {}
            for placeholder_id, results in self._index.items():
                index_data[placeholder_id] = [
                    {
                        'placeholder_id': r.placeholder_id,
                        'content_hash': r.content_hash,
                        'context_hash': r.context_hash,
                        'result_data': r.result_data,
                        'analysis_timestamp': r.analysis_timestamp.isoformat(),
                        'storage_timestamp': r.storage_timestamp.isoformat(),
                        'version': r.version,
                        'metadata': r.metadata,
                        'file_path': r.file_path
                    }
                    for r in results
                ]
            
            async with aiofiles.open(self.index_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(index_data, ensure_ascii=False, indent=2))
            
        except Exception as e:
            logger.error(f"保存索引失败: {e}")
    
    def _generate_content_hash(self, placeholder_content: str) -> str:
        """生成内容哈希"""
        return hashlib.md5(placeholder_content.encode('utf-8')).hexdigest()
    
    def _generate_context_hash(self, context_data: Dict[str, Any]) -> str:
        """生成上下文哈希"""
        context_str = json.dumps(context_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(context_str.encode('utf-8')).hexdigest()
    
    def _generate_file_path(self, placeholder_id: str, version: str) -> str:
        """生成文件路径"""
        # 按占位符ID分目录存储
        placeholder_dir = self.storage_directory / placeholder_id[:2] / placeholder_id
        placeholder_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{version}.json"
        if self.compression_enabled:
            filename += ".gz"
        
        return str(placeholder_dir / filename)
    
    async def store_result(self, 
                          placeholder_id: str,
                          placeholder_content: str,
                          context_data: Dict[str, Any],
                          result_data: Dict[str, Any],
                          analysis_timestamp: Optional[datetime] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        存储分析结果
        
        Returns:
            str: 存储版本号
        """
        async with self._lock:
            # 生成哈希和版本
            content_hash = self._generate_content_hash(placeholder_content)
            context_hash = self._generate_context_hash(context_data)
            version = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{content_hash[:8]}"
            
            # 生成文件路径
            file_path = self._generate_file_path(placeholder_id, version)
            
            # 创建存储结果对象
            stored_result = StoredResult(
                placeholder_id=placeholder_id,
                content_hash=content_hash,
                context_hash=context_hash,
                result_data=result_data,
                analysis_timestamp=analysis_timestamp or datetime.now(),
                storage_timestamp=datetime.now(),
                version=version,
                metadata=metadata or {},
                file_path=file_path
            )
            
            # 保存到文件
            await self._save_result_to_file(stored_result, placeholder_content, context_data)
            
            # 更新内存索引
            if placeholder_id not in self._index:
                self._index[placeholder_id] = []
            
            self._index[placeholder_id].append(stored_result)
            
            # 限制版本数量
            if len(self._index[placeholder_id]) > self.max_versions_per_placeholder:
                # 删除最旧的版本
                oldest = self._index[placeholder_id].pop(0)
                await self._delete_result_file(oldest.file_path)
            
            # 保存索引
            await self._save_index()
            
            # 更新统计信息
            await self._update_stats()
            
            logger.debug(f"结果已存储: {placeholder_id} - {version}")
            return version
    
    async def _save_result_to_file(self, 
                                  stored_result: StoredResult,
                                  placeholder_content: str,
                                  context_data: Dict[str, Any]):
        """保存结果到文件"""
        try:
            # 准备数据
            file_data = {
                'placeholder_content': placeholder_content,
                'context_data': context_data,
                'result_data': stored_result.result_data,
                'metadata': {
                    'placeholder_id': stored_result.placeholder_id,
                    'content_hash': stored_result.content_hash,
                    'context_hash': stored_result.context_hash,
                    'analysis_timestamp': stored_result.analysis_timestamp.isoformat(),
                    'storage_timestamp': stored_result.storage_timestamp.isoformat(),
                    'version': stored_result.version,
                    **stored_result.metadata
                }
            }
            
            json_data = json.dumps(file_data, ensure_ascii=False, indent=2)
            
            if self.compression_enabled:
                import gzip
                # 使用gzip压缩
                async with aiofiles.open(stored_result.file_path, 'wb') as f:
                    compressed_data = gzip.compress(json_data.encode('utf-8'))
                    await f.write(compressed_data)
            else:
                async with aiofiles.open(stored_result.file_path, 'w', encoding='utf-8') as f:
                    await f.write(json_data)
            
        except Exception as e:
            logger.error(f"保存结果文件失败: {e}")
            raise
    
    async def get_result(self, 
                        placeholder_id: str,
                        version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取存储的结果
        
        Args:
            placeholder_id: 占位符ID
            version: 版本号，如果为None则返回最新版本
        """
        async with self._lock:
            if placeholder_id not in self._index:
                return None
            
            results = self._index[placeholder_id]
            if not results:
                return None
            
            # 选择版本
            if version is None:
                # 返回最新版本
                target_result = results[-1]
            else:
                # 查找指定版本
                target_result = None
                for result in results:
                    if result.version == version:
                        target_result = result
                        break
                
                if target_result is None:
                    return None
            
            # 从文件加载数据
            return await self._load_result_from_file(target_result.file_path)
    
    async def _load_result_from_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """从文件加载结果"""
        try:
            if self.compression_enabled:
                import gzip
                async with aiofiles.open(file_path, 'rb') as f:
                    compressed_data = await f.read()
                    json_data = gzip.decompress(compressed_data).decode('utf-8')
            else:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    json_data = await f.read()
            
            return json.loads(json_data)
        
        except Exception as e:
            logger.error(f"加载结果文件失败: {e}")
            return None
    
    async def get_versions(self, placeholder_id: str) -> List[Dict[str, Any]]:
        """获取占位符的所有版本信息"""
        async with self._lock:
            if placeholder_id not in self._index:
                return []
            
            return [
                {
                    'version': result.version,
                    'analysis_timestamp': result.analysis_timestamp.isoformat(),
                    'storage_timestamp': result.storage_timestamp.isoformat(),
                    'content_hash': result.content_hash,
                    'context_hash': result.context_hash,
                    'metadata': result.metadata
                }
                for result in self._index[placeholder_id]
            ]
    
    async def delete_placeholder_results(self, placeholder_id: str) -> bool:
        """删除占位符的所有结果"""
        async with self._lock:
            if placeholder_id not in self._index:
                return False
            
            # 删除所有文件
            results = self._index[placeholder_id]
            for result in results:
                await self._delete_result_file(result.file_path)
            
            # 从索引中移除
            del self._index[placeholder_id]
            
            # 保存索引
            await self._save_index()
            await self._update_stats()
            
            logger.info(f"删除了占位符 {placeholder_id} 的所有结果")
            return True
    
    async def delete_version(self, placeholder_id: str, version: str) -> bool:
        """删除特定版本的结果"""
        async with self._lock:
            if placeholder_id not in self._index:
                return False
            
            # 查找并删除指定版本
            results = self._index[placeholder_id]
            for i, result in enumerate(results):
                if result.version == version:
                    await self._delete_result_file(result.file_path)
                    results.pop(i)
                    
                    # 如果没有版本了，删除占位符条目
                    if not results:
                        del self._index[placeholder_id]
                    
                    await self._save_index()
                    await self._update_stats()
                    
                    logger.info(f"删除了版本: {placeholder_id} - {version}")
                    return True
            
            return False
    
    async def _delete_result_file(self, file_path: str):
        """删除结果文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"删除文件失败 {file_path}: {e}")
    
    async def _update_stats(self):
        """更新统计信息"""
        total_results = sum(len(results) for results in self._index.values())
        total_placeholders = len(self._index)
        
        # 计算存储大小
        storage_size = 0
        try:
            for root, dirs, files in os.walk(self.storage_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    storage_size += os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"计算存储大小失败: {e}")
        
        self.stats.update({
            'total_results': total_results,
            'total_placeholders': total_placeholders,
            'storage_size_bytes': storage_size
        })
    
    async def _periodic_cleanup(self):
        """定期清理过期数据"""
        while True:
            try:
                await asyncio.sleep(24 * 3600)  # 每24小时清理一次
                await self.cleanup_expired_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理任务出错: {e}")
    
    async def cleanup_expired_data(self):
        """清理过期数据"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        removed_count = 0
        
        async with self._lock:
            placeholders_to_remove = []
            
            for placeholder_id, results in self._index.items():
                # 过滤掉过期的结果
                valid_results = []
                for result in results:
                    if result.storage_timestamp >= cutoff_date:
                        valid_results.append(result)
                    else:
                        await self._delete_result_file(result.file_path)
                        removed_count += 1
                
                if valid_results:
                    self._index[placeholder_id] = valid_results
                else:
                    placeholders_to_remove.append(placeholder_id)
            
            # 删除空的占位符条目
            for placeholder_id in placeholders_to_remove:
                del self._index[placeholder_id]
            
            if removed_count > 0:
                await self._save_index()
                await self._update_stats()
                self.stats['last_cleanup'] = datetime.now()
                logger.info(f"清理了 {removed_count} 个过期结果")
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        await self._update_stats()
        
        # 计算平均版本数
        avg_versions = (self.stats['total_results'] / self.stats['total_placeholders'] 
                       if self.stats['total_placeholders'] > 0 else 0)
        
        return {
            'total_results': self.stats['total_results'],
            'total_placeholders': self.stats['total_placeholders'],
            'storage_size_bytes': self.stats['storage_size_bytes'],
            'storage_size_mb': self.stats['storage_size_bytes'] / 1024 / 1024,
            'avg_versions_per_placeholder': avg_versions,
            'last_cleanup': self.stats['last_cleanup'].isoformat(),
            'compression_enabled': self.compression_enabled,
            'retention_days': self.retention_days
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            stats = await self.get_storage_stats()
            
            health_status = "healthy"
            issues = []
            
            # 检查存储大小
            storage_mb = stats['storage_size_mb']
            if storage_mb > 1000:  # 超过1GB
                issues.append(f"存储占用过大: {storage_mb:.1f}MB")
                health_status = "warning"
            
            # 检查索引完整性
            if not self.index_file.exists():
                issues.append("索引文件缺失")
                health_status = "warning"
            
            # 检查清理状态
            last_cleanup = datetime.fromisoformat(stats['last_cleanup'])
            hours_since_cleanup = (datetime.now() - last_cleanup).total_seconds() / 3600
            if hours_since_cleanup > 48:  # 超过48小时未清理
                issues.append("清理任务可能异常")
                health_status = "warning"
            
            return {
                'status': health_status,
                'issues': issues,
                'stats': stats
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'issues': [f"健康检查失败: {str(e)}"],
                'stats': {}
            }
    
    async def shutdown(self):
        """关闭存储"""
        if hasattr(self, '_cleanup_task'):
            self._cleanup_task.cancel()
        
        # 最后保存一次索引
        await self._save_index()
        logger.info("结果存储已关闭")