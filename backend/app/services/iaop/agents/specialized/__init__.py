"""
专业Agent层 - 统一导出和注册接口

提供完整的占位符解析到报告生成的流水线Agent集合
"""

from .placeholder_parser_agent import PlaceholderParserAgent
from .data_query_agent import DataQueryAgent
from .data_analysis_agent import DataAnalysisAgent
from .chart_generator_agent import ChartGeneratorAgent
from .insight_narrator_agent import InsightNarratorAgent

__all__ = [
    'PlaceholderParserAgent',
    'DataQueryAgent', 
    'DataAnalysisAgent',
    'ChartGeneratorAgent',
    'InsightNarratorAgent',
    'register_all_specialized_agents',
    'create_report_pipeline'
]


def register_all_specialized_agents():
    """注册所有专业Agent到全局注册器"""
    from ...registry.agent_registry import get_iaop_agent_registry
    
    registry = get_iaop_agent_registry()
    
    # 注册占位符解析Agent
    registry.register_agent(
        PlaceholderParserAgent(),
        priority=90,
        capabilities=["placeholder_parsing", "semantic_analysis", "text_analysis"],
        requirements=["template_content"]
    )
    
    # 注册数据查询Agent
    registry.register_agent(
        DataQueryAgent(),
        priority=85,
        capabilities=["sql_generation", "data_retrieval", "query_optimization"],
        requirements=["parsed_request", "data_source_info"]
    )
    
    # 注册数据分析Agent
    registry.register_agent(
        DataAnalysisAgent(),
        priority=80,
        capabilities=["statistical_analysis", "trend_analysis", "anomaly_detection"],
        requirements=["query_result", "parsed_request"]
    )
    
    # 注册图表生成Agent
    registry.register_agent(
        ChartGeneratorAgent(),
        priority=75,
        capabilities=["visualization", "chart_generation", "ui_rendering"],
        requirements=["analysis_result", "parsed_request"]
    )
    
    # 注册结果解释Agent
    registry.register_agent(
        InsightNarratorAgent(),
        priority=70,
        capabilities=["narrative_generation", "insight_extraction", "text_generation"],
        requirements=["analysis_result", "chart_config", "parsed_request"]
    )
    
    # 注册完整报告生成流水线
    registry.register_agent_chain(
        "complete_report_pipeline",
        ["placeholder_parser", "data_query", "data_analysis", "chart_generator", "insight_narrator"]
    )
    
    # 注册部分流水线
    registry.register_agent_chain(
        "data_analysis_pipeline", 
        ["data_query", "data_analysis", "chart_generator"]
    )
    
    registry.register_agent_chain(
        "visualization_pipeline",
        ["data_analysis", "chart_generator", "insight_narrator"] 
    )
    
    print("✅ 所有专业Agent注册完成")
    return registry


async def create_report_pipeline():
    """创建完整的报告生成流水线"""
    from ...orchestration.engine import get_orchestration_engine
    
    engine = get_orchestration_engine()
    
    # 确保所有Agent都已注册
    register_all_specialized_agents()
    
    return engine


def get_specialized_agent_status():
    """获取专业Agent状态"""
    from ...registry.agent_registry import get_iaop_agent_registry
    
    registry = get_iaop_agent_registry()
    status = registry.get_registry_status()
    
    specialized_agents = [
        "placeholder_parser",
        "data_query", 
        "data_analysis",
        "chart_generator",
        "insight_narrator"
    ]
    
    available_agents = [agent for agent in specialized_agents if agent in status['agents']]
    
    return {
        "total_specialized_agents": len(specialized_agents),
        "available_agents": len(available_agents),
        "missing_agents": list(set(specialized_agents) - set(available_agents)),
        "agent_chains": [chain for chain in status['chains'] if 'pipeline' in chain],
        "capabilities_coverage": {
            cap: status['capability_coverage'].get(cap, 0)
            for cap in [
                "placeholder_parsing", "sql_generation", "statistical_analysis",
                "visualization", "narrative_generation"
            ]
        }
    }


# 自动注册（可选，在模块导入时执行）
# register_all_specialized_agents()
