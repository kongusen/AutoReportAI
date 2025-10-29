# 上下文传递日志增强总结

## 修改日期
2025-10-25

## 概述

为了调试和追踪 Schema Context 在整个 Agent 执行流程中的传递，我们在**所有关键位置**添加了详细的日志记录，覆盖**全部6个执行阶段**。

## 修改的文件

### 1. `context_retriever.py` - Schema 检索和格式化

#### SchemaContextRetriever.retrieve() (行159-235)

**添加的日志**:
```python
logger.info(f"🔍 [SchemaContextRetriever.retrieve] 被调用")
logger.info(f"   查询内容（前200字符）: {query[:200]}")
logger.info(f"   请求返回 top_k={top_k} 个表")
logger.info(f"   Schema 缓存中共有 {len(self.schema_cache)} 个表")
logger.info(f"   表名列表: {list(self.schema_cache.keys())}")
logger.info(f"   表 '{table_name}' 匹配分数: {score:.1f}")
logger.info(f"✅ [SchemaContextRetriever] 检索到 {len(documents)} 个相关表")
logger.info(f"   返回的表: {[d.metadata['table_name'] for d in documents]}")
```

**记录内容**:
- 查询内容
- 缓存的表列表
- 每个表的匹配分数
- 最终返回的表

---

#### ContextRetriever.retrieve() (行314-359)

**添加的日志**:
```python
logger.info(f"🔍 [ContextRetriever.retrieve] 被Loom调用")
logger.info(f"   查询内容（前200字符）: {query[:200]}")

for i, doc in enumerate(documents, 1):
    logger.info(f"   📄 文档 {i}/{len(documents)}: {doc.metadata.get('table_name', 'unknown')}")
    logger.info(f"      相关性分数: {doc.score:.2f}")
    logger.info(f"      内容前300字符: {doc.content[:300]}...")

logger.info(f"✅ [ContextRetriever] 检索完成，返回 {len(formatted_docs)} 个相关表结构")
logger.info(f"   表名列表: {[d.metadata.get('table_name', '?') for d in formatted_docs]}")
```

**记录内容**:
- Loom 调用确认
- 每个检索到的文档的详细信息
- 文档内容预览

---

#### ContextRetriever.format_documents() (行418-426)

**添加的日志**:
```python
logger.info(f"📝 [ContextRetriever.format_documents] 被Loom调用，收到 {len(documents)} 个文档")
logger.info(f"✅ [ContextRetriever.format_documents] 格式化完成")
logger.info(f"   总长度: {len(formatted_context)} 字符")
logger.info(f"   包含表数: {len(documents)}")
logger.info("=" * 80)
logger.info("📋 [完整上下文内容] - 这是将要传递给 Agent 的上下文:")
logger.info("=" * 80)
logger.info(formatted_context)
logger.info("=" * 80)
```

**记录内容**:
- **完整的格式化上下文**（这是传递给 Agent 的内容）
- 上下文长度
- 包含的表数量

---

### 2. `context_manager.py` - 阶段感知上下文管理

#### StageAwareContextRetriever.retrieve() (行207-257)

**添加的日志**:
```python
logger.info(f"🔍 [StageAwareRetriever] 当前阶段: {current_stage.value}")
logger.info(f"   检索query（前200字符）: {query[:200]}")
logger.info(f"   当前阶段需要的上下文类型: {[t.value for t in required_types]}")
logger.info(f"   📊 正在检索 Schema 上下文...")
logger.info(f"   ✅ Schema上下文: {len(schema_docs)} 个文档")

if schema_docs:
    table_names = [d.metadata.get('table_name', '?') for d in schema_docs]
    logger.info(f"      表名列表: {table_names}")

logger.info(f"✅ [StageAwareRetriever] 最终返回 {len(documents)} 个聚焦的上下文文档")
```

**记录内容**:
- 当前执行阶段
- 该阶段需要的上下文类型
- Schema 检索结果
- 最终聚焦后的文档数量

---

#### StageAwareContextRetriever.format_documents() (行294-315)

