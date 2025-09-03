"""
Infrastructure层AI服务

提供统一的AI基础设施服务，作为DDD架构中的技术基础设施层：

核心职责：
1. 智能代理执行引擎和DAG编排
2. LLM集成、路由和模型管理  
3. AI工具链注册和工厂管理
4. 执行上下文和步骤管理

架构特点：
- 符合DDD Infrastructure层定位
- 为Domain层和Application层提供AI技术支撑
- 统一的AI服务接口和管理
- 支持原有agents系统的渐进式迁移

迁移说明：
本模块整合了原 app/services/agents/ 和 app/services/llm/ 的功能，
重新组织为符合DDD架构的Infrastructure层AI服务。
"""

# 延迟导入避免循环依赖
from typing import TYPE_CHECKING, Optional, Dict, Any

if TYPE_CHECKING:
    from .agents.dag_controller import DAGController
    from .agents.execution_engine import AIExecutionEngine
    from .llm.client_adapter import LLMClientAdapter
    from .tools.registry import AIToolsRegistry

# 全局服务实例缓存
_ai_service_instances: Dict[str, Any] = {}

# 核心AI服务接口
async def get_dag_controller() -> 'DAGController':
    """获取DAG编排控制器"""
    if 'dag_controller' not in _ai_service_instances:
        from .agents.dag_controller import DAGController
        _ai_service_instances['dag_controller'] = DAGController()
    return _ai_service_instances['dag_controller']

async def get_ai_execution_engine() -> 'AIExecutionEngine':
    """获取AI执行引擎"""
    if 'execution_engine' not in _ai_service_instances:
        from .agents.execution_engine import AIExecutionEngine
        _ai_service_instances['execution_engine'] = AIExecutionEngine()
    return _ai_service_instances['execution_engine']

async def get_llm_client_adapter():
    """获取LLM客户端适配器（向后兼容）"""
    # 返回新架构的兼容客户端
    from .llm import get_llm_client
    return get_llm_client()

async def get_ai_tools_registry() -> 'AIToolsRegistry':
    """获取AI工具注册表"""
    if 'tools_registry' not in _ai_service_instances:
        from .tools.registry import AIToolsRegistry
        _ai_service_instances['tools_registry'] = AIToolsRegistry()
    return _ai_service_instances['tools_registry']

