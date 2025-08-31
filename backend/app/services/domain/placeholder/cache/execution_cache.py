"""
执行历史缓存

缓存占位符的执行历史和性能指标
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import deque
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class ExecutionRecord:
    """执行记录"""
    placeholder_id: str
    execution_id: str
    timestamp: datetime
    execution_time_ms: float
    success: bool
    result_preview: Optional[str]  # 结果预览（前100个字符）
    error_message: Optional[str]
    context_hash: str
    sql_query_hash: Optional[str]
    performance_metrics: Dict[str, Any]

@dataclass
class ExecutionStats:
    """执行统计"""
    placeholder_id: str
    total_executions: int
    success_rate: float
    avg_execution_time_ms: float
    min_execution_time_ms: float
    max_execution_time_ms: float
    last_execution: Optional[datetime]
    last_success: Optional[datetime]
    last_error: Optional[str]

class ExecutionCache:
    """执行历史缓存"""
    
    def __init__(self, 
                 max_records_per_placeholder: int = 50,
                 max_total_records: int = 5000,
                 retention_days: int = 30,
                 cleanup_interval: int = 3600):  # 1小时清理间隔
        self.max_records_per_placeholder = max_records_per_placeholder
        self.max_total_records = max_total_records
        self.retention_days = retention_days
        self.cleanup_interval = cleanup_interval
        
        # 按占位符ID存储执行记录
        self._execution_records: Dict[str, deque] = {}
        self._execution_stats: Dict[str, ExecutionStats] = {}
        self._lock = asyncio.Lock()
        
        # 全局统计
        self.global_stats = {
            'total_records': 0,
            'total_placeholders': 0,
            'records_added_today': 0,
            'last_cleanup': datetime.now()
        }
        
        # 启动定期清理任务
        self._cleanup_task = None
        self._start_cleanup_task()
    
    async def add_execution_record(self, 
                                  placeholder_id: str,
                                  execution_id: str,
                                  execution_time_ms: float,
                                  success: bool,
                                  result_preview: Optional[str] = None,
                                  error_message: Optional[str] = None,
                                  context_hash: str = "",
                                  sql_query_hash: Optional[str] = None,
                                  performance_metrics: Dict[str, Any] = None):
        """添加执行记录"""
        record = ExecutionRecord(
            placeholder_id=placeholder_id,
            execution_id=execution_id,
            timestamp=datetime.now(),
            execution_time_ms=execution_time_ms,
            success=success,
            result_preview=result_preview,
            error_message=error_message,
            context_hash=context_hash,
            sql_query_hash=sql_query_hash,
            performance_metrics=performance_metrics or {}
        )
        
        async with self._lock:
            # 初始化占位符的记录队列
            if placeholder_id not in self._execution_records:
                self._execution_records[placeholder_id] = deque(maxlen=self.max_records_per_placeholder)
                self.global_stats['total_placeholders'] += 1
            
            # 添加记录
            self._execution_records[placeholder_id].append(record)
            self.global_stats['total_records'] += 1
            self.global_stats['records_added_today'] += 1
            
            # 更新统计信息
            await self._update_execution_stats(placeholder_id, record)
            
            # 检查总记录数限制
            if self.global_stats['total_records'] > self.max_total_records:
                await self._trim_oldest_records()
    
    async def get_execution_history(self, 
                                   placeholder_id: str,
                                   limit: int = 10) -> List[ExecutionRecord]:
        """获取执行历史"""
        async with self._lock:
            records = self._execution_records.get(placeholder_id, deque())
            # 返回最新的记录
            return list(records)[-limit:] if limit > 0 else list(records)
    
    async def get_execution_stats(self, placeholder_id: str) -> Optional[ExecutionStats]:
        """获取执行统计"""
        async with self._lock:
            return self._execution_stats.get(placeholder_id)
    
    async def get_recent_executions(self, 
                                   hours: int = 24,
                                   limit: int = 100) -> List[ExecutionRecord]:
        """获取最近的执行记录"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_records = []
        
        async with self._lock:
            for records in self._execution_records.values():
                for record in records:
                    if record.timestamp >= cutoff_time:
                        recent_records.append(record)
            
            # 按时间倒序排列，返回最新的记录
            recent_records.sort(key=lambda r: r.timestamp, reverse=True)
            return recent_records[:limit] if limit > 0 else recent_records
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        async with self._lock:
            if not self._execution_stats:
                return {
                    'total_placeholders': 0,
                    'avg_success_rate': 0,
                    'avg_execution_time_ms': 0,
                    'total_executions': 0
                }
            
            total_executions = sum(stats.total_executions for stats in self._execution_stats.values())
            avg_success_rate = sum(stats.success_rate for stats in self._execution_stats.values()) / len(self._execution_stats)
            avg_execution_time = sum(stats.avg_execution_time_ms for stats in self._execution_stats.values()) / len(self._execution_stats)
            
            return {
                'total_placeholders': len(self._execution_stats),
                'total_executions': total_executions,
                'avg_success_rate': avg_success_rate,
                'avg_execution_time_ms': avg_execution_time,
                'performance_distribution': {
                    'fast_placeholders': len([s for s in self._execution_stats.values() if s.avg_execution_time_ms < 100]),
                    'medium_placeholders': len([s for s in self._execution_stats.values() if 100 <= s.avg_execution_time_ms < 500]),
                    'slow_placeholders': len([s for s in self._execution_stats.values() if s.avg_execution_time_ms >= 500])
                }
            }
    
    async def find_similar_executions(self, 
                                     context_hash: str,
                                     sql_query_hash: Optional[str] = None,
                                     limit: int = 10) -> List[ExecutionRecord]:
        """查找相似的执行记录"""
        similar_records = []
        
        async with self._lock:
            for records in self._execution_records.values():
                for record in records:
                    if record.context_hash == context_hash:
                        if sql_query_hash is None or record.sql_query_hash == sql_query_hash:
                            similar_records.append(record)
            
            # 按时间倒序排列
            similar_records.sort(key=lambda r: r.timestamp, reverse=True)
            return similar_records[:limit] if limit > 0 else similar_records
    
    async def _update_execution_stats(self, placeholder_id: str, record: ExecutionRecord):
        """更新执行统计"""
        if placeholder_id not in self._execution_stats:
            # 创建新的统计记录
            self._execution_stats[placeholder_id] = ExecutionStats(
                placeholder_id=placeholder_id,
                total_executions=1,
                success_rate=1.0 if record.success else 0.0,
                avg_execution_time_ms=record.execution_time_ms,
                min_execution_time_ms=record.execution_time_ms,
                max_execution_time_ms=record.execution_time_ms,
                last_execution=record.timestamp,
                last_success=record.timestamp if record.success else None,
                last_error=record.error_message if not record.success else None
            )
        else:
            # 更新现有统计
            stats = self._execution_stats[placeholder_id]
            stats.total_executions += 1
            
            # 重新计算成功率（基于最近的记录）
            records = list(self._execution_records[placeholder_id])
            successful_executions = sum(1 for r in records if r.success)
            stats.success_rate = successful_executions / len(records) if records else 0
            
            # 更新执行时间统计
            execution_times = [r.execution_time_ms for r in records]
            stats.avg_execution_time_ms = sum(execution_times) / len(execution_times)
            stats.min_execution_time_ms = min(execution_times)
            stats.max_execution_time_ms = max(execution_times)
            
            # 更新时间戳
            stats.last_execution = record.timestamp
            if record.success:
                stats.last_success = record.timestamp
            else:
                stats.last_error = record.error_message
    
    async def _trim_oldest_records(self):
        """修剪最旧的记录"""
        # 简单策略：删除最旧占位符的一些记录
        if not self._execution_records:
            return
        
        # 找到最旧的占位符（基于最早的执行记录）
        oldest_placeholder = min(
            self._execution_records.keys(),
            key=lambda pid: min(r.timestamp for r in self._execution_records[pid]) if self._execution_records[pid] else datetime.now()
        )
        
        # 删除该占位符的最旧记录
        if oldest_placeholder in self._execution_records:
            records = self._execution_records[oldest_placeholder]
            if records:
                records.popleft()  # 删除最旧的记录
                self.global_stats['total_records'] -= 1
                
                # 如果队列为空，删除该占位符
                if not records:
                    del self._execution_records[oldest_placeholder]
                    if oldest_placeholder in self._execution_stats:
                        del self._execution_stats[oldest_placeholder]
                    self.global_stats['total_placeholders'] -= 1
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self.cleanup_interval)
                    await self._cleanup_old_records()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"执行缓存清理任务出错: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def _cleanup_old_records(self):
        """清理旧记录"""
        cutoff_time = datetime.now() - timedelta(days=self.retention_days)
        removed_count = 0
        
        async with self._lock:
            placeholders_to_remove = []
            
            for placeholder_id, records in self._execution_records.items():
                # 过滤掉过期的记录
                original_len = len(records)
                
                # 创建新的队列，只包含未过期的记录
                new_records = deque(
                    [r for r in records if r.timestamp >= cutoff_time],
                    maxlen=self.max_records_per_placeholder
                )
                
                removed_count += (original_len - len(new_records))
                
                if new_records:
                    self._execution_records[placeholder_id] = new_records
                else:
                    placeholders_to_remove.append(placeholder_id)
            
            # 删除空的占位符记录
            for placeholder_id in placeholders_to_remove:
                del self._execution_records[placeholder_id]
                if placeholder_id in self._execution_stats:
                    del self._execution_stats[placeholder_id]
                self.global_stats['total_placeholders'] -= 1
            
            self.global_stats['total_records'] -= removed_count
            self.global_stats['last_cleanup'] = datetime.now()
            
            if removed_count > 0:
                logger.debug(f"清理了 {removed_count} 条过期执行记录")
    
    async def clear_placeholder_history(self, placeholder_id: str):
        """清除特定占位符的历史记录"""
        async with self._lock:
            if placeholder_id in self._execution_records:
                record_count = len(self._execution_records[placeholder_id])
                del self._execution_records[placeholder_id]
                self.global_stats['total_records'] -= record_count
            
            if placeholder_id in self._execution_stats:
                del self._execution_stats[placeholder_id]
                self.global_stats['total_placeholders'] -= 1
    
    async def clear_all(self):
        """清除所有执行记录"""
        async with self._lock:
            self._execution_records.clear()
            self._execution_stats.clear()
            self.global_stats.update({
                'total_records': 0,
                'total_placeholders': 0,
                'records_added_today': 0
            })
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            'global_stats': self.global_stats.copy(),
            'config': {
                'max_records_per_placeholder': self.max_records_per_placeholder,
                'max_total_records': self.max_total_records,
                'retention_days': self.retention_days
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        stats = self.get_cache_stats()
        
        health_status = "healthy"
        issues = []
        
        # 检查记录数量
        if stats['global_stats']['total_records'] >= self.max_total_records * 0.9:
            issues.append("执行记录数量接近上限")
            health_status = "warning"
        
        # 检查清理是否正常
        last_cleanup = stats['global_stats']['last_cleanup']
        if isinstance(last_cleanup, datetime):
            hours_since_cleanup = (datetime.now() - last_cleanup).total_seconds() / 3600
            if hours_since_cleanup > self.cleanup_interval / 3600 * 2:  # 超过2个清理周期
                issues.append("清理任务可能异常")
                health_status = "warning"
        
        return {
            'status': health_status,
            'total_records': stats['global_stats']['total_records'],
            'total_placeholders': stats['global_stats']['total_placeholders'],
            'issues': issues,
            'stats': stats
        }
    
    def shutdown(self):
        """关闭缓存"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("执行缓存已关闭")