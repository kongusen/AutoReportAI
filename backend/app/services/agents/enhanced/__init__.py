"""
增强版Agent模块

包含所有增强版的Agent实现，提供更智能的功能和更好的用户体验。

Enhanced Agents:
- EnhancedDataQueryAgent - 语义理解和智能查询
- EnhancedContentGenerationAgent - 上下文管理和风格控制
- EnhancedAnalysisAgent - 机器学习和高级分析
- EnhancedVisualizationAgent - 智能推荐和自适应设计
"""

from .enhanced_data_query_agent import (
    EnhancedDataQueryAgent,
    SemanticQueryRequest,
    QueryIntent,
    MetadataInfo,
    SemanticParser,
    QueryOptimizer,
    MetadataManager
)

from .enhanced_content_generation_agent import (
    EnhancedContentGenerationAgent,
    ContextualContentRequest,
    ConversationContext,
    StyleProfile,
    ContextManager,
    StyleAnalyzer,
    QualityChecker,
    PersonalizationEngine
)

from .enhanced_analysis_agent import (
    EnhancedAnalysisAgent,
    MLAnalysisRequest,
    MLModelInfo,
    PredictionResult,
    AnomalyDetectionResult,
    ClusteringResult,
    MLPredictor,
    AnomalyDetector,
    PatternMiner,
    InsightGenerator
)

from .enhanced_visualization_agent import (
    EnhancedVisualizationAgent,
    SmartChartRequest,
    ChartRecommendation,
    ColorPalette,
    LayoutConfig,
    ChartRecommender,
    ColorHarmonyEngine,
    LayoutOptimizer,
    StorytellingEngine
)

__all__ = [
    # 增强数据查询Agent
    'EnhancedDataQueryAgent',
    'SemanticQueryRequest', 
    'QueryIntent',
    'MetadataInfo',
    'SemanticParser',
    'QueryOptimizer',
    'MetadataManager',
    
    # 增强内容生成Agent
    'EnhancedContentGenerationAgent',
    'ContextualContentRequest',
    'ConversationContext',
    'StyleProfile',
    'ContextManager',
    'StyleAnalyzer',
    'QualityChecker',
    'PersonalizationEngine',
    
    # 增强分析Agent
    'EnhancedAnalysisAgent',
    'MLAnalysisRequest',
    'MLModelInfo',
    'PredictionResult',
    'AnomalyDetectionResult',
    'ClusteringResult',
    'MLPredictor',
    'AnomalyDetector',
    'PatternMiner',
    'InsightGenerator',
    
    # 增强可视化Agent
    'EnhancedVisualizationAgent',
    'SmartChartRequest',
    'ChartRecommendation',
    'ColorPalette',
    'LayoutConfig',
    'ChartRecommender',
    'ColorHarmonyEngine',
    'LayoutOptimizer',
    'StorytellingEngine'
]