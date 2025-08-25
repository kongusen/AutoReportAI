"""
Agent学习引擎 - 增强ContextAwareAgent的学习能力

基于执行历史和上下文模式，实现智能学习和优化决策
"""

import logging
import asyncio
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy.orm import Session

from .context_manager import AgentContext, ContextScope, ContextEntry

logger = logging.getLogger(__name__)


@dataclass
class LearningPattern:
    """学习模式"""
    pattern_id: str
    pattern_type: str  # "success", "failure", "optimization"
    context_signature: str  # 上下文特征签名
    success_rate: float
    usage_count: int
    avg_performance: float  # 平均性能指标
    confidence: float
    created_at: datetime
    last_used: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_metrics(self, success: bool, performance: float):
        """更新模式指标"""
        self.usage_count += 1
        
        # 更新成功率 (使用指数移动平均)
        weight = 0.1 if self.usage_count > 10 else 1.0 / self.usage_count
        if success:
            self.success_rate = self.success_rate * (1 - weight) + weight
        else:
            self.success_rate = self.success_rate * (1 - weight)
        
        # 更新平均性能
        self.avg_performance = self.avg_performance * (1 - weight) + performance * weight
        
        # 更新置信度 (基于使用次数和成功率)
        self.confidence = min(0.95, self.success_rate * (1 - 1.0 / (1 + self.usage_count * 0.1)))
        
        self.last_used = datetime.now()


@dataclass
class LearningSignal:
    """学习信号"""
    context_snapshot: Dict[str, Any]
    action: str
    parameters: Dict[str, Any]
    result: Dict[str, Any]
    success: bool
    performance_metrics: Dict[str, float]
    timestamp: datetime
    agent_name: str


