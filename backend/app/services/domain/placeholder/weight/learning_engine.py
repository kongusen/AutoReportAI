"""
权重学习引擎
基于历史数据和反馈进行权重学习和优化
"""
import logging
import pickle
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from collections import defaultdict, deque
import time
import os

from .weight_calculator import WeightComponents
from ..models import PlaceholderSpec

logger = logging.getLogger(__name__)

class LearningAlgorithm(Enum):
    """学习算法类型"""
    GRADIENT_DESCENT = "gradient_descent"
    REINFORCEMENT = "reinforcement"
    BAYESIAN = "bayesian"
    ENSEMBLE = "ensemble"
    NEURAL_NETWORK = "neural_network"

class RewardType(Enum):
    """奖励类型"""
    USER_SATISFACTION = "user_satisfaction"
    ACCURACY = "accuracy"
    PROCESSING_TIME = "processing_time"
    BUSINESS_VALUE = "business_value"
    COMPOSITE = "composite"

@dataclass
class LearningConfig:
    """学习配置"""
    algorithm: LearningAlgorithm = LearningAlgorithm.REINFORCEMENT
    learning_rate: float = 0.01
    discount_factor: float = 0.9
    exploration_rate: float = 0.1
    exploration_decay: float = 0.995
    memory_size: int = 10000
    batch_size: int = 32
    update_frequency: int = 100
    save_frequency: int = 1000
    model_path: str = "weight_learning_model.pkl"

@dataclass
class LearningExample:
    """学习样本"""
    placeholder_spec: PlaceholderSpec
    context: Dict[str, Any]
    input_weights: WeightComponents
    output_weight: float
    reward: float
    timestamp: float
    metadata: Dict[str, Any]

@dataclass
class ModelState:
    """模型状态"""
    weights: Dict[str, float]
    biases: Dict[str, float]
    learning_statistics: Dict[str, Any]
    version: int
    last_update: float

