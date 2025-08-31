"""
动态权重调整器
基于实时反馈和上下文变化动态调整权重
"""
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import math

from .weight_calculator import WeightComponents, WeightConfig
from ..models import PlaceholderSpec

logger = logging.getLogger(__name__)

class AdjustmentTrigger(Enum):
    """调整触发器类型"""
    TIME_BASED = "time_based"
    PERFORMANCE_BASED = "performance_based"
    CONTEXT_CHANGE = "context_change"
    USER_FEEDBACK = "user_feedback"
    ERROR_THRESHOLD = "error_threshold"
    BATCH_COMPLETION = "batch_completion"

class AdjustmentStrategy(Enum):
    """调整策略"""
    GRADUAL = "gradual"
    IMMEDIATE = "immediate"
    EXPONENTIAL_DECAY = "exponential_decay"
    ADAPTIVE_LEARNING = "adaptive_learning"
    REINFORCEMENT = "reinforcement"

@dataclass
class AdjustmentEvent:
    """调整事件"""
    timestamp: float
    trigger: AdjustmentTrigger
    old_weights: WeightComponents
    new_weights: WeightComponents
    context: Dict[str, Any]
    performance_impact: Optional[float] = None
    success_rate: Optional[float] = None

@dataclass
class FeedbackSignal:
    """反馈信号"""
    placeholder_id: str
    expected_weight: float
    actual_weight: float
    user_satisfaction: float  # 0-1
    processing_time: float
    accuracy_score: float  # 0-1
    timestamp: float = field(default_factory=time.time)

@dataclass
class PerformanceMetrics:
    """性能指标"""
    avg_processing_time: float = 0.0
    accuracy_rate: float = 0.0
    success_rate: float = 0.0
    user_satisfaction: float = 0.0
    error_count: int = 0
    total_requests: int = 0
    
