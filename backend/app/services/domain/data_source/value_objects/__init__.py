"""
Domain层数据源值对象

定义数据源相关的值对象：

核心值对象：
1. ConnectionConfig - 连接配置值对象
2. DataSourceCredentials - 数据源凭据值对象

Value Objects特点：
- 不可变对象
- 通过值比较相等性
- 封装相关的业务逻辑
"""

from .connection_config import ConnectionConfig
from .data_source_credentials import DataSourceCredentials, CredentialType

__all__ = [
    'ConnectionConfig',
    'DataSourceCredentials',
    'CredentialType'
]