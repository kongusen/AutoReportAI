"""
AutoReportAI Agent 核心基础设施服务

提供AutoReportAI Agent系统的核心AI基础设施：

核心功能：
1. AutoReportAI Agent - 三大核心功能的主要编排器
   - 占位符→SQL转换 (placeholder_to_sql_agent)
   - 任务补充机制 (task_supplement_agent)  
   - 图表生成 (chart_generator_tool)
   
2. LLM管理基础设施
   - 智能模型选择 (StepBasedModelSelector)
   - 流式API调用和动态超时
   - 数据库驱动的用户配置管理
   
3. 工具系统
   - 现代化工具注册架构
   - 图表生成工具集成
   - 工具监控和管理

4. 多上下文集成
   - 数据源上下文、任务上下文、模板上下文、时间上下文
   - SQL测试验证服务

设计原则：
- 基于设计文档的简化架构
- 删除冗余组件，保留核心功能
- 支持三大核心功能和五大工作流
- 现代化工具注册和LLM管理
"""

from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# 全局服务实例缓存
_ai_service_instances: Dict[str, Any] = {}

# ===========================================
# 核心AutoReportAI Agent服务
# ===========================================

def get_autoreport_ai_agent(user_id: str = None):
    """获取AI服务(已迁移到ServiceOrchestrator)"""
    from .service_orchestrator import get_service_orchestrator
    return get_service_orchestrator()

def get_placeholder_to_sql_agent():
    """获取SQL生成服务(已迁移到ServiceOrchestrator)"""
    from .service_orchestrator import get_service_orchestrator
    return get_service_orchestrator()

def get_task_supplement_agent():
    """获取任务补充服务(已迁移到ServiceOrchestrator)"""
    from .service_orchestrator import get_service_orchestrator
    return get_service_orchestrator()

def get_multi_context_integrator():
    """获取上下文集成服务(已迁移到ServiceOrchestrator)"""
    from .service_orchestrator import get_service_orchestrator
    return get_service_orchestrator()

def get_sql_testing_validator():
    """获取SQL验证服务(已迁移到ServiceOrchestrator)"""
    from .service_orchestrator import get_service_orchestrator
    return get_service_orchestrator()

def get_tool_based_agent():
    """获取工具集成服务(已迁移到ServiceOrchestrator)"""
    from .service_orchestrator import get_service_orchestrator
    return get_service_orchestrator()

# ===========================================
# LLM管理服务
# ===========================================

async def get_llm_manager():
    """获取LLM管理器"""
    from .llm import get_llm_manager
    return await get_llm_manager()

