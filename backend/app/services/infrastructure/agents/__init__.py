"""
Infrastructure层Agent服务

Infrastructure层的Agent专注于技术实现和外部集成：
1. LLM服务集成
2. 外部API调用
3. 数据转换和处理
4. 工具执行和管理

不应包含：
- 业务逻辑（属于Domain层）
- 工作流编排（属于Application层）
- 数据建模（属于Domain层）
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .llm_integration_agent import LLMIntegrationAgent
    from .data_transformation_agent import DataTransformationAgent
    from .external_api_agent import ExternalApiAgent
    from .tool_execution_agent import ToolExecutionAgent

# 全局服务实例缓存
_infrastructure_agent_instances = {}

async def get_llm_integration_agent() -> 'LLMIntegrationAgent':
    """获取LLM集成代理实例"""
    if 'llm_integration' not in _infrastructure_agent_instances:
        from .llm_integration_agent import LLMIntegrationAgent
        _infrastructure_agent_instances['llm_integration'] = LLMIntegrationAgent()
    return _infrastructure_agent_instances['llm_integration']

async def get_data_transformation_agent() -> 'DataTransformationAgent':
    """获取数据转换代理实例"""
    if 'data_transformation' not in _infrastructure_agent_instances:
        from .data_transformation_agent import DataTransformationAgent
        _infrastructure_agent_instances['data_transformation'] = DataTransformationAgent()
    return _infrastructure_agent_instances['data_transformation']

async def get_external_api_agent() -> 'ExternalApiAgent':
    """获取外部API代理实例"""
    if 'external_api' not in _infrastructure_agent_instances:
        from .external_api_agent import ExternalApiAgent
        _infrastructure_agent_instances['external_api'] = ExternalApiAgent()
    return _infrastructure_agent_instances['external_api']

async def get_tool_execution_agent() -> 'ToolExecutionAgent':
    """获取工具执行代理实例"""
    if 'tool_execution' not in _infrastructure_agent_instances:
        from .tool_execution_agent import ToolExecutionAgent
        _infrastructure_agent_instances['tool_execution'] = ToolExecutionAgent()
    return _infrastructure_agent_instances['tool_execution']

# 别名方法，保持与现有代码的兼容性
async def get_data_extraction_agent():
    """获取数据提取代理实例 - 重用数据转换代理"""
    return await get_data_transformation_agent()

async def get_result_storage_agent():
    """获取结果存储代理实例 - 重用现有存储服务"""
    from ..storage import get_intelligent_result_storage
    return await get_intelligent_result_storage()

__all__ = [
    'get_llm_integration_agent',
    'get_data_transformation_agent',
    'get_external_api_agent',
    'get_tool_execution_agent',
    'get_data_extraction_agent',
    'get_result_storage_agent'
]