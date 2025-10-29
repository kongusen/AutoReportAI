# 上下文传递日志追踪指南

## 概述

为了调试 Schema Context 是否正确注入到 Agent，我们添加了详细的日志来追踪上下文在整个流程中的传递。

## 日志流程图

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Schema 缓存初始化（tasks.py）                                │
│     ✅ Schema Context 初始化完成，缓存了 X 个表                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. Agent 调用开始（facade.py）                                  │
│     📋 [LoomAgentFacade] Context retriever enabled: True         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. Loom 调用 ContextRetriever（如果有上下文需求）                │
│     🔍 [ContextRetriever.retrieve] 被Loom调用                    │
│        查询内容（前200字符）: ...                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. StageAwareContextRetriever 检索（如果启用）                   │
│     🔍 [StageAwareRetriever] 当前阶段: planning                  │
│        当前阶段需要的上下文类型: ['schema']                        │
│        📊 正在检索 Schema 上下文...                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  5. SchemaContextRetriever 检索表结构                             │
│     🔍 [SchemaContextRetriever.retrieve] 被调用                  │
│        Schema 缓存中共有 X 个表                                   │
│        表名列表: ['table1', 'table2', ...]                       │
│        表 'table1' 匹配分数: 10.0                                │
│     ✅ [SchemaContextRetriever] 检索到 X 个相关表                │
│        返回的表: ['table1', ...]                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  6. ContextRetriever 格式化文档                                   │
│     📝 [ContextRetriever.format_documents] 被Loom调用            │
│     =====================================                        │
│     📋 [完整上下文内容] - 这是将要传递给 Agent 的上下文:           │
│     =====================================                        │
│     ## 📊 相关数据表结构                                          │
│     ...                                                          │
│     =====================================                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  7. LoomAgentFacade 发送 Prompt 给 Agent                         │
│     =====================================                        │
│     📤 [LoomAgentFacade] 发送给 Agent 的 Prompt:                 │
│     =====================================                        │
│     （完整的 Prompt，包含用户需求 + 上下文）                       │
│     =====================================                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  8. Agent 生成 SQL                                               │
│     ✅ Agent生成SQL完成: SELECT ... FROM table1 ...              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  9. （可选）优化阶段 - 如果需要优化 SQL                           │
│     🎯 切换到 OPTIMIZATION 阶段                                  │
│     🔍 [StageAwareRetriever] 当前阶段: optimization             │
│        当前阶段需要的上下文类型: ['performance_metrics',        │
│                                   'execution_result']           │
│     📝 [StageAwareRetriever.format_documents]                   │
│     =====================================                        │
│     📋 [optimization阶段] 格式化后的上下文:                      │
│     =====================================                        │
│     ## ⚡ SQL优化上下文                                           │
│     ### 📊 性能指标：...                                          │
│     ### ✅ 执行结果：...                                          │
│     =====================================                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  10. （可选）图表生成阶段 - 如果需要生成图表                       │
│     🎯 切换到 CHART_GENERATION 阶段                              │
│     🔍 [StageAwareRetriever] 当前阶段: chart_generation         │
│        当前阶段需要的上下文类型: ['data_preview',               │
│                                   'execution_result']           │
│     📝 [StageAwareRetriever.format_documents]                   │
│     =====================================                        │
│     📋 [chart_generation阶段] 格式化后的上下文:                  │
│     =====================================                        │
│     ## 📈 图表生成上下文                                          │
│     ### 📊 数据预览：...                                          │
│     ### 📋 执行结果：...                                          │
│     =====================================                        │
└─────────────────────────────────────────────────────────────────┘
```

## 关键日志标记

### 1. Schema 初始化日志

**位置**: `app/services/infrastructure/task_queue/tasks.py:228`

```
✅ Schema Context 初始化完成，缓存了 1 个表
```

**含义**: Schema 缓存已成功初始化，包含指定数量的表。

**如果看不到这条日志**:
- 检查是否有错误日志：`⚠️ Schema Context 初始化失败`
- 检查数据源连接是否正常
- 检查 `create_schema_context_retriever()` 是否被正确调用

---

### 2. Context Retriever 启用检查

**位置**: `app/services/infrastructure/agents/facade.py:207`

```
📋 [LoomAgentFacade] Context retriever enabled: True
```

**含义**: Loom Agent 已配置了 Context Retriever。

**如果显示 False**:
- 检查 `AgentService` 初始化时是否传入了 `context_retriever`
- 检查 `PlaceholderApplicationService.__init__()` 是否正确传递

---

### 3. ContextRetriever 被调用

**位置**: `app/services/infrastructure/agents/context_retriever.py:314-315`

```
🔍 [ContextRetriever.retrieve] 被Loom调用
   查询内容（前200字符）: 计算平均订单金额...
