"""
新一代智能 Agents 系统
====================

完整的智能代理系统，包括：
- 核心Agent框架
- 上下文构建系统  
- 工具系统集成
- 专业化指令系统
- 示例和演示

模块结构：
- core/: 核心Agent框架（消息、协调、内存等）
- tools/: 工具系统（数据、AI、系统工具）
- prompts/: 专业化指令系统
- context_builder.py: 上下文构建器
- context_examples.py: 使用示例
- run_example.py: 运行示例
"""

# =============================================================================
# 核心Agent框架
# =============================================================================
from .core import (
    AgentCoordinator,
    MessageType,
    MessagePriority,
    AgentMessage,
    create_task_request,
    create_progress_message,
    create_result_message,
    MessageBus,
    MemoryManager,
    ProgressAggregator,
    StreamingMessageParser,
    ErrorFormatter
)

# =============================================================================
# 上下文构建系统
# =============================================================================
from .context import (
    AgentContextBuilder,
    ContextType,
    PlaceholderType,
    PlaceholderInfo,
    DatabaseSchemaInfo,
    TemplateInfo,
    TaskInfo,
    AgentContext,
    create_simple_context,
    ContextExamples,
    create_context_for_task,
    create_data_analysis_context,
    create_sql_generation_context,
    create_report_generation_context,
    create_business_intelligence_context,
    get_context_builder as get_context_builder_instance
)

# =============================================================================
# 工具系统
# =============================================================================
from .tools import (
    # 核心工具框架
    AgentTool,
    StreamingAgentTool,
    ToolDefinition,
    ToolResult,
    ToolExecutionContext,
    ToolCategory,
    ToolPriority,
    ToolPermission,
    
    # 数据工具
    SQLGeneratorTool,
    SQLExecutorTool,
    DataAnalysisTool,
    ReportGeneratorTool,
    
    # AI工具
    ReasoningTool,
    
    # LLM工具
    LLMExecutionTool,
    LLMReasoningTool,
    LLMTaskType,
    ReasoningDepth,
    
    # 系统工具
    BashTool,
    FileTool,
    SearchTool
)

# =============================================================================
# LLM服务导入
# =============================================================================
from app.services.infrastructure.llm import (
    # 新的统一接口
    get_llm_manager,
    select_best_model_for_user,
    ask_agent_for_user,
    get_user_available_models,
    get_user_preferences,
    record_usage_feedback,
    health_check,
    get_service_info,
    
    # 必要的类型定义，供agents工具使用
    TaskRequirement,
    TaskComplexity,
    ProcessingStep,
    StepContext
)

# =============================================================================
# LLM工具实例导入
# =============================================================================
from .tools.llm import (
    get_llm_execution_tool,
    get_llm_reasoning_tool,
    get_all_llm_tools
)

# =============================================================================
# 专业化指令系统  
# =============================================================================
from .prompts import (
    get_specialized_instructions,
    DataAnalysisAgentInstructions,
    SystemAdministrationAgentInstructions,
    DevelopmentAgentInstructions,
    BusinessIntelligenceAgentInstructions
)

# =============================================================================
# 便捷函数和工厂方法
# =============================================================================

# 全局实例
_global_coordinator = None

async def get_agent_coordinator() -> AgentCoordinator:
    """获取全局Agent协调器实例"""
    global _global_coordinator
    if _global_coordinator is None:
        _global_coordinator = AgentCoordinator()
        await _global_coordinator.start()
        
        # 注册默认的专业化agents
        await _register_default_agents(_global_coordinator)
    
    return _global_coordinator

def get_context_builder() -> AgentContextBuilder:
    """获取全局上下文构建器实例"""
    return get_context_builder_instance()

async def _register_default_agents(coordinator: AgentCoordinator):
    """注册默认的专业化agents"""
    
    # 数据分析Agent
    await coordinator.register_agent(
        "data_analysis_agent",
        capabilities=["data_analysis", "statistical_analysis", "pattern_recognition"],
        groups=["analysis_agents", "data_agents"]
    )
    
    # SQL生成Agent
    await coordinator.register_agent(
        "sql_generation_agent", 
        capabilities=["sql_generation", "query_optimization", "database_interaction"],
        groups=["data_agents", "sql_agents"]
    )
    
    # 报告生成Agent
    await coordinator.register_agent(
        "report_generation_agent",
        capabilities=["report_generation", "data_visualization", "document_formatting"],
        groups=["presentation_agents", "report_agents"]
    )
    
    # 商业智能Agent
    await coordinator.register_agent(
        "business_intelligence_agent",
        capabilities=["business_intelligence", "kpi_analysis", "dashboard_creation"],
        groups=["bi_agents", "analysis_agents"]
    )
    
    # 系统管理Agent
    await coordinator.register_agent(
        "system_administration_agent",
        capabilities=["system_management", "file_operations", "process_monitoring"],
        groups=["system_agents"]
    )
    
    # 开发Agent
    await coordinator.register_agent(
        "development_agent",
        capabilities=["code_analysis", "software_development", "architecture_review"],
        groups=["development_agents"]
    )

