"""
Domain层数据源实体

定义数据源相关的核心业务实体和枚举：

核心实体：
1. DataSourceEntity - 数据源核心实体
2. DataSourceType - 数据源类型枚举
3. DataSourceStatus - 数据源状态枚举

Domain层实体特点：
- 包含核心业务逻辑
- 封装业务规则和验证
- 独立于技术实现
"""

from .data_source_entity import (
    DataSourceEntity,
    DataSourceType,
    DataSourceStatus
)

__all__ = [
    'DataSourceEntity',
    'DataSourceType',
    'DataSourceStatus'
]