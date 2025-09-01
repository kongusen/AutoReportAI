"""
占位符分析代理

Domain层的代理服务，专注于占位符的业务逻辑分析：
1. 占位符语义分析
2. 业务规则应用
3. 占位符分类和推理
4. 领域知识匹配
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PlaceholderAnalysisAgent:
    """
    占位符分析代理
    
    Domain层的代理，负责占位符的业务逻辑分析
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        # 初始化Domain层的服务
        self._placeholder_service = None
        self._business_rule_service = None
    
    async def analyze_template_placeholders(
        self,
        template_id: str,
        data_source_ids: List[str],
        analysis_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析模板中的占位符
        
        Args:
            template_id: 模板ID
            data_source_ids: 数据源ID列表
            analysis_context: 分析上下文
            
        Returns:
            占位符分析结果
        """
        try:
            self.logger.info(f"开始Domain层占位符分析: template={template_id}")
            
            # 获取模板内容和占位符
            template_info = await self._get_template_info(template_id)
            
            # 提取占位符规格
            placeholder_specs = await self._extract_placeholder_specs(
                template_info, analysis_context
            )
            
            # 应用业务规则进行占位符分类
            classified_placeholders = await self._classify_placeholders_by_business_rules(
                placeholder_specs, analysis_context
            )
            
            # 进行语义分析
            semantic_analysis_results = await self._perform_semantic_analysis(
                classified_placeholders, data_source_ids, analysis_context
            )
            
            # 生成占位符处理建议
            processing_recommendations = await self._generate_processing_recommendations(
                semantic_analysis_results, analysis_context
            )
            
            return {
                'success': True,
                'template_id': template_id,
                'placeholder_specs': placeholder_specs,
                'classified_placeholders': classified_placeholders,
                'semantic_analysis': semantic_analysis_results,
                'processing_recommendations': processing_recommendations,
                'analysis_metadata': {
                    'analyzed_at': datetime.now().isoformat(),
                    'placeholder_count': len(placeholder_specs),
                    'data_source_count': len(data_source_ids),
                    'analysis_quality': self._assess_analysis_quality(semantic_analysis_results)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Domain层占位符分析失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'template_id': template_id,
                'analysis_failed_at': datetime.now().isoformat()
            }
    
    async def analyze_contextual_placeholders(
        self,
        content: str,
        context: Dict[str, Any],
        analysis_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        基于上下文分析占位符
        
        Args:
            content: 内容文本
            context: 上下文信息
            analysis_options: 分析选项
            
        Returns:
            上下文感知的占位符分析结果
        """
        try:
            self.logger.info("开始上下文感知占位符分析")
            
            # 从内容中提取占位符
            placeholders = await self._extract_placeholders_from_content(content)
            
            # 基于上下文进行语义增强
            context_enhanced_placeholders = await self._enhance_with_context(
                placeholders, context
            )
            
            # 应用业务规则
            rule_based_analysis = await self._apply_contextual_business_rules(
                context_enhanced_placeholders, context
            )
            
            # 生成智能建议
            intelligent_recommendations = await self._generate_intelligent_recommendations(
                rule_based_analysis, context, analysis_options
            )
            
            return {
                'success': True,
                'original_placeholders': placeholders,
                'context_enhanced_placeholders': context_enhanced_placeholders,
                'rule_based_analysis': rule_based_analysis,
                'recommendations': intelligent_recommendations,
                'context_analysis': {
                    'context_richness': self._assess_context_richness(context),
                    'business_relevance': self._assess_business_relevance(context),
                    'temporal_sensitivity': self._assess_temporal_sensitivity(context)
                }
            }
            
        except Exception as e:
            self.logger.error(f"上下文占位符分析失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'analysis_type': 'contextual_placeholder_analysis'
            }
    
    async def _get_template_info(self, template_id: str) -> Dict[str, Any]:
        """获取模板信息"""
        try:
            # 获取Domain层的模板服务
            from ..template.services.template_domain_service import get_template_domain_service
            template_service = await get_template_domain_service()
            
            return await template_service.get_template_with_metadata(template_id)
            
        except Exception as e:
            self.logger.error(f"获取模板信息失败: {e}")
            return {'template_id': template_id, 'content': '', 'metadata': {}}
    
    async def _extract_placeholder_specs(
        self, 
        template_info: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """提取占位符规格"""
        try:
            # 获取占位符解析服务
            placeholder_service = await self._get_placeholder_service()
            
            # 解析模板中的占位符
            parsing_result = await placeholder_service.parse_template_placeholders(
                template_content=template_info.get('content', ''),
                parsing_context=context
            )
            
            return parsing_result.get('placeholder_specs', [])
            
        except Exception as e:
            self.logger.error(f"占位符规格提取失败: {e}")
            return []
    
    async def _classify_placeholders_by_business_rules(
        self, 
        placeholder_specs: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """基于业务规则分类占位符"""
        try:
            # 获取业务规则服务
            business_rule_service = await self._get_business_rule_service()
            
            classified_placeholders = []
            
            for spec in placeholder_specs:
                # 应用业务规则分类
                classification = await business_rule_service.classify_placeholder(
                    placeholder_spec=spec,
                    business_context=context.get('business_context', {})
                )
                
                classified_placeholders.append({
                    **spec,
                    'business_classification': classification
                })
            
            return classified_placeholders
            
        except Exception as e:
            self.logger.error(f"占位符业务分类失败: {e}")
            return placeholder_specs  # 返回未分类的原始规格
    
    async def _perform_semantic_analysis(
        self, 
        classified_placeholders: List[Dict[str, Any]], 
        data_source_ids: List[str],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """执行语义分析"""
        try:
            # 获取语义分析服务
            placeholder_service = await self._get_placeholder_service()
            
            semantic_results = []
            
            for placeholder in classified_placeholders:
                # 对每个占位符进行语义分析
                semantic_result = await placeholder_service.analyze_placeholder_semantics(
                    placeholder_spec=placeholder,
                    data_source_ids=data_source_ids,
                    semantic_context=context
                )
                
                semantic_results.append({
                    **placeholder,
                    'semantic_analysis': semantic_result
                })
            
            return semantic_results
            
        except Exception as e:
            self.logger.error(f"语义分析失败: {e}")
            return classified_placeholders
    
    async def _generate_processing_recommendations(
        self, 
        semantic_results: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> List[str]:
        """生成处理建议"""
        recommendations = []
        
        try:
            # 分析占位符复杂度
            complex_placeholders = [
                p for p in semantic_results 
                if p.get('semantic_analysis', {}).get('complexity_score', 0) > 0.7
            ]
            
            if complex_placeholders:
                recommendations.append(f"发现 {len(complex_placeholders)} 个复杂占位符，建议人工审核")
            
            # 分析业务相关性
            low_confidence_placeholders = [
                p for p in semantic_results
                if p.get('semantic_analysis', {}).get('confidence_score', 0) < 0.6
            ]
            
            if low_confidence_placeholders:
                recommendations.append(f"有 {len(low_confidence_placeholders)} 个占位符置信度较低，建议补充上下文信息")
            
            # 基于上下文生成建议
            if context.get('business_context', {}).get('urgency') == 'high':
                recommendations.append("高优先级任务，建议优先处理核心业务占位符")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"生成处理建议失败: {e}")
            return ["建议进行标准占位符处理流程"]
    
    async def _extract_placeholders_from_content(self, content: str) -> List[Dict[str, Any]]:
        """从内容中提取占位符"""
        try:
            import re
            
            # 简单的占位符提取（可以改进）
            placeholder_pattern = r'\{\{([^}]+)\}\}'
            matches = re.findall(placeholder_pattern, content)
            
            placeholders = []
            for i, match in enumerate(matches):
                placeholders.append({
                    'id': f'placeholder_{i}',
                    'raw_text': f'{{{{{match}}}}}',
                    'content': match.strip(),
                    'position': content.find(f'{{{{{match}}}}}'),
                    'type': 'dynamic'  # 默认类型
                })
            
            return placeholders
            
        except Exception as e:
            self.logger.error(f"占位符提取失败: {e}")
            return []
    
    async def _enhance_with_context(
        self, 
        placeholders: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """基于上下文增强占位符"""
        enhanced_placeholders = []
        
        for placeholder in placeholders:
            enhanced = {**placeholder}
            
            # 基于时间上下文增强
            if 'time_context' in context:
                time_context = context['time_context']
                if any(keyword in placeholder['content'].lower() for keyword in ['日期', 'date', '时间', 'time']):
                    enhanced['temporal_relevance'] = 'high'
                    enhanced['suggested_time_range'] = {
                        'start': time_context.get('start_date'),
                        'end': time_context.get('end_date')
                    }
            
            # 基于业务上下文增强
            if 'business_context' in context:
                business_context = context['business_context']
                if business_context.get('department'):
                    enhanced['business_scope'] = business_context['department']
            
            enhanced_placeholders.append(enhanced)
        
        return enhanced_placeholders
    
    async def _apply_contextual_business_rules(
        self, 
        placeholders: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """应用上下文业务规则"""
        # 这里可以集成更复杂的业务规则引擎
        rule_applied_placeholders = []
        
        for placeholder in placeholders:
            rule_applied = {**placeholder}
            
            # 应用业务优先级规则
            if context.get('priority') == 'urgent':
                rule_applied['processing_priority'] = 'high'
            else:
                rule_applied['processing_priority'] = 'normal'
            
            # 应用质量要求规则
            quality_level = context.get('quality_requirements', {}).get('quality_level', 'standard')
            rule_applied['quality_requirements'] = quality_level
            
            rule_applied_placeholders.append(rule_applied)
        
        return rule_applied_placeholders
    
    async def _generate_intelligent_recommendations(
        self, 
        analyzed_placeholders: List[Dict[str, Any]], 
        context: Dict[str, Any],
        options: Dict[str, Any]
    ) -> List[str]:
        """生成智能建议"""
        recommendations = []
        
        # 基于占位符数量的建议
        if len(analyzed_placeholders) > 10:
            recommendations.append("占位符数量较多，建议分批处理")
        
        # 基于上下文质量的建议
        if context.get('context_richness', 0) < 0.5:
            recommendations.append("上下文信息不够丰富，建议补充更多业务背景")
        
        # 基于处理选项的建议
        if options.get('use_context') and context.get('business_context'):
            recommendations.append("已启用上下文增强，处理质量会更好")
        
        return recommendations
    
    def _assess_analysis_quality(self, semantic_results: List[Dict[str, Any]]) -> float:
        """评估分析质量"""
        if not semantic_results:
            return 0.0
        
        # 计算平均置信度
        confidence_scores = [
            result.get('semantic_analysis', {}).get('confidence_score', 0)
            for result in semantic_results
        ]
        
        return sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    
    def _assess_context_richness(self, context: Dict[str, Any]) -> float:
        """评估上下文丰富度"""
        richness_factors = [
            'time_context' in context,
            'business_context' in context,
            'document_context' in context,
            bool(context.get('user_context')),
            bool(context.get('quality_requirements'))
        ]
        
        return sum(richness_factors) / len(richness_factors)
    
    def _assess_business_relevance(self, context: Dict[str, Any]) -> float:
        """评估业务相关性"""
        business_context = context.get('business_context', {})
        relevance_score = 0.0
        
        if business_context.get('department'):
            relevance_score += 0.3
        if business_context.get('task_type'):
            relevance_score += 0.3
        if business_context.get('target_audience'):
            relevance_score += 0.2
        if business_context.get('organizational_context'):
            relevance_score += 0.2
        
        return min(1.0, relevance_score)
    
    def _assess_temporal_sensitivity(self, context: Dict[str, Any]) -> float:
        """评估时间敏感性"""
        time_context = context.get('time_context', {})
        
        if not time_context:
            return 0.0
        
        sensitivity_score = 0.0
        
        # 报告周期越短，敏感性越高
        period_type = time_context.get('period_type', '')
        if period_type in ['real_time', 'hourly']:
            sensitivity_score = 0.9
        elif period_type in ['daily']:
            sensitivity_score = 0.7
        elif period_type in ['weekly']:
            sensitivity_score = 0.5
        elif period_type in ['monthly']:
            sensitivity_score = 0.3
        else:
            sensitivity_score = 0.1
        
        return sensitivity_score
    
    async def _get_placeholder_service(self):
        """获取占位符服务实例"""
        if self._placeholder_service is None:
            from ..placeholder import get_intelligent_placeholder_service
            self._placeholder_service = await get_intelligent_placeholder_service()
        return self._placeholder_service
    
    async def _get_business_rule_service(self):
        """获取业务规则服务实例"""
        if self._business_rule_service is None:
            from .business_rule_agent import BusinessRuleAgent
            self._business_rule_service = BusinessRuleAgent()
        return self._business_rule_service