"""
上下文分析器服务

负责分析和增强上下文信息，为AI工具提供智能上下文分析能力
"""

import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """上下文类型"""
    USER_QUERY = "user_query"           # 用户查询上下文
    DATA_SOURCE = "data_source"         # 数据源上下文  
    TEMPLATE = "template"               # 模板上下文
    BUSINESS = "business"               # 业务上下文
    TEMPORAL = "temporal"               # 时间上下文
    SYSTEM = "system"                   # 系统上下文


class AnalysisDepth(Enum):
    """分析深度"""
    SHALLOW = "shallow"                 # 浅层分析
    STANDARD = "standard"               # 标准分析
    DEEP = "deep"                       # 深度分析
    COMPREHENSIVE = "comprehensive"     # 全面分析


@dataclass
class ContextInsight:
    """上下文洞察"""
    type: str
    message: str
    confidence: float
    importance: str  # high, medium, low
    actionable: bool = False
    recommendations: List[str] = None


@dataclass
class ContextAnalysisResult:
    """上下文分析结果"""
    enhanced_context: Dict[str, Any]
    insights: List[ContextInsight]
    confidence_improvement: float
    analysis_complete: bool
    metadata: Dict[str, Any]


class ContextAnalyzerService:
    """上下文分析器服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 关键词字典用于分析
        self.keywords_dict = {
            'statistical': ['统计', '总数', '平均', '最大', '最小', '求和', 'count', 'sum', 'avg', 'max', 'min'],
            'temporal': ['今天', '昨天', '本月', '上月', '今年', '去年', '时间', 'time', 'date', '时段'],
            'business': ['销售', '收入', '利润', '成本', '客户', '产品', '订单', 'sales', 'revenue', 'profit'],
            'comparison': ['对比', '比较', '增长', '下降', '变化', 'compare', 'growth', 'change', 'vs'],
            'visualization': ['图表', '图', '展示', '可视化', 'chart', 'graph', 'visual', 'display']
        }
        
        # 数据质量评估标准
        self.quality_metrics = {
            'completeness': ['完整性', '缺失值', '空值'],
            'accuracy': ['准确性', '错误', '异常'],
            'consistency': ['一致性', '冲突', '矛盾'],
            'timeliness': ['时效性', '过期', '最新']
        }
    
    def analyze_context(
        self, 
        context_data: Dict[str, Any], 
        requirements: Dict = None
    ) -> Dict[str, Any]:
        """
        分析上下文数据
        
        Args:
            context_data: 上下文数据
            requirements: 分析需求配置
            
        Returns:
            分析结果字典
        """
        try:
            self.logger.info(f"开始上下文分析，数据键数: {len(context_data) if isinstance(context_data, dict) else 0}")
            
            # 确定分析深度
            analysis_depth = self._determine_analysis_depth(requirements)
            
            # 识别上下文类型
            context_types = self._identify_context_types(context_data)
            
            # 执行核心分析
            enhanced_context = self._enhance_context(context_data, context_types)
            
            # 生成洞察
            insights = self._generate_insights(context_data, enhanced_context, context_types)
            
            # 计算置信度提升
            confidence_improvement = self._calculate_confidence_improvement(
                context_data, insights, analysis_depth
            )
            
            # 构建结果
            result = {
                "enhanced_context": enhanced_context,
                "insights": [
                    {
                        "type": insight.type,
                        "message": insight.message,
                        "confidence": insight.confidence,
                        "importance": insight.importance,
                        "actionable": insight.actionable,
                        "recommendations": insight.recommendations or []
                    } for insight in insights
                ],
                "confidence_improvement": confidence_improvement,
                "analysis_complete": True,
                "metadata": {
                    "analysis_depth": analysis_depth.value,
                    "context_types": [ct.value for ct in context_types],
                    "analysis_timestamp": datetime.now().isoformat(),
                    "insights_count": len(insights),
                    "enhancement_applied": len(enhanced_context) > len(context_data)
                }
            }
            
            self.logger.info(
                f"上下文分析完成: 类型={len(context_types)}, 洞察={len(insights)}, "
                f"置信度提升={confidence_improvement:.2f}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"上下文分析失败: {e}")
            raise ValueError(f"上下文分析失败: {str(e)}")
    
    def _determine_analysis_depth(self, requirements: Dict = None) -> AnalysisDepth:
        """确定分析深度"""
        if not requirements:
            return AnalysisDepth.STANDARD
        
        depth_str = requirements.get("analysis_depth", "standard").lower()
        for depth in AnalysisDepth:
            if depth.value == depth_str:
                return depth
        
        return AnalysisDepth.STANDARD
    
    def _identify_context_types(self, context_data: Dict[str, Any]) -> List[ContextType]:
        """识别上下文类型"""
        identified_types = []
        context_str = json.dumps(context_data, ensure_ascii=False).lower()
        
        # 检查用户查询特征
        query_indicators = ['query', 'question', 'request', '请求', '问题', '查询']
        if any(indicator in context_str for indicator in query_indicators):
            identified_types.append(ContextType.USER_QUERY)
        
        # 检查数据源特征
        data_indicators = ['data_source', 'database', 'table', 'sql', '数据源', '数据库', '表']
        if any(indicator in context_str for indicator in data_indicators):
            identified_types.append(ContextType.DATA_SOURCE)
        
        # 检查模板特征
        template_indicators = ['template', 'placeholder', '模板', '占位符', '{{', '}}']
        if any(indicator in context_str for indicator in template_indicators):
            identified_types.append(ContextType.TEMPLATE)
        
        # 检查业务特征
        business_keywords = self.keywords_dict['business']
        if any(keyword in context_str for keyword in business_keywords):
            identified_types.append(ContextType.BUSINESS)
        
        # 检查时间特征
        temporal_keywords = self.keywords_dict['temporal']
        if any(keyword in context_str for keyword in temporal_keywords):
            identified_types.append(ContextType.TEMPORAL)
        
        # 默认至少有系统上下文
        if not identified_types:
            identified_types.append(ContextType.SYSTEM)
        
        return identified_types
    
    def _enhance_context(
        self, 
        context_data: Dict[str, Any], 
        context_types: List[ContextType]
    ) -> Dict[str, Any]:
        """增强上下文数据"""
        enhanced = context_data.copy()
        
        # 添加基础增强信息
        enhanced.update({
            "analysis_metadata": {
                "analyzed_at": datetime.now().isoformat(),
                "context_types": [ct.value for ct in context_types],
                "original_size": len(str(context_data)),
                "complexity_score": self._calculate_complexity_score(context_data)
            }
        })
        
        # 基于上下文类型进行特定增强
        for context_type in context_types:
            if context_type == ContextType.USER_QUERY:
                enhanced = self._enhance_user_query_context(enhanced)
            elif context_type == ContextType.DATA_SOURCE:
                enhanced = self._enhance_data_source_context(enhanced)
            elif context_type == ContextType.TEMPLATE:
                enhanced = self._enhance_template_context(enhanced)
            elif context_type == ContextType.BUSINESS:
                enhanced = self._enhance_business_context(enhanced)
            elif context_type == ContextType.TEMPORAL:
                enhanced = self._enhance_temporal_context(enhanced)
        
        return enhanced
    
    def _enhance_user_query_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """增强用户查询上下文"""
        enhanced = context.copy()
        
        # 分析查询意图
        query_text = str(context).lower()
        intent_analysis = {
            "statistical_intent": any(kw in query_text for kw in self.keywords_dict['statistical']),
            "temporal_intent": any(kw in query_text for kw in self.keywords_dict['temporal']),
            "comparison_intent": any(kw in query_text for kw in self.keywords_dict['comparison']),
            "visualization_intent": any(kw in query_text for kw in self.keywords_dict['visualization'])
        }
        
        enhanced["query_analysis"] = {
            "intent_analysis": intent_analysis,
            "complexity_level": "high" if sum(intent_analysis.values()) > 2 else "medium",
            "requires_data": any(intent_analysis.values())
        }
        
        return enhanced
    
    def _enhance_data_source_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """增强数据源上下文"""
        enhanced = context.copy()
        
        # 分析数据源特征
        enhanced["data_source_analysis"] = {
            "estimated_complexity": "medium",
            "query_optimization_needed": True,
            "indexing_recommendations": ["建议为常用查询字段添加索引"],
            "performance_considerations": ["考虑数据量大小", "考虑查询复杂度"]
        }
        
        return enhanced
    
    def _enhance_template_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """增强模板上下文"""
        enhanced = context.copy()
        
        # 分析模板特征
        enhanced["template_analysis"] = {
            "placeholder_complexity": "standard",
            "dynamic_content_ratio": 0.3,  # 估算动态内容比例
            "processing_recommendations": ["建议缓存静态部分", "优化占位符解析"]
        }
        
        return enhanced
    
    def _enhance_business_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """增强业务上下文"""
        enhanced = context.copy()
        
        # 添加业务分析
        enhanced["business_analysis"] = {
            "domain": "general_business",
            "key_metrics_identified": True,
            "business_rules_applicable": True,
            "compliance_considerations": ["数据隐私", "业务规则一致性"]
        }
        
        return enhanced
    
    def _enhance_temporal_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """增强时间上下文"""
        enhanced = context.copy()
        
        # 添加时间分析
        enhanced["temporal_analysis"] = {
            "time_sensitivity": "medium",
            "period_analysis": "需要确定具体时间范围",
            "timezone_considerations": "建议明确时区",
            "refresh_frequency": "建议定期更新"
        }
        
        return enhanced
    
    def _generate_insights(
        self, 
        original_context: Dict[str, Any],
        enhanced_context: Dict[str, Any],
        context_types: List[ContextType]
    ) -> List[ContextInsight]:
        """生成上下文洞察"""
        insights = []
        
        # 基础洞察
        insights.append(ContextInsight(
            type="analysis_completion",
            message=f"上下文分析完成，识别出{len(context_types)}种上下文类型",
            confidence=0.9,
            importance="high",
            actionable=False
        ))
        
        # 复杂度洞察
        complexity = self._calculate_complexity_score(original_context)
        if complexity > 0.7:
            insights.append(ContextInsight(
                type="complexity_warning",
                message="检测到高复杂度上下文，建议分步处理",
                confidence=0.8,
                importance="medium",
                actionable=True,
                recommendations=["考虑拆分复杂查询", "使用缓存优化性能"]
            ))
        
        # 数据质量洞察
        if ContextType.DATA_SOURCE in context_types:
            insights.append(ContextInsight(
                type="data_quality",
                message="建议进行数据质量检查",
                confidence=0.7,
                importance="medium", 
                actionable=True,
                recommendations=["验证数据完整性", "检查数据一致性"]
            ))
        
        # 优化建议洞察
        if len(enhanced_context) > len(original_context) * 1.5:
            insights.append(ContextInsight(
                type="enhancement_applied",
                message="已应用上下文增强，提供了额外的分析信息",
                confidence=1.0,
                importance="high",
                actionable=False
            ))
        
        # 业务洞察
        if ContextType.BUSINESS in context_types:
            insights.append(ContextInsight(
                type="business_optimization",
                message="检测到业务上下文，建议应用业务规则验证",
                confidence=0.8,
                importance="medium",
                actionable=True,
                recommendations=["应用业务规则验证", "考虑合规性检查"]
            ))
        
        return insights
    
    def _calculate_confidence_improvement(
        self,
        original_context: Dict[str, Any],
        insights: List[ContextInsight],
        analysis_depth: AnalysisDepth
    ) -> float:
        """计算置信度提升"""
        base_improvement = 0.1  # 基础提升
        
        # 基于洞察数量调整
        insight_boost = min(len(insights) * 0.05, 0.3)
        
        # 基于分析深度调整
        depth_multiplier = {
            AnalysisDepth.SHALLOW: 0.8,
            AnalysisDepth.STANDARD: 1.0,
            AnalysisDepth.DEEP: 1.2,
            AnalysisDepth.COMPREHENSIVE: 1.5
        }.get(analysis_depth, 1.0)
        
        # 基于上下文复杂度调整
        complexity = self._calculate_complexity_score(original_context)
        complexity_boost = complexity * 0.1
        
        total_improvement = (base_improvement + insight_boost + complexity_boost) * depth_multiplier
        
        return min(total_improvement, 0.8)  # 最大提升限制在0.8
    
    def _calculate_complexity_score(self, context_data: Dict[str, Any]) -> float:
        """计算上下文复杂度分数"""
        if not isinstance(context_data, dict):
            return 0.1
        
        # 基于键值对数量
        key_complexity = min(len(context_data) / 20.0, 1.0)
        
        # 基于数据大小
        data_size = len(str(context_data))
        size_complexity = min(data_size / 10000.0, 1.0)
        
        # 基于嵌套层次
        nested_complexity = self._calculate_nesting_depth(context_data) / 10.0
        
        return min((key_complexity + size_complexity + nested_complexity) / 3.0, 1.0)
    
    def _calculate_nesting_depth(self, obj: Any, depth: int = 0) -> int:
        """计算嵌套深度"""
        if depth > 5:  # 防止过深递归
            return depth
        
        if isinstance(obj, dict):
            if not obj:
                return depth
            return max(self._calculate_nesting_depth(v, depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return depth
            return max(self._calculate_nesting_depth(item, depth + 1) for item in obj)
        else:
            return depth


# 全局实例
context_analyzer_service = ContextAnalyzerService()