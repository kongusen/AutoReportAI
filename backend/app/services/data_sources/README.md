# 数据源服务模块

## 概述

数据源服务模块提供了完整的数据源管理功能，包括数据源的创建、验证、连接测试、数据获取和同步等功能。该模块与连接器模块紧密集成，提供了统一的数据源管理接口。

## 模块结构

```
data_sources/
├── __init__.py                 # 模块初始化
├── data_source_service.py      # 数据源服务主类
├── connection_pool_manager.py  # 连接池管理器
└── README.md                   # 本文档
```

## 核心组件

### 1. DataSourceService

数据源服务主类，提供以下功能：

- **数据源创建** - 创建和验证各种类型的数据源
- **连接测试** - 测试数据源连接状态
- **数据获取** - 从数据源获取数据
- **数据预览** - 获取数据源的数据预览
- **字段获取** - 获取数据源的字段列表
- **数据同步** - 同步数据源状态

### 2. ConnectionPoolManager

连接池管理器，专门管理SQL数据库连接池：

- **连接池创建** - 根据连接字符串创建连接池
- **连接复用** - 复用数据库连接，提高性能
- **连接管理** - 管理连接的生命周期
- **连接监控** - 监控连接池状态

## 使用方式

### 基本用法

```python
from app.services.data_sources import data_source_service

# 创建数据源
source_config = {
    "name": "my_doris_source",
    "source_type": "doris",
    "doris_fe_hosts": ["localhost"],
    "doris_database": "default",
    "doris_username": "root",
    "doris_password": "password"
}

result = await data_source_service.create_data_source(source_config, user_id="user123")
print(f"Created data source: {result['id']}")

# 测试连接
test_result = await data_source_service.test_connection(result['id'])
print(f"Connection test: {test_result['success']}")

# 获取数据
df = await data_source_service.fetch_data(result['id'], {"limit": 100})
print(f"Fetched {len(df)} rows")

# 获取数据预览
preview = await data_source_service.get_data_preview(result['id'], limit=10)
print(f"Preview columns: {preview['columns']}")

# 获取字段列表
fields = await data_source_service.get_data_source_fields(result['id'])
print(f"Available fields: {fields}")
```

### 数据源类型支持

#### 1. Doris数据源

```python
doris_config = {
    "name": "doris_warehouse",
    "source_type": "doris",
    "doris_fe_hosts": ["fe1.example.com", "fe2.example.com"],
    "doris_be_hosts": ["be1.example.com", "be2.example.com"],
    "doris_http_port": 8030,
    "doris_query_port": 9030,
    "doris_database": "analytics",
    "doris_username": "analytics_user",
    "doris_password": "secure_password",
    "wide_table_name": "user_behavior"
}
```

#### 2. SQL数据源

```python
sql_config = {
    "name": "postgres_db",
    "source_type": "sql",
    "connection_string": "postgresql://user:pass@localhost/dbname",
    "sql_query_type": "single_table",
    "base_query": "SELECT * FROM users WHERE status = 'active'",
    "column_mapping": {
        "user_id": "id",
        "user_name": "name"
    }
}
```

#### 3. API数据源

```python
api_config = {
    "name": "rest_api",
    "source_type": "api",
    "api_url": "https://api.example.com/data",
    "api_method": "GET",
    "api_headers": {
        "Authorization": "Bearer token123",
        "Content-Type": "application/json"
    },
    "api_body": None
}
```

#### 4. CSV数据源

```python
csv_config = {
    "name": "csv_file",
    "source_type": "csv",
    "file_path": "/path/to/data.csv",
    "encoding": "utf-8",
    "delimiter": ","
}
```

## 高级功能

### 1. 多表联查配置

```python
multi_table_config = {
    "name": "complex_query",
    "source_type": "sql",
    "connection_string": "postgresql://user:pass@localhost/dbname",
    "sql_query_type": "multi_table",
    "join_config": {
        "tables": [
            {"name": "users", "fields": ["id", "name", "email"]},
            {"name": "orders", "fields": ["id", "user_id", "amount"]}
        ],
        "joins": [
            {
                "type": "INNER",
                "left_table": "users",
                "right_table": "orders",
                "condition": "users.id = orders.user_id"
            }
        ]
    }
}
```

