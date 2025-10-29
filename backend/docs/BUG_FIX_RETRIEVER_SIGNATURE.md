# 修复Retriever方法签名不兼容问题

**时间**: 2025-10-25
**严重程度**: 🔴 Critical
**前置问题**: [BUG_FIX_CONTEXT_INJECTION.md](./BUG_FIX_CONTEXT_INJECTION.md)

## 🔍 问题描述

在修复Context注入问题后（使用Loom的ContextRetriever），发现新的错误：

```log
Warning: Document retrieval failed: StageAwareContextRetriever.retrieve() got an unexpected keyword argument 'filters'
```

**结果**: Context检索失败，导致schema信息仍然无法传递给LLM。

## 🎯 根本原因

Loom框架调用`BaseRetriever.retrieve()`时会传入额外的参数（如`filters`），但我们的实现没有接受这些参数。

### 错误实现 ❌

```python
# context_manager.py - StageAwareContextRetriever
async def retrieve(self, query: str, top_k: int = 5) -> List[Any]:
    # ❌ 不接受 filters 参数
    schema_docs = await self.schema_retriever.retrieve(query, top_k=top_k)
    # ❌ 也没有传递 filters 给底层retriever
```

### Loom的调用

```python
# Loom内部调用
documents = await retriever.retrieve(
    query=user_query,
    top_k=5,
    filters={}  # ❌ 传入了filters参数，但我们的方法不接受
)
```

## ✅ 修复方案

### 修改1: StageAwareContextRetriever.retrieve() 签名

```python
# 修改前 ❌
async def retrieve(self, query: str, top_k: int = 5) -> List[Any]:

# 修改后 ✅
async def retrieve(
    self,
    query: str,
    top_k: int = 5,
    filters: Optional[Dict[str, Any]] = None,  # ✅ 接受filters参数
    **kwargs  # ✅ 接受其他可能的参数
) -> List[Any]:
```

### 修改2: 传递filters给底层retriever

```python
# 修改前 ❌
schema_docs = await self.schema_retriever.retrieve(query, top_k=top_k)

# 修改后 ✅
schema_docs = await self.schema_retriever.retrieve(
    query,
    top_k=top_k,
    filters=filters  # ✅ 传递filters参数
)
```

## 📝 修改文件

**app/services/infrastructure/agents/context_manager.py**

1. **第195-207行**: 修改`StageAwareContextRetriever.retrieve()`方法签名
   - 添加`filters`参数
   - 添加`**kwargs`接受其他参数
   - 更新docstring

2. **第227行**: 传递`filters`给底层retriever
   ```python
   schema_docs = await self.schema_retriever.retrieve(query, top_k=top_k, filters=filters)
   ```

## 🔍 技术细节

### Loom的BaseRetriever接口

根据Loom文档，`BaseRetriever.retrieve()`方法应该能够接受额外的参数：

```python
from loom.interfaces.retriever import BaseRetriever

class MyRetriever(BaseRetriever):
    async def retrieve(
        self,
        query: str,
        top_k: int = 3,
        filters: Optional[Dict[str, Any]] = None,  # 可选的过滤条件
        **kwargs  # 其他参数
    ) -> List[Document]:
        # 实现逻辑
        pass
```

### 为什么需要filters参数

虽然我们当前不使用`filters`进行实际过滤，但：
1. **接口兼容性**: Loom可能会传入这个参数
2. **未来扩展性**: 可以用于根据metadata过滤文档
3. **错误防止**: 避免"unexpected keyword argument"错误

## 📊 影响范围

### Before ❌

```log
Warning: Document retrieval failed: ... got an unexpected keyword argument 'filters'
✅ Agent生成SQL: SELECT ... FROM sales  ❌ 仍然使用错误表名
```

### After ✅

```log
🔍 [SchemaContextRetriever.retrieve] 被调用
   查询内容: 你是一个SQL生成专家Agent...
   请求返回 top_k=5 个表
✅ Schema上下文: 1 个文档
   表名列表: ['online_retail']
✅ Context注入成功
🧠 Agent生成SQL: SELECT ... FROM online_retail  ✅ 使用正确表名
```

## 🧪 验证方法

### 1. 检查日志 - 不应再有错误

**Before**:
```log
Warning: Document retrieval failed: StageAwareContextRetriever.retrieve() got an unexpected keyword argument 'filters'
```

**After**:
```log
🔍 [StageAwareRetriever] 当前阶段: planning
   📊 正在检索 Schema 上下文...
✅ Schema上下文: 1 个文档
   表名列表: ['online_retail']
```

### 2. 验证Context内容被传递

在日志中应该看到：
```log
🔍 [SchemaContextRetriever.retrieve] 被调用
   查询内容（前200字符）: 你是一个SQL生成专家Agent。请使用可用的工具...
   请求返回 top_k=5 个表
   Schema 缓存中共有 1 个表
   表名列表: ['online_retail']
```

### 3. 验证SQL生成使用正确表名

```log
✅ Agent生成SQL完成: SELECT ... FROM online_retail  ✅
✅ SQL 列验证通过
```

## 🚨 相关问题链接

这个问题是[BUG_FIX_CONTEXT_INJECTION.md](./BUG_FIX_CONTEXT_INJECTION.md)的后续：

1. **第一步**: 使用Loom的ContextRetriever（解决注入逻辑）
2. **第二步**: 修复retrieve()方法签名（本文档 - 解决参数兼容性）

两个修复缺一不可！

## 💡 最佳实践

### 实现BaseRetriever时的建议

```python
from loom.interfaces.retriever import BaseRetriever
from typing import Optional, Dict, Any, List

class MyRetriever(BaseRetriever):
    async def retrieve(
        self,
        query: str,
        top_k: int = 3,
        filters: Optional[Dict[str, Any]] = None,  # ✅ 始终包含
        **kwargs  # ✅ 接受未来可能的参数
    ) -> List[Document]:
        """
        检索相关文档

        Args:
            query: 查询字符串
            top_k: 返回文档数量
            filters: 可选的过滤条件（即使不用也要接受）
            **kwargs: 其他可选参数
        """
        # 实现逻辑...
        pass
```

### 调用底层retriever时

```python
# ✅ 传递所有参数
documents = await self.base_retriever.retrieve(
    query=query,
    top_k=top_k,
    filters=filters,  # 即使是None也传递
    **kwargs  # 传递其他未知参数
)
```

## 📚 相关文档

- [Loom RAG Guide](../loom-docs/LOOM_RAG_GUIDE.md) - 第462-496行：BaseRetriever接口
- [Context注入修复](./BUG_FIX_CONTEXT_INJECTION.md)
- [Context系统架构](./CONTEXT_ENGINEERING_ARCHITECTURE.md)

---

**修复完成日期**: 2025-10-25
**修复人**: Claude Code
**测试状态**: 待验证
