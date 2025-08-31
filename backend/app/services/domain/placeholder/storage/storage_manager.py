"""
存储管理器

统一管理所有占位符相关的存储
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from .result_storage import ResultStorage
from .version_storage import VersionStorage, VersionInfo
from .metadata_storage import MetadataStorage, PlaceholderMetadata, UsageMetrics

logger = logging.getLogger(__name__)

class StorageManager:
    """存储管理器"""
    
    def __init__(self,
                 result_storage_config: Optional[Dict[str, Any]] = None,
                 version_storage_config: Optional[Dict[str, Any]] = None,
                 metadata_storage_config: Optional[Dict[str, Any]] = None):
        """
        初始化存储管理器
        
        Args:
            result_storage_config: 结果存储配置
            version_storage_config: 版本存储配置
            metadata_storage_config: 元数据存储配置
        """
        # 初始化各个存储组件
        self.result_storage = ResultStorage(**(result_storage_config or {}))
        self.version_storage = VersionStorage(**(version_storage_config or {}))
        self.metadata_storage = MetadataStorage(**(metadata_storage_config or {}))
        
        # 管理器统计
        self.manager_stats = {
            'initialization_time': datetime.now(),
            'total_operations': 0,
            'storage_operations': 0,
            'retrieval_operations': 0
        }
        
        logger.info("存储管理器初始化完成")
    
    # ========== 综合存储操作 ==========
    
    async def store_complete_analysis_result(self,
                                           placeholder_id: str,
                                           placeholder_content: str,
                                           context_data: Dict[str, Any],
                                           result_data: Dict[str, Any],
                                           created_by: str = "system",
                                           change_summary: str = "",
                                           metadata: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        完整存储分析结果（包括结果、版本、元数据）
        
        Returns:
            Dict包含存储的各种ID
        """
        self.manager_stats['total_operations'] += 1
        self.manager_stats['storage_operations'] += 1
        
        try:
            # 生成哈希
            content_hash = self.result_storage._generate_content_hash(placeholder_content)
            context_hash = self.result_storage._generate_context_hash(context_data)
            
            # 1. 存储分析结果
            result_version = await self.result_storage.store_result(
                placeholder_id=placeholder_id,
                placeholder_content=placeholder_content,
                context_data=context_data,
                result_data=result_data,
                analysis_timestamp=datetime.now(),
                metadata=metadata
            )
            
            # 2. 创建版本记录
            # 获取最新版本作为父版本
            latest_version = await self.version_storage.get_latest_version(placeholder_id)
            parent_version = latest_version.version_id if latest_version else None
            
            version_id = await self.version_storage.create_version(
                placeholder_id=placeholder_id,
                result_data=result_data,
                content_hash=content_hash,
                context_hash=context_hash,
                created_by=created_by,
                change_summary=change_summary,
                parent_version=parent_version
            )
            
            # 3. 更新或创建元数据
            existing_metadata = await self.metadata_storage.get_metadata(placeholder_id)
            
            if existing_metadata:
                # 更新现有元数据
                existing_metadata.updated_at = datetime.now()
                existing_metadata.last_analyzed_at = datetime.now()
                existing_metadata.analysis_count += 1
                
                # 更新成功率（简化计算）
                if result_data.get('success', True):
                    existing_metadata.success_rate = (existing_metadata.success_rate * (existing_metadata.analysis_count - 1) + 1.0) / existing_metadata.analysis_count
                
                # 更新执行时间
                execution_time = result_data.get('execution_time_ms', 0)
                if execution_time > 0:
                    existing_metadata.avg_execution_time_ms = (
                        existing_metadata.avg_execution_time_ms * (existing_metadata.analysis_count - 1) + execution_time
                    ) / existing_metadata.analysis_count
                
                # 合并自定义属性
                if metadata:
                    existing_metadata.custom_attributes.update(metadata)
                
                await self.metadata_storage.create_or_update_metadata(existing_metadata)
            else:
                # 创建新元数据
                new_metadata = PlaceholderMetadata(
                    placeholder_id=placeholder_id,
                    name=result_data.get('placeholder_name', placeholder_id),
                    description=result_data.get('description', ''),
                    category=result_data.get('semantic_type', 'default'),
                    tags=result_data.get('tags', []),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    created_by=created_by,
                    last_analyzed_at=datetime.now(),
                    analysis_count=1,
                    success_rate=1.0 if result_data.get('success', True) else 0.0,
                    avg_execution_time_ms=result_data.get('execution_time_ms', 0),
                    data_sources=[context_data.get('data_source_id', '')],
                    templates=[context_data.get('template_id', '')],
                    custom_attributes=metadata or {}
                )
                
                await self.metadata_storage.create_or_update_metadata(new_metadata)
            
            # 4. 记录使用指标
            usage_metrics = UsageMetrics(
                placeholder_id=placeholder_id,
                date=datetime.now(),
                analysis_count=1,
                success_count=1 if result_data.get('success', True) else 0,
                error_count=0 if result_data.get('success', True) else 1,
                total_execution_time_ms=result_data.get('execution_time_ms', 0),
                avg_execution_time_ms=result_data.get('execution_time_ms', 0),
                unique_users=1,
                data_volume_processed=result_data.get('data_volume', 0)
            )
            
            await self.metadata_storage.record_usage_metrics(usage_metrics)
            
            logger.info(f"完整存储分析结果: {placeholder_id} - {version_id}")
            
            return {
                'result_version': result_version,
                'version_id': version_id,
                'placeholder_id': placeholder_id,
                'content_hash': content_hash,
                'context_hash': context_hash
            }
            
        except Exception as e:
            logger.error(f"完整存储分析结果失败: {e}")
            raise
    
    async def retrieve_complete_analysis_result(self,
                                              placeholder_id: str,
                                              version_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        完整检索分析结果（包括结果数据、版本信息、元数据）
        """
        self.manager_stats['total_operations'] += 1
        self.manager_stats['retrieval_operations'] += 1
        
        try:
            # 1. 获取结果数据
            result_data = await self.result_storage.get_result(placeholder_id, version_id)
            
            if not result_data:
                return None
            
            # 2. 获取版本信息
            if version_id:
                version_info = await self.version_storage.get_version_info(placeholder_id, version_id)
            else:
                version_info = await self.version_storage.get_latest_version(placeholder_id)
            
            # 3. 获取元数据
            metadata = await self.metadata_storage.get_metadata(placeholder_id)
            
            # 4. 组合完整结果
            complete_result = {
                'placeholder_id': placeholder_id,
                'result_data': result_data,
                'version_info': {
                    'version_id': version_info.version_id,
                    'created_at': version_info.created_at.isoformat(),
                    'created_by': version_info.created_by,
                    'change_summary': version_info.change_summary,
                    'tags': version_info.tags
                } if version_info else None,
                'metadata': {
                    'name': metadata.name,
                    'description': metadata.description,
                    'category': metadata.category,
                    'tags': metadata.tags,
                    'analysis_count': metadata.analysis_count,
                    'success_rate': metadata.success_rate,
                    'avg_execution_time_ms': metadata.avg_execution_time_ms,
                    'custom_attributes': metadata.custom_attributes
                } if metadata else None
            }
            
            return complete_result
            
        except Exception as e:
            logger.error(f"完整检索分析结果失败: {e}")
            return None
    
    # ========== 版本管理操作 ==========
    
    async def get_placeholder_versions(self, placeholder_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取占位符版本历史"""
        versions = await self.version_storage.get_version_history(placeholder_id, limit)
        
        return [
            {
                'version_id': v.version_id,
                'created_at': v.created_at.isoformat(),
                'created_by': v.created_by,
                'change_summary': v.change_summary,
                'tags': v.tags,
                'parent_version': v.parent_version
            }
            for v in versions
        ]
    
    async def compare_placeholder_versions(self, 
                                         placeholder_id: str,
                                         version1: str,
                                         version2: str) -> Optional[Dict[str, Any]]:
        """比较占位符版本"""
        diff = await self.version_storage.compare_versions(placeholder_id, version1, version2)
        
        if diff:
            return {
                'old_version': diff.old_version,
                'new_version': diff.new_version,
                'changes': diff.changes,
                'change_type': diff.change_type,
                'similarity_score': diff.similarity_score
            }
        
        return None
    
    async def tag_placeholder_version(self, 
                                    placeholder_id: str,
                                    version_id: str,
                                    tags: List[str]) -> bool:
        """为占位符版本添加标签"""
        return await self.version_storage.tag_version(placeholder_id, version_id, tags)
    
    # ========== 元数据和统计操作 ==========
    
    async def search_placeholders(self,
                                category: Optional[str] = None,
                                tags: Optional[List[str]] = None,
                                name_pattern: Optional[str] = None,
                                limit: int = 50) -> List[Dict[str, Any]]:
        """搜索占位符"""
        metadata_list = await self.metadata_storage.search_metadata(
            category=category,
            tags=tags,
            name_pattern=name_pattern,
            limit=limit
        )
        
        return [
            {
                'placeholder_id': m.placeholder_id,
                'name': m.name,
                'description': m.description,
                'category': m.category,
                'tags': m.tags,
                'created_at': m.created_at.isoformat(),
                'updated_at': m.updated_at.isoformat(),
                'analysis_count': m.analysis_count,
                'success_rate': m.success_rate,
                'avg_execution_time_ms': m.avg_execution_time_ms
            }
            for m in metadata_list
        ]
    
    async def get_usage_analytics(self,
                                 placeholder_id: Optional[str] = None,
                                 time_range_days: int = 30) -> Dict[str, Any]:
        """获取使用分析"""
        if placeholder_id:
            # 特定占位符的指标
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_range_days)
            
            metrics = await self.metadata_storage.get_usage_metrics(
                placeholder_id, start_date, end_date
            )
            
            return {
                'placeholder_id': placeholder_id,
                'time_range_days': time_range_days,
                'metrics': [
                    {
                        'date': m.date.isoformat(),
                        'analysis_count': m.analysis_count,
                        'success_count': m.success_count,
                        'error_count': m.error_count,
                        'avg_execution_time_ms': m.avg_execution_time_ms
                    }
                    for m in metrics
                ]
            }
        else:
            # 全局聚合指标
            aggregated = await self.metadata_storage.get_aggregated_metrics()
            
            # 排行榜
            top_by_usage = await self.metadata_storage.get_top_placeholders('analysis_count', 10, time_range_days)
            top_by_performance = await self.metadata_storage.get_top_placeholders('avg_execution_time_ms', 10, time_range_days)
            
            return {
                'aggregated_metrics': aggregated,
                'top_by_usage': top_by_usage,
                'top_by_performance': top_by_performance,
                'time_range_days': time_range_days
            }
    
    # ========== 管理操作 ==========
    
    async def delete_placeholder_data(self, placeholder_id: str) -> Dict[str, bool]:
        """删除占位符的所有数据"""
        results = {}
        
        try:
            # 删除结果存储
            results['result_storage'] = await self.result_storage.delete_placeholder_results(placeholder_id)
            
            # 删除版本信息（需要逐个删除版本）
            versions = await self.version_storage.get_version_history(placeholder_id)
            version_deletions = []
            for version in versions:
                deleted = await self.version_storage.delete_version(placeholder_id, version.version_id)
                version_deletions.append(deleted)
            
            results['version_storage'] = all(version_deletions) if version_deletions else True
            
            # 删除元数据
            results['metadata_storage'] = await self.metadata_storage.delete_metadata(placeholder_id)
            
            logger.info(f"删除占位符数据: {placeholder_id}, 结果: {results}")
            return results
            
        except Exception as e:
            logger.error(f"删除占位符数据失败: {e}")
            raise
    
    async def cleanup_old_data(self) -> Dict[str, Any]:
        """清理旧数据"""
        cleanup_results = {}
        
        try:
            # 清理结果存储
            await self.result_storage.cleanup_expired_data()
            cleanup_results['result_storage'] = 'completed'
            
            # 清理元数据存储
            await self.metadata_storage.cleanup_expired_data()
            cleanup_results['metadata_storage'] = 'completed'
            
            logger.info(f"数据清理完成: {cleanup_results}")
            return cleanup_results
            
        except Exception as e:
            logger.error(f"数据清理失败: {e}")
            cleanup_results['error'] = str(e)
            return cleanup_results
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """获取全局统计信息"""
        # 并行获取各存储的统计信息
        result_stats, version_stats, metadata_stats = await asyncio.gather(
            self.result_storage.get_storage_stats(),
            self.version_storage.get_stats(),
            self.metadata_storage.get_storage_stats()
        )
        
        return {
            'manager_stats': self.manager_stats.copy(),
            'result_storage': result_stats,
            'version_storage': version_stats,
            'metadata_storage': metadata_stats,
            'summary': {
                'total_placeholders': max(
                    result_stats.get('total_placeholders', 0),
                    version_stats.get('total_placeholders', 0),
                    metadata_stats.get('metadata_count', 0)
                ),
                'total_storage_mb': (
                    result_stats.get('storage_size_mb', 0) +
                    metadata_stats.get('database_size_mb', 0)
                )
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        # 并行检查所有存储的健康状态
        result_health, version_health, metadata_health = await asyncio.gather(
            self.result_storage.health_check(),
            self.version_storage.health_check(),
            self.metadata_storage.health_check()
        )
        
        # 汇总健康状态
        all_healthy = all([
            result_health['status'] == 'healthy',
            version_health['status'] == 'healthy',
            metadata_health['status'] == 'healthy'
        ])
        
        overall_status = 'healthy' if all_healthy else 'degraded'
        
        # 收集所有问题
        all_issues = []
        all_issues.extend(result_health.get('issues', []))
        all_issues.extend(version_health.get('issues', []))
        all_issues.extend(metadata_health.get('issues', []))
        
        return {
            'overall_status': overall_status,
            'subsystems': {
                'result_storage': result_health,
                'version_storage': version_health,
                'metadata_storage': metadata_health
            },
            'total_issues': len(all_issues),
            'issues': all_issues,
            'manager_uptime': (datetime.now() - self.manager_stats['initialization_time']).total_seconds()
        }
    
    async def shutdown(self):
        """关闭存储管理器"""
        await asyncio.gather(
            self.result_storage.shutdown(),
            self.version_storage.shutdown(),
            self.metadata_storage.shutdown()
        )
        logger.info("存储管理器已关闭")

# 全局存储管理器实例
_storage_manager: Optional[StorageManager] = None

def get_storage_manager() -> StorageManager:
    """获取全局存储管理器实例"""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager

def initialize_storage_manager(
    result_storage_config: Optional[Dict[str, Any]] = None,
    version_storage_config: Optional[Dict[str, Any]] = None,
    metadata_storage_config: Optional[Dict[str, Any]] = None
) -> StorageManager:
    """初始化全局存储管理器"""
    global _storage_manager
    _storage_manager = StorageManager(
        result_storage_config=result_storage_config,
        version_storage_config=version_storage_config,
        metadata_storage_config=metadata_storage_config
    )
    return _storage_manager