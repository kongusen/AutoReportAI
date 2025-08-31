"""
权重计算器
核心权重计算逻辑和算法
"""
import logging
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from ..models import PlaceholderSpec, DocumentContext, BusinessContext, TimeContext

logger = logging.getLogger(__name__)

class WeightType(Enum):
    """权重类型"""
    PARAGRAPH = "paragraph"
    SECTION = "section"
    DOCUMENT = "document"
    BUSINESS_RULE = "business_rule"
    TEMPORAL = "temporal"
    SEMANTIC = "semantic"

class AggregationMethod(Enum):
    """权重聚合方法"""
    WEIGHTED_AVERAGE = "weighted_average"
    HARMONIC_MEAN = "harmonic_mean"
    GEOMETRIC_MEAN = "geometric_mean"
    MAX_POOLING = "max_pooling"
    ATTENTION_BASED = "attention_based"

@dataclass
class WeightComponents:
    """权重组件"""
    paragraph_weight: float = 0.0
    section_weight: float = 0.0
    document_weight: float = 0.0
    business_rule_weight: float = 0.0
    temporal_weight: float = 0.0
    semantic_weight: float = 0.0
    confidence_score: float = 0.0

@dataclass
class WeightConfig:
    """权重配置"""
    component_weights: Dict[WeightType, float]
    aggregation_method: AggregationMethod
    normalization_enabled: bool = True
    confidence_threshold: float = 0.5
    decay_factor: float = 0.9
    boost_factor: float = 1.2