class DynamicWeightAdjuster:
    """动态权重调整器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.adjustment_history: deque = deque(maxlen=self.config.get('history_size', 1000))
        self.feedback_buffer: deque = deque(maxlen=self.config.get('feedback_buffer_size', 500))
        self.performance_metrics = PerformanceMetrics()
        self.current_weights = self._initialize_weights()
        self.adjustment_callbacks: List[Callable] = []
        self.last_adjustment_time = time.time()
        
    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            'adjustment_interval': 300,  # 5分钟
            'min_feedback_samples': 10,
            'learning_rate': 0.1,
            'momentum': 0.9,
            'decay_rate': 0.95,
            'performance_threshold': 0.8,
            'error_threshold': 0.1,
            'max_adjustment_magnitude': 0.2,
            'stability_factor': 0.85,
            'adaptation_speed': 'medium',
            'history_size': 1000,
            'feedback_buffer_size': 500
        }
    
    def _initialize_weights(self) -> WeightComponents:
        """初始化权重"""
        return WeightComponents(
            paragraph_weight=0.5,
            section_weight=0.5,
            document_weight=0.5,
            business_rule_weight=0.5,
            temporal_weight=0.5,
            semantic_weight=0.5,
            confidence_score=0.7
        )
    
    def register_feedback(self, feedback: FeedbackSignal):
        """注册反馈信号"""
        self.feedback_buffer.append(feedback)
        self._update_performance_metrics(feedback)
        
        # 检查是否需要触发调整
        if self._should_trigger_adjustment(AdjustmentTrigger.USER_FEEDBACK):
            self._trigger_adjustment(AdjustmentTrigger.USER_FEEDBACK, {'feedback': feedback})
    
    def register_context_change(self, context_change: Dict[str, Any]):
        """注册上下文变化"""
        if self._is_significant_context_change(context_change):
            self._trigger_adjustment(AdjustmentTrigger.CONTEXT_CHANGE, context_change)
    
    def register_performance_data(self, 
                                 processing_time: float,
                                 accuracy_score: float,
                                 success: bool):
        """注册性能数据"""
        self.performance_metrics.total_requests += 1
        self.performance_metrics.avg_processing_time = (
            (self.performance_metrics.avg_processing_time * (self.performance_metrics.total_requests - 1) + processing_time) /
            self.performance_metrics.total_requests
        )
        
        self.performance_metrics.accuracy_rate = (
            (self.performance_metrics.accuracy_rate * (self.performance_metrics.total_requests - 1) + accuracy_score) /
            self.performance_metrics.total_requests
        )
        
        if success:
            self.performance_metrics.success_rate = (
                (self.performance_metrics.success_rate * (self.performance_metrics.total_requests - 1) + 1.0) /
                self.performance_metrics.total_requests
            )
        else:
            self.performance_metrics.error_count += 1
        
        # 检查性能阈值
        if self._should_trigger_adjustment(AdjustmentTrigger.PERFORMANCE_BASED):
            self._trigger_adjustment(AdjustmentTrigger.PERFORMANCE_BASED, {
                'processing_time': processing_time,
                'accuracy_score': accuracy_score,
                'success': success
            })
    
    def adjust_weights(self, 
                      current_weights: WeightComponents,
                      adjustment_context: Dict[str, Any]) -> WeightComponents:
        """调整权重"""
        try:
            # 分析反馈信号
            feedback_analysis = self._analyze_feedback_signals()
            
            # 计算调整方向和幅度
            adjustments = self._calculate_adjustments(
                current_weights, feedback_analysis, adjustment_context
            )
            
            # 应用调整
            new_weights = self._apply_adjustments(current_weights, adjustments)
            
            # 验证调整合理性
            validated_weights = self._validate_adjustments(current_weights, new_weights)
            
            # 记录调整事件
            self._record_adjustment_event(
                current_weights, validated_weights, adjustment_context
            )
            
            # 更新当前权重
            self.current_weights = validated_weights
            self.last_adjustment_time = time.time()
            
            # 触发回调
            self._notify_adjustment_callbacks(validated_weights, adjustment_context)
            
            return validated_weights
            
        except Exception as e:
            logger.error(f"权重调整失败: {e}")
            return current_weights
    
    def _should_trigger_adjustment(self, trigger: AdjustmentTrigger) -> bool:
        """判断是否应该触发调整"""
        current_time = time.time()
        
        if trigger == AdjustmentTrigger.TIME_BASED:
            return (current_time - self.last_adjustment_time) > self.config['adjustment_interval']
        
        elif trigger == AdjustmentTrigger.USER_FEEDBACK:
            return len(self.feedback_buffer) >= self.config['min_feedback_samples']
        
        elif trigger == AdjustmentTrigger.PERFORMANCE_BASED:
            return (self.performance_metrics.accuracy_rate < self.config['performance_threshold'] or
                   self.performance_metrics.success_rate < self.config['performance_threshold'])
        
        elif trigger == AdjustmentTrigger.ERROR_THRESHOLD:
            if self.performance_metrics.total_requests > 0:
                error_rate = self.performance_metrics.error_count / self.performance_metrics.total_requests
                return error_rate > self.config['error_threshold']
        
        return False
    
    def _trigger_adjustment(self, trigger: AdjustmentTrigger, context: Dict[str, Any]):
        """触发权重调整"""
        try:
            adjustment_context = {
                'trigger': trigger,
                'timestamp': time.time(),
                **context
            }
            
            new_weights = self.adjust_weights(self.current_weights, adjustment_context)
            
            logger.info(f"权重调整完成 - 触发器: {trigger.value}, 新权重: {new_weights}")
            
        except Exception as e:
            logger.error(f"权重调整触发失败 - 触发器: {trigger.value}, 错误: {e}")
    
    def _analyze_feedback_signals(self) -> Dict[str, Any]:
        """分析反馈信号"""
        if not self.feedback_buffer:
            return {'type': 'no_feedback', 'confidence': 0.0}
        
        recent_feedback = list(self.feedback_buffer)
        
        # 计算平均满意度
        avg_satisfaction = sum(f.user_satisfaction for f in recent_feedback) / len(recent_feedback)
        
        # 计算权重误差
        weight_errors = []
        for feedback in recent_feedback:
            error = abs(feedback.expected_weight - feedback.actual_weight)
            weight_errors.append(error)
        
        avg_weight_error = sum(weight_errors) / len(weight_errors) if weight_errors else 0.0
        
        # 分析趋势
        satisfaction_trend = self._calculate_trend([f.user_satisfaction for f in recent_feedback])
        accuracy_trend = self._calculate_trend([f.accuracy_score for f in recent_feedback])
        
        return {
            'type': 'feedback_analysis',
            'avg_satisfaction': avg_satisfaction,
            'avg_weight_error': avg_weight_error,
            'satisfaction_trend': satisfaction_trend,
            'accuracy_trend': accuracy_trend,
            'sample_count': len(recent_feedback),
            'confidence': min(1.0, len(recent_feedback) / self.config['min_feedback_samples'])
        }
    
    def _calculate_adjustments(self, 
                              current_weights: WeightComponents,
                              feedback_analysis: Dict[str, Any],
                              context: Dict[str, Any]) -> Dict[str, float]:
        """计算权重调整"""
        adjustments = {
            'paragraph_weight': 0.0,
            'section_weight': 0.0,
            'document_weight': 0.0,
            'business_rule_weight': 0.0,
            'temporal_weight': 0.0,
            'semantic_weight': 0.0,
            'confidence_score': 0.0
        }
        
        learning_rate = self.config['learning_rate']
        
        if feedback_analysis['type'] == 'feedback_analysis':
            # 基于用户满意度调整
            satisfaction_factor = (feedback_analysis['avg_satisfaction'] - 0.5) * 2  # 归一化到[-1, 1]
            
            # 基于权重误差调整
            error_factor = -feedback_analysis['avg_weight_error']  # 误差越大，调整越大
            
            # 基于趋势调整
            trend_factor = (feedback_analysis['satisfaction_trend'] + feedback_analysis['accuracy_trend']) / 2
            
            # 计算总调整因子
            adjustment_factor = (satisfaction_factor + error_factor + trend_factor) / 3
            adjustment_magnitude = learning_rate * adjustment_factor
            
            # 根据上下文分配调整
            if context.get('trigger') == AdjustmentTrigger.USER_FEEDBACK:
                # 用户反馈主要影响语义权重
                adjustments['semantic_weight'] = adjustment_magnitude * 0.4
                adjustments['paragraph_weight'] = adjustment_magnitude * 0.3
                adjustments['section_weight'] = adjustment_magnitude * 0.2
                adjustments['confidence_score'] = adjustment_magnitude * 0.1
                
            elif context.get('trigger') == AdjustmentTrigger.PERFORMANCE_BASED:
                # 性能问题主要影响计算相关权重
                adjustments['business_rule_weight'] = adjustment_magnitude * 0.4
                adjustments['document_weight'] = adjustment_magnitude * 0.3
                adjustments['temporal_weight'] = adjustment_magnitude * 0.2
                adjustments['confidence_score'] = adjustment_magnitude * 0.1
        
        # 应用衰减和动量
        decay_rate = self.config['decay_rate']
        for key in adjustments:
            adjustments[key] *= decay_rate
        
        return adjustments
    
    def _apply_adjustments(self, 
                          current_weights: WeightComponents,
                          adjustments: Dict[str, float]) -> WeightComponents:
        """应用权重调整"""
        new_weights = WeightComponents(
            paragraph_weight=max(0.0, min(1.0, current_weights.paragraph_weight + adjustments['paragraph_weight'])),
            section_weight=max(0.0, min(1.0, current_weights.section_weight + adjustments['section_weight'])),
            document_weight=max(0.0, min(1.0, current_weights.document_weight + adjustments['document_weight'])),
            business_rule_weight=max(0.0, min(1.0, current_weights.business_rule_weight + adjustments['business_rule_weight'])),
            temporal_weight=max(0.0, min(1.0, current_weights.temporal_weight + adjustments['temporal_weight'])),
            semantic_weight=max(0.0, min(1.0, current_weights.semantic_weight + adjustments['semantic_weight'])),
            confidence_score=max(0.0, min(1.0, current_weights.confidence_score + adjustments['confidence_score']))
        )
        
        return new_weights
    
    def _validate_adjustments(self, 
                             old_weights: WeightComponents,
                             new_weights: WeightComponents) -> WeightComponents:
        """验证权重调整的合理性"""
        max_change = self.config['max_adjustment_magnitude']
        stability_factor = self.config['stability_factor']
        
        # 检查变化幅度
        changes = {
            'paragraph_weight': abs(new_weights.paragraph_weight - old_weights.paragraph_weight),
            'section_weight': abs(new_weights.section_weight - old_weights.section_weight),
            'document_weight': abs(new_weights.document_weight - old_weights.document_weight),
            'business_rule_weight': abs(new_weights.business_rule_weight - old_weights.business_rule_weight),
            'temporal_weight': abs(new_weights.temporal_weight - old_weights.temporal_weight),
            'semantic_weight': abs(new_weights.semantic_weight - old_weights.semantic_weight),
            'confidence_score': abs(new_weights.confidence_score - old_weights.confidence_score)
        }
        
        # 限制最大变化幅度
        validated_weights = WeightComponents()
        
        for attr_name in changes.keys():
            old_value = getattr(old_weights, attr_name)
            new_value = getattr(new_weights, attr_name)
            change = new_value - old_value
            
            if abs(change) > max_change:
                # 限制变化幅度
                limited_change = max_change * (1 if change > 0 else -1)
                validated_value = old_value + limited_change
            else:
                # 应用稳定性因子
                validated_value = old_value + change * stability_factor
            
            # 确保在合理范围内
            validated_value = max(0.0, min(1.0, validated_value))
            setattr(validated_weights, attr_name, validated_value)
        
        return validated_weights
    
    def _record_adjustment_event(self, 
                                old_weights: WeightComponents,
                                new_weights: WeightComponents,
                                context: Dict[str, Any]):
        """记录调整事件"""
        event = AdjustmentEvent(
            timestamp=time.time(),
            trigger=context.get('trigger', AdjustmentTrigger.TIME_BASED),
            old_weights=old_weights,
            new_weights=new_weights,
            context=context
        )
        
        self.adjustment_history.append(event)
    
    def _update_performance_metrics(self, feedback: FeedbackSignal):
        """更新性能指标"""
        # 更新用户满意度
        if self.performance_metrics.total_requests == 0:
            self.performance_metrics.user_satisfaction = feedback.user_satisfaction
        else:
            self.performance_metrics.user_satisfaction = (
                (self.performance_metrics.user_satisfaction * self.performance_metrics.total_requests + 
                 feedback.user_satisfaction) / (self.performance_metrics.total_requests + 1)
            )
    
    def _calculate_trend(self, values: List[float]) -> float:
        """计算趋势（简单线性回归斜率）"""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x_mean = (n - 1) / 2  # 时间索引的平均值
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        return slope
    
    def _is_significant_context_change(self, context_change: Dict[str, Any]) -> bool:
        """判断上下文变化是否显著"""
        # 这里可以定义更复杂的逻辑来判断上下文变化的显著性
        significant_keys = ['document_type', 'business_domain', 'time_sensitivity', 'user_role']
        
        for key in significant_keys:
            if key in context_change:
                return True
        
        return False
    
    def add_adjustment_callback(self, callback: Callable[[WeightComponents, Dict[str, Any]], None]):
        """添加调整回调函数"""
        self.adjustment_callbacks.append(callback)
    
    def _notify_adjustment_callbacks(self, new_weights: WeightComponents, context: Dict[str, Any]):
        """通知调整回调"""
        for callback in self.adjustment_callbacks:
            try:
                callback(new_weights, context)
            except Exception as e:
                logger.error(f"调整回调执行失败: {e}")
    
    def get_adjustment_history(self, limit: Optional[int] = None) -> List[AdjustmentEvent]:
        """获取调整历史"""
        if limit is None:
            return list(self.adjustment_history)
        else:
            return list(self.adjustment_history)[-limit:]
    
    def get_current_weights(self) -> WeightComponents:
        """获取当前权重"""
        return self.current_weights
    
    def reset_weights(self):
        """重置权重到初始状态"""
        self.current_weights = self._initialize_weights()
        self.adjustment_history.clear()
        self.feedback_buffer.clear()
        self.performance_metrics = PerformanceMetrics()
        logger.info("权重已重置到初始状态")
    
    def export_learning_data(self) -> Dict[str, Any]:
        """导出学习数据"""
        return {
            'adjustment_history': [
                {
                    'timestamp': event.timestamp,
                    'trigger': event.trigger.value,
                    'old_weights': event.old_weights.__dict__,
                    'new_weights': event.new_weights.__dict__,
                    'context': event.context
                }
                for event in self.adjustment_history
            ],
            'feedback_data': [
                {
                    'placeholder_id': fb.placeholder_id,
                    'expected_weight': fb.expected_weight,
                    'actual_weight': fb.actual_weight,
                    'user_satisfaction': fb.user_satisfaction,
                    'processing_time': fb.processing_time,
                    'accuracy_score': fb.accuracy_score,
                    'timestamp': fb.timestamp
                }
                for fb in self.feedback_buffer
            ],
            'performance_metrics': self.performance_metrics.__dict__,
            'current_weights': self.current_weights.__dict__
        }