"""
版本存储管理

管理占位符分析结果的版本控制
"""

import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import aiofiles
import asyncio
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class VersionInfo:
    """版本信息"""
    version_id: str
    placeholder_id: str
    parent_version: Optional[str]
    created_at: datetime
    created_by: str
    change_summary: str
    content_hash: str
    context_hash: str
    metadata: Dict[str, Any]
    tags: List[str]

@dataclass
class VersionDiff:
    """版本差异"""
    old_version: str
    new_version: str
    changes: Dict[str, Any]
    change_type: str  # 'minor', 'major', 'patch'
    similarity_score: float

class VersionStorage:
    """版本存储管理器"""
    
    def __init__(self, 
                 storage_directory: str = "data/placeholder_versions",
                 max_versions_per_placeholder: int = 20,
                 auto_tag_major_changes: bool = True):
        """
        初始化版本存储
        
        Args:
            storage_directory: 存储目录
            max_versions_per_placeholder: 每个占位符最大版本数
            auto_tag_major_changes: 是否自动标记重大变更
        """
        self.storage_directory = Path(storage_directory)
        self.max_versions_per_placeholder = max_versions_per_placeholder
        self.auto_tag_major_changes = auto_tag_major_changes
        
        # 创建存储目录
        self.storage_directory.mkdir(parents=True, exist_ok=True)
        
        # 版本图文件
        self.version_graph_file = self.storage_directory / "version_graph.json"
        
        # 内存中的版本图
        self._version_graph: Dict[str, List[VersionInfo]] = {}
        self._lock = asyncio.Lock()
        
        # 统计信息
        self.stats = {
            'total_versions': 0,
            'total_placeholders': 0,
            'major_versions': 0,
            'minor_versions': 0,
            'patch_versions': 0
        }
        
        # 初始化加载版本图
        asyncio.create_task(self._load_version_graph())
    
    async def _load_version_graph(self):
        """加载版本图"""
        try:
            if self.version_graph_file.exists():
                async with aiofiles.open(self.version_graph_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    graph_data = json.loads(content)
                
                # 重建版本图
                for placeholder_id, versions_data in graph_data.items():
                    self._version_graph[placeholder_id] = [
                        VersionInfo(
                            version_id=v['version_id'],
                            placeholder_id=v['placeholder_id'],
                            parent_version=v.get('parent_version'),
                            created_at=datetime.fromisoformat(v['created_at']),
                            created_by=v['created_by'],
                            change_summary=v['change_summary'],
                            content_hash=v['content_hash'],
                            context_hash=v['context_hash'],
                            metadata=v['metadata'],
                            tags=v.get('tags', [])
                        )
                        for v in versions_data
                    ]
                
                await self._update_stats()
                logger.info(f"加载了 {len(self._version_graph)} 个占位符的版本图")
        
        except Exception as e:
            logger.error(f"加载版本图失败: {e}")
            self._version_graph = {}
    
    async def _save_version_graph(self):
        """保存版本图"""
        try:
            # 转换为可序列化的格式
            graph_data = {}
            for placeholder_id, versions in self._version_graph.items():
                graph_data[placeholder_id] = [
                    {
                        'version_id': v.version_id,
                        'placeholder_id': v.placeholder_id,
                        'parent_version': v.parent_version,
                        'created_at': v.created_at.isoformat(),
                        'created_by': v.created_by,
                        'change_summary': v.change_summary,
                        'content_hash': v.content_hash,
                        'context_hash': v.context_hash,
                        'metadata': v.metadata,
                        'tags': v.tags
                    }
                    for v in versions
                ]
            
            async with aiofiles.open(self.version_graph_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(graph_data, ensure_ascii=False, indent=2))
                
        except Exception as e:
            logger.error(f"保存版本图失败: {e}")
    
    def _generate_version_id(self, placeholder_id: str, parent_version: Optional[str] = None) -> str:
        """生成版本ID"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if parent_version is None:
            # 初始版本
            return f"{placeholder_id}_v1.0.0_{timestamp}"
        else:
            # 基于父版本生成新版本
            # 简化的语义化版本控制
            try:
                # 提取版本号
                parts = parent_version.split('_v')[1].split('_')[0].split('.')
                major, minor, patch = map(int, parts)
                
                # 默认增加patch版本
                return f"{placeholder_id}_v{major}.{minor}.{patch + 1}_{timestamp}"
            except:
                # 如果解析失败，创建新的版本
                return f"{placeholder_id}_v1.0.1_{timestamp}"
    
    def _calculate_change_type(self, old_result: Dict[str, Any], new_result: Dict[str, Any]) -> Tuple[str, float]:
        """计算变更类型和相似度分数"""
        try:
            # 比较关键字段
            old_sql = old_result.get('generated_sql', '')
            new_sql = new_result.get('generated_sql', '')
            
            old_semantic = old_result.get('semantic_type', '')
            new_semantic = new_result.get('semantic_type', '')
            
            old_intent = old_result.get('data_intent', '')
            new_intent = new_result.get('data_intent', '')
            
            # 计算相似度 (简化实现)
            sql_similarity = self._calculate_text_similarity(old_sql, new_sql)
            semantic_similarity = 1.0 if old_semantic == new_semantic else 0.0
            intent_similarity = 1.0 if old_intent == new_intent else 0.0
            
            overall_similarity = (sql_similarity * 0.6 + semantic_similarity * 0.2 + intent_similarity * 0.2)
            
            # 确定变更类型
            if overall_similarity < 0.3:
                return "major", overall_similarity
            elif overall_similarity < 0.7:
                return "minor", overall_similarity
            else:
                return "patch", overall_similarity
        
        except Exception as e:
            logger.error(f"计算变更类型失败: {e}")
            return "patch", 0.5
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度 (简化实现)"""
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0
        
        # 使用简单的字符级相似度
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        if text1 == text2:
            return 1.0
        
        # 计算编辑距离的简化版本
        len1, len2 = len(text1), len(text2)
        max_len = max(len1, len2)
        
        if max_len == 0:
            return 1.0
        
        # 简单的字符匹配率
        common_chars = sum(1 for c1, c2 in zip(text1, text2) if c1 == c2)
        similarity = common_chars / max_len
        
        return similarity
    
    async def create_version(self, 
                           placeholder_id: str,
                           result_data: Dict[str, Any],
                           content_hash: str,
                           context_hash: str,
                           created_by: str = "system",
                           change_summary: str = "",
                           parent_version: Optional[str] = None,
                           tags: List[str] = None) -> str:
        """创建新版本"""
        async with self._lock:
            # 生成版本ID
            version_id = self._generate_version_id(placeholder_id, parent_version)
            
            # 如果有父版本，计算变更类型
            change_type = "initial"
            if parent_version and placeholder_id in self._version_graph:
                parent_info = next((v for v in self._version_graph[placeholder_id] if v.version_id == parent_version), None)
                if parent_info:
                    # 这里需要加载父版本的结果数据进行比较
                    # 简化处理，假设有比较逻辑
                    change_type = "minor"  # 默认为minor变更
            
            # 创建版本信息
            version_info = VersionInfo(
                version_id=version_id,
                placeholder_id=placeholder_id,
                parent_version=parent_version,
                created_at=datetime.now(),
                created_by=created_by,
                change_summary=change_summary or f"版本 {version_id} 创建",
                content_hash=content_hash,
                context_hash=context_hash,
                metadata={
                    'change_type': change_type,
                    'result_size': len(str(result_data)),
                    'confidence': result_data.get('confidence', 0.0)
                },
                tags=tags or []
            )
            
            # 添加自动标签
            if self.auto_tag_major_changes and change_type == "major":
                version_info.tags.append("major-change")
            
            # 添加到版本图
            if placeholder_id not in self._version_graph:
                self._version_graph[placeholder_id] = []
            
            self._version_graph[placeholder_id].append(version_info)
            
            # 限制版本数量
            if len(self._version_graph[placeholder_id]) > self.max_versions_per_placeholder:
                # 删除最旧的版本（保留重要版本）
                versions = self._version_graph[placeholder_id]
                
                # 查找可删除的版本（非标记版本，非最新版本）
                removable_versions = [
                    v for v in versions[:-1]  # 不包括最新版本
                    if not any(tag.startswith('important') for tag in v.tags)
                ]
                
                if removable_versions:
                    oldest_version = min(removable_versions, key=lambda v: v.created_at)
                    self._version_graph[placeholder_id].remove(oldest_version)
            
            # 保存版本图
            await self._save_version_graph()
            await self._update_stats()
            
            logger.info(f"创建版本: {version_id} (类型: {change_type})")
            return version_id
    
    async def get_version_info(self, placeholder_id: str, version_id: str) -> Optional[VersionInfo]:
        """获取版本信息"""
        async with self._lock:
            if placeholder_id not in self._version_graph:
                return None
            
            for version in self._version_graph[placeholder_id]:
                if version.version_id == version_id:
                    return version
            
            return None
    
    async def get_version_history(self, placeholder_id: str, limit: int = 10) -> List[VersionInfo]:
        """获取版本历史"""
        async with self._lock:
            if placeholder_id not in self._version_graph:
                return []
            
            versions = self._version_graph[placeholder_id]
            # 按创建时间倒序排列
            sorted_versions = sorted(versions, key=lambda v: v.created_at, reverse=True)
            
            return sorted_versions[:limit] if limit > 0 else sorted_versions
    
    async def get_latest_version(self, placeholder_id: str) -> Optional[VersionInfo]:
        """获取最新版本"""
        history = await self.get_version_history(placeholder_id, limit=1)
        return history[0] if history else None
    
    async def compare_versions(self, placeholder_id: str, version1: str, version2: str) -> Optional[VersionDiff]:
        """比较两个版本"""
        async with self._lock:
            if placeholder_id not in self._version_graph:
                return None
            
            versions = self._version_graph[placeholder_id]
            
            v1_info = next((v for v in versions if v.version_id == version1), None)
            v2_info = next((v for v in versions if v.version_id == version2), None)
            
            if not v1_info or not v2_info:
                return None
            
            # 这里需要加载实际的结果数据进行比较
            # 简化处理，只比较元数据
            changes = {
                'content_hash_changed': v1_info.content_hash != v2_info.content_hash,
                'context_hash_changed': v1_info.context_hash != v2_info.context_hash,
                'metadata_diff': {
                    'old': v1_info.metadata,
                    'new': v2_info.metadata
                }
            }
            
            # 计算相似度（简化）
            similarity_score = 0.8 if not changes['content_hash_changed'] else 0.3
            
            change_type = v2_info.metadata.get('change_type', 'unknown')
            
            return VersionDiff(
                old_version=version1,
                new_version=version2,
                changes=changes,
                change_type=change_type,
                similarity_score=similarity_score
            )
    
    async def tag_version(self, placeholder_id: str, version_id: str, tags: List[str]) -> bool:
        """给版本添加标签"""
        async with self._lock:
            if placeholder_id not in self._version_graph:
                return False
            
            for version in self._version_graph[placeholder_id]:
                if version.version_id == version_id:
                    # 添加新标签，避免重复
                    for tag in tags:
                        if tag not in version.tags:
                            version.tags.append(tag)
                    
                    await self._save_version_graph()
                    logger.info(f"为版本 {version_id} 添加标签: {tags}")
                    return True
            
            return False
    
    async def remove_version_tag(self, placeholder_id: str, version_id: str, tag: str) -> bool:
        """移除版本标签"""
        async with self._lock:
            if placeholder_id not in self._version_graph:
                return False
            
            for version in self._version_graph[placeholder_id]:
                if version.version_id == version_id and tag in version.tags:
                    version.tags.remove(tag)
                    await self._save_version_graph()
                    logger.info(f"从版本 {version_id} 移除标签: {tag}")
                    return True
            
            return False
    
    async def get_versions_by_tag(self, tag: str) -> List[Tuple[str, VersionInfo]]:
        """根据标签获取版本"""
        async with self._lock:
            tagged_versions = []
            
            for placeholder_id, versions in self._version_graph.items():
                for version in versions:
                    if tag in version.tags:
                        tagged_versions.append((placeholder_id, version))
            
            return tagged_versions
    
    async def delete_version(self, placeholder_id: str, version_id: str) -> bool:
        """删除版本"""
        async with self._lock:
            if placeholder_id not in self._version_graph:
                return False
            
            versions = self._version_graph[placeholder_id]
            
            # 找到要删除的版本
            for i, version in enumerate(versions):
                if version.version_id == version_id:
                    # 检查是否有子版本依赖此版本
                    dependent_versions = [
                        v for v in versions 
                        if v.parent_version == version_id
                    ]
                    
                    if dependent_versions:
                        logger.warning(f"版本 {version_id} 有依赖版本，无法删除")
                        return False
                    
                    # 删除版本
                    versions.pop(i)
                    
                    # 如果没有版本了，删除整个占位符条目
                    if not versions:
                        del self._version_graph[placeholder_id]
                    
                    await self._save_version_graph()
                    await self._update_stats()
                    
                    logger.info(f"删除版本: {version_id}")
                    return True
            
            return False
    
    async def _update_stats(self):
        """更新统计信息"""
        total_versions = sum(len(versions) for versions in self._version_graph.values())
        total_placeholders = len(self._version_graph)
        
        # 统计不同类型的版本
        major_versions = 0
        minor_versions = 0
        patch_versions = 0
        
        for versions in self._version_graph.values():
            for version in versions:
                change_type = version.metadata.get('change_type', 'patch')
                if change_type == 'major':
                    major_versions += 1
                elif change_type == 'minor':
                    minor_versions += 1
                else:
                    patch_versions += 1
        
        self.stats.update({
            'total_versions': total_versions,
            'total_placeholders': total_placeholders,
            'major_versions': major_versions,
            'minor_versions': minor_versions,
            'patch_versions': patch_versions
        })
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取版本存储统计信息"""
        await self._update_stats()
        
        return {
            'total_versions': self.stats['total_versions'],
            'total_placeholders': self.stats['total_placeholders'],
            'version_distribution': {
                'major': self.stats['major_versions'],
                'minor': self.stats['minor_versions'],
                'patch': self.stats['patch_versions']
            },
            'avg_versions_per_placeholder': (
                self.stats['total_versions'] / self.stats['total_placeholders']
                if self.stats['total_placeholders'] > 0 else 0
            ),
            'config': {
                'max_versions_per_placeholder': self.max_versions_per_placeholder,
                'auto_tag_major_changes': self.auto_tag_major_changes
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            stats = await self.get_stats()
            
            health_status = "healthy"
            issues = []
            
            # 检查版本图完整性
            if not self.version_graph_file.exists():
                issues.append("版本图文件缺失")
                health_status = "warning"
            
            # 检查版本数量
            if stats['total_versions'] > 10000:
                issues.append("版本数量过多，建议清理")
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
        """关闭版本存储"""
        await self._save_version_graph()
        logger.info("版本存储已关闭")