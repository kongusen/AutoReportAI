"""
实时数据管理器

管理占位符的实时数据流和更新
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, List, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import weakref

logger = logging.getLogger(__name__)

@dataclass
class RealtimeDataPoint:
    """实时数据点"""
    placeholder_id: str
    timestamp: datetime
    value: Any
    data_type: str  # 'metric', 'result', 'status'
    metadata: Dict[str, Any]
    source: str

@dataclass
class DataSubscription:
    """数据订阅"""
    subscription_id: str
    placeholder_ids: Set[str]
    data_types: Set[str]
    callback: Callable
    filters: Dict[str, Any]
    created_at: datetime
    last_activity: datetime

class RealtimeDataManager:
    """实时数据管理器"""
    
    def __init__(self, 
                 max_buffer_size: int = 1000,
                 cleanup_interval: int = 300):  # 5分钟清理间隔
        """
        初始化实时数据管理器
        
        Args:
            max_buffer_size: 每个占位符最大缓冲区大小
            cleanup_interval: 清理间隔（秒）
        """
        self.max_buffer_size = max_buffer_size
        self.cleanup_interval = cleanup_interval
        
        # 数据缓冲区：占位符ID -> 数据点队列
        self._data_buffers: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_buffer_size)
        )
        
        # 订阅管理
        self._subscriptions: Dict[str, DataSubscription] = {}
        self._placeholder_subscribers: Dict[str, Set[str]] = defaultdict(set)
        
        # 数据流监控
        self._stream_stats = {
            'total_data_points': 0,
            'active_subscriptions': 0,
            'data_points_per_second': 0.0,
            'last_data_time': None
        }
        
        # 性能监控
        self._performance_metrics = deque(maxlen=100)  # 保留最近100个性能指标
        
        self._lock = asyncio.Lock()
        
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        # 启动性能监控
        self._metrics_task = asyncio.create_task(self._collect_performance_metrics())
        
        logger.info("实时数据管理器初始化完成")
    
    async def publish_data_point(self, data_point: RealtimeDataPoint):
        """发布数据点"""
        async with self._lock:
            try:
                # 添加到缓冲区
                self._data_buffers[data_point.placeholder_id].append(data_point)
                
                # 更新统计
                self._stream_stats['total_data_points'] += 1
                self._stream_stats['last_data_time'] = datetime.now()
                
                # 通知订阅者
                await self._notify_subscribers(data_point)
                
                logger.debug(f"发布数据点: {data_point.placeholder_id} - {data_point.data_type}")
                
            except Exception as e:
                logger.error(f"发布数据点失败: {e}")
                raise
    
    async def publish_placeholder_result(self,
                                       placeholder_id: str,
                                       result_data: Dict[str, Any],
                                       source: str = "analysis"):
        """发布占位符分析结果"""
        data_point = RealtimeDataPoint(
            placeholder_id=placeholder_id,
            timestamp=datetime.now(),
            value=result_data,
            data_type="result",
            metadata={
                'confidence': result_data.get('confidence', 0.0),
                'execution_time_ms': result_data.get('execution_time_ms', 0),
                'success': result_data.get('success', True)
            },
            source=source
        )
        
        await self.publish_data_point(data_point)
    
    async def publish_placeholder_metric(self,
                                       placeholder_id: str,
                                       metric_name: str,
                                       metric_value: float,
                                       metadata: Dict[str, Any] = None):
        """发布占位符性能指标"""
        data_point = RealtimeDataPoint(
            placeholder_id=placeholder_id,
            timestamp=datetime.now(),
            value={
                'metric_name': metric_name,
                'metric_value': metric_value
            },
            data_type="metric",
            metadata=metadata or {},
            source="performance_monitor"
        )
        
        await self.publish_data_point(data_point)
    
    async def publish_placeholder_status(self,
                                       placeholder_id: str,
                                       status: str,
                                       message: str = ""):
        """发布占位符状态更新"""
        data_point = RealtimeDataPoint(
            placeholder_id=placeholder_id,
            timestamp=datetime.now(),
            value={
                'status': status,
                'message': message
            },
            data_type="status",
            metadata={},
            source="status_monitor"
        )
        
        await self.publish_data_point(data_point)
    
    async def subscribe(self,
                       subscription_id: str,
                       placeholder_ids: List[str],
                       data_types: List[str],
                       callback: Callable,
                       filters: Dict[str, Any] = None) -> bool:
        """创建数据订阅"""
        async with self._lock:
            try:
                # 创建订阅对象
                subscription = DataSubscription(
                    subscription_id=subscription_id,
                    placeholder_ids=set(placeholder_ids),
                    data_types=set(data_types),
                    callback=callback,
                    filters=filters or {},
                    created_at=datetime.now(),
                    last_activity=datetime.now()
                )
                
                # 存储订阅
                self._subscriptions[subscription_id] = subscription
                
                # 更新占位符-订阅者映射
                for placeholder_id in placeholder_ids:
                    self._placeholder_subscribers[placeholder_id].add(subscription_id)
                
                # 更新统计
                self._stream_stats['active_subscriptions'] = len(self._subscriptions)
                
                logger.info(f"创建订阅: {subscription_id}, 占位符: {len(placeholder_ids)}, 类型: {data_types}")
                return True
                
            except Exception as e:
                logger.error(f"创建订阅失败: {e}")
                return False
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        async with self._lock:
            try:
                if subscription_id not in self._subscriptions:
                    return False
                
                subscription = self._subscriptions[subscription_id]
                
                # 从占位符-订阅者映射中移除
                for placeholder_id in subscription.placeholder_ids:
                    if placeholder_id in self._placeholder_subscribers:
                        self._placeholder_subscribers[placeholder_id].discard(subscription_id)
                        
                        # 如果没有订阅者了，清理映射
                        if not self._placeholder_subscribers[placeholder_id]:
                            del self._placeholder_subscribers[placeholder_id]
                
                # 删除订阅
                del self._subscriptions[subscription_id]
                
                # 更新统计
                self._stream_stats['active_subscriptions'] = len(self._subscriptions)
                
                logger.info(f"取消订阅: {subscription_id}")
                return True
                
            except Exception as e:
                logger.error(f"取消订阅失败: {e}")
                return False
    
    async def _notify_subscribers(self, data_point: RealtimeDataPoint):
        """通知订阅者"""
        if data_point.placeholder_id not in self._placeholder_subscribers:
            return
        
        subscriber_ids = self._placeholder_subscribers[data_point.placeholder_id].copy()
        
        for subscription_id in subscriber_ids:
            if subscription_id not in self._subscriptions:
                continue
            
            subscription = self._subscriptions[subscription_id]
            
            # 检查数据类型过滤
            if data_point.data_type not in subscription.data_types:
                continue
            
            # 检查自定义过滤器
            if not self._matches_filters(data_point, subscription.filters):
                continue
            
            # 更新订阅活跃时间
            subscription.last_activity = datetime.now()
            
            # 异步调用回调函数
            try:
                # 使用弱引用避免内存泄漏
                callback = subscription.callback
                if callback:
                    asyncio.create_task(self._safe_callback(callback, data_point))
                    
            except Exception as e:
                logger.error(f"通知订阅者失败 {subscription_id}: {e}")
    
    async def _safe_callback(self, callback: Callable, data_point: RealtimeDataPoint):
        """安全调用回调函数"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(data_point)
            else:
                callback(data_point)
        except Exception as e:
            logger.error(f"回调函数执行失败: {e}")
    
    def _matches_filters(self, data_point: RealtimeDataPoint, filters: Dict[str, Any]) -> bool:
        """检查数据点是否匹配过滤器"""
        if not filters:
            return True
        
        try:
            # 检查值过滤器
            if 'min_value' in filters:
                if isinstance(data_point.value, (int, float)):
                    if data_point.value < filters['min_value']:
                        return False
            
            if 'max_value' in filters:
                if isinstance(data_point.value, (int, float)):
                    if data_point.value > filters['max_value']:
                        return False
            
            # 检查元数据过滤器
            if 'metadata_filters' in filters:
                metadata_filters = filters['metadata_filters']
                for key, expected_value in metadata_filters.items():
                    if key not in data_point.metadata:
                        return False
                    if data_point.metadata[key] != expected_value:
                        return False
            
            # 检查源过滤器
            if 'source' in filters:
                if data_point.source != filters['source']:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"过滤器匹配失败: {e}")
            return False
    
    async def get_recent_data(self, 
                             placeholder_id: str,
                             data_type: Optional[str] = None,
                             limit: int = 100,
                             since: Optional[datetime] = None) -> List[RealtimeDataPoint]:
        """获取最近的数据点"""
        async with self._lock:
            if placeholder_id not in self._data_buffers:
                return []
            
            data_points = list(self._data_buffers[placeholder_id])
            
            # 应用过滤器
            filtered_points = []
            for point in data_points:
                # 数据类型过滤
                if data_type and point.data_type != data_type:
                    continue
                
                # 时间过滤
                if since and point.timestamp < since:
                    continue
                
                filtered_points.append(point)
            
            # 按时间倒序排列，返回最新的
            filtered_points.sort(key=lambda p: p.timestamp, reverse=True)
            return filtered_points[:limit] if limit > 0 else filtered_points
    
    async def get_placeholder_stream_info(self, placeholder_id: str) -> Dict[str, Any]:
        """获取占位符的流信息"""
        async with self._lock:
            buffer = self._data_buffers.get(placeholder_id, deque())
            
            if not buffer:
                return {
                    'placeholder_id': placeholder_id,
                    'data_points_count': 0,
                    'subscriber_count': 0,
                    'last_update': None,
                    'data_types': []
                }
            
            # 统计数据类型
            data_types = set()
            last_update = None
            
            for point in buffer:
                data_types.add(point.data_type)
                if last_update is None or point.timestamp > last_update:
                    last_update = point.timestamp
            
            subscriber_count = len(self._placeholder_subscribers.get(placeholder_id, set()))
            
            return {
                'placeholder_id': placeholder_id,
                'data_points_count': len(buffer),
                'subscriber_count': subscriber_count,
                'last_update': last_update.isoformat() if last_update else None,
                'data_types': list(data_types)
            }
    
    async def get_subscription_info(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """获取订阅信息"""
        async with self._lock:
            if subscription_id not in self._subscriptions:
                return None
            
            subscription = self._subscriptions[subscription_id]
            
            return {
                'subscription_id': subscription.subscription_id,
                'placeholder_ids': list(subscription.placeholder_ids),
                'data_types': list(subscription.data_types),
                'filters': subscription.filters,
                'created_at': subscription.created_at.isoformat(),
                'last_activity': subscription.last_activity.isoformat()
            }
    
    async def _periodic_cleanup(self):
        """定期清理过期订阅"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_inactive_subscriptions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理任务出错: {e}")
    
    async def _cleanup_inactive_subscriptions(self):
        """清理不活跃的订阅"""
        async with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=1)  # 1小时不活跃就清理
            inactive_subscriptions = []
            
            for subscription_id, subscription in self._subscriptions.items():
                if subscription.last_activity < cutoff_time:
                    inactive_subscriptions.append(subscription_id)
            
            for subscription_id in inactive_subscriptions:
                await self.unsubscribe(subscription_id)
            
            if inactive_subscriptions:
                logger.info(f"清理了 {len(inactive_subscriptions)} 个不活跃订阅")
    
    async def _collect_performance_metrics(self):
        """收集性能指标"""
        while True:
            try:
                await asyncio.sleep(10)  # 每10秒收集一次
                
                current_time = datetime.now()
                
                # 计算数据点速率
                if self._performance_metrics:
                    last_metric = self._performance_metrics[-1]
                    time_diff = (current_time - last_metric['timestamp']).total_seconds()
                    data_diff = self._stream_stats['total_data_points'] - last_metric['total_data_points']
                    
                    if time_diff > 0:
                        self._stream_stats['data_points_per_second'] = data_diff / time_diff
                
                # 收集性能指标
                metric = {
                    'timestamp': current_time,
                    'total_data_points': self._stream_stats['total_data_points'],
                    'active_subscriptions': self._stream_stats['active_subscriptions'],
                    'active_placeholders': len(self._data_buffers),
                    'memory_usage_mb': len(str(self._data_buffers)) / 1024 / 1024  # 简化计算
                }
                
                self._performance_metrics.append(metric)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"性能指标收集出错: {e}")
    
    async def get_stream_stats(self) -> Dict[str, Any]:
        """获取流统计信息"""
        async with self._lock:
            return {
                'total_data_points': self._stream_stats['total_data_points'],
                'active_subscriptions': self._stream_stats['active_subscriptions'],
                'active_placeholders': len(self._data_buffers),
                'data_points_per_second': self._stream_stats['data_points_per_second'],
                'last_data_time': self._stream_stats['last_data_time'].isoformat() if self._stream_stats['last_data_time'] else None,
                'buffer_usage': {
                    placeholder_id: len(buffer)
                    for placeholder_id, buffer in self._data_buffers.items()
                }
            }
    
    async def get_performance_metrics(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取性能指标历史"""
        metrics = list(self._performance_metrics)
        metrics.sort(key=lambda m: m['timestamp'], reverse=True)
        
        # 转换时间戳为字符串
        for metric in metrics[:limit]:
            metric['timestamp'] = metric['timestamp'].isoformat()
        
        return metrics[:limit]
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            stats = await self.get_stream_stats()
            
            health_status = "healthy"
            issues = []
            
            # 检查数据流活跃度
            if stats['last_data_time']:
                last_data_time = datetime.fromisoformat(stats['last_data_time'])
                minutes_since_last_data = (datetime.now() - last_data_time).total_seconds() / 60
                
                if minutes_since_last_data > 30:  # 超过30分钟没有数据
                    issues.append("数据流不活跃")
                    health_status = "warning"
            
            # 检查订阅健康度
            if stats['active_subscriptions'] == 0:
                issues.append("没有活跃订阅")
                health_status = "warning"
            
            # 检查缓冲区使用情况
            buffer_usage = stats.get('buffer_usage', {})
            full_buffers = sum(1 for size in buffer_usage.values() if size >= self.max_buffer_size * 0.9)
            
            if full_buffers > 0:
                issues.append(f"{full_buffers} 个缓冲区接近满载")
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
        """关闭实时数据管理器"""
        # 取消任务
        if hasattr(self, '_cleanup_task'):
            self._cleanup_task.cancel()
        
        if hasattr(self, '_metrics_task'):
            self._metrics_task.cancel()
        
        # 清理所有订阅
        subscription_ids = list(self._subscriptions.keys())
        for subscription_id in subscription_ids:
            await self.unsubscribe(subscription_id)
        
        logger.info("实时数据管理器已关闭")

# 全局实时数据管理器实例
_realtime_data_manager: Optional[RealtimeDataManager] = None

def get_realtime_data_manager() -> RealtimeDataManager:
    """获取全局实时数据管理器实例"""
    global _realtime_data_manager
    if _realtime_data_manager is None:
        _realtime_data_manager = RealtimeDataManager()
    return _realtime_data_manager

def initialize_realtime_data_manager(**kwargs) -> RealtimeDataManager:
    """初始化全局实时数据管理器"""
    global _realtime_data_manager
    _realtime_data_manager = RealtimeDataManager(**kwargs)
    return _realtime_data_manager