class WeightCalculator:
    """权重计算器"""
    
    def __init__(self, config: Optional[WeightConfig] = None):
        self.config = config or self._default_config()
        self.calculation_cache = {}
        self.performance_metrics = {}
        
    def _default_config(self) -> WeightConfig:
        """默认权重配置"""
        return WeightConfig(
            component_weights={
                WeightType.PARAGRAPH: 0.25,
                WeightType.SECTION: 0.20,
                WeightType.DOCUMENT: 0.15,
                WeightType.BUSINESS_RULE: 0.20,
                WeightType.TEMPORAL: 0.10,
                WeightType.SEMANTIC: 0.10
            },
            aggregation_method=AggregationMethod.WEIGHTED_AVERAGE,
            normalization_enabled=True,
            confidence_threshold=0.6,
            decay_factor=0.9,
            boost_factor=1.3
        )
    
    def calculate_comprehensive_weight(self, 
                                     placeholder_spec: PlaceholderSpec,
                                     weight_components: WeightComponents,
                                     context: Optional[Dict[str, Any]] = None) -> Tuple[float, Dict[str, float]]:
        """计算综合权重"""
        try:
            # 创建缓存键
            cache_key = self._generate_cache_key(placeholder_spec, weight_components)
            if cache_key in self.calculation_cache:
                return self.calculation_cache[cache_key]
            
            # 准备权重向量
            weight_vector = self._prepare_weight_vector(weight_components)
            
            # 应用上下文调整
            if context:
                weight_vector = self._apply_context_adjustments(weight_vector, context)
            
            # 计算基础权重
            base_weight = self._calculate_base_weight(weight_vector)
            
            # 应用置信度调整
            confidence_adjusted_weight = self._apply_confidence_adjustment(
                base_weight, weight_components.confidence_score
            )
            
            # 应用归一化
            if self.config.normalization_enabled:
                final_weight = self._normalize_weight(confidence_adjusted_weight)
            else:
                final_weight = confidence_adjusted_weight
            
            # 生成详细分解
            weight_breakdown = self._generate_weight_breakdown(
                weight_vector, base_weight, confidence_adjusted_weight, final_weight
            )
            
            # 缓存结果
            result = (final_weight, weight_breakdown)
            self.calculation_cache[cache_key] = result
            
            # 更新性能指标
            self._update_performance_metrics(placeholder_spec, final_weight)
            
            return result
            
        except Exception as e:
            logger.error(f"权重计算失败: {e}")
            return 0.0, {}
    
    def _prepare_weight_vector(self, components: WeightComponents) -> Dict[str, float]:
        """准备权重向量"""
        return {
            'paragraph': components.paragraph_weight,
            'section': components.section_weight,
            'document': components.document_weight,
            'business_rule': components.business_rule_weight,
            'temporal': components.temporal_weight,
            'semantic': components.semantic_weight
        }
    
    def _apply_context_adjustments(self, 
                                  weight_vector: Dict[str, float],
                                  context: Dict[str, Any]) -> Dict[str, float]:
        """应用上下文调整"""
        adjusted_vector = weight_vector.copy()
        
        # 时间敏感性调整
        if context.get('time_sensitive', False):
            adjusted_vector['temporal'] *= self.config.boost_factor
            
        # 业务关键性调整
        if context.get('business_critical', False):
            adjusted_vector['business_rule'] *= self.config.boost_factor
            
        # 文档复杂度调整
        document_complexity = context.get('document_complexity', 0.5)
        if document_complexity > 0.8:
            adjusted_vector['document'] *= self.config.boost_factor
        elif document_complexity < 0.3:
            adjusted_vector['document'] *= self.config.decay_factor
            
        # 语义相关性调整
        semantic_relevance = context.get('semantic_relevance', 0.5)
        if semantic_relevance > 0.7:
            adjusted_vector['semantic'] *= self.config.boost_factor
            
        return adjusted_vector
    
    def _calculate_base_weight(self, weight_vector: Dict[str, float]) -> float:
        """计算基础权重"""
        method = self.config.aggregation_method
        
        if method == AggregationMethod.WEIGHTED_AVERAGE:
            return self._weighted_average(weight_vector)
        elif method == AggregationMethod.HARMONIC_MEAN:
            return self._harmonic_mean(weight_vector)
        elif method == AggregationMethod.GEOMETRIC_MEAN:
            return self._geometric_mean(weight_vector)
        elif method == AggregationMethod.MAX_POOLING:
            return self._max_pooling(weight_vector)
        elif method == AggregationMethod.ATTENTION_BASED:
            return self._attention_based_aggregation(weight_vector)
        else:
            return self._weighted_average(weight_vector)
    
    def _weighted_average(self, weight_vector: Dict[str, float]) -> float:
        """加权平均"""
        total_weight = 0.0
        total_factor = 0.0
        
        for component, weight in weight_vector.items():
            weight_type = WeightType(component) if component in [wt.value for wt in WeightType] else None
            if weight_type and weight_type in self.config.component_weights:
                factor = self.config.component_weights[weight_type]
                total_weight += weight * factor
                total_factor += factor
        
        return total_weight / total_factor if total_factor > 0 else 0.0
    
    def _harmonic_mean(self, weight_vector: Dict[str, float]) -> float:
        """调和平均"""
        valid_weights = [w for w in weight_vector.values() if w > 0]
        if not valid_weights:
            return 0.0
        
        harmonic_sum = sum(1/w for w in valid_weights)
        return len(valid_weights) / harmonic_sum
    
    def _geometric_mean(self, weight_vector: Dict[str, float]) -> float:
        """几何平均"""
        valid_weights = [w for w in weight_vector.values() if w > 0]
        if not valid_weights:
            return 0.0
        
        product = 1.0
        for weight in valid_weights:
            product *= weight
        
        return product ** (1.0 / len(valid_weights))
    
    def _max_pooling(self, weight_vector: Dict[str, float]) -> float:
        """最大池化"""
        return max(weight_vector.values()) if weight_vector.values() else 0.0
    
    def _attention_based_aggregation(self, weight_vector: Dict[str, float]) -> float:
        """基于注意力机制的聚合"""
        # 计算注意力权重
        attention_scores = {}
        max_weight = max(weight_vector.values()) if weight_vector.values() else 1.0
        
        for component, weight in weight_vector.items():
            # 使用softmax计算注意力分数
            attention_scores[component] = math.exp(weight / max_weight)
        
        # 归一化注意力分数
        total_attention = sum(attention_scores.values())
        if total_attention == 0:
            return 0.0
        
        normalized_attention = {k: v / total_attention 
                              for k, v in attention_scores.items()}
        
        # 计算加权和
        weighted_sum = sum(weight_vector[component] * normalized_attention[component]
                          for component in weight_vector.keys())
        
        return weighted_sum
    
    def _apply_confidence_adjustment(self, base_weight: float, confidence_score: float) -> float:
        """应用置信度调整"""
        if confidence_score < self.config.confidence_threshold:
            # 低置信度惩罚
            penalty_factor = confidence_score / self.config.confidence_threshold
            return base_weight * penalty_factor
        else:
            # 高置信度奖励
            bonus_factor = 1 + (confidence_score - self.config.confidence_threshold) * 0.2
            return base_weight * bonus_factor
    
    def _normalize_weight(self, weight: float) -> float:
        """权重归一化"""
        # 使用sigmoid函数进行归一化
        normalized = 1 / (1 + math.exp(-10 * (weight - 0.5)))
        return max(0.0, min(1.0, normalized))
    
    def _generate_weight_breakdown(self, 
                                  weight_vector: Dict[str, float],
                                  base_weight: float,
                                  confidence_adjusted: float,
                                  final_weight: float) -> Dict[str, float]:
        """生成权重分解详情"""
        return {
            'components': weight_vector,
            'base_weight': base_weight,
            'confidence_adjusted': confidence_adjusted,
            'final_weight': final_weight,
            'aggregation_method': self.config.aggregation_method.value,
            'normalization_applied': self.config.normalization_enabled
        }
    
    def _generate_cache_key(self, 
                           placeholder_spec: PlaceholderSpec,
                           weight_components: WeightComponents) -> str:
        """生成缓存键"""
        spec_hash = hash(placeholder_spec.content)
        components_hash = hash((
            weight_components.paragraph_weight,
            weight_components.section_weight,
            weight_components.document_weight,
            weight_components.business_rule_weight,
            weight_components.temporal_weight,
            weight_components.semantic_weight,
            weight_components.confidence_score
        ))
        return f"{spec_hash}_{components_hash}"
    
    def _update_performance_metrics(self, 
                                   placeholder_spec: PlaceholderSpec,
                                   final_weight: float):
        """更新性能指标"""
        spec_type = getattr(placeholder_spec, 'statistical_type', 'unknown')
        
        if spec_type not in self.performance_metrics:
            self.performance_metrics[spec_type] = {
                'count': 0,
                'total_weight': 0.0,
                'avg_weight': 0.0,
                'min_weight': float('inf'),
                'max_weight': 0.0
            }
        
        metrics = self.performance_metrics[spec_type]
        metrics['count'] += 1
        metrics['total_weight'] += final_weight
        metrics['avg_weight'] = metrics['total_weight'] / metrics['count']
        metrics['min_weight'] = min(metrics['min_weight'], final_weight)
        metrics['max_weight'] = max(metrics['max_weight'], final_weight)
    
    def calculate_batch_weights(self, 
                               placeholder_specs: List[PlaceholderSpec],
                               weight_components_list: List[WeightComponents],
                               context: Optional[Dict[str, Any]] = None) -> List[Tuple[float, Dict[str, float]]]:
        """批量计算权重"""
        results = []
        
        for spec, components in zip(placeholder_specs, weight_components_list):
            try:
                result = self.calculate_comprehensive_weight(spec, components, context)
                results.append(result)
            except Exception as e:
                logger.error(f"批量权重计算失败 - 占位符: {spec.content}, 错误: {e}")
                results.append((0.0, {}))
        
        return results
    
    def calculate_relative_weights(self, 
                                  placeholder_specs: List[PlaceholderSpec],
                                  weight_components_list: List[WeightComponents],
                                  context: Optional[Dict[str, Any]] = None) -> List[float]:
        """计算相对权重（归一化后的权重分布）"""
        # 计算绝对权重
        absolute_weights = []
        for spec, components in zip(placeholder_specs, weight_components_list):
            weight, _ = self.calculate_comprehensive_weight(spec, components, context)
            absolute_weights.append(weight)
        
        # 计算相对权重
        total_weight = sum(absolute_weights)
        if total_weight == 0:
            # 均匀分布
            return [1.0 / len(placeholder_specs)] * len(placeholder_specs)
        
        return [w / total_weight for w in absolute_weights]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            'cache_size': len(self.calculation_cache),
            'performance_metrics': self.performance_metrics,
            'config': {
                'component_weights': {wt.value: weight for wt, weight in self.config.component_weights.items()},
                'aggregation_method': self.config.aggregation_method.value,
                'normalization_enabled': self.config.normalization_enabled,
                'confidence_threshold': self.config.confidence_threshold
            }
        }
    
    def clear_cache(self):
        """清空缓存"""
        self.calculation_cache.clear()
        logger.info("权重计算缓存已清空")
    
    def update_config(self, new_config: WeightConfig):
        """更新配置"""
        self.config = new_config
        self.clear_cache()  # 配置更新后清空缓存
        logger.info("权重计算配置已更新")
    
    def analyze_weight_distribution(self, 
                                   weights: List[float]) -> Dict[str, float]:
        """分析权重分布"""
        if not weights:
            return {}
        
        weights_array = sorted(weights)
        n = len(weights_array)
        
        return {
            'mean': sum(weights) / n,
            'median': weights_array[n // 2] if n % 2 == 1 else (weights_array[n // 2 - 1] + weights_array[n // 2]) / 2,
            'std_dev': (sum((w - sum(weights) / n) ** 2 for w in weights) / n) ** 0.5,
            'min': min(weights),
            'max': max(weights),
            'range': max(weights) - min(weights),
            'q1': weights_array[n // 4],
            'q3': weights_array[3 * n // 4],
            'skewness': self._calculate_skewness(weights),
            'kurtosis': self._calculate_kurtosis(weights)
        }
    
    def _calculate_skewness(self, weights: List[float]) -> float:
        """计算偏度"""
        if len(weights) < 3:
            return 0.0
        
        mean = sum(weights) / len(weights)
        variance = sum((w - mean) ** 2 for w in weights) / len(weights)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0.0
        
        skewness = sum(((w - mean) / std_dev) ** 3 for w in weights) / len(weights)
        return skewness
    
    def _calculate_kurtosis(self, weights: List[float]) -> float:
        """计算峰度"""
        if len(weights) < 4:
            return 0.0
        
        mean = sum(weights) / len(weights)
        variance = sum((w - mean) ** 2 for w in weights) / len(weights)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0.0
        
        kurtosis = sum(((w - mean) / std_dev) ** 4 for w in weights) / len(weights) - 3
        return kurtosis