**添加的日志**:
```python
logger.info(f"📝 [StageAwareRetriever.format_documents] 当前阶段: {current_stage.value}")
logger.info(f"   文档数量: {len(documents)}")

# 🔥 记录格式化后的完整上下文
logger.info("=" * 80)
logger.info(f"📋 [{current_stage.value}阶段] 格式化后的上下文:")
logger.info("=" * 80)
logger.info(formatted)
logger.info("=" * 80)
```

**记录内容**:
- 当前阶段
- **格式化后的完整上下文**（按阶段定制）

---

#### 新增格式化方法

##### _format_for_optimization() (行340-384)

为 **OPTIMIZATION** 阶段定制的上下文格式：

```markdown
## ⚡ SQL优化上下文

### 📊 性能指标：
- 执行时间
- 扫描行数
- 返回行数

### ✅ 执行结果：
- 查询结果

💡 **优化建议方向**：
1. 索引优化
2. 查询重写
3. 分区裁剪
4. 聚合优化
```

---

##### _format_for_chart_generation() (行386-431)

为 **CHART_GENERATION** 阶段定制的上下文格式：

```markdown
## 📈 图表生成上下文

### 📊 数据预览：
- 数据样本

### 📋 执行结果：
- 数据特征

💡 **图表选择建议**：
1. 时间序列数据 → 折线图/面积图
2. 分类对比 → 柱状图/条形图
3. 占比分析 → 饼图/环形图
4. 多维分析 → 散点图/气泡图
5. 排名数据 → 排行榜/漏斗图
```

---

### 3. `facade.py` - Agent 执行入口

#### LoomAgentFacade.execute() (行210-214)

**添加的日志**:
```python
# 🔥 记录发送给 Agent 的完整 prompt
logger.info("=" * 80)
logger.info("📤 [LoomAgentFacade] 发送给 Agent 的 Prompt:")
logger.info("=" * 80)
logger.info(prompt)
logger.info("=" * 80)
```

**记录内容**:
- **发送给 LLM 的完整 Prompt**（包含用户需求 + 上下文）

---

## 覆盖的执行阶段

| 阶段 | 上下文需求 | 格式化方法 | 日志标记 |
|------|-----------|-----------|---------|
| **PLANNING** | Schema | `_format_for_planning()` | `📊 数据表结构（SQL规划阶段）` |
| **VALIDATION** | Validation Result + Schema | `_format_default()` | `📋 相关上下文（validation阶段）` |
| **EXECUTION** | Execution Result + Validation + Schema | `_format_default()` | `📋 相关上下文（execution阶段）` |
| **OPTIMIZATION** | Performance Metrics + Execution | `_format_for_optimization()` | `⚡ SQL优化上下文` |
| **CHART_GENERATION** | Data Preview + Execution | `_format_for_chart_generation()` | `📈 图表生成上下文` |
| **ERROR_RECOVERY** | Error Info + Validation + Schema | `_format_for_error_recovery()` | `⚠️ 错误诊断与修复上下文` |

---

## 日志流程示例

### SQL生成阶段（PLANNING）

```log
[INFO] 🔍 [StageAwareRetriever] 当前阶段: planning
[INFO]    当前阶段需要的上下文类型: ['schema']
[INFO]    📊 正在检索 Schema 上下文...
[INFO] 🔍 [SchemaContextRetriever.retrieve] 被调用
[INFO]    Schema 缓存中共有 1 个表
[INFO]    表名列表: ['online_retail']
[INFO] ✅ [SchemaContextRetriever] 检索到 1 个相关表
[INFO]    返回的表: ['online_retail']
[INFO] 📝 [StageAwareRetriever.format_documents] 当前阶段: planning
[INFO] ================================================================================
[INFO] 📋 [planning阶段] 格式化后的上下文:
[INFO] ================================================================================
[INFO] ## 📊 数据表结构（SQL规划阶段）
[INFO]
[INFO] ### 表: online_retail
[INFO] **列信息**:
[INFO] - **InvoiceNo** (VARCHAR(20)): 发票号
[INFO] - **Quantity** (INT): 数量
[INFO] ================================================================================
[INFO] 📤 [LoomAgentFacade] 发送给 Agent 的 Prompt:
[INFO] ================================================================================
[INFO] 计算平均订单金额...
[INFO] [包含上面的表结构上下文]
[INFO] ================================================================================
```

