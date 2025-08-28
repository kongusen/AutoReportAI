"""
IAOP API层 - 统一的外部接口

提供RESTful API和内部调用接口，支持：
- 占位符解析和报告生成
- Agent管理和状态查询
- 编排引擎控制
- 系统监控和配置
"""

from .endpoints import IAOPAPIRouter, create_iaop_router, get_iaop_router
from .services import IAOPService, get_iaop_service
from .schemas import *

__all__ = [
    'IAOPAPIRouter',
    'IAOPService',
    'get_iaop_service',
    'create_iaop_router',
    'get_iaop_router',
    'PlaceholderRequest',
    'ReportGenerationRequest',
    'AgentStatusResponse',
    'ReportResponse'
]