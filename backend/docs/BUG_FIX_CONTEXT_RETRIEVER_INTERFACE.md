# Context Retriever 接口修复总结

## 问题描述

在运行 Agent 系统时出现以下错误：

```
AttributeError: 'SchemaContextRetriever' object has no attribute 'retrieve_for_query'
```

同时还有 ContextVar token 的上下文错误：

```
ValueError: <Token var=<ContextVar name='loom_agent_user_id' default='' at 0x...> at 0x...> was created in a different Context
```

## 根本原因

### 1. 缺少 `retrieve_for_query` 方法

**问题**：`SchemaContextRetriever` 继承自 `BaseRetriever`，只实现了 `retrieve()` 方法，但 Loom 0.0.3 的 TT 递归模式期望 context_retriever 有 `retrieve_for_query()` 方法。

**代码位置**：
- `/app/services/infrastructure/agents/context_retriever.py:23`
- Loom 期望：`/venv/.../loom/core/context_retriever.py:55`

### 2. 缺少 `format_documents` 方法

**问题**：Loom Agent 在注入上下文时会调用 `format_documents()` 方法来格式化检索到的文档，但 `SchemaContextRetriever` 没有实现这个方法。

### 3. ContextVar token 清理异常

**问题**：在异步生成器关闭时，ContextVar token 可能已经在不同的上下文中，导致 `reset()` 调用失败。

**代码位置**：`/app/services/infrastructure/agents/runtime.py:315`

## 修复方案

### 修复 1：添加 `retrieve_for_query` 方法

在 `SchemaContextRetriever` 中添加标准接口方法：

```python
async def retrieve_for_query(
    self,
    query: str,
    top_k: Optional[int] = None,
    filters: Optional[Dict[str, Any]] = None
) -> List[Document]:
    """
    为查询检索相关文档 - Loom ContextRetriever 标准接口

    这是 Loom TT 递归模式要求的标准方法名

    Args:
        query: 用户的业务需求描述
        top_k: 返回最相关的 top_k 个表
        filters: 可选的过滤条件

    Returns:
        Document 列表，每个 Document 包含一个表的完整结构信息
    """
    return await self.retrieve(query, top_k, filters)
```

**文件**：`app/services/infrastructure/agents/context_retriever.py:306-325`

### 修复 2：添加 `format_documents` 方法

添加文档格式化方法：

```python
def format_documents(
    self,
    documents: List[Document],
    max_length: int = 2000
) -> str:
    """
    格式化文档为字符串（用于上下文注入）

    这是 Loom ContextRetriever 的标准方法，用于将检索到的文档
    格式化为字符串注入到 LLM 上下文中

    Args:
        documents: 文档列表
        max_length: 单个文档最大长度

    Returns:
        格式化的文档字符串
    """
    if not documents:
        return ""

    lines = ["## Retrieved Schema Context\n"]
    lines.append(f"Found {len(documents)} relevant table(s):\n")

    for i, doc in enumerate(documents, 1):
        lines.append(f"### Document {i}")

        # 元数据
        if doc.metadata:
            table_name = doc.metadata.get("table_name", "Unknown")
            lines.append(f"**Table**: {table_name}")
            
            source = doc.metadata.get("source", "schema")
            if source:
                lines.append(f"**Source**: {source}")

        # 相关性分数
        if doc.score is not None:
            lines.append(f"**Relevance**: {doc.score:.2%}")

        # 内容（截断）
        content = doc.content
        if len(content) > max_length:
            content = content[:max_length] + "...\n[truncated]"

        lines.append(f"\n{content}\n")

    lines.append("---\n")
    lines.append("Please use the above schema information to answer the question.\n")

    return "\n".join(lines)
```

**文件**：`app/services/infrastructure/agents/context_retriever.py:603-652`

### 修复 3：ContextVar token 异常处理

在 `finally` 块中捕获异常：

```python
finally:
    # 清理 context variable
    try:
        _CURRENT_USER_ID.reset(token)
    except (ValueError, LookupError) as e:
        # 在生成器关闭时，token 可能已经在不同的上下文中
        # 这种情况下忽略 reset 错误
        logger.debug(f"⚠️ Context variable reset failed (可以忽略): {e}")
```

**文件**：`app/services/infrastructure/agents/runtime.py:313-320`

## 验证测试

### 测试 1：接口完整性验证

脚本：`scripts/verify_context_interface.py`

结果：
```
✅ retrieve_for_query - EXISTS (async method)
✅ retrieve - EXISTS (async method)
✅ format_documents - EXISTS (sync method)
✅ add_documents - EXISTS (async method)
✅ initialize - EXISTS (async method)

PASS: All required methods are present!
```

### 测试 2：方法调用验证

脚本：`scripts/test_context_retriever_fix.py`

结果：
```
✅ retrieve_for_query 修复: PASS
✅ ContextVar token reset 修复: PASS

All tests passed!
```

### 测试 3：集成测试

脚本：`scripts/test_context_loading_integration.py`

结果：
```
Simple method call test: PASS
Loom Agent integration test: PASS

retrieve_for_query call count: 1  ✅ 成功调用
retrieve call count: 1            ✅ 成功调用
LLM call count: 1                 ✅ 成功调用

All tests passed! Context loading is working!
```

## 关键发现

1. **Loom ContextRetriever 标准接口**：
   - `retrieve_for_query(query, top_k, filters)` - 必需
   - `format_documents(documents, max_length)` - 必需
   - `retrieve(query, top_k, filters)` - BaseRetriever 接口

2. **你的系统现在完全符合标准**：
   - ✅ `SchemaContextRetriever` 实现了所有必需方法
   - ✅ 可以正确注入到 Loom Agent 的 TT 递归执行中
   - ✅ 上下文检索功能正常工作

3. **与测试代码的对比**：
   - 测试中的 `MockSchemaContextRetriever` 实现了同样的接口
   - 你的系统 `SchemaContextRetriever` 现在与测试模式完全一致

## 修复文件清单

1. `app/services/infrastructure/agents/context_retriever.py`
   - 添加 `retrieve_for_query` 方法
   - 添加 `format_documents` 方法

2. `app/services/infrastructure/agents/runtime.py`
   - 修复 ContextVar token reset 异常处理

3. 测试脚本（新增）：
   - `scripts/verify_context_interface.py` - 接口验证
   - `scripts/test_context_retriever_fix.py` - 方法测试
   - `scripts/test_context_loading_integration.py` - 集成测试

## 下一步

现在你的上下文加载逻辑完全符合 Loom 标准，可以：

1. ✅ 正常运行 Agent TT 递归
2. ✅ 自动检索和注入 Schema 上下文
3. ✅ 没有 AttributeError 异常
4. ✅ ContextVar 正确管理

可以重新运行原来失败的占位符分析请求，应该能够正常工作了！