```

**含义**: Loom 正在通过 ContextRetriever 检索上下文。

**如果看不到这条日志**:
- ❌ **Loom 没有调用 retrieve() 方法！**
- 检查 `ContextRetriever` 是否继承了 `BaseRetriever`
- 检查 `retrieve()` 方法是否是 `async def`
- 检查 Loom Agent 配置中 `context_retriever` 参数是否正确传递

---

### 4. SchemaContextRetriever 检索详情

**位置**: `app/services/infrastructure/agents/context_retriever.py:159-233`

```
🔍 [SchemaContextRetriever.retrieve] 被调用
   查询内容（前200字符）: 计算平均订单金额...
   请求返回 top_k=10 个表
   Schema 缓存中共有 1 个表
   表名列表: ['online_retail']
   表 'online_retail' 匹配分数: 10.0
✅ [SchemaContextRetriever] 检索到 1 个相关表
   返回的表: ['online_retail']
```

**含义**:
- Schema 缓存包含的表
- 哪些表匹配了查询
- 每个表的相关性分数
- 最终返回的表

**如果表为空**:
- 检查 `initialize()` 是否成功执行
- 检查数据源查询是否返回了表列表
- 检查 `schema_cache` 是否被正确填充

---

### 5. 完整上下文内容

**位置**: `app/services/infrastructure/agents/context_retriever.py:422-426`

```
================================================================================
📋 [完整上下文内容] - 这是将要传递给 Agent 的上下文:
================================================================================
## 📊 相关数据表结构

以下是与你的任务相关的数据表结构信息，请严格按照这些表和列来生成 SQL：

### 表: online_retail
**列信息**:
- **InvoiceNo** (VARCHAR(20)): 发票号
- **StockCode** (VARCHAR(20)): 商品代码
- **Quantity** (INT): 数量
- **InvoiceDate** (DATETIME): 发票日期
- **UnitPrice** (DECIMAL(10,2)): 单价

⚠️ **重要提醒**：请只使用上述表和列，不要臆造不存在的表名或列名！
================================================================================
```

**含义**: 这是格式化后的完整上下文，将被注入到 Agent 的 prompt 中。

**检查点**:
- ✅ 是否包含了正确的表名？
- ✅ 是否包含了所有需要的列？
- ✅ 列的数据类型是否正确？

---

### 6. 发送给 Agent 的完整 Prompt

**位置**: `app/services/infrastructure/agents/facade.py:210-214`

```
================================================================================
📤 [LoomAgentFacade] 发送给 Agent 的 Prompt:
================================================================================
计算平均订单金额（数量*单价）。

