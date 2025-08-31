"""
权重聚合器
将多个层次的权重进行智能聚合和优化
"""
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import math

from .weight_calculator import WeightComponents, WeightType
from ..models import PlaceholderSpec

logger = logging.getLogger(__name__)

class AggregationStrategy(Enum):
    """聚合策略"""
    HIERARCHICAL = "hierarchical"
    ENSEMBLE = "ensemble"
    ADAPTIVE = "adaptive"
    CONSENSUS = "consensus"
    COMPETITIVE = "competitive"

class NormalizationMethod(Enum):
    """归一化方法"""
    MIN_MAX = "min_max"
    Z_SCORE = "z_score"
    SOFTMAX = "softmax"
    SIGMOID = "sigmoid"
    RANK_BASED = "rank_based"

@dataclass
class AggregationConfig:
    """聚合配置"""
    strategy: AggregationStrategy = AggregationStrategy.HIERARCHICAL
    normalization: NormalizationMethod = NormalizationMethod.SOFTMAX
    layer_weights: Dict[str, float] = None
    confidence_threshold: float = 0.6
    diversity_factor: float = 0.3
    stability_weight: float = 0.2
    performance_weight: float = 0.5
    recency_weight: float = 0.3

@dataclass
class LayerResult:
    """层级结果"""
    layer_name: str
    weight_value: float
    confidence: float
    processing_time: float
    metadata: Dict[str, Any]

@dataclass
class AggregatedResult:
    """聚合结果"""
    final_weight: float
    confidence_score: float
    layer_contributions: Dict[str, float]
    aggregation_metadata: Dict[str, Any]
    quality_metrics: Dict[str, float]

