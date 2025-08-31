"""
数据流处理器

处理和转换实时数据流
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import deque
import statistics

from .realtime_data_manager import RealtimeDataPoint

logger = logging.getLogger(__name__)

@dataclass
class ProcessingRule:
    """处理规则"""
    rule_id: str
    name: str
    description: str
    condition: Dict[str, Any]  # 触发条件
    action: Dict[str, Any]     # 执行动作
    enabled: bool = True
    priority: int = 0          # 优先级，数字越大优先级越高

@dataclass
class AggregationConfig:
    """聚合配置"""
    placeholder_id: str
    metric_name: str
    aggregation_type: str  # 'avg', 'sum', 'min', 'max', 'count'
    time_window_seconds: int
    trigger_threshold: Optional[float] = None

class DataStreamProcessor:
    """数据流处理器"""
    
    def __init__(self, 
                 realtime_manager,
                 max_history_size: int = 1000):
        """
        初始化数据流处理器
        
        Args:
            realtime_manager: 实时数据管理器实例
            max_history_size: 最大历史记录大小
        """
        self.realtime_manager = realtime_manager
        self.max_history_size = max_history_size
        
        # 处理规则
        self._processing_rules: Dict[str, ProcessingRule] = {}
        
        # 聚合器
        self._aggregators: Dict[str, AggregationConfig] = {}
        self._aggregation_buffers: Dict[str, deque] = {}
        
        # 处理历史
        self._processing_history = deque(maxlen=max_history_size)
        
        # 统计信息
        self._stats = {
            'processed_data_points': 0,
            'triggered_rules': 0,
            'aggregations_computed': 0,
            'errors': 0
        }
        
        self._lock = asyncio.Lock()
        
        # 启动聚合器任务
        self._aggregation_task = asyncio.create_task(self._run_aggregations())
        
        logger.info("数据流处理器初始化完成")
    
    async def add_processing_rule(self, rule: ProcessingRule) -> bool:
        """添加处理规则"""
        async with self._lock:
            try:
                self._processing_rules[rule.rule_id] = rule
                logger.info(f"添加处理规则: {rule.rule_id} - {rule.name}")
                return True
            except Exception as e:
                logger.error(f"添加处理规则失败: {e}")
                return False
    
    async def remove_processing_rule(self, rule_id: str) -> bool:
        """移除处理规则"""
        async with self._lock:
            try:
                if rule_id in self._processing_rules:
                    del self._processing_rules[rule_id]
                    logger.info(f"移除处理规则: {rule_id}")
                    return True
                return False
            except Exception as e:
                logger.error(f"移除处理规则失败: {e}")
                return False
    
    async def add_aggregator(self, config: AggregationConfig) -> bool:
        """添加聚合器"""
        async with self._lock:
            try:
                agg_key = f"{config.placeholder_id}_{config.metric_name}_{config.aggregation_type}"
                self._aggregators[agg_key] = config
                self._aggregation_buffers[agg_key] = deque(maxlen=1000)
                
                logger.info(f"添加聚合器: {agg_key}")
                return True
            except Exception as e:
                logger.error(f"添加聚合器失败: {e}")
                return False
    
    async def process_data_point(self, data_point: RealtimeDataPoint) -> Dict[str, Any]:
        """处理数据点"""
        async with self._lock:
            processing_result = {
                'data_point_id': f"{data_point.placeholder_id}_{data_point.timestamp.isoformat()}",
                'processed_at': datetime.now(),
                'rules_triggered': [],
                'aggregations_updated': [],
                'transformed_data': None,
                'errors': []
            }
            
            try:
                # 1. 应用处理规则
                triggered_rules = await self._apply_processing_rules(data_point)
                processing_result['rules_triggered'] = triggered_rules
                
                # 2. 更新聚合缓冲区
                updated_aggregations = await self._update_aggregations(data_point)
                processing_result['aggregations_updated'] = updated_aggregations
                
                # 3. 数据转换（如果需要）
                transformed_data = await self._transform_data_point(data_point)
                if transformed_data != data_point:
                    processing_result['transformed_data'] = transformed_data
                
                # 更新统计
                self._stats['processed_data_points'] += 1
                self._stats['triggered_rules'] += len(triggered_rules)
                
                # 记录处理历史
                self._processing_history.append(processing_result)
                
                return processing_result
                
            except Exception as e:
                error_msg = f"处理数据点失败: {e}"
                logger.error(error_msg)
                processing_result['errors'].append(error_msg)
                self._stats['errors'] += 1
                return processing_result
    
    async def _apply_processing_rules(self, data_point: RealtimeDataPoint) -> List[str]:
        """应用处理规则"""
        triggered_rules = []
        
        # 按优先级排序规则
        sorted_rules = sorted(
            self._processing_rules.values(),
            key=lambda r: r.priority,
            reverse=True
        )
        
        for rule in sorted_rules:
            if not rule.enabled:
                continue
            
            try:
                if await self._check_rule_condition(data_point, rule):
                    await self._execute_rule_action(data_point, rule)
                    triggered_rules.append(rule.rule_id)
                    
            except Exception as e:
                logger.error(f"规则执行失败 {rule.rule_id}: {e}")
        
        return triggered_rules
    
    async def _check_rule_condition(self, data_point: RealtimeDataPoint, rule: ProcessingRule) -> bool:
        """检查规则条件"""
        condition = rule.condition
        
        try:
            # 检查占位符ID条件
            if 'placeholder_ids' in condition:
                if data_point.placeholder_id not in condition['placeholder_ids']:
                    return False
            
            # 检查数据类型条件
            if 'data_types' in condition:
                if data_point.data_type not in condition['data_types']:
                    return False
            
            # 检查数值条件
            if 'value_conditions' in condition:
                value_conditions = condition['value_conditions']
                
                if isinstance(data_point.value, dict):
                    for field, field_condition in value_conditions.items():
                        if field not in data_point.value:
                            continue
                        
                        field_value = data_point.value[field]
                        
                        if not self._check_value_condition(field_value, field_condition):
                            return False
                
                elif isinstance(data_point.value, (int, float)):
                    if not self._check_value_condition(data_point.value, value_conditions):
                        return False
            
            # 检查元数据条件
            if 'metadata_conditions' in condition:
                metadata_conditions = condition['metadata_conditions']
                for key, expected_value in metadata_conditions.items():
                    if key not in data_point.metadata:
                        return False
                    if data_point.metadata[key] != expected_value:
                        return False
            
            # 检查时间条件
            if 'time_conditions' in condition:
                time_conditions = condition['time_conditions']
                
                if 'after' in time_conditions:
                    after_time = datetime.fromisoformat(time_conditions['after'])
                    if data_point.timestamp <= after_time:
                        return False
                
                if 'before' in time_conditions:
                    before_time = datetime.fromisoformat(time_conditions['before'])
                    if data_point.timestamp >= before_time:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查规则条件失败: {e}")
            return False
    
    def _check_value_condition(self, value: Union[int, float], condition: Dict[str, Any]) -> bool:
        """检查数值条件"""
        try:
            if 'gt' in condition and value <= condition['gt']:
                return False
            if 'gte' in condition and value < condition['gte']:
                return False
            if 'lt' in condition and value >= condition['lt']:
                return False
            if 'lte' in condition and value > condition['lte']:
                return False
            if 'eq' in condition and value != condition['eq']:
                return False
            if 'ne' in condition and value == condition['ne']:
                return False
            
            return True
        except Exception:
            return False
    
    async def _execute_rule_action(self, data_point: RealtimeDataPoint, rule: ProcessingRule):
        """执行规则动作"""
        action = rule.action
        
        try:
            # 发布新数据点
            if action.get('type') == 'publish_data_point':
                new_data_point = RealtimeDataPoint(
                    placeholder_id=action.get('target_placeholder_id', data_point.placeholder_id),
                    timestamp=datetime.now(),
                    value=action.get('value', data_point.value),
                    data_type=action.get('data_type', 'derived'),
                    metadata={
                        **data_point.metadata,
                        'derived_from': data_point.placeholder_id,
                        'rule_id': rule.rule_id
                    },
                    source=f"rule_{rule.rule_id}"
                )
                
                await self.realtime_manager.publish_data_point(new_data_point)
            
            # 发送通知
            elif action.get('type') == 'send_notification':
                notification_data = {
                    'rule_id': rule.rule_id,
                    'rule_name': rule.name,
                    'placeholder_id': data_point.placeholder_id,
                    'data_point': data_point,
                    'message': action.get('message', f'规则 {rule.name} 被触发'),
                    'severity': action.get('severity', 'info')
                }
                
                # 这里可以集成通知服务
                logger.info(f"规则通知: {notification_data['message']}")
            
            # 记录日志
            elif action.get('type') == 'log':
                log_level = action.get('level', 'info')
                log_message = action.get('message', f'规则 {rule.name} 被触发')
                
                if log_level == 'error':
                    logger.error(log_message)
                elif log_level == 'warning':
                    logger.warning(log_message)
                else:
                    logger.info(log_message)
            
            # 自定义动作
            elif action.get('type') == 'custom':
                # 可以扩展自定义动作处理
                pass
                
        except Exception as e:
            logger.error(f"执行规则动作失败 {rule.rule_id}: {e}")
    
    async def _update_aggregations(self, data_point: RealtimeDataPoint) -> List[str]:
        """更新聚合"""
        updated_aggregations = []
        
        for agg_key, config in self._aggregators.items():
            if config.placeholder_id != data_point.placeholder_id:
                continue
            
            if data_point.data_type != 'metric':
                continue
            
            # 检查是否是目标指标
            if isinstance(data_point.value, dict):
                metric_name = data_point.value.get('metric_name')
                if metric_name == config.metric_name:
                    metric_value = data_point.value.get('metric_value')
                    if metric_value is not None:
                        self._aggregation_buffers[agg_key].append({
                            'value': metric_value,
                            'timestamp': data_point.timestamp
                        })
                        updated_aggregations.append(agg_key)
        
        return updated_aggregations
    
    async def _transform_data_point(self, data_point: RealtimeDataPoint) -> RealtimeDataPoint:
        """数据转换（可扩展）"""
        # 这里可以实现各种数据转换逻辑
        # 目前返回原始数据点
        return data_point
    
    async def _run_aggregations(self):
        """运行聚合计算"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟运行一次聚合
                await self._compute_aggregations()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"聚合任务出错: {e}")
    
    async def _compute_aggregations(self):
        """计算聚合"""
        async with self._lock:
            current_time = datetime.now()
            
            for agg_key, config in self._aggregators.items():
                try:
                    buffer = self._aggregation_buffers[agg_key]
                    if not buffer:
                        continue
                    
                    # 过滤时间窗口内的数据
                    cutoff_time = current_time - timedelta(seconds=config.time_window_seconds)
                    window_data = [
                        item for item in buffer
                        if item['timestamp'] >= cutoff_time
                    ]
                    
                    if not window_data:
                        continue
                    
                    values = [item['value'] for item in window_data]
                    
                    # 计算聚合值
                    aggregated_value = None
                    
                    if config.aggregation_type == 'avg':
                        aggregated_value = statistics.mean(values)
                    elif config.aggregation_type == 'sum':
                        aggregated_value = sum(values)
                    elif config.aggregation_type == 'min':
                        aggregated_value = min(values)
                    elif config.aggregation_type == 'max':
                        aggregated_value = max(values)
                    elif config.aggregation_type == 'count':
                        aggregated_value = len(values)
                    
                    if aggregated_value is not None:
                        # 检查是否达到触发阈值
                        should_publish = True
                        if config.trigger_threshold is not None:
                            should_publish = aggregated_value >= config.trigger_threshold
                        
                        if should_publish:
                            # 发布聚合结果
                            aggregated_data_point = RealtimeDataPoint(
                                placeholder_id=config.placeholder_id,
                                timestamp=current_time,
                                value={
                                    'metric_name': f"{config.metric_name}_{config.aggregation_type}",
                                    'metric_value': aggregated_value,
                                    'aggregation_window_seconds': config.time_window_seconds,
                                    'data_points_count': len(values)
                                },
                                data_type='aggregated_metric',
                                metadata={
                                    'aggregation_type': config.aggregation_type,
                                    'original_metric': config.metric_name
                                },
                                source='data_stream_processor'
                            )
                            
                            await self.realtime_manager.publish_data_point(aggregated_data_point)
                            self._stats['aggregations_computed'] += 1
                
                except Exception as e:
                    logger.error(f"计算聚合失败 {agg_key}: {e}")
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计"""
        async with self._lock:
            return {
                'processed_data_points': self._stats['processed_data_points'],
                'triggered_rules': self._stats['triggered_rules'],
                'aggregations_computed': self._stats['aggregations_computed'],
                'errors': self._stats['errors'],
                'active_rules': len([r for r in self._processing_rules.values() if r.enabled]),
                'total_rules': len(self._processing_rules),
                'active_aggregators': len(self._aggregators)
            }
    
    async def get_processing_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取处理历史"""
        history = list(self._processing_history)
        history.reverse()  # 最新的在前面
        
        # 转换时间戳为字符串
        for item in history[:limit]:
            item['processed_at'] = item['processed_at'].isoformat()
        
        return history[:limit]
    
    async def get_rule_info(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """获取规则信息"""
        async with self._lock:
            if rule_id not in self._processing_rules:
                return None
            
            rule = self._processing_rules[rule_id]
            return {
                'rule_id': rule.rule_id,
                'name': rule.name,
                'description': rule.description,
                'condition': rule.condition,
                'action': rule.action,
                'enabled': rule.enabled,
                'priority': rule.priority
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            stats = await self.get_processing_stats()
            
            health_status = "healthy"
            issues = []
            
            # 检查错误率
            total_processed = stats['processed_data_points']
            error_count = stats['errors']
            
            if total_processed > 0:
                error_rate = error_count / total_processed
                if error_rate > 0.1:  # 错误率超过10%
                    issues.append(f"处理错误率过高: {error_rate:.2%}")
                    health_status = "warning"
            
            # 检查规则状态
            if stats['total_rules'] > 0 and stats['active_rules'] == 0:
                issues.append("没有活跃的处理规则")
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
        """关闭数据流处理器"""
        if hasattr(self, '_aggregation_task'):
            self._aggregation_task.cancel()
        
        logger.info("数据流处理器已关闭")