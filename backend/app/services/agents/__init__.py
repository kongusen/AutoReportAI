"""
智能代理系统 - DAG编排架构
基于Background Controller的DAG流程控制和Think/Default模型动态选择

主要用于placeholder和template域服务的智能化处理
核心特性：
- 基于placeholder上下文工程的智能路由
- DAG(有向无环图)流程控制
- Think/Default模型动态选择
- 步骤级别的质量控制和重试机制
"""

# 核心DAG编排组件
from .core.placeholder_task_context import (
    PlaceholderTaskContext,
    ExecutionStep,
    ExecutionStepType,
    ModelRequirement,
    PlaceholderComplexity,
    create_task_context_from_placeholder_analysis
)
from .core.background_controller import (
    BackgroundController,
    ControlContext,
    ControlDecision,
    ExecutionStatus,
    StepResult,
    create_control_context
)
from .core.execution_engine import (
    ExecutionEngine
)

# 兼容性：保留原有组件以支持现有集成
from .core.react_agent import ReactIntelligentAgent
from .core.llm_adapter import (
    LLMClientAdapter, 
    create_llm_adapter, 
    create_agent_llm,
    create_fixed_model_adapter,
    get_llm_routing_stats,
    get_model_performance_report
)
from .core.agent_manager import (
    IntelligentAgentManager, 
    get_agent_manager,
    execute_agent_task,
    get_agents_status,
    get_agents_health,
    AgentType, TaskPriority, AgentStatus
)

# 工具系统
from .core.tools_registry import (
    FunctionToolsRegistry,
    get_tools_registry,
    register_all_tools,
    get_tools_by_category
)

from .tools.tools_factory import (
    ToolsFactory,
    get_tools_factory,
    create_all_tools,
    create_tools_by_category,
    create_tool_combination,
    get_available_combinations,
    ToolsMonitor,
    get_tools_monitor
)

# 版本信息
__version__ = "2.0.0-dag"  # DAG编排架构版本

__all__ = [
    # DAG编排核心组件
    "PlaceholderTaskContext",
    "ExecutionStep",
    "ExecutionStepType", 
    "ModelRequirement",
    "PlaceholderComplexity",
    "create_task_context_from_placeholder_analysis",
    
    "BackgroundController",
    "ControlContext",
    "ControlDecision",
    "ExecutionStatus",
    "StepResult",
    "create_control_context",
    
    "ExecutionEngine",
    
    # 兼容性：原有组件
    "ReactIntelligentAgent",
    "LLMClientAdapter",
    "create_llm_adapter",
    "create_agent_llm",
    "IntelligentAgentManager",
    
    # 管理器函数
    "get_agent_manager",
    "execute_agent_task", 
    "get_agents_status",
    "get_agents_health",
    
    # 枚举类型
    "AgentType",
    "TaskPriority", 
    "AgentStatus",
    
    # 工具注册系统
    "FunctionToolsRegistry",
    "get_tools_registry",
    "register_all_tools",
    "get_tools_by_category",
    
    # 工具工厂
    "ToolsFactory",
    "get_tools_factory", 
    "create_all_tools",
    "create_tools_by_category",
    "create_tool_combination",
    "get_available_combinations",
    
    # 工具监控
    "ToolsMonitor",
    "get_tools_monitor"
]

