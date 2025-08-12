"""
知识共享模块

提供Agent间的智能知识共享和协作学习功能。

主要组件：
- KnowledgeShareManager: 核心知识管理器
- AgentKnowledgeIntegrator: Agent知识集成器
- KnowledgeEnhancedAgent: 知识增强Agent基类

Features:
- 跨Agent知识共享
- 用户行为模式学习
- 智能推荐系统
- 性能优化建议
- 协作模式分析
"""

from .knowledge_base import (
    KnowledgeShareManager,
    KnowledgeItem,
    UserPattern,
    AgentInsight,
    BestPractice,
    KnowledgeStorage,
    PatternLearner,
    InsightEngine,
    KnowledgeRetriever
)

from .knowledge_integration import (
    AgentKnowledgeIntegrator,
    KnowledgeEnhancedAgent,
    KnowledgeContext,
    create_knowledge_enhanced_execution,
    get_cross_agent_insights
)

__all__ = [
    # 核心知识管理
    'KnowledgeShareManager',
    'KnowledgeItem',
    'UserPattern', 
    'AgentInsight',
    'BestPractice',
    
    # 知识存储和学习
    'KnowledgeStorage',
    'PatternLearner',
    'InsightEngine', 
    'KnowledgeRetriever',
    
    # 知识集成
    'AgentKnowledgeIntegrator',
    'KnowledgeEnhancedAgent',
    'KnowledgeContext',
    
    # 便用函数
    'create_knowledge_enhanced_execution',
    'get_cross_agent_insights'
]