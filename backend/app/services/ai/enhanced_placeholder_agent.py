"""
增强的占位符SQL Agent - 集成学习、缓存和质量评估能力

整合了三大优化组件：
1. 学习引擎 - 从执行历史中学习优化决策
2. 智能缓存 - 多层级智能缓存管理  
3. 质量评估 - 多维度SQL质量评估

使用示例:
    agent = create_enhanced_placeholder_agent(db_session)
    result = await agent.analyze_placeholder_with_enhancements(request)
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from .agents.placeholder_sql_agent import PlaceholderSQLAgent, PlaceholderAnalysisRequest, PlaceholderAnalysisResult
from .core.learning_engine import ContextLearningEngine, EnhancedContextAwareAgent, create_learning_engine
from .core.intelligent_cache import IntelligentCacheManager, CacheStrategy, create_intelligent_cache_manager
from .core.sql_quality_assessor import SQLQualityAssessor, create_sql_quality_assessor, QualityLevel
from .core.context_manager import AgentContext, ContextScope, get_context_manager

logger = logging.getLogger(__name__)


class EnhancedPlaceholderSQLAgent:
    """增强的占位符SQL Agent"""
    
    def __init__(self, 
                 base_agent: PlaceholderSQLAgent,
                 learning_engine: ContextLearningEngine,
                 cache_manager: IntelligentCacheManager,
                 quality_assessor: SQLQualityAssessor):
        
        self.base_agent = base_agent
        self.learning_engine = learning_engine
        self.cache_manager = cache_manager
        self.quality_assessor = quality_assessor
        
        # 增强Agent包装器
        self.enhanced_agent = EnhancedContextAwareAgent(base_agent, learning_engine)
        
        # 注册学习规则和缓存预测规则
        self._register_learning_rules()
        self._register_cache_rules()
        
        logger.info("EnhancedPlaceholderSQLAgent initialized with all optimizations")
    
    async def analyze_placeholder_with_enhancements(self, 
                                                  request: PlaceholderAnalysisRequest,
                                                  session_id: str = None) -> Dict[str, Any]:
        """
        带全面增强的占位符分析
        
        包含：学习优化 + 智能缓存 + 质量评估
        """
        start_time = datetime.now()
        
        try:
            # 1. 生成会话ID（如果没有提供）
            if not session_id:
                session_id = f"placeholder_analysis_{request.placeholder_id}_{int(start_time.timestamp())}"
            
            # 2. 构建分析上下文
            context = await self._build_analysis_context(request, session_id)
            
            # 3. 智能缓存检查
            cache_key = self._generate_cache_key(request)
            cached_result = await self.cache_manager.get(cache_key, context)
            
            if cached_result and not request.force_reanalyze:
                logger.info(f"缓存命中: {request.placeholder_id}")
                
                # 添加缓存标记
                cached_result['source'] = 'cache'
                cached_result['cache_hit'] = True
                cached_result['analysis_time'] = (datetime.now() - start_time).total_seconds()
                
                # 记录缓存命中到学习引擎
                await self.learning_engine.learn_from_execution(
                    context['agent_context'],
                    'analyze_placeholder_sql',
                    request.to_dict(),
                    cached_result,
                    'enhanced_placeholder_agent'
                )
                
                return cached_result
            
            # 4. 获取学习优化建议
            optimization_hints = await self.learning_engine.get_optimization_hints(
                context['agent_context'],
                'analyze_placeholder_sql',
                request.to_dict()
            )
            
            # 5. 应用优化建议到请求参数
            optimized_request = self._apply_optimization_hints(request, optimization_hints)
            
            # 6. 预测成功概率
            success_probability = await self.learning_engine.predict_success_probability(
                context['agent_context'],
                'analyze_placeholder_sql',
                optimized_request.to_dict()
            )
            
            logger.info(f"预测成功概率: {success_probability:.2%} for {request.placeholder_id}")
            
            # 7. 执行增强的分析
            analysis_result = await self.enhanced_agent.execute_with_learning(
                session_id,
                'analyze_placeholder_sql',
                optimized_request.to_dict()
            )
            
            # 8. SQL质量评估
            if analysis_result.get('success') and analysis_result.get('generated_sql'):
                quality_report = await self.quality_assessor.assess_sql_quality(
                    analysis_result['generated_sql'],
                    context
                )
                
                # 将质量评估结果整合到分析结果中
                analysis_result.update({
                    'quality_score': quality_report.overall_score,
                    'quality_level': quality_report.overall_level.value,
                    'quality_issues': [issue.__dict__ for issue in quality_report.issues],
                    'quality_suggestions': quality_report.suggestions
                })
                
                # 如果质量太低，尝试重新生成
                if quality_report.overall_level in [QualityLevel.POOR, QualityLevel.CRITICAL]:
                    logger.warning(f"SQL质量较低 ({quality_report.overall_score:.1f}), 尝试重新生成")
                    retry_result = await self._retry_with_quality_feedback(
                        optimized_request, quality_report, context
                    )
                    if retry_result.get('success') and retry_result.get('quality_score', 0) > quality_report.overall_score:
                        analysis_result = retry_result
            
            # 9. 智能缓存存储
            if analysis_result.get('success'):
                cache_strategy = self._determine_cache_strategy(analysis_result, context)
                cache_ttl = self._calculate_cache_ttl(analysis_result, context)
                
                await self.cache_manager.set(
                    cache_key,
                    analysis_result,
                    ttl_seconds=cache_ttl,
                    strategy=cache_strategy,
                    context=context
                )
            
            # 10. 添加增强信息
            analysis_result.update({
                'source': 'enhanced_analysis',
                'cache_hit': False,
                'predicted_success_probability': success_probability,
                'applied_optimizations': len(optimization_hints),
                'analysis_time': (datetime.now() - start_time).total_seconds()
            })
            
            logger.info(f"增强分析完成: {request.placeholder_id}, 成功: {analysis_result.get('success')}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"增强分析失败: {request.placeholder_id}, 错误: {e}")
            
            # 回退到基础分析
            try:
                fallback_result = await self._fallback_analysis(request)
                fallback_result.update({
                    'source': 'fallback_analysis',
                    'enhancement_error': str(e),
                    'analysis_time': (datetime.now() - start_time).total_seconds()
                })
                return fallback_result
            except Exception as fallback_error:
                logger.error(f"回退分析也失败: {fallback_error}")
                return {
                    'success': False,
                    'error': f"增强和回退分析都失败: {str(e)}, {str(fallback_error)}",
                    'placeholder_id': request.placeholder_id,
                    'analysis_time': (datetime.now() - start_time).total_seconds()
                }
    
    async def batch_analyze_with_enhancements(self, 
                                            requests: List[PlaceholderAnalysisRequest]) -> List[Dict[str, Any]]:
        """
        批量增强分析
        
        支持并行处理和智能调度
        """
        logger.info(f"开始批量增强分析: {len(requests)} 个占位符")
        
        # 1. 预分析和优先级排序
        prioritized_requests = await self._prioritize_batch_requests(requests)
        
        # 2. 创建分析任务
        tasks = []
        for request in prioritized_requests:
            task = asyncio.create_task(
                self.analyze_placeholder_with_enhancements(request)
            )
            tasks.append(task)
        
        # 3. 并行执行（带限制）
        semaphore = asyncio.Semaphore(5)  # 最多同时执行5个任务
        
        async def controlled_analysis(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(*[controlled_analysis(task) for task in tasks], return_exceptions=True)
        
        # 4. 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'success': False,
                    'error': str(result),
                    'placeholder_id': requests[i].placeholder_id
                })
            else:
                processed_results.append(result)
        
        # 5. 批量统计和学习
        await self._batch_learning_update(requests, processed_results)
        
        logger.info(f"批量增强分析完成: 成功 {sum(1 for r in processed_results if r.get('success'))} / {len(requests)}")
        return processed_results
    
    async def get_enhancement_statistics(self) -> Dict[str, Any]:
        """获取增强功能统计信息"""
        learning_stats = self.enhanced_agent.get_learning_statistics()
        cache_stats = await self.cache_manager.get_cache_statistics()
        
        return {
            'learning_engine': learning_stats,
            'cache_manager': cache_stats,
            'quality_assessor': {
                'enabled': True,
                'dimensions': len([d for d in SQLQualityDimension])
            },
            'enhancement_status': 'active'
        }
    
    async def optimize_system(self) -> Dict[str, Any]:
        """优化整个增强系统"""
        optimization_results = {}
        
        # 1. 优化缓存
        cache_optimization = await self.cache_manager.optimize_cache()
        optimization_results['cache'] = cache_optimization
        
        # 2. 清理学习历史
        # (学习引擎会自动管理历史大小)
        optimization_results['learning'] = {'status': 'auto_managed'}
        
        # 3. 系统健康检查
        health_check = await self._system_health_check()
        optimization_results['health_check'] = health_check
        
        logger.info(f"系统优化完成: {optimization_results}")
        return optimization_results
    
    # 私有方法
    
    async def _build_analysis_context(self, 
                                    request: PlaceholderAnalysisRequest,
                                    session_id: str) -> Dict[str, Any]:
        """构建分析上下文"""
        # 获取或创建Agent上下文
        context_manager = get_context_manager()
        agent_context = context_manager.get_context(session_id)
        
        if not agent_context:
            agent_context = context_manager.create_context(
                session_id=session_id,
                task_id=request.template_id,
                user_id=self.base_agent.user_id
            )
        
        # 设置分析相关上下文
        agent_context.set_context('placeholder_id', request.placeholder_id, ContextScope.REQUEST)
        agent_context.set_context('placeholder_text', request.placeholder_text, ContextScope.REQUEST)
        agent_context.set_context('placeholder_type', request.placeholder_type, ContextScope.REQUEST)
        agent_context.set_context('data_source_id', request.data_source_id, ContextScope.REQUEST)
        
        if request.template_context:
            for key, value in request.template_context.items():
                agent_context.set_context(f'template_{key}', value, ContextScope.TASK)
        
        return {
            'agent_context': agent_context,
            'placeholder_id': request.placeholder_id,
            'placeholder_text': request.placeholder_text,
            'placeholder_type': request.placeholder_type,
            'data_source_id': request.data_source_id,
            'template_id': request.template_id
        }
    
    def _generate_cache_key(self, request: PlaceholderAnalysisRequest) -> str:
        """生成缓存键"""
        key_components = [
            'placeholder_sql',
            request.placeholder_id,
            request.placeholder_text,
            request.placeholder_type,
            request.data_source_id
        ]
        
        key_string = '|'.join(str(c) for c in key_components)
        import hashlib
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _apply_optimization_hints(self, 
                                request: PlaceholderAnalysisRequest,
                                hints: List[Dict[str, Any]]) -> PlaceholderAnalysisRequest:
        """应用优化建议到请求"""
        # 创建优化后的请求副本
        optimized_request = PlaceholderAnalysisRequest(**request.to_dict())
        
        # 应用高置信度的优化建议
        for hint in hints:
            if hint.get('confidence', 0) > 0.8:
                metadata = hint.get('metadata', {})
                suggested_params = metadata.get('suggested_parameters', {})
                
                # 应用建议的参数
                for param, value in suggested_params.items():
                    if hasattr(optimized_request, param):
                        setattr(optimized_request, param, value)
        
        return optimized_request
    
    async def _retry_with_quality_feedback(self,
                                         request: PlaceholderAnalysisRequest,
                                         quality_report,
                                         context: Dict[str, Any]) -> Dict[str, Any]:
        """基于质量反馈重试分析"""
        try:
            # 基于质量问题调整请求
            retry_request = PlaceholderAnalysisRequest(**request.to_dict())
            retry_request.force_reanalyze = True
            
            # 在上下文中添加质量反馈信息
            context['quality_feedback'] = {
                'previous_score': quality_report.overall_score,
                'main_issues': [issue.message for issue in quality_report.issues[:3]],
                'suggestions': quality_report.suggestions[:3]
            }
            
            # 重新分析
            retry_result = await self.enhanced_agent.execute_with_learning(
                context['agent_context'].session_id,
                'analyze_placeholder_sql',
                retry_request.to_dict()
            )
            
            # 再次评估质量
            if retry_result.get('success') and retry_result.get('generated_sql'):
                retry_quality = await self.quality_assessor.assess_sql_quality(
                    retry_result['generated_sql'],
                    context
                )
                
                retry_result.update({
                    'quality_score': retry_quality.overall_score,
                    'quality_level': retry_quality.overall_level.value,
                    'quality_issues': [issue.__dict__ for issue in retry_quality.issues],
                    'retry_attempt': True
                })
            
            return retry_result
            
        except Exception as e:
            logger.warning(f"质量反馈重试失败: {e}")
            return {'success': False, 'error': f'重试失败: {str(e)}'}
    
    def _determine_cache_strategy(self, 
                                result: Dict[str, Any],
                                context: Dict[str, Any]) -> CacheStrategy:
        """确定缓存策略"""
        # 根据质量分数和置信度确定缓存策略
        quality_score = result.get('quality_score', 0)
        confidence = result.get('confidence', 0)
        
        if quality_score >= 90 and confidence >= 0.9:
            return CacheStrategy.HOT_DATA
        elif quality_score >= 70 and confidence >= 0.7:
            return CacheStrategy.WARM_DATA
        elif quality_score >= 50:
            return CacheStrategy.CONTEXTUAL
        else:
            return CacheStrategy.COLD_DATA
    
    def _calculate_cache_ttl(self, 
                           result: Dict[str, Any],
                           context: Dict[str, Any]) -> int:
        """计算缓存TTL"""
        base_ttl = 1800  # 30分钟基础TTL
        
        # 根据质量分数调整TTL
        quality_score = result.get('quality_score', 0)
        if quality_score >= 90:
            return base_ttl * 4  # 2小时
        elif quality_score >= 70:
            return base_ttl * 2  # 1小时
        elif quality_score >= 50:
            return base_ttl      # 30分钟
        else:
            return base_ttl // 2 # 15分钟
    
    async def _prioritize_batch_requests(self, 
                                       requests: List[PlaceholderAnalysisRequest]) -> List[PlaceholderAnalysisRequest]:
        """批量请求优先级排序"""
        # 简化的优先级算法
        def priority_score(request):
            score = 0
            
            # 强制重新分析的优先级更高
            if request.force_reanalyze:
                score += 10
            
            # 统计类型占位符优先级较高
            if 'statistic' in request.placeholder_type.lower():
                score += 5
            
            # 根据placeholder_text长度调整（越短越简单，优先级稍高）
            if len(request.placeholder_text) < 20:
                score += 2
            
            return score
        
        return sorted(requests, key=priority_score, reverse=True)
    
    async def _batch_learning_update(self, 
                                   requests: List[PlaceholderAnalysisRequest],
                                   results: List[Dict[str, Any]]) -> None:
        """批量学习更新"""
        try:
            # 分析批量执行的模式
            success_count = sum(1 for r in results if r.get('success'))
            total_time = sum(r.get('analysis_time', 0) for r in results)
            
            batch_metadata = {
                'batch_size': len(requests),
                'success_rate': success_count / len(requests) if requests else 0,
                'avg_time_per_request': total_time / len(requests) if requests else 0,
                'batch_efficiency': success_count / total_time if total_time > 0 else 0
            }
            
            logger.info(f"批量分析统计: {batch_metadata}")
            
        except Exception as e:
            logger.warning(f"批量学习更新失败: {e}")
    
    async def _fallback_analysis(self, request: PlaceholderAnalysisRequest) -> Dict[str, Any]:
        """回退到基础分析"""
        logger.info(f"执行回退分析: {request.placeholder_id}")
        
        # 直接调用基础Agent的分析方法
        result = await self.base_agent.analyze_placeholder(
            placeholder_id=request.placeholder_id,
            placeholder_text=request.placeholder_text,
            data_source_id=request.data_source_id,
            placeholder_type=request.placeholder_type,
            template_id=request.template_id,
            force_reanalyze=request.force_reanalyze
        )
        
        return result.to_dict() if hasattr(result, 'to_dict') else result
    
    async def _system_health_check(self) -> Dict[str, Any]:
        """系统健康检查"""
        health_status = {
            'learning_engine': True,
            'cache_manager': True,
            'quality_assessor': True,
            'overall_health': 'good'
        }
        
        try:
            # 检查学习引擎
            learning_stats = self.enhanced_agent.get_learning_statistics()
            if learning_stats['total_patterns'] == 0:
                health_status['learning_engine'] = 'warming_up'
            
            # 检查缓存管理器
            cache_stats = await self.cache_manager.get_cache_statistics()
            if cache_stats['overall_hit_rate'] < 0.1:
                health_status['cache_manager'] = 'low_efficiency'
            
        except Exception as e:
            logger.warning(f"健康检查异常: {e}")
            health_status['overall_health'] = 'degraded'
        
        return health_status
    
    def _register_learning_rules(self):
        """注册学习规则"""
        def placeholder_similarity_analyzer(context: AgentContext) -> Dict[str, Any]:
            """占位符相似性分析器"""
            features = {}
            
            placeholder_text = context.get_context('placeholder_text', '')
            if placeholder_text:
                # 提取关键特征
                features['has_numbers'] = any(char.isdigit() for char in placeholder_text)
                features['has_chinese'] = any('\u4e00' <= char <= '\u9fff' for char in placeholder_text)
                features['text_length'] = len(placeholder_text)
                features['word_count'] = len(placeholder_text.split())
            
            return features
        
        self.learning_engine.register_context_analyzer(placeholder_similarity_analyzer)
        
        def pattern_matcher(pattern, context_features):
            """自定义模式匹配器"""
            # 基于文本相似性的模式匹配
            if 'placeholder_text' in context_features:
                # 简化的文本相似性检查
                return len(set(context_features['placeholder_text'].split()) & 
                          set(pattern.metadata.get('sample_text', '').split())) >= 2
            return False
        
        self.learning_engine.register_pattern_matcher(pattern_matcher)
    
    def _register_cache_rules(self):
        """注册缓存预测规则"""
        from .core.intelligent_cache import template_access_prediction_rule, user_behavior_prediction_rule
        
        self.cache_manager.register_prediction_rule(template_access_prediction_rule)
        self.cache_manager.register_prediction_rule(user_behavior_prediction_rule)
        
        # 自定义占位符预测规则
        def placeholder_type_prediction_rule(access_patterns, context_associations):
            """基于占位符类型的预测规则"""
            predictions = []
            
            # 如果访问了某种类型的占位符，预测其他同类型占位符可能被访问
            type_patterns = {}
            for context_key, cache_keys in context_associations.items():
                if 'placeholder_type:' in context_key:
                    placeholder_type = context_key.split(':', 1)[1]
                    type_patterns[placeholder_type] = cache_keys
            
            # 基于类型访问频率预测
            current_time = datetime.now()
            for ptype, cache_keys in type_patterns.items():
                recent_accesses = []
                for cache_key in cache_keys:
                    if cache_key in access_patterns:
                        recent_access_times = [
                            t for t in access_patterns[cache_key]
                            if (current_time - t).total_seconds() < 3600
                        ]
                        recent_accesses.extend(recent_access_times)
                
                # 如果某类型最近有较多访问，预测同类型其他占位符
                if len(recent_accesses) >= 3:
                    predictions.extend(cache_keys)
            
            return predictions
        
        self.cache_manager.register_prediction_rule(placeholder_type_prediction_rule)


# 便捷函数
def create_enhanced_placeholder_agent(db_session: Session,
                                    user_id: str = None,
                                    redis_client=None) -> EnhancedPlaceholderSQLAgent:
    """创建增强的占位符SQL Agent"""
    
    # 创建基础Agent
    base_agent = PlaceholderSQLAgent(db_session, user_id)
    
    # 创建增强组件
    learning_engine = create_learning_engine(db_session)
    cache_manager = create_intelligent_cache_manager(redis_client, db_session)
    quality_assessor = create_sql_quality_assessor(db_session)
    
    return EnhancedPlaceholderSQLAgent(
        base_agent, learning_engine, cache_manager, quality_assessor
    )


# 使用示例
async def example_usage():
    """使用示例"""
    from sqlalchemy.orm import sessionmaker
    
    # 假设已有数据库会话
    # db_session = SessionLocal()
    
    # 创建增强Agent
    # enhanced_agent = create_enhanced_placeholder_agent(db_session, user_id="test_user")
    
    # 创建分析请求
    request = PlaceholderAnalysisRequest(
        placeholder_id="test_placeholder_001",
        placeholder_text="统计销售总额",
        placeholder_type="statistic",
        data_source_id="datasource_001",
        template_id="template_001"
    )
    
    # 执行增强分析
    # result = await enhanced_agent.analyze_placeholder_with_enhancements(request)
    
    # 打印结果
    # print(f"分析结果: {result}")
    # print(f"质量分数: {result.get('quality_score')}")
    # print(f"缓存状态: {'命中' if result.get('cache_hit') else '未命中'}")
    # print(f"应用优化: {result.get('applied_optimizations')} 个")
    
    pass


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())