时间范围要求：{{start_date}} 到 {{end_date}}
数据库类型：Apache Doris
================================================================================
```

**含义**: 这是最终发送给 LLM 的完整 prompt。

**⚠️ 关键检查**:
- **Prompt 中是否包含了上面的表结构信息？**
- 如果**没有**，说明 Loom 没有将检索到的上下文注入到 prompt 中

**可能的原因**:
1. Loom 的 `context_retriever` 机制未正确工作
2. `format_documents()` 方法未被调用
3. Loom Agent 配置问题

---

## 调试流程

### 问题1：没有看到 `[ContextRetriever.retrieve] 被Loom调用`

**原因**: Loom 没有调用 Context Retriever

**检查步骤**:
1. 确认 `ContextRetriever` 继承了 `BaseRetriever`
   ```bash
   grep "class ContextRetriever" app/services/infrastructure/agents/context_retriever.py
   # 应该显示: class ContextRetriever(BaseRetriever):
   ```

2. 确认 `retrieve()` 是异步方法
   ```bash
   grep -A 2 "async def retrieve" app/services/infrastructure/agents/context_retriever.py
   ```

3. 确认 `context_retriever` 传递正确
   ```bash
   # 检查日志中是否有：
   📋 [LoomAgentFacade] Context retriever enabled: True
   ```

---

### 问题2：看到 `[ContextRetriever.retrieve] 被调用`，但返回的表为空

**原因**: Schema 缓存为空或检索逻辑问题

**检查步骤**:
1. 检查 Schema 初始化日志
   ```
   ✅ Schema Context 初始化完成，缓存了 X 个表
   ```
   如果 X = 0，说明初始化有问题

2. 检查 `schema_cache` 内容
   ```
   Schema 缓存中共有 X 个表
   表名列表: [...]
   ```

3. 检查匹配分数
   ```
   表 'xxx' 匹配分数: Y
   ```
   如果所有表的分数都是 0，可能是查询关键词匹配问题

---

### 问题3：上下文格式化了，但 Prompt 中没有

**原因**: Loom 没有将格式化后的上下文注入到 Prompt

**检查步骤**:
1. 查看 `format_documents()` 的输出
2. 查看最终的 Prompt
3. 对比两者，确认上下文是否被包含

**可能的解决方案**:
- 检查 Loom Agent 的配置
- 确认 `inject_as` 参数设置正确（应该是 "system"）
- 检查 Loom 版本是否兼容

---

## 预期的正常日志序列

当一切正常工作时，日志应该是这样的：

```
[INFO] ✅ Schema Context 初始化完成，缓存了 1 个表
[INFO] 📋 [LoomAgentFacade] Context retriever enabled: True
[INFO] ================================================================================
[INFO] 📤 [LoomAgentFacade] 发送给 Agent 的 Prompt:
[INFO] ================================================================================
[INFO] 计算平均订单金额...
[INFO] ================================================================================
[INFO] 🔍 [ContextRetriever.retrieve] 被Loom调用
[INFO]    查询内容（前200字符）: 计算平均订单金额...
[INFO] 🔍 [StageAwareRetriever] 当前阶段: planning
[INFO]    当前阶段需要的上下文类型: ['schema']
[INFO]    📊 正在检索 Schema 上下文...
[INFO] 🔍 [SchemaContextRetriever.retrieve] 被调用
[INFO]    Schema 缓存中共有 1 个表
[INFO]    表名列表: ['online_retail']
[INFO]    表 'online_retail' 匹配分数: 10.0
[INFO] ✅ [SchemaContextRetriever] 检索到 1 个相关表
[INFO]    返回的表: ['online_retail']
[INFO]    📄 文档 1/1: online_retail
[INFO]       相关性分数: 10.00
[INFO]       内容前300字符: ### 表: online_retail ...
[INFO] ✅ [ContextRetriever] 检索完成，返回 1 个相关表结构
[INFO]    表名列表: ['online_retail']
[INFO] 📝 [ContextRetriever.format_documents] 被Loom调用，收到 1 个文档
[INFO] ================================================================================
[INFO] 📋 [完整上下文内容] - 这是将要传递给 Agent 的上下文:
[INFO] ================================================================================
[INFO] ## 📊 相关数据表结构
[INFO]
[INFO] ### 表: online_retail
[INFO] **列信息**:
[INFO] - **InvoiceNo** (VARCHAR(20))
[INFO] - **Quantity** (INT)
[INFO] ...
[INFO] ================================================================================
[INFO] ✅ Agent生成SQL完成: SELECT AVG(Quantity * UnitPrice) FROM online_retail ...
```

### 优化阶段（如果启用）

```log
[INFO] 🎯 切换到 OPTIMIZATION 阶段
[INFO] 🔍 [StageAwareRetriever] 当前阶段: optimization
[INFO]    当前阶段需要的上下文类型: ['performance_metrics', 'execution_result']
[INFO] 📝 [StageAwareRetriever.format_documents] 当前阶段: optimization
[INFO]    文档数量: 2
[INFO] ================================================================================
[INFO] 📋 [optimization阶段] 格式化后的上下文:
[INFO] ================================================================================
[INFO] ## ⚡ SQL优化上下文
[INFO]
[INFO] 以下是SQL执行结果和性能指标，请分析并提供优化建议：
[INFO]
[INFO] ### 📊 性能指标：
[INFO] - 执行时间: 2.3s
[INFO] - 扫描行数: 1,000,000
[INFO] - 返回行数: 1
[INFO]
[INFO] ### ✅ 执行结果：
[INFO] - 平均订单金额: 18.52
[INFO]
[INFO] 💡 **优化建议方向**：
[INFO] 1. 索引优化
[INFO] 2. 查询重写
[INFO] 3. 分区裁剪
[INFO] 4. 聚合优化
[INFO] ================================================================================
[INFO] ✅ Agent优化建议完成: 建议在 InvoiceDate 列上添加索引...
```

### 图表生成阶段（如果启用）

```log
[INFO] 🎯 切换到 CHART_GENERATION 阶段
[INFO] 🔍 [StageAwareRetriever] 当前阶段: chart_generation
[INFO]    当前阶段需要的上下文类型: ['data_preview', 'execution_result']
[INFO] 📝 [StageAwareRetriever.format_documents] 当前阶段: chart_generation
[INFO]    文档数量: 2
[INFO] ================================================================================
[INFO] 📋 [chart_generation阶段] 格式化后的上下文:
[INFO] ================================================================================
[INFO] ## 📈 图表生成上下文
[INFO]
[INFO] 以下是数据预览和执行结果，请根据数据特征生成合适的图表配置：
[INFO]
[INFO] ### 📊 数据预览：
[INFO] | InvoiceDate | OrderAmount |
[INFO] |-------------|-------------|
[INFO] | 2024-01-01  | 125.50      |
[INFO] | 2024-01-02  | 98.20       |
[INFO] | 2024-01-03  | 210.00      |
[INFO]
[INFO] ### 📋 执行结果：
[INFO] - 数据点数: 365
[INFO] - 数据类型: 时间序列
[INFO]
[INFO] 💡 **图表选择建议**：
[INFO] 1. 时间序列数据 → 折线图/面积图
[INFO] 2. 分类对比 → 柱状图/条形图
[INFO] 3. 占比分析 → 饼图/环形图
[INFO] 4. 多维分析 → 散点图/气泡图
[INFO] 5. 排名数据 → 排行榜/漏斗图
[INFO] ================================================================================
[INFO] ✅ Agent图表配置完成: {type: 'line', xAxis: 'InvoiceDate', ...}
```

## 日志级别设置

如果看不到这些详细日志，检查日志级别配置：

```python
# app/core/config.py 或日志配置文件
import logging