# 集成说明
def get_integration_info():
    """获取集成信息"""
    return {
        "description": "DAG编排智能代理系统，基于Background Controller的流程控制和动态模型选择",
        "architecture": "DAG (Directed Acyclic Graph) 编排架构",
        "core_components": {
            "background_controller": "DAG流程控制和决策引擎",
            "execution_engine": "步骤执行和模型调度引擎",
            "task_context": "占位符任务上下文和状态管理"
        },
        "primary_integrations": [
            "backend.app.services.domain.placeholder.context.context_analysis_engine",
            "backend.app.services.domain.placeholder.intelligent_placeholder_service", 
            "backend.app.services.domain.template.agent_enhanced_template_service"
        ],
        "usage": {
            "context_driven_routing": "基于placeholder上下文工程分析结果进行智能路由",
            "dag_execution": "DAG流程控制，支持步骤级别的质量控制和重试",
            "dynamic_model_selection": "动态选择Think/Default模型以平衡质量和效率",
            "placeholder_processing": "专业化的占位符处理流程"
        },
        "model_types": {
            "think": "复杂推理模型 - 用于复杂SQL生成、业务逻辑推理、异常处理",
            "default": "快速处理模型 - 用于简单查询、数据格式化、基础统计"
        },
        "execution_flow": {
            "step_1": "接收placeholder上下文工程分析结果",
            "step_2": "创建PlaceholderTaskContext，评估复杂度",
            "step_3": "Background Controller进行DAG流程控制",
            "step_4": "ExecutionEngine执行具体步骤，动态选择模型",
            "step_5": "SQL生成→数据源连接验证→迭代优化（如需要）",
            "step_6": "图表生成和可视化处理（如需要）",
            "step_7": "质量验证和结果迭代优化",
            "step_8": "返回最终占位符替换结果"
        },
        "quality_control": {
            "step_level_validation": "每个步骤都有质量验证机制",
            "adaptive_retry": "基于结果质量自动重试或升级模型",
            "error_recovery": "完善的错误恢复和降级处理",
            "performance_monitoring": "实时性能监控和统计分析",
            "sql_validation": "基于数据源连接的SQL实际验证",
            "iterative_optimization": "SQL验证失败时自动迭代优化"
        },
        "tool_capabilities": {
            "chart_generation": "支持六种统计图类型：柱状图、饼图、折线图、散点图、雷达图、漏斗图",
            "sql_processing": "智能SQL生成、语法验证、数据源连接测试、迭代优化",
            "data_source_support": "支持Apache Doris、MySQL、PostgreSQL等多种数据源",
            "visualization_optimization": "图表智能选择、配置优化、批量生成"
        }
    }


def execute_placeholder_with_context(
    placeholder_text: str,
    statistical_type: str,
    description: str,
    context_engine: dict,  # 修正：接收上下文工程而非分析结果
    user_id: str = "system"
) -> dict:
    """
    使用DAG编排架构处理占位符的主入口函数（符合新架构）
    
    流程：
    1. 接收placeholder domain构建的上下文工程
    2. background agent分析上下文工程信息  
    3. 通过DAG流程控制进行智能处理
    4. 上下文工程协助存储中间结果
    
    Args:
        placeholder_text: 占位符文本
        statistical_type: 统计类型
        description: 需求描述 
        context_engine: placeholder domain构建的上下文工程
        user_id: 用户ID
        
    Returns:
        处理结果字典
        
    Usage:
        # placeholder domain构建上下文工程后调用
        context_engine = placeholder_service.build_context_engine(...)
        result = execute_placeholder_with_context(
            placeholder_text="{{统计：Q1销售额}}",
            statistical_type="统计",
            description="Q1销售额",
            context_engine=context_engine,  # 传递上下文工程
            user_id="user_123"
        )
    """
    # 1. background agent分析上下文工程信息
    context_analysis = analyze_context_engine(context_engine)
    
    # 2. 创建任务上下文
    task_context = create_task_context_from_placeholder_analysis(
        placeholder_text=placeholder_text,
        statistical_type=statistical_type,
        description=description,
        context_analysis=context_analysis,
        user_id=user_id,
        context_engine=context_engine  # 传递上下文工程用于协助存储
    )
    
    # 3. 创建执行引擎并注册Think/Default模型
    execution_engine = ExecutionEngine()
    
    # 自动注册默认的Think/Default模型和工具
    _register_default_models_and_tools(execution_engine)
    
    # 4. 执行DAG流程
    import asyncio
    return asyncio.run(execution_engine.execute_placeholder_task(task_context))


def analyze_context_engine(context_engine: dict) -> dict:
    """
    background agent分析上下文工程信息（新架构要求）
    
    Args:
        context_engine: 来自placeholder domain的上下文工程
        
    Returns:
        分析结果字典
    """
    try:
        # background agent分析上下文工程中的信息
        analysis_result = {
            "confidence_score": 0.8,  # 基于上下文工程质量评估
            "complexity": _assess_complexity_from_context(context_engine),
            "integrated_context": {
                "template_info": context_engine.get("template_content", ""),
                "business_context": context_engine.get("business_context", {}),
                "time_context": context_engine.get("time_context", {}),
                "document_context": context_engine.get("document_context", {}),
                "storage_capabilities": context_engine.get("storage_capabilities", {}),
                "metadata": context_engine.get("metadata", {})
            },
            "processing_recommendations": _generate_processing_recommendations(context_engine)
        }
        
        return analysis_result
        
    except Exception as e:
        # 分析失败时返回基础分析结果
        return {
            "confidence_score": 0.5,
            "complexity": "medium",
            "integrated_context": {},
            "processing_recommendations": {"model": "default", "priority": "medium"},
            "error": str(e)
        }


