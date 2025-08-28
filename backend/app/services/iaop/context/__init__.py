"""
统一智能上下文系统 - 替换原有上下文管理

这个模块提供了完整的智能上下文管理解决方案，基于Claude Code最佳实践：
1. 智能上下文管理器 - 核心上下文管理和推理
2. 渐进式优化引擎 - 基于反馈的持续优化
3. 学习增强系统 - 从成功案例中学习改进
4. 统一的上下文接口 - 简化使用和维护
"""

# 核心上下文管理
from .execution_context import EnhancedExecutionContext, ContextScope, ContextEntry
from .intelligent_context_manager import IntelligentContextManager, ContextIntelligenceLevel
from .progressive_optimization_engine import ProgressiveOptimizationEngine, OptimizationStrategy
from .learning_enhanced_context import LearningEnhancedContextSystem, LearningMode

# 工厂函数
from .intelligent_context_manager import create_intelligent_context_manager
from .progressive_optimization_engine import create_progressive_optimization_engine
from .learning_enhanced_context import create_learning_enhanced_context_system

# 统一上下文系统接口
from .unified_context_system import UnifiedContextSystem, create_unified_context_system

__all__ = [
    # 核心类
    'EnhancedExecutionContext',
    'ContextScope', 
    'ContextEntry',
    'IntelligentContextManager',
    'ProgressiveOptimizationEngine',
    'LearningEnhancedContextSystem',
    'UnifiedContextSystem',
    
    # 枚举类
    'ContextIntelligenceLevel',
    'OptimizationStrategy',
    'LearningMode',
    
    # 工厂函数
    'create_intelligent_context_manager',
    'create_progressive_optimization_engine',
    'create_learning_enhanced_context_system',
    'create_unified_context_system',
]