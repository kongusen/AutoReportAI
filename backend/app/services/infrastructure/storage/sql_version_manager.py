"""
SQL Version Manager

SQL版本管理器，负责管理SQL的版本控制、存储和检索
支持版本历史、差异比较、回滚等功能
"""

import asyncio
import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import pickle
from contextlib import asynccontextmanager

from .file_storage_service import file_storage_service
from ...llm_agents.engines.sql_evolution_engine import SQLVersion, SQLComplexity, SQLQuality
from ...llm_agents.monitoring.performance_monitor import get_performance_monitor, monitor_performance

logger = logging.getLogger(__name__)


class VersionStatus(Enum):
    """版本状态"""
    DRAFT = "draft"          # 草稿
    ACTIVE = "active"        # 激活
    DEPRECATED = "deprecated" # 废弃
    ARCHIVED = "archived"    # 归档


class ChangeType(Enum):
    """变更类型"""
    CREATE = "create"        # 创建
    UPDATE = "update"        # 更新
    OPTIMIZE = "optimize"    # 优化
    BUGFIX = "bugfix"        # 修复
    REFACTOR = "refactor"    # 重构


@dataclass
class VersionMetadata:
    """版本元数据"""
    version_id: str
    context_id: str
    parent_version_id: Optional[str] = None
    version_number: str = "1.0.0"
    status: VersionStatus = VersionStatus.DRAFT
    change_type: ChangeType = ChangeType.CREATE
    title: str = ""
    description: str = ""
    author: str = "system"
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    activated_at: Optional[datetime] = None
    deprecated_at: Optional[datetime] = None


@dataclass
class SQLVersionRecord:
    """SQL版本记录"""
    metadata: VersionMetadata
    sql_version: SQLVersion
    storage_path: str
    file_size: int
    checksum: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "metadata": asdict(self.metadata),
            "sql_version": {
                "version_id": self.sql_version.version_id,
                "sql_text": self.sql_version.sql_text,
                "generated_at": self.sql_version.generated_at.isoformat(),
                "placeholders": [asdict(p) for p in self.sql_version.placeholders],
                "complexity": self.sql_version.complexity.value,
                "quality_score": self.sql_version.quality_score,
                "performance_score": self.sql_version.performance_score,
                "metadata": self.sql_version.metadata
            },
            "storage_path": self.storage_path,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "metrics": self.metrics
        }


@dataclass
class VersionDiff:
    """版本差异"""
    from_version_id: str
    to_version_id: str
    diff_type: str  # "text", "structure", "performance"
    changes: List[Dict[str, Any]]
    similarity_score: float
    impact_assessment: Dict[str, Any]
    generated_at: datetime = field(default_factory=datetime.now)