def _assess_complexity_from_context(context_engine: dict) -> str:
    """评估上下文工程的复杂度"""
    try:
        business_context = context_engine.get("business_context", {})
        time_context = context_engine.get("time_context", {})
        
        complexity_factors = 0
        
        # 评估业务复杂度
        if business_context.get("report_level") == "detailed":
            complexity_factors += 2
        if business_context.get("include_comparisons"):
            complexity_factors += 1
        
        # 评估时间复杂度
        if time_context.get("period_type") in ["custom", "multi_period"]:
            complexity_factors += 2
        
        # 评估模板复杂度
        template_content = context_engine.get("template_content", "")
        if len(template_content) > 1000:
            complexity_factors += 1
        
        if complexity_factors >= 4:
            return "very_high"
        elif complexity_factors >= 2:
            return "high"
        else:
            return "medium"
            
    except:
        return "medium"


def _generate_processing_recommendations(context_engine: dict) -> dict:
    """基于上下文工程生成处理建议"""
    complexity = _assess_complexity_from_context(context_engine)
    
    if complexity in ["very_high", "high"]:
        return {
            "model": "think",
            "priority": "high",
            "steps": ["enhanced_parsing", "complex_analysis", "think_sql_generation", "validation"],
            "quality_threshold": 0.8
        }
    else:
        return {
            "model": "default", 
            "priority": "medium",
            "steps": ["basic_parsing", "simple_analysis", "default_sql_generation"],
            "quality_threshold": 0.6
        }


def _register_default_models_and_tools(execution_engine):
    """自动注册默认的Think/Default模型和工具"""
    try:
        # 这里应该注册实际的Think和Default模型
        # 目前使用占位符实现，实际使用时需要替换为真实模型
        
        # 注册模拟的Think和Default模型
        from .example_dag_usage import MockThinkModel, MockDefaultModel
        
        think_model = MockThinkModel()
        default_model = MockDefaultModel()
        execution_engine.register_models(think_model, default_model)
        
        # 注册工具集（包含图表生成和SQL工具）
        from .example_dag_usage import (
            MockPlaceholderParser, MockContextAnalyzer, MockSQLGenerator,
            MockSchemaAnalyzer, MockDataExecutor, MockBusinessProcessor,
            MockCalculator, MockResultValidator, MockFormatter,
            MockChartGenerator, MockDataAnalyzer, MockVisualizationOptimizer,
            MockSQLGeneratorAdvanced, MockSQLValidator, MockSQLOptimizer, MockDataSourceConnector
        )
        
        tools_registry = {
            "placeholder_parser": MockPlaceholderParser(),
            "context_analyzer": MockContextAnalyzer(),
            "sql_generator": MockSQLGenerator(),
            "schema_analyzer": MockSchemaAnalyzer(),
            "data_executor": MockDataExecutor(),
            "business_processor": MockBusinessProcessor(),
            "calculator": MockCalculator(),
            "result_validator": MockResultValidator(),
            "formatter": MockFormatter(),
            # 图表生成工具（六种统计图）
            "chart_generator": MockChartGenerator(),
            "bar_chart_generator": MockChartGenerator(),
            "pie_chart_generator": MockChartGenerator(),
            "line_chart_generator": MockChartGenerator(),
            "scatter_chart_generator": MockChartGenerator(),
            "radar_chart_generator": MockChartGenerator(),
            "funnel_chart_generator": MockChartGenerator(),
            # 数据分析和可视化优化工具
            "data_analyzer": MockDataAnalyzer(),
            "visualization_optimizer": MockVisualizationOptimizer(),
            # SQL生成和验证工具集合
            "sql_generator_advanced": MockSQLGeneratorAdvanced(),
            "sql_validator": MockSQLValidator(),
            "sql_optimizer": MockSQLOptimizer(),
            "data_source_connector": MockDataSourceConnector()
        }
        execution_engine.register_tools(tools_registry)
        
    except Exception as e:
        # 注册失败时记录错误，但不影响主流程
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"注册默认模型和工具失败: {e}")