async def execute_agent_task(
    task_name: str,
    task_description: str, 
    context_data: dict = None,
    target_agent: str = None,
    timeout_seconds: int = 300
) -> dict:
    """
    执行Agent任务的便捷函数
    
    Args:
        task_name: 任务名称
        task_description: 任务描述
        context_data: 上下文数据（占位符、表结构等）
        target_agent: 目标Agent（自动推断如果为None）
        timeout_seconds: 超时时间
        
    Returns:
        dict: 执行结果
    """
    
    # 获取系统实例
    coordinator = await get_agent_coordinator()
    builder = get_context_builder()
    
    # 构建任务上下文
    if context_data:
        # 构建完整上下文
        task_info = TaskInfo(
            task_id=f"task_{hash(task_name)}",
            task_name=task_name,
            task_type="general",
            description=task_description
        )
        
        # 解析上下文数据
        placeholders = []
        if "placeholders" in context_data:
            for name, value in context_data["placeholders"].items():
                placeholders.append(PlaceholderInfo(
                    name=name,
                    type=PlaceholderType.TEMPLATE_VARIABLE,
                    value=value
                ))
        
        database_schemas = []
        if "database_schemas" in context_data:
            for schema_data in context_data["database_schemas"]:
                database_schemas.append(DatabaseSchemaInfo(
                    table_name=schema_data.get("table_name", ""),
                    columns=schema_data.get("columns", []),
                    relationships=schema_data.get("relationships", [])
                ))
        
        templates = []
        if "templates" in context_data:
            for template_data in context_data["templates"]:
                templates.append(TemplateInfo(
                    template_id=template_data.get("id", "template"),
                    name=template_data.get("name", "Template"),
                    template_type=template_data.get("type", "general"),
                    content=template_data.get("content", "")
                ))
        
        context = builder.build_context(
            task_info=task_info,
            placeholders=placeholders,
            database_schemas=database_schemas,
            templates=templates
        )
    else:
        # 简单上下文
        context = create_simple_context(
            task_name=task_name,
            task_description=task_description
        )
    
    # 自动选择目标Agent
    if not target_agent:
        context_type = context.context_type.value
        agent_map = {
            "data_analysis": "data_analysis_agent",
            "sql_generation": "sql_generation_agent", 
            "report_generation": "report_generation_agent",
            "business_intelligence": "business_intelligence_agent"
        }
        target_agent = agent_map.get(context_type, "data_analysis_agent")
    
    # 创建消息
    message = builder.create_agent_message(
        context=context,
        target_agent=target_agent,
        from_agent="system"
    )
    
    # 执行任务
    result = await coordinator.execute_task(
        task_description=task_description,
        target_agents=[target_agent],
        timeout_seconds=timeout_seconds,
        use_six_stage_orchestration=True,
        enable_streaming=True
    )
    
    return {
        "success": result.get("success", False),
        "result": result,
        "context": context.to_dict(),
        "message_id": message.message_id,
        "target_agent": target_agent
    }

async def shutdown_agents():
    """关闭agents系统"""
    global _global_coordinator
    if _global_coordinator:
        await _global_coordinator.stop()
        _global_coordinator = None

# =============================================================================
# 导出所有组件
# =============================================================================
__all__ = [
    # 核心框架
    "AgentCoordinator",
    "MessageType",
    "MessagePriority", 
    "AgentMessage",
    "create_task_request",
    "create_progress_message", 
    "create_result_message",
    "MessageBus",
    "MemoryManager",
    "ProgressAggregator",
    "StreamingMessageParser",
    "ErrorFormatter",
    
    # 上下文系统
    "AgentContextBuilder",
    "ContextType",
    "PlaceholderType",
    "PlaceholderInfo", 
    "DatabaseSchemaInfo",
    "TemplateInfo",
    "TaskInfo",
    "AgentContext",
    "create_simple_context",
    "ContextExamples",
    "create_context_for_task",
    "create_data_analysis_context",
    "create_sql_generation_context", 
    "create_report_generation_context",
    "create_business_intelligence_context",
    
    # 工具系统
    "AgentTool",
    "StreamingAgentTool", 
    "ToolDefinition",
    "ToolResult",
    "ToolExecutionContext",
    "ToolCategory",
    "ToolPriority",
    "ToolPermission",
    "SQLGeneratorTool",
    "SQLExecutorTool",
    "DataAnalysisTool",
    "ReportGeneratorTool",
    "ReasoningTool",
    "BashTool",
    "FileTool", 
    "SearchTool",
    
    # 专业化指令
    "get_specialized_instructions",
    "DataAnalysisAgentInstructions",
    "SystemAdministrationAgentInstructions", 
    "DevelopmentAgentInstructions",
    "BusinessIntelligenceAgentInstructions",
    
    # 便捷函数
    "get_agent_coordinator",
    "get_context_builder",
    "execute_agent_task",
    "shutdown_agents",
    
    # LLM工具实例
    "get_llm_execution_tool",
    "get_llm_reasoning_tool",
    "get_all_llm_tools",
    
    # LLM服务接口 - 统一新API
    "get_llm_manager",
    "select_best_model_for_user",
    "ask_agent_for_user", 
    "get_user_available_models",
    "get_user_preferences",
    "record_usage_feedback",
    "health_check",
    "get_service_info",
    
    # LLM类型定义 - agents工具需要
    "TaskRequirement",
    "TaskComplexity",
    "ProcessingStep",
    "StepContext"
]