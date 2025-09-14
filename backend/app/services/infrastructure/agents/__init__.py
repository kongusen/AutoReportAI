"""
Agent System - Clean Architecture
=================================

简洁的智能代理系统架构：

核心模块：
- core/: 核心协调器和TT控制循环
- context/: 任务上下文构建
- tools/: 工具系统
- prompts/: 指令系统

设计原则：
- 统一的命名规范
- 清晰的模块分离
- 最小化复杂度
- 标准化接口
"""

# =============================================================================
# 核心系统 - 简化架构
# =============================================================================
from .core import (
    # 核心协调器
    AgentCoordinator,
    get_coordinator,
    shutdown_coordinator,
    
    # TT控制循环
    TTController,
    TTContext,
    TTLoopState,
    TTEvent,
    TTEventType,
    
    # 消息系统
    AgentMessage,
    MessageType,
    MessagePriority,
    create_task_request,
    create_progress_message,
    create_result_message,
    MessageBus,
    
    # 核心组件
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
    timeout_seconds: int = 120,
    user_id: str = None
) -> dict:
    """
    执行Agent任务 - 简化版本
    
    Args:
        task_name: 任务名称
        task_description: 任务描述
        context_data: 任务上下文数据
        target_agent: 目标Agent
        timeout_seconds: 超时时间
        
    Returns:
        dict: 执行结果
    """
    
    # 获取协调器
    coordinator = await get_coordinator()
    
    # 确定目标Agent
    if not target_agent:
        target_agent = "sql_generation_agent"  # 默认SQL生成Agent
    
    # 执行任务
    result = await coordinator.execute_task(
        task_description=task_description,
        context=context_data or {},
        target_agents=[target_agent],
        timeout_seconds=timeout_seconds,
        user_id=user_id
    )
    
    # 构建标准化结果
    if result.get("success", False):
        return {
            "success": True,
            "result": result.get("result", {}),
            "task_name": task_name,
            "target_agent": target_agent,
            "llm_interactions": result.get("llm_interactions", 0),
            "architecture": result.get("architecture", "tt_controlled")
        }
    else:
        return {
            "success": False,
            "error": result.get("error", "Task execution failed"),
            "task_name": task_name,
            "target_agent": target_agent,
            "architecture": result.get("architecture", "tt_controlled")
        }


async def shutdown_agents():
    """关闭agents系统"""
    await shutdown_coordinator()

# =============================================================================
# 导出组件 - 简化列表
# =============================================================================
__all__ = [
    # 核心系统
    "AgentCoordinator",
    "get_coordinator",
    "shutdown_coordinator",
    
    # TT控制循环
    "TTController",
    "TTContext",
    "TTLoopState",
    "TTEvent", 
    "TTEventType",
    
    # 消息系统
    "AgentMessage",
    "MessageType",
    "MessagePriority", 
    "create_task_request",
    "create_progress_message", 
    "create_result_message",
    "MessageBus",
    
    # 核心组件
    "MemoryManager",
    "ProgressAggregator",
    "StreamingMessageParser",
    "ErrorFormatter",
    
    # 便捷函数
    "execute_agent_task",
    "shutdown_agents"
]