class WeightAggregator:
    """权重聚合器"""
    
    def __init__(self, config: Optional[AggregationConfig] = None):
        self.config = config or AggregationConfig()
        if self.config.layer_weights is None:
            self.config.layer_weights = self._default_layer_weights()
        
        self.aggregation_history: List[Dict[str, Any]] = []
        self.performance_tracker: Dict[str, List[float]] = {}
        self.layer_reliability: Dict[str, float] = {}
        
    def _default_layer_weights(self) -> Dict[str, float]:
        """默认层级权重"""
        return {
            'paragraph': 0.25,
            'section': 0.20,
            'document': 0.15,
            'business_rule': 0.20,
            'temporal': 0.10,
            'semantic': 0.10
        }
    
    def aggregate_weights(self, 
                         layer_results: List[LayerResult],
                         placeholder_spec: PlaceholderSpec,
                         context: Optional[Dict[str, Any]] = None) -> AggregatedResult:
        """聚合多层权重"""
        try:
            # 预处理层级结果
            processed_results = self._preprocess_layer_results(layer_results)
            
            # 根据策略聚合权重
            if self.config.strategy == AggregationStrategy.HIERARCHICAL:
                aggregated_weight = self._hierarchical_aggregation(processed_results, context)
            elif self.config.strategy == AggregationStrategy.ENSEMBLE:
                aggregated_weight = self._ensemble_aggregation(processed_results, context)
            elif self.config.strategy == AggregationStrategy.ADAPTIVE:
                aggregated_weight = self._adaptive_aggregation(processed_results, context)
            elif self.config.strategy == AggregationStrategy.CONSENSUS:
                aggregated_weight = self._consensus_aggregation(processed_results, context)
            elif self.config.strategy == AggregationStrategy.COMPETITIVE:
                aggregated_weight = self._competitive_aggregation(processed_results, context)
            else:
                aggregated_weight = self._hierarchical_aggregation(processed_results, context)
            
            # 计算置信度
            confidence_score = self._calculate_confidence_score(processed_results, aggregated_weight)
            
            # 计算层级贡献度
            layer_contributions = self._calculate_layer_contributions(processed_results, aggregated_weight)
            
            # 生成质量指标
            quality_metrics = self._calculate_quality_metrics(processed_results, aggregated_weight)
            
            # 创建聚合结果
            result = AggregatedResult(
                final_weight=aggregated_weight,
                confidence_score=confidence_score,
                layer_contributions=layer_contributions,
                aggregation_metadata={
                    'strategy': self.config.strategy.value,
                    'normalization': self.config.normalization.value,
                    'layer_count': len(processed_results),
                    'processing_timestamp': self._get_timestamp()
                },
                quality_metrics=quality_metrics
            )
            
            # 记录聚合历史
            self._record_aggregation_history(layer_results, result, context)
            
            # 更新层级可靠性
            self._update_layer_reliability(processed_results, result)
            
            return result
            
        except Exception as e:
            logger.error(f"权重聚合失败: {e}")
            return self._create_fallback_result(layer_results)
    
    def _preprocess_layer_results(self, layer_results: List[LayerResult]) -> List[LayerResult]:
        """预处理层级结果"""
        if not layer_results:
            return []
        
        # 过滤无效结果
        valid_results = [r for r in layer_results if r.weight_value >= 0 and r.confidence > 0]
        
        # 归一化权重值
        if self.config.normalization != NormalizationMethod.RANK_BASED:
            valid_results = self._normalize_weights(valid_results)
        
        # 根据置信度过滤
        filtered_results = [r for r in valid_results if r.confidence >= self.config.confidence_threshold]
        
        return filtered_results if filtered_results else valid_results
    
    def _normalize_weights(self, layer_results: List[LayerResult]) -> List[LayerResult]:
        """归一化权重"""
        if not layer_results:
            return layer_results
        
        weights = [r.weight_value for r in layer_results]
        
        if self.config.normalization == NormalizationMethod.MIN_MAX:
            normalized_weights = self._min_max_normalize(weights)
        elif self.config.normalization == NormalizationMethod.Z_SCORE:
            normalized_weights = self._z_score_normalize(weights)
        elif self.config.normalization == NormalizationMethod.SOFTMAX:
            normalized_weights = self._softmax_normalize(weights)
        elif self.config.normalization == NormalizationMethod.SIGMOID:
            normalized_weights = self._sigmoid_normalize(weights)
        else:
            normalized_weights = weights
        
        # 更新权重值
        for i, result in enumerate(layer_results):
            result.weight_value = normalized_weights[i]
        
        return layer_results
    
    def _hierarchical_aggregation(self, 
                                 layer_results: List[LayerResult],
                                 context: Optional[Dict[str, Any]] = None) -> float:
        """分层聚合"""
        if not layer_results:
            return 0.0
        
        total_weight = 0.0
        total_factor = 0.0
        
        for result in layer_results:
            layer_factor = self.config.layer_weights.get(result.layer_name, 0.1)
            
            # 应用置信度权重
            confidence_weight = result.confidence
            
            # 应用可靠性权重
            reliability_weight = self.layer_reliability.get(result.layer_name, 1.0)
            
            # 综合因子
            combined_factor = layer_factor * confidence_weight * reliability_weight
            
            total_weight += result.weight_value * combined_factor
            total_factor += combined_factor
        
        return total_weight / total_factor if total_factor > 0 else 0.0
    
    def _ensemble_aggregation(self, 
                             layer_results: List[LayerResult],
                             context: Optional[Dict[str, Any]] = None) -> float:
        """集成聚合"""
        if not layer_results:
            return 0.0
        
        # 计算多种聚合方法的结果
        methods_results = []
        
        # 加权平均
        weighted_avg = self._weighted_average(layer_results)
        methods_results.append(weighted_avg)
        
        # 几何平均
        geometric_mean = self._geometric_mean([r.weight_value for r in layer_results])
        methods_results.append(geometric_mean)
        
        # 调和平均
        harmonic_mean = self._harmonic_mean([r.weight_value for r in layer_results if r.weight_value > 0])
        methods_results.append(harmonic_mean)
        
        # 中位数
        median_value = self._calculate_median([r.weight_value for r in layer_results])
        methods_results.append(median_value)
        
        # 集成多种方法的结果
        ensemble_weights = [0.4, 0.3, 0.2, 0.1]  # 加权平均权重最高
        final_result = sum(w * r for w, r in zip(ensemble_weights, methods_results))
        
        return final_result
    
    def _adaptive_aggregation(self, 
                             layer_results: List[LayerResult],
                             context: Optional[Dict[str, Any]] = None) -> float:
        """自适应聚合"""
        if not layer_results:
            return 0.0
        
        # 分析层级结果的分布特征
        weights = [r.weight_value for r in layer_results]
        confidences = [r.confidence for r in layer_results]
        
        # 计算分布特征
        weight_variance = np.var(weights) if len(weights) > 1 else 0
        avg_confidence = np.mean(confidences)
        
        # 根据分布特征选择聚合策略
        if weight_variance < 0.1 and avg_confidence > 0.8:
            # 低方差、高置信度 -> 简单平均
            return np.mean(weights)
        elif weight_variance > 0.3:
            # 高方差 -> 使用中位数减少异常值影响
            return self._calculate_median(weights)
        else:
            # 中等情况 -> 置信度加权平均
            total_weight = sum(w * c for w, c in zip(weights, confidences))
            total_confidence = sum(confidences)
            return total_weight / total_confidence if total_confidence > 0 else 0.0
    
    def _consensus_aggregation(self, 
                              layer_results: List[LayerResult],
                              context: Optional[Dict[str, Any]] = None) -> float:
        """共识聚合"""
        if not layer_results:
            return 0.0
        
        weights = [r.weight_value for r in layer_results]
        confidences = [r.confidence for r in layer_results]
        
        # 计算每个权重的共识度
        consensus_scores = []
        for i, weight in enumerate(weights):
            # 计算与其他权重的相似度
            similarities = []
            for j, other_weight in enumerate(weights):
                if i != j:
                    similarity = 1 - abs(weight - other_weight)
                    similarities.append(similarity)
            
            consensus_score = np.mean(similarities) if similarities else 0.0
            consensus_scores.append(consensus_score)
        
        # 基于共识度和置信度加权
        total_weight = 0.0
        total_factor = 0.0
        
        for weight, confidence, consensus in zip(weights, confidences, consensus_scores):
            factor = confidence * consensus
            total_weight += weight * factor
            total_factor += factor
        
        return total_weight / total_factor if total_factor > 0 else np.mean(weights)
    
    def _competitive_aggregation(self, 
                                layer_results: List[LayerResult],
                                context: Optional[Dict[str, Any]] = None) -> float:
        """竞争聚合"""
        if not layer_results:
            return 0.0
        
        # 计算每个层级的竞争力分数
        competitiveness_scores = []
        
        for result in layer_results:
            # 基于置信度、可靠性和性能历史计算竞争力
            reliability = self.layer_reliability.get(result.layer_name, 1.0)
            
            # 获取历史性能
            historical_performance = self.performance_tracker.get(result.layer_name, [1.0])
            avg_performance = np.mean(historical_performance[-10:])  # 最近10次性能
            
            competitiveness = (result.confidence * 0.4 + 
                             reliability * 0.3 + 
                             avg_performance * 0.3)
            competitiveness_scores.append(competitiveness)
        
        # 找到最具竞争力的层级
        max_competitiveness = max(competitiveness_scores)
        winner_index = competitiveness_scores.index(max_competitiveness)
        
        # 使用获胜者的权重，但考虑其他层级的影响
        winner_weight = layer_results[winner_index].weight_value
        
        # 计算其他层级的影响
        other_influences = []
        for i, result in enumerate(layer_results):
            if i != winner_index:
                influence = result.weight_value * competitiveness_scores[i] * 0.1
                other_influences.append(influence)
        
        total_influence = sum(other_influences)
        final_weight = winner_weight * 0.8 + total_influence * 0.2
        
        return final_weight
    
    def _calculate_confidence_score(self, 
                                   layer_results: List[LayerResult],
                                   aggregated_weight: float) -> float:
        """计算置信度分数"""
        if not layer_results:
            return 0.0
        
        # 基于层级置信度的平均值
        avg_confidence = np.mean([r.confidence for r in layer_results])
        
        # 基于权重分布的一致性
        weights = [r.weight_value for r in layer_results]
        weight_std = np.std(weights) if len(weights) > 1 else 0
        consistency_score = max(0, 1 - weight_std * 2)  # 标准差越小，一致性越高
        
        # 基于层级数量
        coverage_score = min(1.0, len(layer_results) / 6)  # 假设6个层级为完整覆盖
        
        # 综合置信度
        final_confidence = (avg_confidence * 0.5 + 
                          consistency_score * 0.3 + 
                          coverage_score * 0.2)
        
        return max(0.0, min(1.0, final_confidence))
    
    def _calculate_layer_contributions(self, 
                                     layer_results: List[LayerResult],
                                     aggregated_weight: float) -> Dict[str, float]:
        """计算层级贡献度"""
        contributions = {}
        
        if not layer_results or aggregated_weight == 0:
            return contributions
        
        for result in layer_results:
            layer_weight = self.config.layer_weights.get(result.layer_name, 0.1)
            confidence_weight = result.confidence
            
            # 计算该层级对最终结果的贡献
            contribution = (result.weight_value * layer_weight * confidence_weight) / aggregated_weight
            contributions[result.layer_name] = min(1.0, max(0.0, contribution))
        
        # 归一化贡献度
        total_contribution = sum(contributions.values())
        if total_contribution > 0:
            contributions = {k: v / total_contribution for k, v in contributions.items()}
        
        return contributions
    
    def _calculate_quality_metrics(self, 
                                  layer_results: List[LayerResult],
                                  aggregated_weight: float) -> Dict[str, float]:
        """计算质量指标"""
        if not layer_results:
            return {}
        
        weights = [r.weight_value for r in layer_results]
        confidences = [r.confidence for r in layer_results]
        
        return {
            'weight_variance': float(np.var(weights)),
            'weight_std': float(np.std(weights)),
            'avg_confidence': float(np.mean(confidences)),
            'min_confidence': float(np.min(confidences)),
            'max_confidence': float(np.max(confidences)),
            'coverage': len(layer_results) / 6,  # 假设6个层级为完整覆盖
            'diversity': self._calculate_diversity(weights),
            'stability': self._calculate_stability(layer_results)
        }
    
    def _calculate_diversity(self, weights: List[float]) -> float:
        """计算多样性指标"""
        if len(weights) < 2:
            return 0.0
        
        # 使用香农熵计算多样性
        # 先将权重转换为概率分布
        total = sum(weights)
        if total == 0:
            return 0.0
        
        probs = [w / total for w in weights]
        entropy = -sum(p * math.log2(p) for p in probs if p > 0)
        
        # 归一化到[0, 1]
        max_entropy = math.log2(len(weights))
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    def _calculate_stability(self, layer_results: List[LayerResult]) -> float:
        """计算稳定性指标"""
        # 基于处理时间的一致性计算稳定性
        processing_times = [r.processing_time for r in layer_results if r.processing_time > 0]
        
        if len(processing_times) < 2:
            return 1.0
        
        time_cv = np.std(processing_times) / np.mean(processing_times)  # 变异系数
        stability = max(0, 1 - time_cv)  # 变异系数越小，稳定性越高
        
        return stability
    
    # 辅助方法
    def _min_max_normalize(self, weights: List[float]) -> List[float]:
        """最小-最大归一化"""
        if not weights:
            return weights
        
        min_w, max_w = min(weights), max(weights)
        if min_w == max_w:
            return [0.5] * len(weights)
        
        return [(w - min_w) / (max_w - min_w) for w in weights]
    
    def _z_score_normalize(self, weights: List[float]) -> List[float]:
        """Z分数归一化"""
        if len(weights) < 2:
            return weights
        
        mean_w = np.mean(weights)
        std_w = np.std(weights)
        
        if std_w == 0:
            return [0.5] * len(weights)
        
        z_scores = [(w - mean_w) / std_w for w in weights]
        # 转换到[0, 1]区间
        return [(1 / (1 + math.exp(-z))) for z in z_scores]
    
    def _softmax_normalize(self, weights: List[float]) -> List[float]:
        """Softmax归一化"""
        if not weights:
            return weights
        
        max_w = max(weights)
        exp_weights = [math.exp(w - max_w) for w in weights]  # 数值稳定性
        sum_exp = sum(exp_weights)
        
        return [exp_w / sum_exp for exp_w in exp_weights]
    
    def _sigmoid_normalize(self, weights: List[float]) -> List[float]:
        """Sigmoid归一化"""
        return [1 / (1 + math.exp(-w)) for w in weights]
    
    def _weighted_average(self, layer_results: List[LayerResult]) -> float:
        """加权平均"""
        total_weight = sum(r.weight_value * r.confidence for r in layer_results)
        total_confidence = sum(r.confidence for r in layer_results)
        return total_weight / total_confidence if total_confidence > 0 else 0.0
    
    def _geometric_mean(self, weights: List[float]) -> float:
        """几何平均"""
        positive_weights = [w for w in weights if w > 0]
        if not positive_weights:
            return 0.0
        
        product = 1.0
        for w in positive_weights:
            product *= w
        
        return product ** (1.0 / len(positive_weights))
    
    def _harmonic_mean(self, weights: List[float]) -> float:
        """调和平均"""
        positive_weights = [w for w in weights if w > 0]
        if not positive_weights:
            return 0.0
        
        harmonic_sum = sum(1/w for w in positive_weights)
        return len(positive_weights) / harmonic_sum
    
    def _calculate_median(self, weights: List[float]) -> float:
        """计算中位数"""
        if not weights:
            return 0.0
        
        sorted_weights = sorted(weights)
        n = len(sorted_weights)
        
        if n % 2 == 1:
            return sorted_weights[n // 2]
        else:
            return (sorted_weights[n // 2 - 1] + sorted_weights[n // 2]) / 2
    
    def _get_timestamp(self) -> float:
        """获取时间戳"""
        import time
        return time.time()
    
    def _record_aggregation_history(self, 
                                   layer_results: List[LayerResult],
                                   result: AggregatedResult,
                                   context: Optional[Dict[str, Any]]):
        """记录聚合历史"""
        history_entry = {
            'timestamp': self._get_timestamp(),
            'layer_count': len(layer_results),
            'final_weight': result.final_weight,
            'confidence_score': result.confidence_score,
            'strategy': self.config.strategy.value,
            'context': context or {}
        }
        
        self.aggregation_history.append(history_entry)
        
        # 保持历史记录数量限制
        if len(self.aggregation_history) > 1000:
            self.aggregation_history = self.aggregation_history[-1000:]
    
    def _update_layer_reliability(self, 
                                 layer_results: List[LayerResult],
                                 result: AggregatedResult):
        """更新层级可靠性"""
        for layer_result in layer_results:
            layer_name = layer_result.layer_name
            
            # 基于置信度和最终结果的一致性更新可靠性
            consistency = 1 - abs(layer_result.weight_value - result.final_weight)
            performance_score = layer_result.confidence * consistency
            
            if layer_name not in self.performance_tracker:
                self.performance_tracker[layer_name] = []
            
            self.performance_tracker[layer_name].append(performance_score)
            
            # 计算滑动平均可靠性
            recent_scores = self.performance_tracker[layer_name][-20:]  # 最近20次
            self.layer_reliability[layer_name] = np.mean(recent_scores)
    
    def _create_fallback_result(self, layer_results: List[LayerResult]) -> AggregatedResult:
        """创建回退结果"""
        if layer_results:
            fallback_weight = np.mean([r.weight_value for r in layer_results])
            fallback_confidence = np.mean([r.confidence for r in layer_results])
        else:
            fallback_weight = 0.5
            fallback_confidence = 0.3
        
        return AggregatedResult(
            final_weight=fallback_weight,
            confidence_score=fallback_confidence,
            layer_contributions={},
            aggregation_metadata={
                'strategy': 'fallback',
                'error': True
            },
            quality_metrics={}
        )