class SQLVersionDatabase:
    """SQL版本数据库管理器"""
    
    def __init__(self, db_path: str = "sql_versions.db"):
        self.db_path = Path(db_path)
        self._connection_pool = {}
        self._lock = asyncio.Lock()
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS version_metadata (
                    version_id TEXT PRIMARY KEY,
                    context_id TEXT NOT NULL,
                    parent_version_id TEXT,
                    version_number TEXT NOT NULL,
                    status TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    title TEXT,
                    description TEXT,
                    author TEXT NOT NULL DEFAULT 'system',
                    tags TEXT,  -- JSON array
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    activated_at TEXT,
                    deprecated_at TEXT,
                    FOREIGN KEY (parent_version_id) REFERENCES version_metadata (version_id)
                );
                
                CREATE TABLE IF NOT EXISTS version_records (
                    version_id TEXT PRIMARY KEY,
                    context_id TEXT NOT NULL,
                    storage_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    checksum TEXT NOT NULL,
                    sql_complexity TEXT,
                    quality_score REAL,
                    performance_score REAL,
                    metrics TEXT,  -- JSON
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (version_id) REFERENCES version_metadata (version_id)
                );
                
                CREATE TABLE IF NOT EXISTS version_diffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_version_id TEXT NOT NULL,
                    to_version_id TEXT NOT NULL,
                    diff_type TEXT NOT NULL,
                    changes TEXT NOT NULL,  -- JSON
                    similarity_score REAL,
                    impact_assessment TEXT,  -- JSON
                    generated_at TEXT NOT NULL,
                    FOREIGN KEY (from_version_id) REFERENCES version_metadata (version_id),
                    FOREIGN KEY (to_version_id) REFERENCES version_metadata (version_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_context_id ON version_metadata (context_id);
                CREATE INDEX IF NOT EXISTS idx_status ON version_metadata (status);
                CREATE INDEX IF NOT EXISTS idx_created_at ON version_metadata (created_at);
                CREATE INDEX IF NOT EXISTS idx_version_records_context ON version_records (context_id);
                CREATE INDEX IF NOT EXISTS idx_diffs_versions ON version_diffs (from_version_id, to_version_id);
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
    
    async def save_metadata(self, metadata: VersionMetadata):
        """保存版本元数据"""
        async with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO version_metadata (
                    version_id, context_id, parent_version_id, version_number,
                    status, change_type, title, description, author, tags,
                    created_at, updated_at, activated_at, deprecated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.version_id,
                metadata.context_id,
                metadata.parent_version_id,
                metadata.version_number,
                metadata.status.value,
                metadata.change_type.value,
                metadata.title,
                metadata.description,
                metadata.author,
                json.dumps(metadata.tags),
                metadata.created_at.isoformat(),
                metadata.updated_at.isoformat(),
                metadata.activated_at.isoformat() if metadata.activated_at else None,
                metadata.deprecated_at.isoformat() if metadata.deprecated_at else None
            ))
    
    async def save_record(self, record: SQLVersionRecord):
        """保存版本记录"""
        async with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO version_records (
                    version_id, context_id, storage_path, file_size, checksum,
                    sql_complexity, quality_score, performance_score, metrics, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.metadata.version_id,
                record.metadata.context_id,
                record.storage_path,
                record.file_size,
                record.checksum,
                record.sql_version.complexity.value,
                record.sql_version.quality_score,
                record.sql_version.performance_score,
                json.dumps(record.metrics),
                record.metadata.created_at.isoformat()
            ))
    
    async def get_metadata(self, version_id: str) -> Optional[VersionMetadata]:
        """获取版本元数据"""
        async with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM version_metadata WHERE version_id = ?
            """, (version_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return VersionMetadata(
                version_id=row['version_id'],
                context_id=row['context_id'],
                parent_version_id=row['parent_version_id'],
                version_number=row['version_number'],
                status=VersionStatus(row['status']),
                change_type=ChangeType(row['change_type']),
                title=row['title'] or "",
                description=row['description'] or "",
                author=row['author'],
                tags=json.loads(row['tags']) if row['tags'] else [],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                activated_at=datetime.fromisoformat(row['activated_at']) if row['activated_at'] else None,
                deprecated_at=datetime.fromisoformat(row['deprecated_at']) if row['deprecated_at'] else None
            )
    
    async def list_versions(
        self,
        context_id: Optional[str] = None,
        status: Optional[VersionStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[VersionMetadata]:
        """列出版本"""
        conditions = []
        params = []
        
        if context_id:
            conditions.append("context_id = ?")
            params.append(context_id)
        
        if status:
            conditions.append("status = ?")
            params.append(status.value)
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        params.extend([limit, offset])
        
        async with self.get_connection() as conn:
            cursor = conn.execute(f"""
                SELECT * FROM version_metadata {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, params)
            
            versions = []
            for row in cursor.fetchall():
                metadata = VersionMetadata(
                    version_id=row['version_id'],
                    context_id=row['context_id'],
                    parent_version_id=row['parent_version_id'],
                    version_number=row['version_number'],
                    status=VersionStatus(row['status']),
                    change_type=ChangeType(row['change_type']),
                    title=row['title'] or "",
                    description=row['description'] or "",
                    author=row['author'],
                    tags=json.loads(row['tags']) if row['tags'] else [],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    activated_at=datetime.fromisoformat(row['activated_at']) if row['activated_at'] else None,
                    deprecated_at=datetime.fromisoformat(row['deprecated_at']) if row['deprecated_at'] else None
                )
                versions.append(metadata)
            
            return versions
    
    async def save_diff(self, diff: VersionDiff):
        """保存版本差异"""
        async with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO version_diffs (
                    from_version_id, to_version_id, diff_type, changes,
                    similarity_score, impact_assessment, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                diff.from_version_id,
                diff.to_version_id,
                diff.diff_type,
                json.dumps(diff.changes),
                diff.similarity_score,
                json.dumps(diff.impact_assessment),
                diff.generated_at.isoformat()
            ))