### 优化阶段（OPTIMIZATION）

```log
[INFO] 🎯 切换到 OPTIMIZATION 阶段
[INFO] 🔍 [StageAwareRetriever] 当前阶段: optimization
[INFO]    当前阶段需要的上下文类型: ['performance_metrics', 'execution_result']
[INFO] 📝 [StageAwareRetriever.format_documents] 当前阶段: optimization
[INFO] ================================================================================
[INFO] 📋 [optimization阶段] 格式化后的上下文:
[INFO] ================================================================================
[INFO] ## ⚡ SQL优化上下文
[INFO]
[INFO] ### 📊 性能指标：
[INFO] - 执行时间: 2.3s
[INFO] ================================================================================
```

### 图表生成阶段（CHART_GENERATION）

```log
[INFO] 🎯 切换到 CHART_GENERATION 阶段
[INFO] 🔍 [StageAwareRetriever] 当前阶段: chart_generation
[INFO]    当前阶段需要的上下文类型: ['data_preview', 'execution_result']
[INFO] 📝 [StageAwareRetriever.format_documents] 当前阶段: chart_generation
[INFO] ================================================================================
[INFO] 📋 [chart_generation阶段] 格式化后的上下文:
[INFO] ================================================================================
[INFO] ## 📈 图表生成上下文
[INFO]
[INFO] ### 📊 数据预览：
[INFO] | InvoiceDate | OrderAmount |
[INFO] ================================================================================
```

---

## 关键诊断点

### ✅ 上下文注入成功的标志

1. 看到 `🔍 [ContextRetriever.retrieve] 被Loom调用`
2. 看到 `📋 [完整上下文内容] - 这是将要传递给 Agent 的上下文:`
3. 看到 `📤 [LoomAgentFacade] 发送给 Agent 的 Prompt:` **包含了上下文**

### ❌ 上下文注入失败的标志

1. **没有**看到 `[ContextRetriever.retrieve] 被Loom调用`
   - 原因：Loom 没有识别 Context Retriever
   - 检查：继承关系、方法签名

2. 看到了格式化的上下文，但 Prompt 中**没有**
   - 原因：Loom 的上下文注入机制有问题
   - 检查：Loom 配置、inject_as 参数

3. 上下文为空或包含错误的表
   - 原因：Schema 缓存初始化失败或检索逻辑问题
   - 检查：Schema 初始化日志、匹配分数

---

## 使用方法

1. **启用日志级别**:
   ```python
   logging.getLogger('app.services.infrastructure.agents').setLevel(logging.INFO)
   ```

2. **运行任务**，查看日志

3. **搜索关键日志标记**:
   - `[ContextRetriever.retrieve]` - Context 检索
   - `[完整上下文内容]` - 格式化后的上下文
   - `[LoomAgentFacade] 发送给 Agent 的 Prompt` - 最终 Prompt

4. **对比上下文和 Prompt**:
   - 确认格式化的上下文是否出现在最终的 Prompt 中

---

## 相关文档

- `CONTEXT_LOGGING_GUIDE.md` - 详细的日志追踪指南
- `CRITICAL_BUG_FIXES_CONTEXT_AND_VALIDATION.md` - Context 注入修复说明
- `STAGE_AWARE_CONTEXT_USAGE.md` - 阶段感知上下文使用指南

---

## 总结

通过这些详细的日志，我们可以：

✅ 追踪上下文在**所有6个阶段**的传递
✅ 看到**完整的格式化上下文**
✅ 看到**最终发送给 Agent 的 Prompt**
✅ 快速定位上下文丢失的问题
✅ 验证每个阶段的上下文是否符合预期

这些日志覆盖了从 Schema 初始化、检索、格式化，到最终注入到 Prompt 的**完整流程**，为调试提供了全方位的可见性。
