"""
上下文分析引擎

整合多层次上下文分析的核心引擎
"""

import logging
from typing import Dict, List, Optional, Any
from ..models import (
    PlaceholderSpec, DocumentContext, BusinessContext, TimeContext,
    ContextAnalysisResult, ContextAnalyzerInterface
)
from .paragraph_analyzer import ParagraphAnalyzer
from .section_analyzer import SectionAnalyzer
from .document_analyzer import DocumentAnalyzer
from .business_rule_analyzer import BusinessRuleAnalyzer

logger = logging.getLogger(__name__)


class ContextAnalysisEngine(ContextAnalyzerInterface):
    """上下文分析引擎"""
    
    def __init__(self):
        # 初始化各层级分析器
        self.paragraph_analyzer = ParagraphAnalyzer()
        self.section_analyzer = SectionAnalyzer()
        self.document_analyzer = DocumentAnalyzer()
        self.business_rule_analyzer = BusinessRuleAnalyzer()
        
        # 分析器权重配置
        self.analyzer_weights = {
            'paragraph': 0.4,
            'section': 0.3,
            'document': 0.2,
            'business': 0.1
        }
        
        # 上下文融合策略
        self.fusion_strategy = 'weighted_average'
        
        # 分析缓存
        self.analysis_cache: Dict[str, ContextAnalysisResult] = {}
        self.cache_size_limit = 1000
        
        # 初始化状态
        self.initialized = False
    
    async def initialize(self):
        """初始化上下文分析引擎"""
        if self.initialized:
            return
        
        try:
            # 初始化各层级分析器
            if hasattr(self.paragraph_analyzer, 'initialize'):
                await self.paragraph_analyzer.initialize()
            if hasattr(self.section_analyzer, 'initialize'):
                await self.section_analyzer.initialize()
            if hasattr(self.document_analyzer, 'initialize'):
                await self.document_analyzer.initialize()
            if hasattr(self.business_rule_analyzer, 'initialize'):
                await self.business_rule_analyzer.initialize()
            
            self.initialized = True
            logger.info("上下文分析引擎初始化完成")
            
        except Exception as e:
            logger.error(f"上下文分析引擎初始化失败: {e}")
            raise
    
    async def analyze(
        self,
        placeholder: PlaceholderSpec,
        document_context: DocumentContext,
        business_context: BusinessContext,
        time_context: TimeContext
    ) -> ContextAnalysisResult:
        """执行全面的上下文分析"""
        try:
            # 检查缓存
            cache_key = self._generate_cache_key(
                placeholder, document_context, business_context, time_context
            )
            
            if cache_key in self.analysis_cache:
                logger.debug("使用缓存的上下文分析结果")
                return self.analysis_cache[cache_key]
            
            # 记录分析开始时间
            import time
            start_time = time.time()
            
            # 1. 段落级别分析
            paragraph_analysis = await self.paragraph_analyzer.analyze_paragraph(
                placeholder, document_context
            )
            
            # 2. 章节级别分析
            section_analysis = await self.section_analyzer.analyze_section(
                placeholder, document_context, paragraph_analysis
            )
            
            # 3. 文档级别分析
            document_analysis = await self.document_analyzer.analyze_document(
                placeholder, document_context, business_context, time_context
            )
            
            # 4. 业务规则分析
            business_analysis = await self.business_rule_analyzer.analyze_business_rules(
                placeholder, business_context, time_context
            )
            
            # 5. 集成分析结果
            integrated_context = await self._integrate_analysis_results(
                paragraph_analysis,
                section_analysis, 
                document_analysis,
                business_analysis,
                placeholder
            )
            
            # 6. 计算综合置信度
            confidence_score = self._calculate_overall_confidence(
                paragraph_analysis,
                section_analysis,
                document_analysis, 
                business_analysis
            )
            
            # 计算处理时间
            processing_time = int((time.time() - start_time) * 1000)
            
            # 构建分析结果
            result = ContextAnalysisResult(
                paragraph_analysis=paragraph_analysis,
                section_analysis=section_analysis,
                document_analysis=document_analysis,
                business_analysis=business_analysis,
                integrated_context=integrated_context,
                confidence_score=confidence_score,
                processing_time_ms=processing_time
            )
            
            # 缓存结果
            self._cache_result(cache_key, result)
            
            logger.info(f"上下文分析完成，置信度: {confidence_score:.3f}, 用时: {processing_time}ms")
            return result
            
        except Exception as e:
            logger.error(f"上下文分析失败: {e}")
            return self._create_fallback_result()
    
    async def _integrate_analysis_results(
        self,
        paragraph_analysis: Dict[str, Any],
        section_analysis: Dict[str, Any],
        document_analysis: Dict[str, Any],
        business_analysis: Dict[str, Any],
        placeholder: PlaceholderSpec
    ) -> Dict[str, Any]:
        """集成多层次分析结果"""
        
        # 提取关键信息
        integrated_context = {
            'placeholder_type': placeholder.statistical_type.value,
            'description': placeholder.description,
            'confidence_score': placeholder.confidence_score
        }
        
        # 时间维度集成
        time_info = self._extract_time_dimension(
            paragraph_analysis, section_analysis, document_analysis, business_analysis
        )
        integrated_context['time_dimension'] = time_info
        
        # 业务维度集成
        business_info = self._extract_business_dimension(
            paragraph_analysis, section_analysis, document_analysis, business_analysis
        )
        integrated_context['business_dimension'] = business_info
        
        # 数据维度集成
        data_info = self._extract_data_dimension(
            paragraph_analysis, section_analysis, document_analysis
        )
        integrated_context['data_dimension'] = data_info
        
        # 语义信息集成
        semantic_info = self._extract_semantic_dimension(
            paragraph_analysis, section_analysis, document_analysis
        )
        integrated_context['semantic_dimension'] = semantic_info
        
        # 约束条件集成
        constraints = self._extract_constraints(
            paragraph_analysis, section_analysis, business_analysis
        )
        integrated_context['constraints'] = constraints
        
        # 优化建议集成
        optimization_hints = self._generate_optimization_hints(
            paragraph_analysis, section_analysis, document_analysis, business_analysis
        )
        integrated_context['optimization_hints'] = optimization_hints
        
        return integrated_context
    
    def _extract_time_dimension(
        self,
        paragraph_analysis: Dict[str, Any],
        section_analysis: Dict[str, Any], 
        document_analysis: Dict[str, Any],
        business_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """提取时间维度信息"""
        time_dimension = {}
        
        # 从各层级分析中提取时间相关信息
        sources = [paragraph_analysis, section_analysis, document_analysis, business_analysis]
        
        for source in sources:
            if 'time_period' in source:
                time_dimension['detected_periods'] = source.get('time_period', [])
            if 'time_granularity' in source:
                time_dimension['granularity'] = source.get('time_granularity')
            if 'temporal_context' in source:
                time_dimension['context'] = source.get('temporal_context')
        
        # 时间维度置信度
        time_dimension['confidence'] = self._calculate_dimension_confidence(
            sources, ['time_period', 'time_granularity', 'temporal_context']
        )
        
        return time_dimension
    
    def _extract_business_dimension(
        self,
        paragraph_analysis: Dict[str, Any],
        section_analysis: Dict[str, Any],
        document_analysis: Dict[str, Any], 
        business_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """提取业务维度信息"""
        business_dimension = {}
        
        # 业务领域
        if 'business_domain' in business_analysis:
            business_dimension['domain'] = business_analysis['business_domain']
        
        # 业务实体
        entities = []
        for source in [paragraph_analysis, section_analysis, document_analysis]:
            if 'business_entities' in source:
                entities.extend(source['business_entities'])
        
        business_dimension['entities'] = list(set(entities))  # 去重
        
        # 业务规则
        if 'applicable_rules' in business_analysis:
            business_dimension['rules'] = business_analysis['applicable_rules']
        
        # 业务上下文
        if 'business_context' in document_analysis:
            business_dimension['context'] = document_analysis['business_context']
        
        return business_dimension
    
    def _extract_data_dimension(
        self,
        paragraph_analysis: Dict[str, Any],
        section_analysis: Dict[str, Any],
        document_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """提取数据维度信息"""
        data_dimension = {}
        
        # 数据源信息
        if 'data_sources' in document_analysis:
            data_dimension['sources'] = document_analysis['data_sources']
        
        # 数据字段
        fields = []
        for source in [paragraph_analysis, section_analysis, document_analysis]:
            if 'mentioned_fields' in source:
                fields.extend(source['mentioned_fields'])
        
        data_dimension['fields'] = list(set(fields))
        
        # 数据质量要求
        if 'data_quality' in section_analysis:
            data_dimension['quality_requirements'] = section_analysis['data_quality']
        
        return data_dimension
    
    def _extract_semantic_dimension(
        self,
        paragraph_analysis: Dict[str, Any],
        section_analysis: Dict[str, Any],
        document_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """提取语义维度信息"""
        semantic_dimension = {}
        
        # 关键词和概念
        keywords = []
        concepts = []
        
        for source in [paragraph_analysis, section_analysis, document_analysis]:
            if 'keywords' in source:
                keywords.extend(source['keywords'])
            if 'concepts' in source:
                concepts.extend(source['concepts'])
        
        semantic_dimension['keywords'] = list(set(keywords))
        semantic_dimension['concepts'] = list(set(concepts))
        
        # 语义关系
        if 'semantic_relations' in document_analysis:
            semantic_dimension['relations'] = document_analysis['semantic_relations']
        
        return semantic_dimension
    
    def _extract_constraints(
        self,
        paragraph_analysis: Dict[str, Any],
        section_analysis: Dict[str, Any],
        business_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """提取约束条件"""
        constraints = {
            'data_constraints': [],
            'business_constraints': [],
            'temporal_constraints': [],
            'quality_constraints': []
        }
        
        # 数据约束
        for source in [paragraph_analysis, section_analysis]:
            if 'data_constraints' in source:
                constraints['data_constraints'].extend(source['data_constraints'])
        
        # 业务约束
        if 'constraints' in business_analysis:
            constraints['business_constraints'] = business_analysis['constraints']
        
        # 去重
        for key in constraints:
            constraints[key] = list(set(constraints[key]))
        
        return constraints
    
    def _generate_optimization_hints(
        self,
        paragraph_analysis: Dict[str, Any],
        section_analysis: Dict[str, Any],
        document_analysis: Dict[str, Any],
        business_analysis: Dict[str, Any]
    ) -> List[str]:
        """生成优化建议"""
        hints = []
        
        # 基于段落分析的建议
        if paragraph_analysis.get('clarity_score', 1.0) < 0.7:
            hints.append("建议明确占位符的具体需求描述")
        
        # 基于章节分析的建议
        if section_analysis.get('context_completeness', 1.0) < 0.8:
            hints.append("建议补充更多上下文信息")
        
        # 基于文档分析的建议
        if 'missing_metadata' in document_analysis:
            hints.append(f"建议补充缺失的元数据: {', '.join(document_analysis['missing_metadata'])}")
        
        # 基于业务规则的建议
        if business_analysis.get('rule_compliance', 1.0) < 0.9:
            hints.append("建议检查业务规则合规性")
        
        return hints
    
    def _calculate_dimension_confidence(
        self,
        sources: List[Dict[str, Any]],
        dimension_keys: List[str]
    ) -> float:
        """计算维度置信度"""
        total_confidence = 0.0
        valid_sources = 0
        
        for source in sources:
            source_confidence = 0.0
            found_keys = 0
            
            for key in dimension_keys:
                if key in source:
                    found_keys += 1
                    if isinstance(source[key], dict) and 'confidence' in source[key]:
                        source_confidence += source[key]['confidence']
                    else:
                        source_confidence += 0.8  # 默认置信度
            
            if found_keys > 0:
                total_confidence += source_confidence / found_keys
                valid_sources += 1
        
        return total_confidence / valid_sources if valid_sources > 0 else 0.5
    
    def _calculate_overall_confidence(
        self,
        paragraph_analysis: Dict[str, Any],
        section_analysis: Dict[str, Any],
        document_analysis: Dict[str, Any],
        business_analysis: Dict[str, Any]
    ) -> float:
        """计算综合置信度"""
        # 各层级置信度
        confidences = {
            'paragraph': paragraph_analysis.get('confidence', 0.5),
            'section': section_analysis.get('confidence', 0.5),
            'document': document_analysis.get('confidence', 0.5),
            'business': business_analysis.get('confidence', 0.5)
        }
        
        # 加权平均
        weighted_confidence = sum(
            self.analyzer_weights[level] * confidence
            for level, confidence in confidences.items()
        )
        
        return min(weighted_confidence, 1.0)
    
    def _generate_cache_key(
        self,
        placeholder: PlaceholderSpec,
        document_context: DocumentContext,
        business_context: BusinessContext,
        time_context: TimeContext
    ) -> str:
        """生成缓存键"""
        key_components = [
            placeholder.get_hash(),
            document_context.get_hash(),
            business_context.get_hash(),
            time_context.get_hash()
        ]
        
        import hashlib
        combined_key = "|".join(key_components)
        return hashlib.md5(combined_key.encode()).hexdigest()
    
    def _cache_result(self, cache_key: str, result: ContextAnalysisResult):
        """缓存分析结果"""
        # 检查缓存大小限制
        if len(self.analysis_cache) >= self.cache_size_limit:
            # 移除最旧的缓存项（简单的FIFO策略）
            oldest_key = next(iter(self.analysis_cache))
            del self.analysis_cache[oldest_key]
        
        self.analysis_cache[cache_key] = result
    
    def _create_fallback_result(self) -> ContextAnalysisResult:
        """创建回退的分析结果"""
        return ContextAnalysisResult(
            paragraph_analysis={'confidence': 0.3, 'error': 'Analysis failed'},
            section_analysis={'confidence': 0.3, 'error': 'Analysis failed'},
            document_analysis={'confidence': 0.3, 'error': 'Analysis failed'},
            business_analysis={'confidence': 0.3, 'error': 'Analysis failed'},
            integrated_context={'error': 'Integration failed'},
            confidence_score=0.3,
            processing_time_ms=0
        )
    
    def clear_cache(self):
        """清空缓存"""
        self.analysis_cache.clear()
        logger.info("上下文分析缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            'cache_size': len(self.analysis_cache),
            'cache_limit': self.cache_size_limit,
            'cache_hit_rate': getattr(self, '_cache_hit_count', 0) / getattr(self, '_total_requests', 1)
        }
    
    def configure_weights(self, new_weights: Dict[str, float]):
        """配置分析器权重"""
        # 验证权重合法性
        total_weight = sum(new_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError("权重总和必须等于1.0")
        
        self.analyzer_weights.update(new_weights)
        logger.info(f"分析器权重已更新: {self.analyzer_weights}")