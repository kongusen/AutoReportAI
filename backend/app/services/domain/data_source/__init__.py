"""
Domain层数据源服务

负责数据源相关的核心业务逻辑和规则：

核心职责：
1. 数据源实体的业务逻辑
2. 数据源连接和验证规则
3. 数据源权限和安全策略
4. 数据源配置的业务验证

Domain层特点：
- 包含核心业务逻辑
- 独立于技术实现
- 可被Application层调用
- 不依赖外部基础设施
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .services.data_source_domain_service import DataSourceDomainService
    from .entities.data_source_entity import DataSourceEntity

# 延迟导入和服务获取
_domain_instances = {}

async def get_data_source_domain_service() -> 'DataSourceDomainService':
    """获取数据源领域服务"""
    if 'data_source_domain' not in _domain_instances:
        from .services.data_source_domain_service import DataSourceDomainService
        _domain_instances['data_source_domain'] = DataSourceDomainService()
    return _domain_instances['data_source_domain']

# 导出核心类
from .entities import DataSourceEntity, DataSourceType, DataSourceStatus
from .services import DataSourceDomainService
from .value_objects import ConnectionConfig, DataSourceCredentials, CredentialType

__all__ = [
    'get_data_source_domain_service',
    'DataSourceEntity',
    'DataSourceType', 
    'DataSourceStatus',
    'DataSourceDomainService',
    'ConnectionConfig',
    'DataSourceCredentials',
    'CredentialType'
]