logging.getLogger('app.services.infrastructure.agents').setLevel(logging.INFO)
```

## 总结

通过这些详细的日志，您可以在**所有阶段**追踪上下文传递：

### SQL生成阶段（PLANNING）

1. ✅ 确认 Schema Context 是否成功初始化
2. ✅ 确认 Context Retriever 是否被 Loom 调用
3. ✅ 看到检索到的具体表和列
4. ✅ 看到格式化后的完整 Schema 上下文
5. ✅ **看到最终发送给 Agent 的 Prompt（包含表结构）**

### 优化阶段（OPTIMIZATION）

1. ✅ 确认阶段切换：`🎯 切换到 OPTIMIZATION 阶段`
2. ✅ 看到性能指标和执行结果上下文
3. ✅ 看到优化建议格式的上下文
4. ✅ **看到 Agent 的优化建议输出**

### 图表生成阶段（CHART_GENERATION）

1. ✅ 确认阶段切换：`🎯 切换到 CHART_GENERATION 阶段`
2. ✅ 看到数据预览和执行结果上下文
3. ✅ 看到图表选择建议格式的上下文
4. ✅ **看到 Agent 生成的图表配置**

### 错误恢复阶段（ERROR_RECOVERY）

1. ✅ 确认阶段切换：`🎯 切换到 ERROR_RECOVERY 阶段`
2. ✅ 看到错误信息和相关上下文
3. ✅ 看到错误诊断格式的上下文
4. ✅ **看到 Agent 的修复建议**

---

**关键诊断点**：

如果在某个阶段看到了格式化的上下文，但最终的 Prompt 中没有，说明 Loom 的上下文注入机制有问题，需要进一步排查 Loom 的配置和实现。

**各阶段的上下文需求**：

- **PLANNING**: Schema（表结构）
- **VALIDATION**: Validation Result + Schema
- **EXECUTION**: Execution Result + Validation Result + Schema
- **OPTIMIZATION**: Performance Metrics + Execution Result
- **CHART_GENERATION**: Data Preview + Execution Result
- **ERROR_RECOVERY**: Error Info + Validation Result + Schema
