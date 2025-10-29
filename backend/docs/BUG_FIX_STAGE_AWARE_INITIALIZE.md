# Bug Fix: StageAwareContextRetriever 缺少 initialize 方法

## 问题描述

执行报告任务时出现 `AttributeError`：

```
[2025-10-25 12:37:15,228: WARNING/ForkPoolWorker-1] ⚠️ Schema Context 初始化失败:
'StageAwareContextRetriever' object has no attribute 'initialize'

Traceback (most recent call last):
  File "/app/app/services/infrastructure/task_queue/tasks.py", line 225, in execute_report_task
    run_async(schema_context_retriever.retriever.initialize())
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'StageAwareContextRetriever' object has no attribute 'initialize'
```

## 根本原因

在 `context_retriever.py` 的 `create_schema_context_retriever()` 函数中：

1. 当 `enable_stage_aware=True` 时（这是默认设置），会创建 `StageAwareContextRetriever` 包装 `SchemaContextRetriever`
2. `SchemaContextRetriever` 有 `initialize()` 方法用于预加载表结构
3. 但 `StageAwareContextRetriever` 没有实现 `initialize()` 方法
4. `tasks.py:225` 调用 `schema_context_retriever.retriever.initialize()` 时失败

**调用链分析：**

```python
# context_retriever.py:486-497
stage_aware_retriever = StageAwareContextRetriever(
    schema_retriever=schema_retriever,  # 这个有 initialize()
    state_manager=state_manager
)

retriever = ContextRetriever(
    retriever=stage_aware_retriever,  # 包装后的对象没有 initialize()
    ...
)

# tasks.py:225
schema_context_retriever.retriever.initialize()  # ❌ 访问的是 StageAwareContextRetriever，没有此方法
schema_context_retriever.retriever.schema_cache  # ❌ 也没有此属性
```

## 解决方案

在 `StageAwareContextRetriever` 类中添加两个代理方法/属性，委托给内部的 `schema_retriever`：

### 1. 添加 `initialize()` 方法

```python
async def initialize(self):
    """
    初始化方法：委托给底层的 schema_retriever

    这是一个代理方法，确保外部调用者可以直接调用 StageAwareContextRetriever.initialize()
    而不需要知道内部的 schema_retriever 结构
    """
    logger.info("🔧 [StageAwareRetriever] 初始化 schema 缓存")
    await self.schema_retriever.initialize()
```

### 2. 添加 `schema_cache` 属性

```python
@property
def schema_cache(self):
    """
    暴露底层 schema_retriever 的 schema_cache

    这允许外部代码访问缓存的表结构信息
    """
    return self.schema_retriever.schema_cache
```

## 修改文件

- `backend/app/services/infrastructure/agents/context_manager.py`
  - 在 `StageAwareContextRetriever` 类中添加 `initialize()` 方法（第175-183行）
  - 在 `StageAwareContextRetriever` 类中添加 `schema_cache` 属性（第185-192行）

## 验证

使用 AST 解析验证脚本 `scripts/verify_initialize_fix.py` 确认：
- ✅ `async def initialize()` 方法已添加
- ✅ `@property schema_cache` 属性已添加

## 预期效果

修复后，`tasks.py` 中的以下代码将正常工作：

```python
# Line 225: 初始化 schema 缓存
run_async(schema_context_retriever.retriever.initialize())

# Line 227: 访问缓存的表数量
table_count = len(schema_context_retriever.retriever.schema_cache)
```

Schema Context 将成功初始化，Agent 在生成 SQL 时将自动获得准确的表结构上下文信息。

## 相关文件

- `backend/app/services/infrastructure/agents/context_manager.py` - 修复文件
- `backend/app/services/infrastructure/task_queue/tasks.py` - 调用方
- `backend/app/services/infrastructure/agents/context_retriever.py` - 创建上下文检索器的工厂函数

## 设计改进建议

为了避免类似问题，可以考虑：

1. **接口定义**: 定义一个明确的 `BaseContextRetriever` 协议/抽象类，规定所有检索器必须实现的方法
2. **类型注解**: 使用更严格的类型注解和类型检查工具（如 mypy）
3. **单元测试**: 为包装类添加单元测试，确保所有必要的方法都被正确委托

## 日期

2025-10-25
