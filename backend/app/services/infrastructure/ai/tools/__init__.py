"""
Infrastructure层AI工具服务

提供AI工具注册、工厂和监控的基础设施服务：

核心功能：
1. AI工具注册和发现
2. 工具工厂和组合管理
3. 工具性能监控
4. 工具生命周期管理

技术职责：
- 工具的注册、发现和实例化
- 工具组合和配置管理
- 工具执行监控和统计
- 工具健康检查和故障处理

本模块整合了原agents/tools/的功能，
提供更完善的工具管理基础设施。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .registry import AIToolsRegistry
    from .factory import AIToolsFactory
    from .monitor import ToolsMonitor

# 延迟导入和服务获取
_tools_instances = {}

# 导出核心类用于直接导入
from .registry import (
    AIToolsRegistry,
    ToolMetadata,
    ToolCategory,
    ToolComplexity,
    RegisteredTool
)
from .factory import (
    AIToolsFactory,
    ToolCreationError,
    create_standard_tool
)
from .monitor import (
    ToolsMonitor,
    ToolHealthStatus,
    AlertLevel,
    ToolExecutionMetric,
    ToolHealthCheck,
    Alert
)
from .integration_service import (
    AIToolsIntegrationService,
    TaskType,
    ToolRecommendation,
    create_ai_tools_integration_service
)
# 图表生成工具
from .chart_generator_tool import generate_chart, ChartGeneratorTool, generate_sample_data

async def get_ai_tools_registry() -> 'AIToolsRegistry':
    """获取AI工具注册表"""
    if 'tools_registry' not in _tools_instances:
        from .registry import AIToolsRegistry
        _tools_instances['tools_registry'] = AIToolsRegistry()
    return _tools_instances['tools_registry']

async def get_ai_tools_factory() -> 'AIToolsFactory':
    """获取AI工具工厂"""
    if 'tools_factory' not in _tools_instances:
        from .factory import AIToolsFactory
        
        # 获取注册表并创建工厂
        registry = await get_ai_tools_registry()
        _tools_instances['tools_factory'] = AIToolsFactory(registry=registry)
    return _tools_instances['tools_factory']

async def get_tools_monitor() -> 'ToolsMonitor':
    """获取工具监控器"""
    if 'tools_monitor' not in _tools_instances:
        from .monitor import ToolsMonitor
        _tools_instances['tools_monitor'] = ToolsMonitor()
    return _tools_instances['tools_monitor']

# React Agent工具系统统一接口

async def get_ai_tools_integration_service(user_id: str) -> 'AIToolsIntegrationService':
    """获取AI工具集成服务"""
    service_key = f'tools_integration_{user_id}'
    if service_key not in _tools_instances:
        from .integration_service import create_ai_tools_integration_service
        _tools_instances[service_key] = create_ai_tools_integration_service(user_id)
    return _tools_instances[service_key]

__all__ = [
    'get_ai_tools_registry',
    'get_ai_tools_factory',
    'get_tools_monitor',
    'get_ai_tools_integration_service',
    'generate_chart',
    'ChartGeneratorTool',
    'generate_sample_data'
]