class WeightLearningEngine:
    """权重学习引擎"""
    
    def __init__(self, config: Optional[LearningConfig] = None):
        self.config = config or LearningConfig()
        self.learning_memory: deque = deque(maxlen=self.config.memory_size)
        self.model_state = self._initialize_model_state()
        self.learning_statistics = self._initialize_statistics()
        self.feature_extractors = self._initialize_feature_extractors()
        self.reward_calculator = self._initialize_reward_calculator()
        
        # 加载已有模型
        self._load_model()
        
    def _initialize_model_state(self) -> ModelState:
        """初始化模型状态"""
        return ModelState(
            weights={
                'paragraph_importance': 1.0,
                'section_relevance': 1.0,
                'document_context': 1.0,
                'business_rule_match': 1.0,
                'temporal_relevance': 1.0,
                'semantic_similarity': 1.0,
                'user_preference': 1.0,
                'historical_performance': 1.0
            },
            biases={
                'baseline_weight': 0.5,
                'confidence_bias': 0.1,
                'complexity_bias': 0.0,
                'domain_bias': 0.0
            },
            learning_statistics={
                'total_examples': 0,
                'total_updates': 0,
                'avg_reward': 0.0,
                'learning_curve': []
            },
            version=1,
            last_update=time.time()
        )
    
    def _initialize_statistics(self) -> Dict[str, Any]:
        """初始化学习统计"""
        return {
            'reward_history': deque(maxlen=1000),
            'weight_evolution': defaultdict(lambda: deque(maxlen=100)),
            'performance_metrics': {
                'accuracy': deque(maxlen=100),
                'precision': deque(maxlen=100),
                'recall': deque(maxlen=100),
                'user_satisfaction': deque(maxlen=100)
            },
            'learning_phases': {
                'exploration': 0,
                'exploitation': 0,
                'convergence': 0
            }
        }
    
    def _initialize_feature_extractors(self) -> Dict[str, Any]:
        """初始化特征提取器"""
        return {
            'text_features': self._extract_text_features,
            'context_features': self._extract_context_features,
            'temporal_features': self._extract_temporal_features,
            'business_features': self._extract_business_features,
            'user_features': self._extract_user_features
        }
    
    def _initialize_reward_calculator(self):
        """初始化奖励计算器"""
        return {
            RewardType.USER_SATISFACTION: self._calculate_satisfaction_reward,
            RewardType.ACCURACY: self._calculate_accuracy_reward,
            RewardType.PROCESSING_TIME: self._calculate_time_reward,
            RewardType.BUSINESS_VALUE: self._calculate_business_reward,
            RewardType.COMPOSITE: self._calculate_composite_reward
        }
    
    def learn_from_feedback(self, 
                           placeholder_spec: PlaceholderSpec,
                           context: Dict[str, Any],
                           input_weights: WeightComponents,
                           actual_output: float,
                           user_feedback: Dict[str, Any]) -> bool:
        """从反馈中学习"""
        try:
            # 计算奖励
            reward = self._calculate_reward(actual_output, user_feedback)
            
            # 创建学习样本
            learning_example = LearningExample(
                placeholder_spec=placeholder_spec,
                context=context,
                input_weights=input_weights,
                output_weight=actual_output,
                reward=reward,
                timestamp=time.time(),
                metadata=user_feedback
            )
            
            # 添加到学习记忆
            self.learning_memory.append(learning_example)
            
            # 更新学习统计
            self._update_learning_statistics(learning_example)
            
            # 检查是否需要更新模型
            if len(self.learning_memory) % self.config.update_frequency == 0:
                self._update_model()
            
            # 检查是否需要保存模型
            if len(self.learning_memory) % self.config.save_frequency == 0:
                self._save_model()
            
            return True
            
        except Exception as e:
            logger.error(f"学习失败: {e}")
            return False
    
    def predict_optimal_weights(self, 
                               placeholder_spec: PlaceholderSpec,
                               context: Dict[str, Any],
                               current_weights: WeightComponents) -> Tuple[WeightComponents, float]:
        """预测最优权重"""
        try:
            # 提取特征
            features = self._extract_all_features(placeholder_spec, context, current_weights)
            
            # 使用当前模型预测
            predicted_weights = self._predict_weights(features)
            
            # 计算预测置信度
            confidence = self._calculate_prediction_confidence(features, predicted_weights)
            
            # 应用探索策略
            if np.random.random() < self.config.exploration_rate:
                predicted_weights = self._apply_exploration(predicted_weights)
                confidence *= 0.8  # 探索时降低置信度
            
            return predicted_weights, confidence
            
        except Exception as e:
            logger.error(f"权重预测失败: {e}")
            return current_weights, 0.5
    
    def _extract_all_features(self, 
                             placeholder_spec: PlaceholderSpec,
                             context: Dict[str, Any],
                             current_weights: WeightComponents) -> Dict[str, float]:
        """提取所有特征"""
        all_features = {}
        
        # 提取各类特征
        for feature_type, extractor in self.feature_extractors.items():
            try:
                features = extractor(placeholder_spec, context, current_weights)
                all_features.update({f"{feature_type}_{k}": v for k, v in features.items()})
            except Exception as e:
                logger.warning(f"特征提取失败 - {feature_type}: {e}")
        
        return all_features
    
    def _extract_text_features(self, 
                              placeholder_spec: PlaceholderSpec,
                              context: Dict[str, Any],
                              current_weights: WeightComponents) -> Dict[str, float]:
        """提取文本特征"""
        content = placeholder_spec.content
        
        return {
            'content_length': min(1.0, len(content) / 100),
            'complexity_score': self._calculate_text_complexity(content),
            'keyword_density': self._calculate_keyword_density(content),
            'placeholder_type_score': self._get_placeholder_type_score(placeholder_spec)
        }
    
    def _extract_context_features(self, 
                                 placeholder_spec: PlaceholderSpec,
                                 context: Dict[str, Any],
                                 current_weights: WeightComponents) -> Dict[str, float]:
        """提取上下文特征"""
        return {
            'context_richness': len(context) / 20,  # 归一化
            'time_sensitivity': context.get('time_sensitive', 0.0),
            'business_criticality': context.get('business_critical', 0.0),
            'user_priority': context.get('user_priority', 0.5),
            'document_complexity': context.get('document_complexity', 0.5)
        }
    
    def _extract_temporal_features(self, 
                                  placeholder_spec: PlaceholderSpec,
                                  context: Dict[str, Any],
                                  current_weights: WeightComponents) -> Dict[str, float]:
        """提取时间特征"""
        current_time = time.time()
        
        return {
            'hour_of_day': (time.localtime(current_time).tm_hour) / 24,
            'day_of_week': (time.localtime(current_time).tm_wday) / 7,
            'recency_factor': 1.0,  # 当前请求，始终为1
            'seasonality': self._calculate_seasonality_factor(current_time)
        }
    
    def _extract_business_features(self, 
                                  placeholder_spec: PlaceholderSpec,
                                  context: Dict[str, Any],
                                  current_weights: WeightComponents) -> Dict[str, float]:
        """提取业务特征"""
        return {
            'domain_match': self._calculate_domain_match(placeholder_spec, context),
            'rule_complexity': self._calculate_rule_complexity(context),
            'compliance_requirement': context.get('compliance_required', 0.0),
            'performance_sensitivity': context.get('performance_sensitive', 0.5)
        }
    
    def _extract_user_features(self, 
                              placeholder_spec: PlaceholderSpec,
                              context: Dict[str, Any],
                              current_weights: WeightComponents) -> Dict[str, float]:
        """提取用户特征"""
        user_info = context.get('user_info', {})
        
        return {
            'user_experience': user_info.get('experience_level', 0.5),
            'user_role': self._encode_user_role(user_info.get('role', 'general')),
            'historical_satisfaction': user_info.get('avg_satisfaction', 0.7),
            'preference_alignment': self._calculate_preference_alignment(user_info, placeholder_spec)
        }
    
    def _predict_weights(self, features: Dict[str, float]) -> WeightComponents:
        """预测权重"""
        if self.config.algorithm == LearningAlgorithm.REINFORCEMENT:
            return self._reinforcement_predict(features)
        elif self.config.algorithm == LearningAlgorithm.GRADIENT_DESCENT:
            return self._gradient_descent_predict(features)
        elif self.config.algorithm == LearningAlgorithm.BAYESIAN:
            return self._bayesian_predict(features)
        else:
            return self._reinforcement_predict(features)  # 默认
    
    def _reinforcement_predict(self, features: Dict[str, float]) -> WeightComponents:
        """强化学习预测"""
        # 简化的Q-learning近似
        weights = self.model_state.weights
        biases = self.model_state.biases
        
        # 计算加权特征值
        paragraph_weight = max(0, min(1, 
            biases['baseline_weight'] + 
            sum(weights.get(f, 1.0) * features.get(f, 0.0) for f in features.keys()) * 0.1
        ))
        
        section_weight = max(0, min(1, 
            biases['baseline_weight'] * 0.9 + 
            weights.get('section_relevance', 1.0) * features.get('context_richness', 0.5) * 0.3
        ))
        
        document_weight = max(0, min(1,
            biases['baseline_weight'] * 0.8 + 
            weights.get('document_context', 1.0) * features.get('document_complexity', 0.5) * 0.4
        ))
        
        business_rule_weight = max(0, min(1,
            biases['baseline_weight'] * 1.1 + 
            weights.get('business_rule_match', 1.0) * features.get('business_domain_match', 0.5) * 0.5
        ))
        
        temporal_weight = max(0, min(1,
            biases['baseline_weight'] * 0.7 + 
            weights.get('temporal_relevance', 1.0) * features.get('temporal_time_sensitivity', 0.3) * 0.6
        ))
        
        semantic_weight = max(0, min(1,
            biases['baseline_weight'] * 0.9 + 
            weights.get('semantic_similarity', 1.0) * features.get('text_complexity_score', 0.5) * 0.3
        ))
        
        confidence_score = max(0, min(1,
            0.7 + biases.get('confidence_bias', 0.1) + 
            weights.get('historical_performance', 1.0) * 0.2
        ))
        
        return WeightComponents(
            paragraph_weight=paragraph_weight,
            section_weight=section_weight,
            document_weight=document_weight,
            business_rule_weight=business_rule_weight,
            temporal_weight=temporal_weight,
            semantic_weight=semantic_weight,
            confidence_score=confidence_score
        )
    
    def _gradient_descent_predict(self, features: Dict[str, float]) -> WeightComponents:
        """梯度下降预测"""
        # 简化的线性模型
        weights = self.model_state.weights
        feature_vector = np.array(list(features.values()))
        weight_vector = np.array(list(weights.values())[:len(feature_vector)])
        
        # 计算线性组合
        linear_output = np.dot(feature_vector, weight_vector) + self.model_state.biases['baseline_weight']
        
        # 应用激活函数
        activated_output = 1 / (1 + np.exp(-linear_output))  # sigmoid
        
        # 分配到各个权重组件
        base_weight = activated_output * 0.5 + 0.25  # 范围[0.25, 0.75]
        
        return WeightComponents(
            paragraph_weight=base_weight * 1.1,
            section_weight=base_weight * 1.0,
            document_weight=base_weight * 0.9,
            business_rule_weight=base_weight * 1.2,
            temporal_weight=base_weight * 0.8,
            semantic_weight=base_weight * 1.0,
            confidence_score=activated_output
        )
    
    def _bayesian_predict(self, features: Dict[str, float]) -> WeightComponents:
        """贝叶斯预测"""
        # 简化的贝叶斯推断
        prior_weights = self.model_state.weights
        
        # 计算后验概率（简化版本）
        evidence = sum(features.values()) / len(features) if features else 0.5
        
        # 更新权重（贝叶斯更新）
        posterior_strength = evidence * 2  # 简化的似然
        
        return WeightComponents(
            paragraph_weight=min(1.0, prior_weights.get('paragraph_importance', 0.5) * posterior_strength),
            section_weight=min(1.0, prior_weights.get('section_relevance', 0.5) * posterior_strength),
            document_weight=min(1.0, prior_weights.get('document_context', 0.5) * posterior_strength),
            business_rule_weight=min(1.0, prior_weights.get('business_rule_match', 0.5) * posterior_strength),
            temporal_weight=min(1.0, prior_weights.get('temporal_relevance', 0.5) * posterior_strength),
            semantic_weight=min(1.0, prior_weights.get('semantic_similarity', 0.5) * posterior_strength),
            confidence_score=evidence
        )
    
    def _update_model(self):
        """更新模型"""
        try:
            if len(self.learning_memory) < self.config.batch_size:
                return
            
            # 采样批次数据
            batch_samples = list(self.learning_memory)[-self.config.batch_size:]
            
            # 计算梯度和更新
            if self.config.algorithm == LearningAlgorithm.REINFORCEMENT:
                self._update_reinforcement_model(batch_samples)
            elif self.config.algorithm == LearningAlgorithm.GRADIENT_DESCENT:
                self._update_gradient_model(batch_samples)
            
            # 更新模型统计
            self.model_state.learning_statistics['total_updates'] += 1
            self.model_state.last_update = time.time()
            
            # 衰减探索率
            self.config.exploration_rate *= self.config.exploration_decay
            
            logger.info(f"模型更新完成 - 更新次数: {self.model_state.learning_statistics['total_updates']}")
            
        except Exception as e:
            logger.error(f"模型更新失败: {e}")
    
    def _update_reinforcement_model(self, batch_samples: List[LearningExample]):
        """更新强化学习模型"""
        for example in batch_samples:
            # 提取特征
            features = self._extract_all_features(
                example.placeholder_spec, 
                example.context, 
                example.input_weights
            )
            
            # 计算目标值
            target_value = example.reward + self.config.discount_factor * self._estimate_future_reward(features)
            
            # 更新权重（简化的Q-learning更新）
            for feature_name, feature_value in features.items():
                if feature_name in self.model_state.weights:
                    prediction_error = target_value - example.output_weight
                    self.model_state.weights[feature_name] += (
                        self.config.learning_rate * prediction_error * feature_value
                    )
    
    def _update_gradient_model(self, batch_samples: List[LearningExample]):
        """更新梯度下降模型"""
        # 计算批次梯度
        gradient_sum = defaultdict(float)
        
        for example in batch_samples:
            features = self._extract_all_features(
                example.placeholder_spec, 
                example.context, 
                example.input_weights
            )
            
            # 计算预测误差
            prediction_error = example.output_weight - example.reward
            
            # 累加梯度
            for feature_name, feature_value in features.items():
                if feature_name in self.model_state.weights:
                    gradient_sum[feature_name] += prediction_error * feature_value
        
        # 应用梯度更新
        for weight_name, gradient in gradient_sum.items():
            avg_gradient = gradient / len(batch_samples)
            self.model_state.weights[weight_name] -= self.config.learning_rate * avg_gradient
    
    def _calculate_reward(self, actual_output: float, user_feedback: Dict[str, Any]) -> float:
        """计算奖励"""
        reward_type = RewardType.COMPOSITE  # 默认使用综合奖励
        
        if 'reward_type' in user_feedback:
            reward_type = RewardType(user_feedback['reward_type'])
        
        calculator = self.reward_calculator.get(reward_type, self._calculate_composite_reward)
        return calculator(actual_output, user_feedback)
    
    def _calculate_satisfaction_reward(self, actual_output: float, user_feedback: Dict[str, Any]) -> float:
        """计算满意度奖励"""
        satisfaction = user_feedback.get('user_satisfaction', 0.5)
        return satisfaction * 2 - 1  # 转换到[-1, 1]范围
    
    def _calculate_accuracy_reward(self, actual_output: float, user_feedback: Dict[str, Any]) -> float:
        """计算准确性奖励"""
        expected_output = user_feedback.get('expected_weight', actual_output)
        accuracy = 1 - abs(actual_output - expected_output)
        return accuracy * 2 - 1  # 转换到[-1, 1]范围
    
    def _calculate_time_reward(self, actual_output: float, user_feedback: Dict[str, Any]) -> float:
        """计算时间奖励"""
        processing_time = user_feedback.get('processing_time', 1.0)
        target_time = user_feedback.get('target_time', 1.0)
        
        if processing_time <= target_time:
            return 1.0
        else:
            return max(-1.0, 1.0 - (processing_time - target_time) / target_time)
    
    def _calculate_business_reward(self, actual_output: float, user_feedback: Dict[str, Any]) -> float:
        """计算业务价值奖励"""
        business_value = user_feedback.get('business_value', 0.5)
        return business_value * 2 - 1  # 转换到[-1, 1]范围
    
    def _calculate_composite_reward(self, actual_output: float, user_feedback: Dict[str, Any]) -> float:
        """计算综合奖励"""
        satisfaction_reward = self._calculate_satisfaction_reward(actual_output, user_feedback)
        accuracy_reward = self._calculate_accuracy_reward(actual_output, user_feedback)
        time_reward = self._calculate_time_reward(actual_output, user_feedback)
        business_reward = self._calculate_business_reward(actual_output, user_feedback)
        
        # 加权组合
        composite_reward = (
            satisfaction_reward * 0.4 +
            accuracy_reward * 0.3 +
            time_reward * 0.2 +
            business_reward * 0.1
        )
        
        return composite_reward
    
    # 辅助方法
    def _calculate_text_complexity(self, text: str) -> float:
        """计算文本复杂度"""
        if not text:
            return 0.0
        
        # 简单的复杂度指标
        sentence_count = len(text.split('。'))
        avg_sentence_length = len(text) / sentence_count if sentence_count > 0 else 0
        char_variety = len(set(text)) / len(text) if text else 0
        
        complexity = (avg_sentence_length / 50 + char_variety) / 2
        return min(1.0, complexity)
    
    def _calculate_keyword_density(self, text: str) -> float:
        """计算关键词密度"""
        keywords = ['统计', '分析', '报告', '数据', '指标', '趋势', '对比']
        if not text:
            return 0.0
        
        keyword_count = sum(text.count(keyword) for keyword in keywords)
        return min(1.0, keyword_count / len(text) * 100)
    
    def _get_placeholder_type_score(self, placeholder_spec: PlaceholderSpec) -> float:
        """获取占位符类型分数"""
        statistical_type = getattr(placeholder_spec, 'statistical_type', '')
        
        type_scores = {
            '统计': 0.8,
            '趋势': 0.7,
            '对比': 0.9,
            '列表': 0.6,
            '统计图': 0.8,
            '极值': 0.7,
            '预测': 0.9
        }
        
        return type_scores.get(statistical_type, 0.5)
    
    def _save_model(self):
        """保存模型"""
        try:
            model_data = {
                'model_state': asdict(self.model_state),
                'learning_statistics': self.learning_statistics,
                'config': asdict(self.config)
            }
            
            with open(self.config.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"模型已保存到: {self.config.model_path}")
            
        except Exception as e:
            logger.error(f"模型保存失败: {e}")
    
    def _load_model(self):
        """加载模型"""
        try:
            if os.path.exists(self.config.model_path):
                with open(self.config.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                
                # 恢复模型状态
                state_dict = model_data['model_state']
                self.model_state = ModelState(**state_dict)
                
                if 'learning_statistics' in model_data:
                    self.learning_statistics.update(model_data['learning_statistics'])
                
                logger.info(f"模型已从 {self.config.model_path} 加载")
            
        except Exception as e:
            logger.warning(f"模型加载失败，使用默认模型: {e}")
    
    def get_learning_report(self) -> Dict[str, Any]:
        """获取学习报告"""
        return {
            'model_version': self.model_state.version,
            'total_examples': len(self.learning_memory),
            'total_updates': self.model_state.learning_statistics['total_updates'],
            'current_weights': self.model_state.weights,
            'current_biases': self.model_state.biases,
            'exploration_rate': self.config.exploration_rate,
            'recent_rewards': list(self.learning_statistics['reward_history'])[-10:],
            'performance_trends': {
                metric: list(values)[-10:] 
                for metric, values in self.learning_statistics['performance_metrics'].items()
            }
        }