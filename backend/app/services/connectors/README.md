# 数据源连接器模块

## 概述

数据源连接器模块提供了统一的数据源连接接口，支持多种数据源类型的连接、查询和管理。该模块采用工厂模式和策略模式，实现了高度的可扩展性和可维护性。

## 架构设计

### 核心组件

1. **BaseConnector** - 基础连接器抽象类
2. **ConnectorFactory** - 连接器工厂
3. **具体连接器实现** - 各种数据源的具体连接器

### 支持的数据源类型

- **Doris** - Apache Doris数据仓库
- **SQL** - 传统SQL数据库（MySQL、PostgreSQL等）
- **API** - REST API数据源
- **CSV** - CSV文件数据源

## 使用方式

### 基本用法

```python
from app.services.connectors import create_connector
from app.models.data_source import DataSource

# 创建连接器
connector = create_connector(data_source)

# 使用异步上下文管理器
async with connector:
    # 测试连接
    test_result = await connector.test_connection()
    
    # 执行查询
    result = await connector.execute_query("SELECT * FROM table LIMIT 10")
    
    # 获取字段列表
    fields = await connector.get_fields()
    
    # 获取数据预览
    preview = await connector.get_data_preview(limit=5)
```

### 连接器配置

每种连接器都有对应的配置类：

```python
from app.services.connectors import DorisConfig, SQLConfig, APIConfig, CSVConfig

# Doris配置
doris_config = DorisConfig(
    source_type="doris",
    name="my_doris",
    fe_hosts=["localhost"],
    database="default",
    username="root",
    password="password"
)

# SQL配置
sql_config = SQLConfig(
    source_type="sql",
    name="my_sql",
    connection_string="postgresql://user:pass@localhost/db"
)

# API配置
api_config = APIConfig(
    source_type="api",
    name="my_api",
    api_url="https://api.example.com/data",
    method="GET"
)

# CSV配置
csv_config = CSVConfig(
    source_type="csv",
    name="my_csv",
    file_path="/path/to/file.csv"
)
```

## 连接器特性

### 1. 统一接口

所有连接器都实现了相同的接口：

- `connect()` - 建立连接
- `disconnect()` - 断开连接
- `test_connection()` - 测试连接
- `execute_query()` - 执行查询
- `get_fields()` - 获取字段列表
- `get_tables()` - 获取表列表
- `get_data_preview()` - 获取数据预览

### 2. 异步支持

所有操作都是异步的，支持高并发场景：

```python
# 并发执行多个查询
async def fetch_multiple_sources(data_sources):
    tasks = []
    for source in data_sources:
        connector = create_connector(source)
        task = asyncio.create_task(connector.execute_query("SELECT * FROM table"))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

### 3. 连接池管理

SQL连接器支持连接池管理，提高性能：

```python
sql_config = SQLConfig(
    connection_string="postgresql://user:pass@localhost/db",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

### 4. 错误处理

统一的错误处理机制：

```python
try:
    async with connector:
        result = await connector.execute_query("SELECT * FROM table")
        if not result.success:
            print(f"Query failed: {result.error_message}")
        else:
            print(f"Query succeeded: {len(result.data)} rows")
except Exception as e:
    print(f"Connection failed: {e}")
```

## 扩展新的连接器

### 1. 创建配置类

```python
@dataclass
class NewDataSourceConfig(ConnectorConfig):
    """新数据源配置"""
    custom_param: str
    timeout: int = 30
```

### 2. 实现连接器类

```python
class NewDataSourceConnector(BaseConnector):
    """新数据源连接器"""
    
    def __init__(self, config: NewDataSourceConfig):
        super().__init__(config)
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def connect(self) -> None:
        """建立连接"""
        # 实现连接逻辑
        pass
    
    async def disconnect(self) -> None:
        """断开连接"""
        # 实现断开逻辑
        pass
    
    async def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        # 实现测试逻辑
        pass
    
    async def execute_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """执行查询"""
        # 实现查询逻辑
        pass
    
    async def get_fields(self, table_name: Optional[str] = None) -> List[str]:
        """获取字段列表"""
        # 实现字段获取逻辑
        pass
    
    async def get_tables(self) -> List[str]:
        """获取表列表"""
        # 实现表获取逻辑
        pass
```

### 3. 更新工厂

```python
def create_connector(data_source: DataSource) -> BaseConnector:
    if data_source.source_type == DataSourceType.new_source:
        return _create_new_source_connector(data_source)
    # ... 其他类型
```

## 性能优化

### 1. 连接复用

使用异步上下文管理器确保连接正确复用和释放：

```python
async with connector:
    # 连接自动建立
    result = await connector.execute_query("SELECT 1")
    # 连接自动释放
```

### 2. 查询优化

Doris连接器支持查询优化提示：

```python
optimization_hints = ["vectorization", "partition_pruning"]
result = await connector.execute_optimized_query(query, optimization_hints)
```

### 3. 批量操作

支持批量查询和数据处理：

```python
# 批量获取多个表的数据
tables = await connector.get_tables()
for table in tables:
    data = await connector.execute_query(f"SELECT * FROM {table}")
    # 处理数据
```

## 监控和日志

### 1. 查询性能监控

```python
result = await connector.execute_query("SELECT * FROM large_table")
print(f"Query executed in {result.execution_time:.3f}s")
print(f"Returned {len(result.data)} rows")
```

### 2. 连接状态监控

```python
info = await connector.get_connection_info()
print(f"Connected: {info['connected']}")
print(f"Source type: {info['source_type']}")
```

## 最佳实践

1. **总是使用异步上下文管理器**确保连接正确管理
2. **处理查询结果**检查success状态和错误信息
3. **合理设置超时时间**避免长时间等待
4. **使用连接池**对于频繁访问的SQL数据源
5. **实现错误重试**对于不稳定的连接
6. **监控查询性能**及时发现性能问题

## 故障排除

### 常见问题

1. **连接超时** - 检查网络和配置
2. **认证失败** - 验证用户名密码
3. **查询语法错误** - 检查SQL语句
4. **权限不足** - 确认数据库权限

### 调试技巧

```python
import logging
logging.getLogger("app.services.connectors").setLevel(logging.DEBUG)

# 启用详细日志
connector.logger.setLevel(logging.DEBUG)
```
