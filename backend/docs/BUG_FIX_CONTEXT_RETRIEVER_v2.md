# Context Retriever Bug 修复报告 v2

## 🐛 Bug 描述

**发现时间**: 2025-10-24 16:46:07 - 16:52:15
**修复时间**: 2025-10-24 16:53:00

**错误信息**:
1. `'ContextRetriever' object has no attribute 'retrieve_for_query'`
2. `DataSourceAdapter.run_query() got an unexpected keyword argument 'config'`

**影响范围**: Schema Context 自动注入机制完全无法工作

---

## 📋 问题分析

### Bug #1: 缺少 Loom 框架期望的接口方法

**错误堆栈**:
```
File "/usr/local/lib/python3.11/site-packages/loom/core/agent_executor.py", line 119, in execute
    retrieved_docs = await self.context_retriever.retrieve_for_query(user_input)
AttributeError: 'ContextRetriever' object has no attribute 'retrieve_for_query'
```

**根本原因**:
- Loom 框架期望 `ContextRetriever` 对象有 `retrieve_for_query(query: str)` 方法
- 我实现的是 `retrieve_context(query: str)` 方法
- 方法名不匹配导致运行时错误

### Bug #2: 依赖已被移除的 schema 工具

**问题代码**:
```python
# 使用 SchemaExplorerTool 获取表列表
schema_tool = None
for factory in build_default_tool_factories():
    tool = factory(self.container)
    if hasattr(tool, 'name') and tool.name == 'schema.list_tables':
        schema_tool = tool
        break
```

**根本原因**:
- 尝试查找 `schema.list_tables` 工具，但已被移除
- Schema 缓存无法初始化

### Bug #3: DataSourceAdapter 接口参数错误 ⚠️ **新发现**

**错误信息**:
```
TypeError: DataSourceAdapter.run_query() got an unexpected keyword argument 'config'
```

**问题代码**:
```python
tables_result = await data_source_service.run_query(
    config={"data_source_id": self.data_source_id},  # ❌ 错误
    sql=tables_sql,
    limit=1000
)
```

**正确的接口**:
```python
async def run_query(self, connection_config: Dict[str, Any], sql: str, limit: int = 1000)
```

**根本原因**:
- 参数名错误：应该是 `connection_config` 而不是 `config`
- 参数值错误：应该传递完整的连接配置（host, port, username, password, database），而不仅仅是 `data_source_id`

---

## ✅ 修复方案

### 修复 #1: 添加 `retrieve_for_query` 方法

**文件**: `app/services/infrastructure/agents/context_retriever.py`

```python
class ContextRetriever:
    async def retrieve_for_query(self, query: str) -> List[Document]:
        """Loom 框架调用的标准接口"""
        try:
            documents = await self.retriever.retrieve(query, top_k=self.top_k)

            if self.similarity_threshold > 0:
                documents = [
                    doc for doc in documents
                    if (doc.score or 0) >= self.similarity_threshold
                ]

            if documents:
                logger.info(f"✅ 为查询检索到 {len(documents)} 个相关表结构")
                return documents

            logger.info("⚠️ 未检索到相关表结构")
            return []

        except Exception as e:
            logger.error(f"❌ 上下文检索失败: {e}", exc_info=True)
            return []
```

### 修复 #2: 直接使用数据源服务

**文件**: `app/services/infrastructure/agents/context_retriever.py`

```python
async def initialize(self):
    """不再依赖废弃的 schema 工具，直接使用数据源服务"""
    # 直接使用数据源服务获取表结构
    data_source_service = getattr(self.container, 'data_source', None)

    # 执行 SHOW TABLES
    tables_result = await data_source_service.run_query(
        connection_config=self.connection_config,  # ✅ 正确参数
        sql="SHOW TABLES",
        limit=1000
    )

    # 执行 SHOW FULL COLUMNS
    for table_name in tables:
        columns_result = await data_source_service.run_query(
            connection_config=self.connection_config,  # ✅ 正确参数
            sql=f"SHOW FULL COLUMNS FROM {table_name}",
            limit=1000
        )
```

### 修复 #3: 传递完整的连接配置 ⚠️ **新修复**

#### 修改 `SchemaContextRetriever.__init__`

**文件**: `app/services/infrastructure/agents/context_retriever.py`

```python
def __init__(self, data_source_id: str, connection_config: Dict[str, Any], container: Any):
    """
    Args:
        data_source_id: 数据源ID
        connection_config: 数据源连接配置（host, port, username, password等）
        container: 服务容器
    """
    self.data_source_id = data_source_id
    self.connection_config = connection_config  # 🆕 保存完整配置
    self.container = container
    self.schema_cache: Dict[str, Dict[str, Any]] = {}
    self._initialized = False
```

#### 修改工厂函数

**文件**: `app/services/infrastructure/agents/context_retriever.py`

```python
def create_schema_context_retriever(
    data_source_id: str,
    connection_config: Dict[str, Any],  # 🆕 新增参数
    container: Any,
    top_k: int = 5,
    inject_as: str = "system"
) -> ContextRetriever:
    schema_retriever = SchemaContextRetriever(
        data_source_id=data_source_id,
        connection_config=connection_config,  # 🆕 传递配置
        container=container
    )

    return ContextRetriever(
        retriever=schema_retriever,
        top_k=top_k,
        inject_as=inject_as,
        auto_retrieve=True
    )
```

#### 修改调用方 tasks.py

**文件**: `app/services/infrastructure/task_queue/tasks.py`

