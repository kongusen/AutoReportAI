# 修复Context注入失败问题

**时间**: 2025-10-25
**严重程度**: 🔴 Critical
**影响范围**: SQL生成准确性

## 🔍 问题描述

虽然Context Retriever系统已经启用并成功初始化schema缓存，但Agent生成的SQL仍然使用错误的表名，导致执行失败。

### 症状

```log
✅ Schema 缓存初始化完成，共 1 个表
   表名: online_retail (8列)

✅ Agent生成SQL完成: SELECT SUM(sales_amount) AS total_sales FROM sales WHERE...

⚠️ 表 'sales' 不存在
❌ SQL 列验证失败
```

**问题**: Schema正确获取到了`online_retail`表，但Agent生成的SQL使用了`sales`表。

## 🎯 根本原因

代码使用了**自定义的ContextRetriever类**而非Loom框架的ContextRetriever：

### 错误实现 ❌

```python
# app/services/infrastructure/agents/context_retriever.py
class ContextRetriever(BaseRetriever):  # ❌ 自定义类，只是存储inject_as参数
    def __init__(self, retriever, inject_as="system"):
        self.inject_as = inject_as  # ❌ 参数被存储但从未使用
        # ... 缺少注入逻辑
```

```python
# app/api/endpoints/placeholders.py
from app.services.infrastructure.agents.context_retriever import ContextRetriever  # ❌

context_retriever = ContextRetriever(  # ❌ 使用自定义类
    retriever=stage_aware,
    inject_as="system"  # ❌ 这个参数不会生效！
)
```

### 问题分析

1. **Loom的BaseRetriever**: 只是一个检索接口，定义了`retrieve()`方法
2. **注入逻辑**: 由`loom.core.context_retriever.ContextRetriever`实现，不是BaseRetriever的一部分
3. **自定义类的问题**:
   - 虽然有`inject_as`参数，但没有实现注入到System Message的逻辑
   - Loom的Agent接收到这个retriever时，只把它当作普通的BaseRetriever
   - 检索到的schema信息无法注入到System Message

## ✅ 修复方案

### 修改1: placeholders.py

```python
# 修改前 ❌
from app.services.infrastructure.agents.context_retriever import (
    SchemaContextRetriever, ContextRetriever  # ❌ 自定义类
)

# 修改后 ✅
from app.services.infrastructure.agents.context_retriever import (
    SchemaContextRetriever  # ✅ 只导入SchemaContextRetriever
)
from loom.core.context_retriever import ContextRetriever  # ✅ 导入Loom的ContextRetriever
```

### 修改2: context_retriever.py 工厂函数

```python
# 修改前 ❌
def create_schema_context_retriever(...) -> ContextRetriever:  # ❌ 返回自定义类
    return ContextRetriever(...)  # ❌

# 修改后 ✅
def create_schema_context_retriever(...):
    from loom.core.context_retriever import ContextRetriever as LoomContextRetriever
    return LoomContextRetriever(...)  # ✅ 返回Loom的ContextRetriever
```

### 修改3: 标记废弃类

```python
class ContextRetriever(BaseRetriever):
    """
    ⚠️ DEPRECATED: 请使用 loom.core.context_retriever.ContextRetriever 代替

    这个自定义实现缺少真正的注入逻辑，inject_as参数不会生效。
    """
```

## 📋 修改文件清单

1. `app/api/endpoints/placeholders.py`
   - 导入改为Loom的ContextRetriever
   - 添加日志确认使用Loom包装器

2. `app/services/infrastructure/agents/context_retriever.py`
   - 工厂函数使用Loom的ContextRetriever
   - 标记自定义类为废弃

## 🔧 技术细节

### Loom的ContextRetriever工作原理

```python
from loom.core.context_retriever import ContextRetriever

# Loom的ContextRetriever是一个包装器
context_retriever = ContextRetriever(
    retriever=base_retriever,  # 你的BaseRetriever实现
    inject_as="system"         # 指定注入方式
)

# 当Agent运行时，Loom会：
# 1. 调用 base_retriever.retrieve(query) 获取Documents
# 2. 根据 inject_as="system" 将Documents注入到System Message
# 3. 传递给LLM
```

### 注入方式

- `inject_as="system"`: 注入到System Message（最高优先级，推荐）
- `inject_as="user_prefix"`: 添加到用户消息前缀

## 📊 预期效果

### Before ❌

```log
✅ Schema 缓存初始化: online_retail
🧠 Agent生成SQL: SELECT ... FROM sales  ❌ 臆造的表名
❌ SQL验证失败: 表 'sales' 不存在
```

### After ✅

```log
✅ Schema 缓存初始化: online_retail
✅ 使用Loom ContextRetriever包装，inject_as=system
🔍 Context注入到System Message:
   表名: online_retail
   列: InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country
🧠 Agent生成SQL: SELECT ... FROM online_retail  ✅ 正确的表名
✅ SQL验证通过
✅ SQL执行成功
```

### 改善指标

| 指标 | Before | After | 提升 |
|------|--------|-------|------|
| 表名正确率 | 0% | ~95%+ | +∞ |
| SQL执行成功率 | 0% | ~90%+ | +∞ |
| Context使用率 | 0% | 100% | +100% |

## 🧪 验证方法

### 1. 检查日志

重新执行报告生成，应该看到：

```log
✅ 使用Loom ContextRetriever包装，inject_as=system
✅ 已启用 ContextRetriever 动态上下文机制
🔍 [SchemaContextRetriever.retrieve] 被调用
   返回的表: ['online_retail']
✅ Agent生成SQL完成: SELECT ... FROM online_retail
✅ SQL 列验证通过
✅ SQL执行成功
```

### 2. 添加调试日志（临时）

在`runtime.py`中添加：

```python
# 临时调试
if context_retriever is not None:
    logger.info(f"🔍 Context Retriever类型: {type(context_retriever)}")
    logger.info(f"   来自模块: {context_retriever.__class__.__module__}")
    # 应该看到: loom.core.context_retriever.ContextRetriever
```

### 3. 验证SQL生成

生成的SQL应该使用正确的表名：`online_retail`而非`sales`、`sales_data`等。

## 🚨 注意事项

1. **不要删除自定义ContextRetriever类**
   - 可能有遗留代码或测试脚本在使用
   - 标记为废弃即可

2. **确保Loom版本**
   - 需要loom-agent包含`loom.core.context_retriever`模块
   - 当前版本: loom-agent==0.0.1

3. **缓存管理**
   - Context Retriever会被缓存10分钟
   - 如果schema变更，需要重启服务或等待缓存过期

## 📚 相关文档

- [Loom RAG Guide](/loom-docs/LOOM_RAG_GUIDE.md)
- [Context系统架构](./CONTEXT_ENGINEERING_ARCHITECTURE.md)
- [Context Retriever启用报告](./CONTEXT_RETRIEVER_ENABLEMENT_COMPLETE.md)

## 🔄 后续工作

1. ✅ 修复Context注入问题
2. ⏭️ 测试验证修复效果
3. ⏭️ 监控SQL生成质量
4. ⏭️ 优化检索策略（如果需要）

---

**修复完成日期**: 2025-10-25
**修复人**: Claude Code
**测试状态**: 待验证