async def select_model_for_user(
    user_id: str,
    task_type: str = "general",
    complexity: str = "medium",
    constraints: Optional[Dict[str, Any]] = None,
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """为用户选择最佳模型"""
    from .llm import select_best_model_for_user
    return await select_best_model_for_user(
        user_id=user_id,
        task_type=task_type,
        complexity=complexity,
        constraints=constraints,
        agent_id=agent_id
    )

async def ask_agent(
    user_id: str,
    question: str,
    agent_type: str = "general",
    context: Optional[str] = None,
    task_type: str = "general", 
    complexity: str = "medium"
) -> str:
    """Agent友好的问答接口"""
    from .llm import ask_agent_for_user
    return await ask_agent_for_user(
        user_id=user_id,
        question=question,
        agent_type=agent_type,
        context=context,
        task_type=task_type,
        complexity=complexity
    )

# ===========================================
# 工具系统服务
# ===========================================

async def get_ai_tools_registry():
    """获取AI工具注册表"""
    if 'tools_registry' not in _ai_service_instances:
        from .tools.registry import AIToolsRegistry
        _ai_service_instances['tools_registry'] = AIToolsRegistry()
    return _ai_service_instances['tools_registry']

async def get_tools_factory():
    """获取工具工厂"""
    if 'tools_factory' not in _ai_service_instances:
        from .tools.factory import AIToolsFactory
        _ai_service_instances['tools_factory'] = AIToolsFactory()
    return _ai_service_instances['tools_factory']

async def get_chart_generator_tool():
    """获取图表生成工具"""
    if 'chart_generator_tool' not in _ai_service_instances:
        from .tools.chart_generator_tool import ChartGeneratorTool
        _ai_service_instances['chart_generator_tool'] = ChartGeneratorTool()
    return _ai_service_instances['chart_generator_tool']

# ===========================================
# 核心工作流接口（向后兼容）
# ===========================================

async def execute_placeholder_with_context(
    placeholder_text: str,
    statistical_type: str,
    description: str,
    context_engine: Dict[str, Any],
    user_id: str = "system"
) -> Dict[str, Any]:
    """
    执行占位符处理的主入口函数
    
    这是AutoReportAI Agent系统的核心接口，支持三大核心功能：
    1. 占位符→SQL转换
    2. 任务补充机制  
    3. 图表生成（通过工具集成）
    
    Args:
        placeholder_text: 占位符文本
        statistical_type: 统计类型
        description: 需求描述  
        context_engine: 上下文工程数据
        user_id: 用户ID
        
    Returns:
        处理结果字典
    """
    try:
        # 获取AutoReportAI Agent主编排器
        ai_agent = await get_autoreport_ai_agent(user_id)
        
        # 执行占位符处理工作流
        result = await ai_agent.process_placeholder_task(
            placeholder_text=placeholder_text,
            statistical_type=statistical_type,
            description=description,
            context_engine=context_engine,
            user_id=user_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"AutoReportAI Agent执行占位符任务失败: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'source': 'autoreport_ai_agent',
            'fallback': True
        }

# ===========================================
# 服务监控和健康检查
# ===========================================

async def get_ai_service_status() -> Dict[str, Any]:
    """获取AI服务整体状态"""
    try:
        status = {
            'service_name': 'AutoReportAI Agent Infrastructure',
            'version': '3.0.0-optimized',
            'architecture': 'Modern Agent System',
            'status': 'running',
            'components': {}
        }
        
        # 检查核心组件状态
        components_to_check = [
            ('autoreport_ai_agent', get_autoreport_ai_agent),
            ('placeholder_to_sql_agent', get_placeholder_to_sql_agent),
            ('task_supplement_agent', get_task_supplement_agent),
            ('multi_context_integrator', get_multi_context_integrator),
            ('sql_testing_validator', get_sql_testing_validator),
            ('tool_based_agent', get_tool_based_agent),
            ('llm_manager', get_llm_manager),
            ('tools_registry', get_ai_tools_registry),
            ('tools_factory', get_tools_factory),
            ('chart_generator_tool', get_chart_generator_tool)
        ]
        
        for component_name, component_getter in components_to_check:
            try:
                await component_getter()
                status['components'][component_name] = 'available'
            except Exception as e:
                status['components'][component_name] = f'unavailable: {str(e)}'
        
        # 检查LLM健康状态
        try:
            from .llm import health_check
            llm_health = await health_check()
            status['components']['llm_health'] = 'available' if llm_health.get('healthy') else 'degraded'
        except Exception:
            status['components']['llm_health'] = 'unavailable'
        
        # 计算总体健康度
        available_count = sum(1 for s in status['components'].values() if s == 'available')
        total_count = len(status['components'])
        status['health_score'] = available_count / total_count if total_count > 0 else 0
        
        return status
        
    except Exception as e:
        return {
            'service_name': 'AutoReportAI Agent Infrastructure',
            'status': 'error',
            'error': str(e),
            'health_score': 0
        }

# ===========================================
# 导入核心组件
# ===========================================

# LLM服务导入
from .llm import (
    select_best_model_for_user,
    ask_agent_for_user,
    get_user_available_models,
    get_user_preferences,
    record_usage_feedback,
    health_check,
    get_service_info
)

# 工具系统导入
from .tools import (
    AIToolsRegistry,
    AIToolsFactory,
    ToolsMonitor
)

# ===========================================
# 导出接口
# ===========================================

__all__ = [
    # 核心Agent服务
    'get_autoreport_ai_agent',
    'get_placeholder_to_sql_agent', 
    'get_task_supplement_agent',
    'get_multi_context_integrator',
    'get_sql_testing_validator',
    'get_tool_based_agent',
    
    # LLM管理服务
    'get_llm_manager',
    'select_model_for_user',
    'ask_agent',
    'select_best_model_for_user',
    'ask_agent_for_user',
    'get_user_available_models',
    'get_user_preferences',
    'record_usage_feedback',
    'health_check',
    'get_service_info',
    
    # 工具系统服务
    'get_ai_tools_registry',
    'get_tools_factory',
    'get_chart_generator_tool',
    'AIToolsRegistry',
    'AIToolsFactory',
    'ToolsMonitor',
    
    # 核心工作流接口
    'execute_placeholder_with_context',
    
    # 监控和管理
    'get_ai_service_status',
]