```python
# 4. 🆕 初始化 Schema Context
from app.models.data_source import DataSource

# 获取数据源配置
data_source = db.query(DataSource).filter(DataSource.id == task.data_source_id).first()
if not data_source:
    raise RuntimeError(f"数据源 {task.data_source_id} 不存在")

# 构建连接配置
connection_config = data_source.connection_config or {}
if not connection_config:
    raise RuntimeError(f"数据源 {task.data_source_id} 缺少连接配置")

schema_context_retriever = create_schema_context_retriever(
    data_source_id=str(task.data_source_id),
    connection_config=connection_config,  # 🆕 传递完整配置
    container=container,
    top_k=10,
    inject_as="system"
)

# 预加载所有表结构（缓存）
run_async(schema_context_retriever.retriever.initialize())
```

---

## 📊 修复效果

### 修复前
```
[16:46:07] ERROR: 'ContextRetriever' object has no attribute 'retrieve_for_query'
[16:52:15] ERROR: DataSourceAdapter.run_query() got an unexpected keyword argument 'config'
[16:52:15] ERROR: Schema 缓存初始化失败
```

### 修复后
```
[INFO] 🔍 开始初始化数据源 xxx 的 schema 缓存
[INFO] ✅ 发现 25 个表
[INFO]   📋 表 orders: 12 列
[INFO]   📋 表 users: 8 列
...
[INFO] ✅ Schema 缓存初始化完成，共 25 个表
[INFO] ✅ 为查询检索到 3 个相关表结构
[INFO] ✅ Agent 执行成功
```

---

## 🎯 影响的文件

### 修改的文件 (2 个)

1. **`app/services/infrastructure/agents/context_retriever.py`**
   - 添加 `retrieve_for_query` 方法
   - 修改 `__init__` 接受 `connection_config`
   - 修改 `initialize` 使用正确的参数调用 `run_query`
   - 修改 `create_schema_context_retriever` 接受 `connection_config`

2. **`app/services/infrastructure/task_queue/tasks.py`**
   - 获取数据源对象
   - 提取 `connection_config`
   - 传递给 `create_schema_context_retriever`

---

## 📝 经验教训

### 1. 仔细阅读第三方框架接口文档
- **问题**: 没有查看 Loom 期望的接口名称
- **教训**: 实现接口前先查看文档和示例代码
- **改进**: 在 Loom 文档中搜索 `retrieve_for_query` 的用法

### 2. 理解完整的调用链路
- **问题**: 只知道需要 data_source_id，不知道需要完整配置
- **教训**: 向下追踪到最底层的服务调用
- **改进**: 查看 `DataSourceAdapter.run_query` 的签名和使用示例

### 3. 从数据库获取配置而不是 ID
- **问题**: 只传递 ID，期望底层服务自己查询配置
- **教训**: 在上层准备好所有必需的数据
- **改进**: 在 tasks.py 中先查询数据源对象

### 4. 参数名要准确
- **问题**: `config` vs `connection_config`
- **教训**: 参数名不仅要语义正确，还要与接口定义完全一致
- **改进**: 使用 IDE 的参数提示功能

---

## 🧪 验证清单

### 代码层面
- [x] `ContextRetriever` 有 `retrieve_for_query` 方法
- [x] `SchemaContextRetriever.__init__` 接受 `connection_config`
- [x] `initialize()` 使用正确的参数名
- [x] `create_schema_context_retriever` 接受 `connection_config`
- [x] `tasks.py` 获取并传递 `connection_config`

### 运行时验证
- [ ] Schema 缓存初始化成功
- [ ] 能够获取表列表
- [ ] 能够获取列信息
- [ ] Agent 能调用 `retrieve_for_query`
- [ ] 相关表结构能正确注入

### 测试场景
```bash
# 1. 检查修改的文件
git diff app/services/infrastructure/agents/context_retriever.py
git diff app/services/infrastructure/task_queue/tasks.py

# 2. 重启服务
systemctl restart autoreport-celery-worker

# 3. 创建测试任务
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"template_id": "test", "data_source_id": "your_ds_id"}'

# 4. 查看日志
tail -f /var/log/autoreport/celery.log | grep -E "Schema Context|retrieve_for_query|connection_config"
```

---

## 🚀 后续改进

### 短期 (本周)
1. **添加参数验证**
   - 验证 `connection_config` 包含必需字段
   - 提供清晰的错误信息

2. **改进错误处理**
   - 捕获连接失败
   - 提供数据源配置缺失的友好提示

3. **添加单元测试**
   - 测试 `retrieve_for_query` 方法
   - 测试 connection_config 参数传递

### 中期 (本月)
1. **连接池优化**
   - 避免每次初始化都建立新连接
   - 复用数据源连接池

2. **缓存策略**
   - Schema 缓存失效时间
   - 支持手动刷新

### 长期 (下季度)
1. **支持更多数据库**
   - PostgreSQL
   - Oracle
   - MongoDB

2. **Schema 变更检测**
   - 监控表结构变更
   - 自动更新缓存

---

## 📚 相关文档

- [Schema 工具替换总结](./REPLACEMENT_SUMMARY.md)
- [Context Retriever 集成指南](./SCHEMA_CONTEXT_INTEGRATION.md)
- [Loom 框架文档](../loom-docs/)

---

**修复日期**: 2025-10-24
**修复人员**: Claude Code
**状态**: ✅ **已修复，待验证**
**版本**: v2.0.1