class ContextLearningEngine:
    """上下文学习引擎"""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db_session = db_session
        self.patterns: Dict[str, LearningPattern] = {}
        self.learning_history: List[LearningSignal] = []
        self._context_analyzers: List[callable] = []
        self._pattern_matchers: List[callable] = []
        
        # 学习配置
        self.min_pattern_occurrences = 3
        self.confidence_threshold = 0.7
        self.max_history_size = 1000
        
        logger.info("ContextLearningEngine initialized")
    
    def register_context_analyzer(self, analyzer: callable):
        """注册上下文分析器"""
        self._context_analyzers.append(analyzer)
    
    def register_pattern_matcher(self, matcher: callable):
        """注册模式匹配器"""
        self._pattern_matchers.append(matcher)
    
    async def learn_from_execution(self, 
                                 context: AgentContext,
                                 action: str,
                                 parameters: Dict[str, Any],
                                 result: Dict[str, Any],
                                 agent_name: str) -> None:
        """从执行结果中学习"""
        try:
            # 创建学习信号
            learning_signal = LearningSignal(
                context_snapshot=self._extract_context_features(context),
                action=action,
                parameters=parameters,
                result=result,
                success=result.get('success', False),
                performance_metrics=self._extract_performance_metrics(result),
                timestamp=datetime.now(),
                agent_name=agent_name
            )
            
            # 添加到学习历史
            self.learning_history.append(learning_signal)
            if len(self.learning_history) > self.max_history_size:
                self.learning_history = self.learning_history[-self.max_history_size//2:]
            
            # 识别和更新模式
            await self._identify_and_update_patterns(learning_signal)
            
            # 异步持久化学习结果
            if self.db_session:
                asyncio.create_task(self._persist_learning_data(learning_signal))
                
        except Exception as e:
            logger.error(f"Learning from execution failed: {e}")
    
    async def get_optimization_hints(self, 
                                   context: AgentContext,
                                   action: str,
                                   parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取优化建议"""
        try:
            context_features = self._extract_context_features(context)
            context_signature = self._generate_context_signature(context_features, action, parameters)
            
            hints = []
            
            # 1. 基于历史模式的建议
            historical_hints = await self._get_historical_optimization_hints(
                context_signature, context_features, action, parameters
            )
            hints.extend(historical_hints)
            
            # 2. 基于相似情况的建议
            similarity_hints = await self._get_similarity_based_hints(
                context_features, action, parameters
            )
            hints.extend(similarity_hints)
            
            # 3. 基于失败模式的预警
            failure_warnings = await self._get_failure_warnings(
                context_features, action, parameters
            )
            hints.extend(failure_warnings)
            
            # 按置信度排序
            hints.sort(key=lambda h: h.get('confidence', 0), reverse=True)
            
            return hints[:5]  # 返回最多5个建议
            
        except Exception as e:
            logger.error(f"Getting optimization hints failed: {e}")
            return []
    
    async def predict_success_probability(self,
                                        context: AgentContext,
                                        action: str,
                                        parameters: Dict[str, Any]) -> float:
        """预测成功概率"""
        try:
            context_features = self._extract_context_features(context)
            context_signature = self._generate_context_signature(context_features, action, parameters)
            
            # 查找匹配的模式
            matching_patterns = self._find_matching_patterns(context_signature, context_features)
            
            if not matching_patterns:
                return 0.5  # 默认成功率
            
            # 加权平均成功率
            total_weight = sum(p.confidence * p.usage_count for p in matching_patterns)
            if total_weight == 0:
                return 0.5
            
            weighted_success_rate = sum(
                p.success_rate * p.confidence * p.usage_count 
                for p in matching_patterns
            ) / total_weight
            
            return min(0.95, max(0.05, weighted_success_rate))
            
        except Exception as e:
            logger.error(f"Predicting success probability failed: {e}")
            return 0.5
    
    def _extract_context_features(self, context: AgentContext) -> Dict[str, Any]:
        """提取上下文特征"""
        features = {
            'session_id': context.session_id,
            'task_id': context.task_id,
            'user_id': context.user_id,
            'capabilities': context.capabilities,
            'config': context.config
        }
        
        # 提取关键上下文值
        for scope in [ContextScope.GLOBAL, ContextScope.TASK, ContextScope.SESSION]:
            scope_data = context.get_context_by_scope(scope)
            features[f'{scope.value}_context'] = scope_data
        
        # 应用自定义分析器
        for analyzer in self._context_analyzers:
            try:
                custom_features = analyzer(context)
                if custom_features:
                    features.update(custom_features)
            except Exception as e:
                logger.warning(f"Context analyzer failed: {e}")
        
        return features
    
    def _extract_performance_metrics(self, result: Dict[str, Any]) -> Dict[str, float]:
        """提取性能指标"""
        metrics = {}
        
        # 标准指标
        if 'execution_time' in result:
            metrics['execution_time'] = float(result['execution_time'])
        if 'confidence' in result:
            metrics['confidence'] = float(result['confidence'])
        if 'memory_usage' in result:
            metrics['memory_usage'] = float(result['memory_usage'])
        
        # SQL相关指标
        if 'sql_complexity' in result:
            metrics['sql_complexity'] = float(result['sql_complexity'])
        if 'query_rows' in result:
            metrics['query_rows'] = float(result['query_rows'])
        
        return metrics
    
    def _generate_context_signature(self, 
                                  context_features: Dict[str, Any],
                                  action: str,
                                  parameters: Dict[str, Any]) -> str:
        """生成上下文签名"""
        # 提取关键特征进行哈希
        key_features = {
            'action': action,
            'data_source_type': context_features.get('data_source_type'),
            'placeholder_type': parameters.get('placeholder_type'),
            'semantic_type': parameters.get('semantic_type'),
            'table_count': len(context_features.get('table_structures', {})),
            'user_context': bool(context_features.get('user_id'))
        }
        
        signature_string = json.dumps(key_features, sort_keys=True)
        return hashlib.md5(signature_string.encode()).hexdigest()[:16]
    
    async def _identify_and_update_patterns(self, learning_signal: LearningSignal) -> None:
        """识别并更新学习模式"""
        context_signature = self._generate_context_signature(
            learning_signal.context_snapshot,
            learning_signal.action,
            learning_signal.parameters
        )
        
        # 查找或创建模式
        pattern_id = f"{context_signature}_{learning_signal.action}"
        
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
        else:
            pattern = LearningPattern(
                pattern_id=pattern_id,
                pattern_type="general",
                context_signature=context_signature,
                success_rate=0.5,
                usage_count=0,
                avg_performance=0.0,
                confidence=0.0,
                created_at=datetime.now(),
                last_used=datetime.now(),
                metadata={
                    'action': learning_signal.action,
                    'agent_name': learning_signal.agent_name
                }
            )
            self.patterns[pattern_id] = pattern
        
        # 更新模式指标
        performance = learning_signal.performance_metrics.get('execution_time', 1.0)
        pattern.update_metrics(learning_signal.success, performance)
    
    def _find_matching_patterns(self, 
                               context_signature: str,
                               context_features: Dict[str, Any]) -> List[LearningPattern]:
        """查找匹配的学习模式"""
        matching_patterns = []
        
        for pattern in self.patterns.values():
            # 精确匹配
            if pattern.context_signature == context_signature:
                matching_patterns.append(pattern)
                continue
            
            # 模糊匹配（使用自定义匹配器）
            for matcher in self._pattern_matchers:
                try:
                    if matcher(pattern, context_features):
                        matching_patterns.append(pattern)
                        break
                except Exception as e:
                    logger.warning(f"Pattern matcher failed: {e}")
        
        # 过滤低置信度模式
        return [p for p in matching_patterns if p.confidence >= self.confidence_threshold]
    
    async def _get_historical_optimization_hints(self,
                                               context_signature: str,
                                               context_features: Dict[str, Any],
                                               action: str,
                                               parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于历史模式获取优化建议"""
        hints = []
        
        # 查找成功的历史模式
        successful_patterns = [
            p for p in self.patterns.values()
            if p.success_rate > 0.8 and p.usage_count >= self.min_pattern_occurrences
        ]
        
        for pattern in successful_patterns:
            if pattern.context_signature == context_signature:
                hints.append({
                    'type': 'historical_success',
                    'message': f'此类场景历史成功率 {pattern.success_rate:.2%}',
                    'confidence': pattern.confidence,
                    'suggestion': f'建议使用与历史成功案例相似的参数配置',
                    'metadata': {
                        'pattern_id': pattern.pattern_id,
                        'usage_count': pattern.usage_count,
                        'avg_performance': pattern.avg_performance
                    }
                })
        
        return hints
    
    async def _get_similarity_based_hints(self,
                                        context_features: Dict[str, Any],
                                        action: str,
                                        parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于相似情况获取建议"""
        hints = []
        
        # 分析相似的成功案例
        similar_successes = []
        for signal in self.learning_history[-100:]:  # 最近100个记录
            if (signal.action == action and 
                signal.success and
                self._calculate_context_similarity(context_features, signal.context_snapshot) > 0.7):
                similar_successes.append(signal)
        
        if similar_successes:
            # 分析成功案例的共同特征
            common_features = self._extract_common_features(similar_successes)
            if common_features:
                hints.append({
                    'type': 'similarity_based',
                    'message': f'发现 {len(similar_successes)} 个相似的成功案例',
                    'confidence': 0.8,
                    'suggestion': f'建议采用相似的配置参数',
                    'metadata': {
                        'common_features': common_features,
                        'success_count': len(similar_successes)
                    }
                })
        
        return hints
    
    async def _get_failure_warnings(self,
                                  context_features: Dict[str, Any],
                                  action: str,
                                  parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取失败模式预警"""
        warnings = []
        
        # 查找失败模式
        failure_patterns = [
            p for p in self.patterns.values()
            if p.success_rate < 0.3 and p.usage_count >= self.min_pattern_occurrences
        ]
        
        context_signature = self._generate_context_signature(context_features, action, parameters)
        
        for pattern in failure_patterns:
            if pattern.context_signature == context_signature:
                warnings.append({
                    'type': 'failure_warning',
                    'message': f'⚠️ 此场景历史失败率较高 ({1-pattern.success_rate:.2%})',
                    'confidence': pattern.confidence,
                    'suggestion': '建议检查参数配置或考虑其他方案',
                    'metadata': {
                        'pattern_id': pattern.pattern_id,
                        'failure_rate': 1 - pattern.success_rate,
                        'usage_count': pattern.usage_count
                    }
                })
        
        return warnings
    
    def _calculate_context_similarity(self, 
                                    context1: Dict[str, Any],
                                    context2: Dict[str, Any]) -> float:
        """计算上下文相似度"""
        # 简化的相似度计算
        common_keys = set(context1.keys()) & set(context2.keys())
        if not common_keys:
            return 0.0
        
        matches = 0
        for key in common_keys:
            if context1[key] == context2[key]:
                matches += 1
        
        return matches / len(common_keys)
    
    def _extract_common_features(self, signals: List[LearningSignal]) -> Dict[str, Any]:
        """提取成功案例的共同特征"""
        if not signals:
            return {}
        
        # 统计参数出现频率
        param_counter = defaultdict(Counter)
        for signal in signals:
            for key, value in signal.parameters.items():
                if isinstance(value, (str, int, bool)):
                    param_counter[key][value] += 1
        
        # 提取高频特征
        common_features = {}
        for param, value_counts in param_counter.items():
            most_common = value_counts.most_common(1)[0]
            if most_common[1] >= len(signals) * 0.6:  # 60%以上出现
                common_features[param] = most_common[0]
        
        return common_features
    
    async def _persist_learning_data(self, learning_signal: LearningSignal) -> None:
        """持久化学习数据（异步）"""
        if not self.db_session:
            return
        
        try:
            # 这里可以将学习数据保存到数据库
            # 为简化示例，暂时跳过具体实现
            logger.debug(f"Learning data persisted for {learning_signal.agent_name}")
        except Exception as e:
            logger.error(f"Failed to persist learning data: {e}")


class EnhancedContextAwareAgent:
    """增强的上下文感知Agent - 集成学习能力"""
    
    def __init__(self, base_agent, learning_engine: ContextLearningEngine):
        self.base_agent = base_agent
        self.learning_engine = learning_engine
        self._learning_enabled = True
    
    async def execute_with_learning(self, 
                                  session_id: str,
                                  action: str,
                                  parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """带学习能力的执行"""
        context = self.base_agent.context_manager.get_context(session_id)
        if not context:
            raise ValueError(f"Context not found for session: {session_id}")
        
        parameters = parameters or {}
        
        # 1. 获取优化建议
        if self._learning_enabled:
            optimization_hints = await self.learning_engine.get_optimization_hints(
                context, action, parameters
            )
            
            # 应用优化建议（可以根据置信度决定是否采纳）
            for hint in optimization_hints:
                if hint.get('confidence', 0) > 0.8:
                    suggested_params = hint.get('metadata', {}).get('suggested_parameters')
                    if suggested_params:
                        parameters.update(suggested_params)
        
        # 2. 预测成功概率
        success_probability = await self.learning_engine.predict_success_probability(
            context, action, parameters
        )
        
        # 3. 执行原始操作
        start_time = datetime.now()
        try:
            result = await self.base_agent.execute_with_context(session_id, action, parameters)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 添加性能指标
            result['execution_time'] = execution_time
            result['predicted_success_probability'] = success_probability
            
            # 4. 学习执行结果
            if self._learning_enabled:
                await self.learning_engine.learn_from_execution(
                    context, action, parameters, result, self.base_agent.name
                )
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_result = {
                'success': False,
                'error': str(e),
                'execution_time': execution_time,
                'predicted_success_probability': success_probability
            }
            
            # 从错误中学习
            if self._learning_enabled:
                await self.learning_engine.learn_from_execution(
                    context, action, parameters, error_result, self.base_agent.name
                )
            
            raise
    
    def enable_learning(self, enabled: bool = True):
        """启用/禁用学习功能"""
        self._learning_enabled = enabled
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """获取学习统计信息"""
        return {
            'total_patterns': len(self.learning_engine.patterns),
            'learning_history_size': len(self.learning_engine.learning_history),
            'high_confidence_patterns': len([
                p for p in self.learning_engine.patterns.values()
                if p.confidence > 0.8
            ]),
            'successful_patterns': len([
                p for p in self.learning_engine.patterns.values()
                if p.success_rate > 0.8
            ])
        }


# 便捷函数
def create_learning_engine(db_session: Optional[Session] = None) -> ContextLearningEngine:
    """创建学习引擎"""
    return ContextLearningEngine(db_session)

def enhance_agent_with_learning(agent, 
                               learning_engine: Optional[ContextLearningEngine] = None) -> EnhancedContextAwareAgent:
    """为Agent增加学习能力"""
    if learning_engine is None:
        learning_engine = create_learning_engine()
    return EnhancedContextAwareAgent(agent, learning_engine)