# 保持向后兼容的主要接口
async def execute_placeholder_with_context(
    placeholder_text: str,
    statistical_type: str,
    description: str,
    context_engine: Dict[str, Any],
    user_id: str = "system"
) -> Dict[str, Any]:
    """
    使用AI基础设施处理占位符的主入口函数
    
    这是原 app.services.agents.execute_placeholder_with_context 的迁移版本，
    保持完全的API兼容性，但使用新的Infrastructure层AI架构。
    
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
        # 获取AI执行引擎
        execution_engine = await get_ai_execution_engine()
        
        # 使用新架构执行占位符处理
        result = await execution_engine.execute_placeholder_task(
            placeholder_text=placeholder_text,
            statistical_type=statistical_type,
            description=description,
            context_engine=context_engine,
            user_id=user_id
        )
        
        return result
        
    except Exception as e:
        # 兼容性错误处理
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Infrastructure AI执行占位符任务失败: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'fallback': True,
            'source': 'infrastructure_ai'
        }

# 向后兼容的别名接口
async def get_react_agent():
    """获取React智能代理 - 向后兼容接口"""
    from .agents.react_agent import ReactAgent
    return ReactAgent()

async def get_model_manager():
    """获取模型管理器（向后兼容）"""
    # 返回新架构的LLM管理器作为兼容对象
    from .llm import get_llm_manager
    return await get_llm_manager()

async def get_tools_factory():
    """获取工具工厂"""
    if 'tools_factory' not in _ai_service_instances:
        from .tools.factory import AIToolsFactory
        _ai_service_instances['tools_factory'] = AIToolsFactory()
    return _ai_service_instances['tools_factory']

# 统一AI服务状态和健康检查
async def get_ai_service_status() -> Dict[str, Any]:
    """获取AI服务整体状态"""
    try:
        status = {
            'service_name': 'Infrastructure AI Service',
            'version': '2.0.0-ddd',
            'architecture': 'DDD Infrastructure Layer',
            'status': 'running',
            'components': {}
        }
        
        # 检查各组件状态
        try:
            dag_controller = await get_dag_controller()
            status['components']['dag_controller'] = 'available'
        except Exception:
            status['components']['dag_controller'] = 'unavailable'
            
        try:
            execution_engine = await get_ai_execution_engine() 
            status['components']['execution_engine'] = 'available'
        except Exception:
            status['components']['execution_engine'] = 'unavailable'
            
        try:
            llm_client = await get_llm_client_adapter()
            status['components']['llm_client'] = 'available'
        except Exception:
            status['components']['llm_client'] = 'unavailable'
            
        try:
            tools_registry = await get_ai_tools_registry()
            status['components']['tools_registry'] = 'available'
        except Exception:
            status['components']['tools_registry'] = 'unavailable'
        
        # 计算总体健康度
        available_count = sum(1 for s in status['components'].values() if s == 'available')
        total_count = len(status['components'])
        status['health_score'] = available_count / total_count if total_count > 0 else 0
        
        return status
        
    except Exception as e:
        return {
            'service_name': 'Infrastructure AI Service',
            'status': 'error',
            'error': str(e),
            'health_score': 0
        }

# 迁移信息和使用指南
def get_migration_info() -> Dict[str, Any]:
    """获取迁移信息和使用指南"""
    return {
        'migration_status': 'in_progress',
        'from': ['app.services.agents', 'app.services.llm'],
        'to': 'app.services.infrastructure.ai',
        'architecture_change': 'Standalone layer → DDD Infrastructure Layer',
        
        'api_compatibility': {
            'execute_placeholder_with_context': 'Full compatibility maintained',
            'get_react_agent': 'Backward compatible alias provided',
            'llm_services': 'Integrated into unified AI service',
            'tools_system': 'Enhanced with factory pattern'
        },
        
        'usage_guide': {
            'new_imports': [
                'from app.services.infrastructure.ai import execute_placeholder_with_context',
                'from app.services.infrastructure.ai import get_dag_controller',
                'from app.services.infrastructure.ai import get_ai_execution_engine'
            ],
            'old_imports_still_work': [
                'app.services.agents.execute_placeholder_with_context',
                # Will be gradually deprecated
            ]
        },
        
        'benefits': [
            'Complies with DDD Architecture principles',
            'Unified AI infrastructure management', 
            'Better separation of concerns',
            'Enhanced testability and maintainability',
            'Improved service discovery and health monitoring'
        ]
    }

# 导出核心类用于直接导入
from .agents import (
    DAGController,
    AIExecutionEngine,
    AITaskContext,
    ReactAgent,
    ControlContext,
    ControlDecision,
    ExecutionStatus,
    StepResult,
    ExecutionStep,
    ExecutionStepType,
    ModelRequirement,
    TaskComplexity
)
from .llm import (
    select_best_model_for_user,
    ask_agent_for_user,
    health_check,
    get_service_info
    # call_llm,
    # ask_agent,
    # get_best_model_for_task,
    # register_provider,
    # list_available_models,
    # call_llm_with_system_prompt,
    # get_llm_client
)
from .tools import (
    AIToolsRegistry,
    AIToolsFactory,
    ToolsMonitor,
    ToolMetadata,
    ToolCategory,
    ToolComplexity,
)

__all__ = [
    # 核心AI服务
    'get_dag_controller',
    'get_ai_execution_engine', 
    'get_llm_client_adapter',
    'get_ai_tools_registry',
    
    # 主要处理接口
    'execute_placeholder_with_context',
    
    # LlamaIndex LLM接口
    'call_llm',
    'ask_agent',
    'get_best_model_for_task',
    'register_provider',
    'list_available_models',
    'health_check',
    'call_llm_with_system_prompt',
    'get_llm_client',
    
    # 管理和监控
    'get_ai_service_status',
    'get_migration_info',
    
    # 向后兼容接口
    'get_react_agent',
    'get_model_manager',
    'get_tools_factory',
    
    # 导出的类
    'DAGController',
    'AIExecutionEngine', 
    'AITaskContext',
    'ReactAgent',
    'AIToolsRegistry',
    'AIToolsFactory',
    'ToolsMonitor'
]