"""
元数据存储

存储占位符的元数据信息，如性能指标、使用统计等
"""

import logging
import json
import sqlite3
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import aiosqlite
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class PlaceholderMetadata:
    """占位符元数据"""
    placeholder_id: str
    name: str
    description: str
    category: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_analyzed_at: Optional[datetime]
    analysis_count: int
    success_rate: float
    avg_execution_time_ms: float
    data_sources: List[str]
    templates: List[str]
    custom_attributes: Dict[str, Any]

@dataclass
class UsageMetrics:
    """使用指标"""
    placeholder_id: str
    date: datetime
    analysis_count: int
    success_count: int
    error_count: int
    total_execution_time_ms: float
    avg_execution_time_ms: float
    unique_users: int
    data_volume_processed: int

class MetadataStorage:
    """元数据存储"""
    
    def __init__(self, 
                 database_path: str = "data/placeholder_metadata.db",
                 retention_days: int = 365):
        """
        初始化元数据存储
        
        Args:
            database_path: SQLite数据库路径
            retention_days: 数据保留天数
        """
        self.database_path = database_path
        self.retention_days = retention_days
        
        # 确保目录存在
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        asyncio.create_task(self._initialize_database())
        
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _initialize_database(self):
        """初始化数据库表"""
        try:
            async with aiosqlite.connect(self.database_path) as db:
                # 占位符元数据表
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS placeholder_metadata (
                        placeholder_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        category TEXT,
                        tags TEXT,  -- JSON数组
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        created_by TEXT NOT NULL,
                        last_analyzed_at TEXT,
                        analysis_count INTEGER DEFAULT 0,
                        success_rate REAL DEFAULT 0.0,
                        avg_execution_time_ms REAL DEFAULT 0.0,
                        data_sources TEXT,  -- JSON数组
                        templates TEXT,  -- JSON数组
                        custom_attributes TEXT  -- JSON对象
                    )
                ''')
                
                # 使用指标表
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS usage_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        placeholder_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        analysis_count INTEGER DEFAULT 0,
                        success_count INTEGER DEFAULT 0,
                        error_count INTEGER DEFAULT 0,
                        total_execution_time_ms REAL DEFAULT 0.0,
                        avg_execution_time_ms REAL DEFAULT 0.0,
                        unique_users INTEGER DEFAULT 0,
                        data_volume_processed INTEGER DEFAULT 0,
                        UNIQUE(placeholder_id, date)
                    )
                ''')
                
                # 创建索引
                await db.execute('CREATE INDEX IF NOT EXISTS idx_metadata_category ON placeholder_metadata(category)')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_metadata_created_by ON placeholder_metadata(created_by)')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_usage_placeholder_date ON usage_metrics(placeholder_id, date)')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_usage_date ON usage_metrics(date)')
                
                await db.commit()
                
            logger.info("元数据数据库初始化完成")
            
        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")
            raise
    
    async def create_or_update_metadata(self, metadata: PlaceholderMetadata) -> bool:
        """创建或更新占位符元数据"""
        try:
            async with aiosqlite.connect(self.database_path) as db:
                # 检查是否已存在
                cursor = await db.execute(
                    'SELECT placeholder_id FROM placeholder_metadata WHERE placeholder_id = ?',
                    (metadata.placeholder_id,)
                )
                exists = await cursor.fetchone() is not None
                
                if exists:
                    # 更新
                    await db.execute('''
                        UPDATE placeholder_metadata SET
                            name = ?, description = ?, category = ?, tags = ?,
                            updated_at = ?, last_analyzed_at = ?, analysis_count = ?,
                            success_rate = ?, avg_execution_time_ms = ?,
                            data_sources = ?, templates = ?, custom_attributes = ?
                        WHERE placeholder_id = ?
                    ''', (
                        metadata.name,
                        metadata.description,
                        metadata.category,
                        json.dumps(metadata.tags, ensure_ascii=False),
                        metadata.updated_at.isoformat(),
                        metadata.last_analyzed_at.isoformat() if metadata.last_analyzed_at else None,
                        metadata.analysis_count,
                        metadata.success_rate,
                        metadata.avg_execution_time_ms,
                        json.dumps(metadata.data_sources, ensure_ascii=False),
                        json.dumps(metadata.templates, ensure_ascii=False),
                        json.dumps(metadata.custom_attributes, ensure_ascii=False),
                        metadata.placeholder_id
                    ))
                    logger.debug(f"更新占位符元数据: {metadata.placeholder_id}")
                else:
                    # 创建
                    await db.execute('''
                        INSERT INTO placeholder_metadata (
                            placeholder_id, name, description, category, tags,
                            created_at, updated_at, created_by, last_analyzed_at,
                            analysis_count, success_rate, avg_execution_time_ms,
                            data_sources, templates, custom_attributes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        metadata.placeholder_id,
                        metadata.name,
                        metadata.description,
                        metadata.category,
                        json.dumps(metadata.tags, ensure_ascii=False),
                        metadata.created_at.isoformat(),
                        metadata.updated_at.isoformat(),
                        metadata.created_by,
                        metadata.last_analyzed_at.isoformat() if metadata.last_analyzed_at else None,
                        metadata.analysis_count,
                        metadata.success_rate,
                        metadata.avg_execution_time_ms,
                        json.dumps(metadata.data_sources, ensure_ascii=False),
                        json.dumps(metadata.templates, ensure_ascii=False),
                        json.dumps(metadata.custom_attributes, ensure_ascii=False)
                    ))
                    logger.debug(f"创建占位符元数据: {metadata.placeholder_id}")
                
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"创建/更新元数据失败: {e}")
            return False
    
    async def get_metadata(self, placeholder_id: str) -> Optional[PlaceholderMetadata]:
        """获取占位符元数据"""
        try:
            async with aiosqlite.connect(self.database_path) as db:
                cursor = await db.execute(
                    'SELECT * FROM placeholder_metadata WHERE placeholder_id = ?',
                    (placeholder_id,)
                )
                row = await cursor.fetchone()
                
                if row:
                    return PlaceholderMetadata(
                        placeholder_id=row[0],
                        name=row[1],
                        description=row[2] or "",
                        category=row[3] or "default",
                        tags=json.loads(row[4]) if row[4] else [],
                        created_at=datetime.fromisoformat(row[5]),
                        updated_at=datetime.fromisoformat(row[6]),
                        created_by=row[7],
                        last_analyzed_at=datetime.fromisoformat(row[8]) if row[8] else None,
                        analysis_count=row[9] or 0,
                        success_rate=row[10] or 0.0,
                        avg_execution_time_ms=row[11] or 0.0,
                        data_sources=json.loads(row[12]) if row[12] else [],
                        templates=json.loads(row[13]) if row[13] else [],
                        custom_attributes=json.loads(row[14]) if row[14] else {}
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"获取元数据失败: {e}")
            return None
    
    async def search_metadata(self, 
                             category: Optional[str] = None,
                             tags: Optional[List[str]] = None,
                             created_by: Optional[str] = None,
                             name_pattern: Optional[str] = None,
                             limit: int = 100) -> List[PlaceholderMetadata]:
        """搜索占位符元数据"""
        try:
            conditions = []
            params = []
            
            if category:
                conditions.append('category = ?')
                params.append(category)
            
            if created_by:
                conditions.append('created_by = ?')
                params.append(created_by)
            
            if name_pattern:
                conditions.append('name LIKE ?')
                params.append(f'%{name_pattern}%')
            
            where_clause = ' AND '.join(conditions) if conditions else '1=1'
            
            async with aiosqlite.connect(self.database_path) as db:
                cursor = await db.execute(f'''
                    SELECT * FROM placeholder_metadata 
                    WHERE {where_clause}
                    ORDER BY updated_at DESC
                    LIMIT ?
                ''', params + [limit])
                
                rows = await cursor.fetchall()
                results = []
                
                for row in rows:
                    metadata = PlaceholderMetadata(
                        placeholder_id=row[0],
                        name=row[1],
                        description=row[2] or "",
                        category=row[3] or "default",
                        tags=json.loads(row[4]) if row[4] else [],
                        created_at=datetime.fromisoformat(row[5]),
                        updated_at=datetime.fromisoformat(row[6]),
                        created_by=row[7],
                        last_analyzed_at=datetime.fromisoformat(row[8]) if row[8] else None,
                        analysis_count=row[9] or 0,
                        success_rate=row[10] or 0.0,
                        avg_execution_time_ms=row[11] or 0.0,
                        data_sources=json.loads(row[12]) if row[12] else [],
                        templates=json.loads(row[13]) if row[13] else [],
                        custom_attributes=json.loads(row[14]) if row[14] else {}
                    )
                    
                    # 标签过滤（如果指定）
                    if not tags or any(tag in metadata.tags for tag in tags):
                        results.append(metadata)
                
                return results
                
        except Exception as e:
            logger.error(f"搜索元数据失败: {e}")
            return []
    
    async def record_usage_metrics(self, metrics: UsageMetrics) -> bool:
        """记录使用指标"""
        try:
            async with aiosqlite.connect(self.database_path) as db:
                # 使用INSERT OR REPLACE来处理冲突
                await db.execute('''
                    INSERT OR REPLACE INTO usage_metrics (
                        placeholder_id, date, analysis_count, success_count,
                        error_count, total_execution_time_ms, avg_execution_time_ms,
                        unique_users, data_volume_processed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metrics.placeholder_id,
                    metrics.date.date().isoformat(),
                    metrics.analysis_count,
                    metrics.success_count,
                    metrics.error_count,
                    metrics.total_execution_time_ms,
                    metrics.avg_execution_time_ms,
                    metrics.unique_users,
                    metrics.data_volume_processed
                ))
                
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"记录使用指标失败: {e}")
            return False
    
    async def get_usage_metrics(self, 
                               placeholder_id: str,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None,
                               limit: int = 30) -> List[UsageMetrics]:
        """获取使用指标"""
        try:
            conditions = ['placeholder_id = ?']
            params = [placeholder_id]
            
            if start_date:
                conditions.append('date >= ?')
                params.append(start_date.date().isoformat())
            
            if end_date:
                conditions.append('date <= ?')
                params.append(end_date.date().isoformat())
            
            where_clause = ' AND '.join(conditions)
            
            async with aiosqlite.connect(self.database_path) as db:
                cursor = await db.execute(f'''
                    SELECT * FROM usage_metrics
                    WHERE {where_clause}
                    ORDER BY date DESC
                    LIMIT ?
                ''', params + [limit])
                
                rows = await cursor.fetchall()
                results = []
                
                for row in rows:
                    results.append(UsageMetrics(
                        placeholder_id=row[1],
                        date=datetime.fromisoformat(row[2]),
                        analysis_count=row[3] or 0,
                        success_count=row[4] or 0,
                        error_count=row[5] or 0,
                        total_execution_time_ms=row[6] or 0.0,
                        avg_execution_time_ms=row[7] or 0.0,
                        unique_users=row[8] or 0,
                        data_volume_processed=row[9] or 0
                    ))
                
                return results
                
        except Exception as e:
            logger.error(f"获取使用指标失败: {e}")
            return []
    
    async def get_aggregated_metrics(self, 
                                    placeholder_ids: Optional[List[str]] = None,
                                    start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """获取聚合指标"""
        try:
            conditions = []
            params = []
            
            if placeholder_ids:
                placeholders = ','.join(['?' for _ in placeholder_ids])
                conditions.append(f'placeholder_id IN ({placeholders})')
                params.extend(placeholder_ids)
            
            if start_date:
                conditions.append('date >= ?')
                params.append(start_date.date().isoformat())
            
            if end_date:
                conditions.append('date <= ?')
                params.append(end_date.date().isoformat())
            
            where_clause = ' AND '.join(conditions) if conditions else '1=1'
            
            async with aiosqlite.connect(self.database_path) as db:
                # 总体统计
                cursor = await db.execute(f'''
                    SELECT 
                        COUNT(DISTINCT placeholder_id) as unique_placeholders,
                        SUM(analysis_count) as total_analyses,
                        SUM(success_count) as total_successes,
                        SUM(error_count) as total_errors,
                        AVG(avg_execution_time_ms) as avg_execution_time,
                        SUM(unique_users) as total_users,
                        SUM(data_volume_processed) as total_data_volume
                    FROM usage_metrics
                    WHERE {where_clause}
                ''', params)
                
                row = await cursor.fetchone()
                
                if row:
                    total_analyses = row[1] or 0
                    total_successes = row[2] or 0
                    success_rate = (total_successes / total_analyses * 100) if total_analyses > 0 else 0
                    
                    return {
                        'unique_placeholders': row[0] or 0,
                        'total_analyses': total_analyses,
                        'total_successes': total_successes,
                        'total_errors': row[3] or 0,
                        'success_rate_percent': success_rate,
                        'avg_execution_time_ms': row[4] or 0.0,
                        'total_users': row[5] or 0,
                        'total_data_volume': row[6] or 0
                    }
                
                return {}
                
        except Exception as e:
            logger.error(f"获取聚合指标失败: {e}")
            return {}
    
    async def get_top_placeholders(self, 
                                  metric: str = 'analysis_count',
                                  limit: int = 10,
                                  time_range_days: int = 30) -> List[Dict[str, Any]]:
        """获取排行榜"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=time_range_days)).date().isoformat()
            
            # 根据指标选择聚合函数
            if metric in ['analysis_count', 'success_count', 'error_count', 'unique_users', 'data_volume_processed']:
                agg_func = 'SUM'
            elif metric in ['avg_execution_time_ms']:
                agg_func = 'AVG'
            else:
                agg_func = 'SUM'
                metric = 'analysis_count'  # 默认
            
            async with aiosqlite.connect(self.database_path) as db:
                cursor = await db.execute(f'''
                    SELECT 
                        um.placeholder_id,
                        pm.name,
                        pm.category,
                        {agg_func}(um.{metric}) as metric_value
                    FROM usage_metrics um
                    LEFT JOIN placeholder_metadata pm ON um.placeholder_id = pm.placeholder_id
                    WHERE um.date >= ?
                    GROUP BY um.placeholder_id
                    ORDER BY metric_value DESC
                    LIMIT ?
                ''', (cutoff_date, limit))
                
                rows = await cursor.fetchall()
                results = []
                
                for row in rows:
                    results.append({
                        'placeholder_id': row[0],
                        'name': row[1] or row[0],  # 如果没有名称，使用ID
                        'category': row[2] or 'unknown',
                        'metric_value': row[3] or 0
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"获取排行榜失败: {e}")
            return []
    
    async def delete_metadata(self, placeholder_id: str) -> bool:
        """删除占位符元数据"""
        try:
            async with aiosqlite.connect(self.database_path) as db:
                # 删除元数据
                await db.execute('DELETE FROM placeholder_metadata WHERE placeholder_id = ?', (placeholder_id,))
                
                # 删除使用指标
                await db.execute('DELETE FROM usage_metrics WHERE placeholder_id = ?', (placeholder_id,))
                
                await db.commit()
                logger.info(f"删除占位符元数据: {placeholder_id}")
                return True
                
        except Exception as e:
            logger.error(f"删除元数据失败: {e}")
            return False
    
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
        try:
            cutoff_date = (datetime.now() - timedelta(days=self.retention_days)).date().isoformat()
            
            async with aiosqlite.connect(self.database_path) as db:
                # 清理过期的使用指标
                cursor = await db.execute('DELETE FROM usage_metrics WHERE date < ?', (cutoff_date,))
                deleted_count = cursor.rowcount
                
                await db.commit()
                
                if deleted_count > 0:
                    logger.info(f"清理了 {deleted_count} 条过期使用指标")
                    
        except Exception as e:
            logger.error(f"清理过期数据失败: {e}")
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            async with aiosqlite.connect(self.database_path) as db:
                # 元数据统计
                cursor = await db.execute('SELECT COUNT(*) FROM placeholder_metadata')
                metadata_count = (await cursor.fetchone())[0]
                
                # 使用指标统计
                cursor = await db.execute('SELECT COUNT(*) FROM usage_metrics')
                metrics_count = (await cursor.fetchone())[0]
                
                # 按分类统计
                cursor = await db.execute('''
                    SELECT category, COUNT(*) 
                    FROM placeholder_metadata 
                    GROUP BY category
                ''')
                category_stats = dict(await cursor.fetchall())
                
                # 数据库文件大小
                db_size = Path(self.database_path).stat().st_size if Path(self.database_path).exists() else 0
                
                return {
                    'metadata_count': metadata_count,
                    'metrics_count': metrics_count,
                    'category_distribution': category_stats,
                    'database_size_bytes': db_size,
                    'database_size_mb': db_size / 1024 / 1024,
                    'retention_days': self.retention_days
                }
                
        except Exception as e:
            logger.error(f"获取存储统计失败: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            stats = await self.get_storage_stats()
            
            health_status = "healthy"
            issues = []
            
            # 检查数据库文件
            if not Path(self.database_path).exists():
                issues.append("数据库文件不存在")
                health_status = "error"
                return {
                    'status': health_status,
                    'issues': issues,
                    'stats': {}
                }
            
            # 检查数据库大小
            db_size_mb = stats.get('database_size_mb', 0)
            if db_size_mb > 100:  # 超过100MB
                issues.append(f"数据库文件过大: {db_size_mb:.1f}MB")
                health_status = "warning"
            
            # 测试数据库连接
            async with aiosqlite.connect(self.database_path) as db:
                await db.execute('SELECT 1')
            
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
        """关闭元数据存储"""
        if hasattr(self, '_cleanup_task'):
            self._cleanup_task.cancel()
        logger.info("元数据存储已关闭")