class SQLVersionManager:
    """SQL版本管理器主类"""
    
    def __init__(self, db_path: str = "sql_versions.db"):
        self.db = SQLVersionDatabase(db_path)
        self.performance_monitor = get_performance_monitor()
    
    @monitor_performance("sql_version_manager", "create_version")
    async def create_version(
        self,
        context_id: str,
        sql_version: SQLVersion,
        change_type: ChangeType = ChangeType.CREATE,
        title: str = "",
        description: str = "",
        author: str = "system",
        tags: List[str] = None,
        parent_version_id: Optional[str] = None
    ) -> SQLVersionRecord:
        """
        创建新版本
        
        Args:
            context_id: 上下文ID
            sql_version: SQL版本对象
            change_type: 变更类型
            title: 版本标题
            description: 版本描述
            author: 作者
            tags: 标签列表
            parent_version_id: 父版本ID
            
        Returns:
            SQL版本记录
        """
        try:
            logger.info(f"创建SQL版本: {context_id}")
            
            # 生成版本号
            version_number = await self._generate_version_number(context_id, parent_version_id)
            
            # 创建元数据
            metadata = VersionMetadata(
                version_id=sql_version.version_id,
                context_id=context_id,
                parent_version_id=parent_version_id,
                version_number=version_number,
                status=VersionStatus.DRAFT,
                change_type=change_type,
                title=title,
                description=description,
                author=author,
                tags=tags or [],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 序列化SQL版本对象
            sql_data = pickle.dumps(sql_version)
            
            # 计算校验和
            checksum = hashlib.sha256(sql_data).hexdigest()
            
            # 存储到文件系统
            from io import BytesIO
            storage_result = file_storage_service.upload_file(
                file_data=BytesIO(sql_data),
                original_filename=f"{sql_version.version_id}.sql",
                file_type="sql_versions",
                content_type="application/octet-stream"
            )
            
            # 创建版本记录
            record = SQLVersionRecord(
                metadata=metadata,
                sql_version=sql_version,
                storage_path=storage_result["file_path"],
                file_size=len(sql_data),
                checksum=checksum,
                metrics=await self._calculate_version_metrics(sql_version)
            )
            
            # 保存到数据库
            await self.db.save_metadata(metadata)
            await self.db.save_record(record)
            
            logger.info(f"SQL版本创建成功: {sql_version.version_id}")
            return record
            
        except Exception as e:
            logger.error(f"创建SQL版本失败: {e}")
            raise
    
    @monitor_performance("sql_version_manager", "get_version")
    async def get_version(self, version_id: str) -> Optional[SQLVersionRecord]:
        """
        获取版本
        
        Args:
            version_id: 版本ID
            
        Returns:
            SQL版本记录或None
        """
        try:
            # 获取元数据
            metadata = await self.db.get_metadata(version_id)
            if not metadata:
                return None
            
            # 获取记录信息
            async with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM version_records WHERE version_id = ?
                """, (version_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
            
            # 从存储中加载SQL版本对象
            file_data, _ = file_storage_service.download_file(row['storage_path'])
            sql_version = pickle.loads(file_data)
            
            # 创建完整记录
            record = SQLVersionRecord(
                metadata=metadata,
                sql_version=sql_version,
                storage_path=row['storage_path'],
                file_size=row['file_size'],
                checksum=row['checksum'],
                metrics=json.loads(row['metrics']) if row['metrics'] else {}
            )
            
            return record
            
        except Exception as e:
            logger.error(f"获取SQL版本失败: {e}")
            return None
    
    @monitor_performance("sql_version_manager", "activate_version")
    async def activate_version(self, version_id: str) -> bool:
        """
        激活版本
        
        Args:
            version_id: 版本ID
            
        Returns:
            操作是否成功
        """
        try:
            metadata = await self.db.get_metadata(version_id)
            if not metadata:
                raise ValueError(f"版本不存在: {version_id}")
            
            # 先将同一上下文的其他版本设为deprecated
            await self._deprecate_active_versions(metadata.context_id)
            
            # 激活当前版本
            metadata.status = VersionStatus.ACTIVE
            metadata.activated_at = datetime.now()
            metadata.updated_at = datetime.now()
            
            await self.db.save_metadata(metadata)
            
            logger.info(f"SQL版本激活成功: {version_id}")
            return True
            
        except Exception as e:
            logger.error(f"激活SQL版本失败: {e}")
            return False
    
    async def _deprecate_active_versions(self, context_id: str):
        """废弃活跃版本"""
        active_versions = await self.db.list_versions(
            context_id=context_id,
            status=VersionStatus.ACTIVE
        )
        
        for version_metadata in active_versions:
            version_metadata.status = VersionStatus.DEPRECATED
            version_metadata.deprecated_at = datetime.now()
            version_metadata.updated_at = datetime.now()
            await self.db.save_metadata(version_metadata)
    
    async def _generate_version_number(self, context_id: str, parent_version_id: Optional[str] = None) -> str:
        """生成版本号"""
        if parent_version_id:
            parent_metadata = await self.db.get_metadata(parent_version_id)
            if parent_metadata:
                # 基于父版本生成新版本号
                parts = parent_metadata.version_number.split('.')
                if len(parts) >= 3:
                    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                    return f"{major}.{minor}.{patch + 1}"
        
        # 获取上下文中的最新版本号
        versions = await self.db.list_versions(context_id=context_id, limit=1)
        if versions:
            parts = versions[0].version_number.split('.')
            if len(parts) >= 2:
                major, minor = int(parts[0]), int(parts[1])
                return f"{major}.{minor + 1}.0"
        
        return "1.0.0"
    
    async def _calculate_version_metrics(self, sql_version: SQLVersion) -> Dict[str, Any]:
        """计算版本指标"""
        return {
            "sql_length": len(sql_version.sql_text),
            "placeholders_count": len(sql_version.placeholders),
            "complexity_score": self._complexity_to_score(sql_version.complexity),
            "quality_score": sql_version.quality_score,
            "performance_score": sql_version.performance_score,
            "generated_at": sql_version.generated_at.isoformat()
        }
    
    def _complexity_to_score(self, complexity: SQLComplexity) -> int:
        """将复杂度转换为数值"""
        complexity_map = {
            SQLComplexity.SIMPLE: 1,
            SQLComplexity.MODERATE: 2,
            SQLComplexity.COMPLEX: 3,
            SQLComplexity.ADVANCED: 4
        }
        return complexity_map.get(complexity, 1)
    
    @monitor_performance("sql_version_manager", "compare_versions")
    async def compare_versions(self, from_version_id: str, to_version_id: str) -> VersionDiff:
        """
        比较两个版本
        
        Args:
            from_version_id: 源版本ID
            to_version_id: 目标版本ID
            
        Returns:
            版本差异对象
        """
        try:
            from_record = await self.get_version(from_version_id)
            to_record = await self.get_version(to_version_id)
            
            if not from_record or not to_record:
                raise ValueError("版本不存在")
            
            changes = []
            
            # SQL文本差异
            if from_record.sql_version.sql_text != to_record.sql_version.sql_text:
                changes.append({
                    "type": "sql_text",
                    "from": from_record.sql_version.sql_text,
                    "to": to_record.sql_version.sql_text,
                    "change_type": "modified"
                })
            
            # 复杂度差异
            if from_record.sql_version.complexity != to_record.sql_version.complexity:
                changes.append({
                    "type": "complexity",
                    "from": from_record.sql_version.complexity.value,
                    "to": to_record.sql_version.complexity.value,
                    "change_type": "modified"
                })
            
            # 质量分数差异
            quality_diff = to_record.sql_version.quality_score - from_record.sql_version.quality_score
            if abs(quality_diff) > 0.01:  # 忽略微小差异
                changes.append({
                    "type": "quality_score",
                    "from": from_record.sql_version.quality_score,
                    "to": to_record.sql_version.quality_score,
                    "change_type": "improved" if quality_diff > 0 else "degraded",
                    "difference": quality_diff
                })
            
            # 占位符差异
            from_placeholders = set(p.original_text for p in from_record.sql_version.placeholders)
            to_placeholders = set(p.original_text for p in to_record.sql_version.placeholders)
            
            added_placeholders = to_placeholders - from_placeholders
            removed_placeholders = from_placeholders - to_placeholders
            
            if added_placeholders or removed_placeholders:
                changes.append({
                    "type": "placeholders",
                    "added": list(added_placeholders),
                    "removed": list(removed_placeholders),
                    "change_type": "modified"
                })
            
            # 计算相似度
            similarity_score = self._calculate_similarity(
                from_record.sql_version.sql_text,
                to_record.sql_version.sql_text
            )
            
            # 影响评估
            impact_assessment = {
                "performance_impact": "positive" if quality_diff > 0 else "negative" if quality_diff < 0 else "none",
                "complexity_impact": self._assess_complexity_impact(
                    from_record.sql_version.complexity,
                    to_record.sql_version.complexity
                ),
                "breaking_changes": len(removed_placeholders) > 0,
                "risk_level": self._assess_risk_level(changes)
            }
            
            diff = VersionDiff(
                from_version_id=from_version_id,
                to_version_id=to_version_id,
                diff_type="comprehensive",
                changes=changes,
                similarity_score=similarity_score,
                impact_assessment=impact_assessment
            )
            
            # 保存差异记录
            await self.db.save_diff(diff)
            
            return diff
            
        except Exception as e:
            logger.error(f"比较版本失败: {e}")
            raise
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        import difflib
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    def _assess_complexity_impact(self, from_complexity: SQLComplexity, to_complexity: SQLComplexity) -> str:
        """评估复杂度影响"""
        from_score = self._complexity_to_score(from_complexity)
        to_score = self._complexity_to_score(to_complexity)
        
        if to_score > from_score:
            return "increased"
        elif to_score < from_score:
            return "decreased"
        else:
            return "unchanged"
    
    def _assess_risk_level(self, changes: List[Dict[str, Any]]) -> str:
        """评估风险级别"""
        high_risk_changes = ["sql_text", "placeholders"]
        medium_risk_changes = ["complexity"]
        
        for change in changes:
            if change["type"] in high_risk_changes:
                if change["type"] == "placeholders" and change.get("removed"):
                    return "high"
                elif change["type"] == "sql_text":
                    return "medium"
            elif change["type"] in medium_risk_changes:
                return "low"
        
        return "low"
    
    @monitor_performance("sql_version_manager", "list_versions")
    async def list_versions(
        self,
        context_id: Optional[str] = None,
        status: Optional[VersionStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[VersionMetadata]:
        """列出版本"""
        return await self.db.list_versions(context_id, status, limit, offset)
    
    @monitor_performance("sql_version_manager", "get_active_version")
    async def get_active_version(self, context_id: str) -> Optional[SQLVersionRecord]:
        """获取活跃版本"""
        active_versions = await self.db.list_versions(
            context_id=context_id,
            status=VersionStatus.ACTIVE,
            limit=1
        )
        
        if active_versions:
            return await self.get_version(active_versions[0].version_id)
        
        return None
    
    async def rollback_to_version(self, context_id: str, version_id: str) -> bool:
        """回滚到指定版本"""
        try:
            # 检查目标版本是否存在
            target_record = await self.get_version(version_id)
            if not target_record or target_record.metadata.context_id != context_id:
                raise ValueError(f"目标版本不存在或不属于指定上下文: {version_id}")
            
            # 激活目标版本
            return await self.activate_version(version_id)
            
        except Exception as e:
            logger.error(f"回滚版本失败: {e}")
            return False
    
    async def cleanup_old_versions(self, days: int = 90) -> Dict[str, Any]:
        """清理旧版本"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 获取需要清理的版本
            async with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT version_id, storage_path FROM version_records 
                    WHERE created_at < ? AND version_id NOT IN (
                        SELECT version_id FROM version_metadata 
                        WHERE status IN ('active', 'draft')
                    )
                """, (cutoff_date.isoformat(),))
                
                old_versions = cursor.fetchall()
            
            cleaned_count = 0
            failed_count = 0
            
            for row in old_versions:
                try:
                    # 删除存储文件
                    file_storage_service.delete_file(row['storage_path'])
                    
                    # 删除数据库记录
                    async with self.db.get_connection() as conn:
                        conn.execute("DELETE FROM version_records WHERE version_id = ?", (row['version_id'],))
                        conn.execute("DELETE FROM version_metadata WHERE version_id = ?", (row['version_id'],))
                        conn.execute("DELETE FROM version_diffs WHERE from_version_id = ? OR to_version_id = ?", 
                                   (row['version_id'], row['version_id']))
                    
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.error(f"清理版本失败 {row['version_id']}: {e}")
                    failed_count += 1
            
            logger.info(f"版本清理完成: 清理{cleaned_count}个，失败{failed_count}个")
            
            return {
                "total_versions": len(old_versions),
                "cleaned_count": cleaned_count,
                "failed_count": failed_count,
                "cleanup_date": cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"清理旧版本失败: {e}")
            raise
    
    async def get_version_statistics(self, context_id: Optional[str] = None) -> Dict[str, Any]:
        """获取版本统计信息"""
        try:
            conditions = []
            params = []
            
            if context_id:
                conditions.append("context_id = ?")
                params.append(context_id)
            
            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)
            
            async with self.db.get_connection() as conn:
                # 总体统计
                cursor = conn.execute(f"""
                    SELECT 
                        COUNT(*) as total_versions,
                        COUNT(CASE WHEN status = 'active' THEN 1 END) as active_versions,
                        COUNT(CASE WHEN status = 'draft' THEN 1 END) as draft_versions,
                        COUNT(CASE WHEN status = 'deprecated' THEN 1 END) as deprecated_versions,
                        COUNT(CASE WHEN status = 'archived' THEN 1 END) as archived_versions
                    FROM version_metadata {where_clause}
                """, params)
                
                stats = dict(cursor.fetchone())
                
                # 按上下文统计
                cursor = conn.execute(f"""
                    SELECT 
                        context_id,
                        COUNT(*) as version_count,
                        MAX(created_at) as latest_version,
                        AVG(CAST(quality_score as REAL)) as avg_quality
                    FROM version_metadata vm
                    LEFT JOIN version_records vr ON vm.version_id = vr.version_id
                    {where_clause}
                    GROUP BY context_id
                    ORDER BY version_count DESC
                    LIMIT 20
                """, params)
                
                context_stats = [dict(row) for row in cursor.fetchall()]
                
                # 质量分布
                cursor = conn.execute(f"""
                    SELECT 
                        CASE 
                            WHEN quality_score >= 0.9 THEN 'excellent'
                            WHEN quality_score >= 0.7 THEN 'good'
                            WHEN quality_score >= 0.5 THEN 'fair'
                            ELSE 'poor'
                        END as quality_level,
                        COUNT(*) as count
                    FROM version_records vr
                    JOIN version_metadata vm ON vr.version_id = vm.version_id
                    {where_clause}
                    GROUP BY quality_level
                """, params)
                
                quality_distribution = {row['quality_level']: row['count'] for row in cursor.fetchall()}
                
                return {
                    "overview": stats,
                    "context_statistics": context_stats,
                    "quality_distribution": quality_distribution,
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"获取版本统计失败: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查数据库连接
            async with self.db.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) as count FROM version_metadata")
                total_versions = cursor.fetchone()['count']
            
            # 检查存储状态
            storage_status = file_storage_service.get_storage_status()
            
            return {
                "status": "healthy",
                "database_connected": True,
                "total_versions": total_versions,
                "storage_status": storage_status,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# 全局SQL版本管理器实例
_sql_version_manager: Optional[SQLVersionManager] = None

def get_sql_version_manager() -> SQLVersionManager:
    """获取全局SQL版本管理器实例"""
    global _sql_version_manager
    if _sql_version_manager is None:
        _sql_version_manager = SQLVersionManager()
    return _sql_version_manager