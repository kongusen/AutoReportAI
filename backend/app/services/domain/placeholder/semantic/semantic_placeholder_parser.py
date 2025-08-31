"""
语义占位符解析器

结合语义理解能力的高级占位符解析器
"""

import logging
from typing import Dict, List, Optional, Any
from ..models import (
    PlaceholderSpec, ParameterizedPlaceholder, StatisticalType, SyntaxType,
    PlaceholderSyntaxError, PlaceholderParserInterface, DocumentContext
)
from .intent_classifier import IntentClassifier
from .semantic_analyzer import SemanticAnalyzer
from .implicit_parameter_inferencer import ImplicitParameterInferencer

logger = logging.getLogger(__name__)


class SemanticPlaceholderParser(PlaceholderParserInterface):
    """语义增强占位符解析器"""
    
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.semantic_analyzer = SemanticAnalyzer()
        self.parameter_inferencer = ImplicitParameterInferencer()
        
        # 语义匹配置信度阈值
        self.confidence_threshold = 0.7
        
        # 语义模式库
        self.semantic_patterns = {
            # 销售相关语义
            'sales': {
                'keywords': ['销售', '营收', '收入', '业绩', '成交'],
                'default_type': StatisticalType.STATISTICS,
                'common_params': ['时间范围', '地区', '产品线']
            },
            # 趋势分析语义
            'trend': {
                'keywords': ['增长', '下降', '趋势', '变化', '发展'],
                'default_type': StatisticalType.TREND,
                'common_params': ['时间粒度', '对比期']
            },
            # 排名排行语义
            'ranking': {
                'keywords': ['排名', '排行', '第一', '最好', '最差', 'TOP'],
                'default_type': StatisticalType.LIST,
                'common_params': ['数量', '排序']
            },
            # 对比分析语义
            'comparison': {
                'keywords': ['对比', '比较', '差异', '相比', '环比', '同比'],
                'default_type': StatisticalType.COMPARISON,
                'common_params': ['对比期', '基准']
            }
        }
    
    async def parse(self, placeholder_text: str, context: Optional[DocumentContext] = None) -> PlaceholderSpec:
        """语义增强的占位符解析"""
        try:
            # 1. 基础语法解析
            basic_spec = await self._basic_parse(placeholder_text)
            
            # 2. 意图分类
            intent_info = await self.intent_classifier.classify_intent(
                placeholder_text, context
            )
            
            # 3. 语义分析
            semantic_info = await self.semantic_analyzer.analyze_semantics(
                placeholder_text, context, intent_info
            )
            
            # 4. 隐式参数推断
            inferred_params = await self.parameter_inferencer.infer_parameters(
                basic_spec, semantic_info, context
            )
            
            # 5. 构建增强的占位符规格
            enhanced_spec = await self._build_enhanced_spec(
                basic_spec, intent_info, semantic_info, inferred_params
            )
            
            logger.debug(f"语义解析完成: {placeholder_text} -> {enhanced_spec.statistical_type.value}")
            return enhanced_spec
            
        except Exception as e:
            logger.error(f"语义占位符解析失败: {placeholder_text}, 错误: {e}")
            raise PlaceholderSyntaxError(f"Semantic parsing failed: {placeholder_text}") from e
    
    def supports_syntax(self, syntax_type: SyntaxType) -> bool:
        """支持所有语法类型的语义增强"""
        return True
    
    async def _basic_parse(self, placeholder_text: str) -> PlaceholderSpec:
        """基础语法解析"""
        # 使用基础解析器进行初步解析
        from ..parsers.placeholder_parser import PlaceholderParser
        basic_parser = PlaceholderParser()
        return await basic_parser.parse(placeholder_text)
    
    async def _build_enhanced_spec(
        self,
        basic_spec: PlaceholderSpec,
        intent_info: Dict[str, Any],
        semantic_info: Dict[str, Any],
        inferred_params: Dict[str, str]
    ) -> PlaceholderSpec:
        """构建语义增强的占位符规格"""
        
        # 决定最终的统计类型
        final_stat_type = self._determine_statistical_type(
            basic_spec.statistical_type,
            intent_info,
            semantic_info
        )
        
        # 合并参数
        if isinstance(basic_spec, ParameterizedPlaceholder):
            final_params = basic_spec.parameters.copy()
        else:
            final_params = {}
        
        final_params.update(inferred_params)
        
        # 计算语义置信度
        semantic_confidence = self._calculate_semantic_confidence(
            intent_info, semantic_info, inferred_params
        )
        
        # 创建增强的占位符规格
        if final_params or inferred_params:
            # 创建参数化占位符
            enhanced_spec = ParameterizedPlaceholder(
                statistical_type=final_stat_type,
                description=self._enhance_description(
                    basic_spec.description, semantic_info
                ),
                raw_text=basic_spec.raw_text,
                syntax_type=SyntaxType.PARAMETERIZED,
                parameters=final_params,
                confidence_score=min(
                    basic_spec.confidence_score * 0.7 + semantic_confidence * 0.3,
                    1.0
                )
            )
        else:
            # 保持基础占位符
            enhanced_spec = PlaceholderSpec(
                statistical_type=final_stat_type,
                description=self._enhance_description(
                    basic_spec.description, semantic_info
                ),
                raw_text=basic_spec.raw_text,
                syntax_type=basic_spec.syntax_type,
                confidence_score=min(
                    basic_spec.confidence_score * 0.8 + semantic_confidence * 0.2,
                    1.0
                )
            )
        
        # 添加语义元数据
        enhanced_spec.semantic_metadata = {
            'intent': intent_info,
            'semantic_analysis': semantic_info,
            'inferred_parameters': inferred_params
        }
        
        return enhanced_spec
    
    def _determine_statistical_type(
        self,
        basic_type: StatisticalType,
        intent_info: Dict[str, Any],
        semantic_info: Dict[str, Any]
    ) -> StatisticalType:
        """基于语义信息确定最终的统计类型"""
        
        # 获取语义建议的类型
        semantic_type = semantic_info.get('suggested_type')
        intent_type = intent_info.get('statistical_type')
        
        # 优先级：语义分析 > 意图分类 > 基础解析
        if semantic_type and semantic_info.get('confidence', 0) > self.confidence_threshold:
            return semantic_type
        elif intent_type and intent_info.get('confidence', 0) > self.confidence_threshold:
            return intent_type
        else:
            return basic_type
    
    def _enhance_description(self, original_description: str, semantic_info: Dict[str, Any]) -> str:
        """增强描述信息"""
        enhanced_parts = [original_description]
        
        # 添加语义理解的详细信息
        if 'business_domain' in semantic_info:
            enhanced_parts.append(f"[{semantic_info['business_domain']}]")
        
        if 'time_dimension' in semantic_info:
            enhanced_parts.append(f"[时间维度: {semantic_info['time_dimension']}]")
        
        if 'data_granularity' in semantic_info:
            enhanced_parts.append(f"[粒度: {semantic_info['data_granularity']}]")
        
        return " ".join(enhanced_parts)
    
    def _calculate_semantic_confidence(
        self,
        intent_info: Dict[str, Any],
        semantic_info: Dict[str, Any],
        inferred_params: Dict[str, str]
    ) -> float:
        """计算语义分析的置信度"""
        confidence_factors = []
        
        # 意图分类置信度
        if 'confidence' in intent_info:
            confidence_factors.append(intent_info['confidence'])
        
        # 语义分析置信度
        if 'confidence' in semantic_info:
            confidence_factors.append(semantic_info['confidence'])
        
        # 参数推断置信度
        param_confidence = len(inferred_params) * 0.1  # 每个推断参数增加0.1
        confidence_factors.append(min(param_confidence, 0.5))
        
        # 综合置信度
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.5
    
    async def parse_with_context(
        self,
        placeholder_text: str,
        document_context: DocumentContext
    ) -> PlaceholderSpec:
        """带上下文的语义解析"""
        return await self.parse(placeholder_text, document_context)
    
    def get_semantic_suggestions(self, partial_text: str) -> List[str]:
        """获取语义建议"""
        suggestions = []
        
        # 基于语义模式生成建议
        for domain, pattern_info in self.semantic_patterns.items():
            for keyword in pattern_info['keywords']:
                if keyword in partial_text.lower():
                    # 生成该领域的建议
                    stat_type = pattern_info['default_type'].value
                    for param in pattern_info['common_params']:
                        suggestion = f"{{{{{stat_type}：{partial_text}|{param}=值}}}}"
                        suggestions.append(suggestion)
                    break
        
        return suggestions
    
    def explain_semantic_analysis(self, placeholder_spec: PlaceholderSpec) -> Dict[str, Any]:
        """解释语义分析结果"""
        if not hasattr(placeholder_spec, 'semantic_metadata'):
            return {"message": "无语义分析数据"}
        
        metadata = placeholder_spec.semantic_metadata
        
        explanation = {
            "intent_analysis": {
                "detected_intent": metadata['intent'].get('intent_type'),
                "confidence": metadata['intent'].get('confidence'),
                "reasoning": metadata['intent'].get('reasoning', '')
            },
            "semantic_analysis": {
                "business_domain": metadata['semantic_analysis'].get('business_domain'),
                "suggested_type": metadata['semantic_analysis'].get('suggested_type'),
                "key_entities": metadata['semantic_analysis'].get('entities', [])
            },
            "inferred_parameters": metadata['inferred_parameters'],
            "enhancement_summary": f"通过语义分析，占位符从 {placeholder_spec.syntax_type.value} 增强为包含 {len(metadata['inferred_parameters'])} 个推断参数的高级占位符"
        }
        
        return explanation