"""
Lexicon Agent Framework v2.0

基于Claude Code分析的智能体框架，实现上下文工程和多智能体协调
"""

# 导出主要类型
from .types import (
    AgentEvent, AgentEventType, ToolCall, ToolResult, 
    ToolSafetyLevel, Agent, ManagedContext, SessionState
)

# 导出核心组件
from .core.context import ContextRetrievalEngine, ContextProcessor, ContextManager
from .core.agent import AgentController
from .core.orchestration import OrchestrationEngine, AgentCoordinator
from .core.tools import ToolRegistry, IntelligentToolScheduler, ToolExecutor
from .core.streaming import StreamingProcessor, PerformanceOptimizer, StreamingPipeline

# 导出主框架接口
from .main import (
    LexiconAgent, 
    create_agent, 
    quick_chat,
    create_development_agent,
    create_production_agent,
    create_minimal_agent,
    create_custom_llm_agent
)

# 设置包版本
__version__ = "2.0.0"

# 临时兼容性函数 - 用于满足现有代码的导入需求
async def execute_agent_task(
    task_name: str,
    task_description: str,
    context_data: dict,
    user_id: str = None
) -> dict:
    """
    执行Agent任务 - 临时实现
    
    TODO: 这是一个临时的兼容性实现，在完整的agent系统实现后应被替换
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"execute_agent_task临时实现被调用: {task_name}")
    
    return {
        "success": False,
        "error": "agent任务执行功能暂未完全实现",
        "task_name": task_name,
        "description": task_description
    }

async def analyze_placeholder_technical(
    placeholder_text: str,
    technical_context: dict = None
) -> dict:
    """
    占位符技术分析 - 基础设施层实现
    
    仅提供技术层面的分析功能，不包含业务逻辑
    业务逻辑应该在领域服务中实现
    
    Args:
        placeholder_text: 占位符文本
        technical_context: 技术上下文（数据库连接、SQL能力等）
        
    Returns:
        技术分析结果
    """
    import logging
    import re
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    logger.info(f"[Agent基础设施层] 开始技术分析占位符: {placeholder_text}")
    
    try:
        # 技术层面的模式识别 - 增强版
        sql_patterns = {
            "count": r"(总数|数量|count|num|件数|个数|条数|统计)",
            "sum": r"(总计|合计|sum|total|累计|汇总)",
            "avg": r"(平均|average|avg|均值)",
            "max": r"(最大|最高|max|最多)",
            "min": r"(最小|最低|min|最少)",
            "date": r"(时间|日期|date|time|年|月|日|周)",
            "group": r"(分组|group|category|分类|按.*分|类型)",
            "statistical": r"(统计|分析|计算|总.*数|总.*量)",
            "financial": r"(金额|费用|成本|收入|价格|总价|单价)",
            "performance": r"(率|比例|占比|百分比|效率|性能)"
        }
        
        detected_patterns = []
        for pattern_type, pattern in sql_patterns.items():
            if re.search(pattern, placeholder_text, re.IGNORECASE):
                detected_patterns.append(pattern_type)
        
        # 技术复杂度评估
        complexity_score = len(detected_patterns)
        if "group" in detected_patterns:
            complexity_score += 2
        if "date" in detected_patterns:
            complexity_score += 1
            
        complexity_level = "low"
        if complexity_score >= 4:
            complexity_level = "high"
        elif complexity_score >= 2:
            complexity_level = "medium"
        
        # SQL生成建议（技术层面）- 增强版
        sql_suggestions = []
        if "count" in detected_patterns or "statistical" in detected_patterns:
            sql_suggestions.append("使用COUNT()聚合函数")
            sql_suggestions.append("SELECT COUNT(*) FROM table_name")
        if "sum" in detected_patterns:
            sql_suggestions.append("使用SUM()聚合函数")
            sql_suggestions.append("SELECT SUM(column_name) FROM table_name")
        if "avg" in detected_patterns:
            sql_suggestions.append("使用AVG()聚合函数")
        if "group" in detected_patterns:
            sql_suggestions.append("需要GROUP BY子句")
        if "date" in detected_patterns:
            sql_suggestions.append("需要日期函数处理")
            sql_suggestions.append("WHERE DATE(date_column) = CURDATE()")
        if "financial" in detected_patterns:
            sql_suggestions.append("注意金额字段的精度处理")
        if "performance" in detected_patterns:
            sql_suggestions.append("计算比率: (value1/value2)*100")
            
        return {
            "success": True,
            "technical_analysis": {
                "detected_patterns": detected_patterns,
                "complexity_level": complexity_level,
                "complexity_score": complexity_score,
                "sql_suggestions": sql_suggestions,
                "requires_aggregation": any(p in detected_patterns for p in ["count", "sum", "avg", "max", "min"]),
                "requires_grouping": "group" in detected_patterns,
                "requires_date_handling": "date" in detected_patterns
            },
            "metadata": {
                "analyzed_at": datetime.now().isoformat(),
                "agent_layer": "infrastructure",
                "analysis_type": "technical_only"
            }
        }
        
    except Exception as e:
        logger.error(f"[Agent基础设施层] 技术分析失败: {str(e)}")
        return {
            "success": False,
            "error": f"技术分析失败: {str(e)}",
            "metadata": {
                "analyzed_at": datetime.now().isoformat(),
                "error_type": type(e).__name__
            }
        }

# 向后兼容的包装器
async def analyze_placeholder(placeholder_text: str, **kwargs) -> dict:
    """
    兼容性包装器 - 重定向到技术分析
    
    注意：这个函数应该被废弃，API层应该调用领域服务，
    领域服务再调用 analyze_placeholder_technical
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("⚠️  架构警告：API层直接调用agent，应该通过领域服务调用")
    
    return await analyze_placeholder_technical(placeholder_text, technical_context=kwargs)

def get_agent_coordinator():
    """
    获取Agent协调器 - 临时实现
    
    TODO: 这是一个临时的兼容性实现
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("get_agent_coordinator临时实现被调用")
    
    # 返回一个基础的协调器对象
    return AgentCoordinator()

def create_data_analysis_context(**kwargs):
    """
    创建数据分析上下文 - 临时实现
    
    TODO: 这是一个临时的兼容性实现
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("create_data_analysis_context临时实现被调用")
    
    # 返回一个基础的ManagedContext对象
    return ManagedContext()

__all__ = [
    # 主框架接口
    "LexiconAgent", "create_agent", "quick_chat",
    "create_development_agent", "create_production_agent", 
    "create_minimal_agent", "create_custom_llm_agent",
    
    # 主要类型
    "AgentEvent", "AgentEventType", "ToolCall", "ToolResult", 
    "ToolSafetyLevel", "Agent", "ManagedContext", "SessionState",
    
    # 核心组件
    "ContextRetrievalEngine", "ContextProcessor", "ContextManager",
    "AgentController", "OrchestrationEngine", "AgentCoordinator",
    "ToolRegistry", "IntelligentToolScheduler", "ToolExecutor",
    "StreamingProcessor", "PerformanceOptimizer", "StreamingPipeline",
    
    # 兼容性函数
    "execute_agent_task",
    "analyze_placeholder",  # 废弃，仅兼容
    "analyze_placeholder_technical",  # 正确的基础设施层接口
    "get_agent_coordinator",
    "create_data_analysis_context"
]