### 2. 查询参数化

```python
# 获取数据时传递参数
query_params = {
    "limit": 1000,
    "date_from": "2024-01-01",
    "date_to": "2024-12-31",
    "status": "active"
}

df = await data_source_service.fetch_data(source_id, query_params)
```

### 3. 列映射

```python
# 在数据源配置中定义列映射
column_mapping = {
    "user_id": "id",
    "user_name": "name",
    "user_email": "email",
    "created_at": "timestamp"
}

# 获取数据时会自动应用列映射
df = await data_source_service.fetch_data(source_id)
# df的列名会被映射为新的名称
```

## 错误处理

### 1. 连接错误

```python
try:
    test_result = await data_source_service.test_connection(source_id)
    if not test_result['success']:
        print(f"Connection failed: {test_result['error']}")
except Exception as e:
    print(f"Test connection error: {e}")
```

### 2. 数据获取错误

```python
try:
    df = await data_source_service.fetch_data(source_id)
except ValueError as e:
    print(f"Data fetch failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## 性能优化

### 1. 连接池管理

```python
from app.services.data_sources import ConnectionPoolManager

# 创建连接池管理器
pool_manager = ConnectionPoolManager()

# 获取连接池
engine = pool_manager.get_engine(
    connection_string="postgresql://user:pass@localhost/db",
    pool_size=10
)

# 获取连接池信息
pool_info = pool_manager.get_pool_info()
print(f"Active pools: {pool_info['total_pools']}")

# 清理连接池
pool_manager.close_all_pools()
```

### 2. 批量操作

```python
# 批量测试多个数据源连接
async def test_multiple_sources(source_ids):
    tasks = []
    for source_id in source_ids:
        task = data_source_service.test_connection(source_id)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# 批量获取数据
async def fetch_multiple_sources(source_ids, query_params=None):
    tasks = []
    for source_id in source_ids:
        task = data_source_service.fetch_data(source_id, query_params)
        tasks.append(task)
    
    dataframes = await asyncio.gather(*tasks, return_exceptions=True)
    return dataframes
```

## 监控和日志

### 1. 服务状态监控

```python
# 获取数据源服务状态
service_status = {
    "active_connections": len(data_source_service.connection_manager._pools),
    "total_data_sources": await get_total_data_sources(),
    "last_sync_time": datetime.now().isoformat()
}
```

### 2. 性能监控

```python
import time

# 监控数据获取性能
start_time = time.time()
df = await data_source_service.fetch_data(source_id)
execution_time = time.time() - start_time

print(f"Data fetch completed in {execution_time:.3f}s")
print(f"Retrieved {len(df)} rows")
```

## 最佳实践

### 1. 数据源命名

```python
# 使用描述性的名称
good_names = [
    "user_behavior_doris",
    "sales_data_postgres",
    "api_analytics_rest",
    "customer_feedback_csv"
]

# 避免使用通用名称
bad_names = [
    "data",
    "source",
    "db",
    "api"
]
```

### 2. 连接字符串安全

```python
# 使用环境变量存储敏感信息
import os

connection_string = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)
```

### 3. 错误重试

```python
import asyncio
from functools import wraps

def retry_on_error(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

# 使用重试装饰器
@retry_on_error(max_retries=3)
async def reliable_fetch_data(source_id):
    return await data_source_service.fetch_data(source_id)
```

## 故障排除

### 常见问题

1. **连接超时**
   - 检查网络连接
   - 验证连接字符串
   - 调整超时设置

2. **认证失败**
   - 验证用户名密码
   - 检查数据库权限
   - 确认认证方式

3. **查询语法错误**
   - 验证SQL语句
   - 检查表名和字段名
   - 确认数据库方言

4. **权限不足**
   - 检查数据库用户权限
   - 验证表访问权限
   - 确认API访问权限

### 调试技巧

```python
import logging

# 启用详细日志
logging.getLogger("app.services.data_sources").setLevel(logging.DEBUG)

# 启用连接器日志
logging.getLogger("app.services.connectors").setLevel(logging.DEBUG)

# 查看连接池状态
pool_info = data_source_service.connection_manager.get_pool_info()
print(f"Connection pools: {pool_info}")
```
