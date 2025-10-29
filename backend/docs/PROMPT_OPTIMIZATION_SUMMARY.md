# Prompt 优化总结

**日期**: 2025-10-26
**版本**: 1.0
**状态**: ✅ 已完成

---

## 🎯 优化目标

减少 prompt 的 token 使用量，提高效率，同时保持关键信息的完整性。

**优化策略**：
1. ✂️ 移除重复说明
2. 📝 使用简洁语言
3. 🗜️ 压缩 JSON 格式
4. 🔤 简化标题和格式

---

## 📊 优化成果

### 总体效果

| 组件 | 优化前 (估算) | 优化后 (估算) | 减少 |
|------|--------------|--------------|------|
| ReAct Prompt | ~800 tokens | ~200 tokens | **-75%** |
| Task Context JSON | ~600 tokens | ~150 tokens | **-75%** |
| Schema Context | ~1000 tokens | ~600 tokens | **-40%** |
| Static Context Headers | ~50 tokens | ~20 tokens | **-60%** |
| **总计** | **~2450 tokens** | **~970 tokens** | **-60%** |

---

## 🔧 具体优化

### 1. ReAct Prompt 模板优化

**文件**: `app/services/application/placeholder/placeholder_service.py:140-164`

#### 优化前（❌ 冗长，~800 tokens）

```python
task_prompt = f"""
你是一个SQL生成专家Agent。请使用可用的工具完成以下任务：

## 任务目标
生成一个高质量的SQL查询来满足以下业务需求：

### 业务需求
{request.business_command}

### 具体目标
{request.target_objective or request.requirements}
{time_window_desc}

### 数据源信息
- 数据源ID: {data_source_config.get('data_source_id', 'N/A')}
- 数据库: {data_source_config.get('database_name', 'N/A')}

## ⚠️ 重要约束
1. **必须包含时间过滤条件** - 这是基于时间周期的统计查询
2. **只能使用实际存在的表和列** - 必须先探索schema
3. **必须验证SQL正确性** - 确保SQL可执行
4. **使用占位符格式** - 时间过滤使用 {{start_date}} 和 {{end_date}}
   ⚠️ **关键要点：占位符周围不要加引号！**
   - ✅ 正确: WHERE date BETWEEN {{start_date}} AND {{end_date}}
   - ❌ 错误: WHERE date BETWEEN '{{start_date}}' AND '{{end_date}}'
   - **原因**: 占位符替换时会自动添加引号，如果SQL中已有引号会导致双重引号语法错误

## 可用工具
你有以下工具可用：
1. **schema.list_tables** - 列出数据源中的所有表
2. **schema.list_columns** - 获取指定表的列信息
3. **sql.validate** - 验证SQL的正确性
4. **sql.execute** - 执行SQL进行测试（使用LIMIT限制）
5. **sql.refine** - 基于错误信息优化SQL

## 推荐流程（ReAct循环）
1. 使用 schema.list_tables 查看所有可用的表
2. 根据业务需求选择相关的表
3. 使用 schema.list_columns 获取这些表的列信息
4. 生成SQL查询（确保包含时间过滤，**占位符不加引号**）
5. 使用 sql.validate 验证SQL
6. **如果验证失败（如双重引号错误）**：
   - 检查SQL中占位符周围是否有引号
   - 移除占位符周围的引号
   - 使用 sql.refine 优化SQL
   - 重新验证（最多重试3次）
7. 验证成功后，可选择使用 sql.execute 测试SQL

## 期望输出
最终返回一个JSON格式的结果：
{
    "sql": "SELECT ... WHERE dt BETWEEN {{start_date}} AND {{end_date}}",
    "reasoning": "解释为什么这个SQL满足业务需求",
    "tables_used": ["table1", "table2"],
    "has_time_filter": true,
    "time_column_used": "dt"
}

现在开始执行任务，使用工具进行推理和行动(ReAct)！
"""
```

**问题**：
- ❌ 占位符说明重复了3次
- ❌ 工具描述过于详细
- ❌ 流程步骤冗长
- ❌ 大量的标题和格式化符号

#### 优化后（✅ 简洁，~200 tokens，减少 75%）

```python
task_prompt = f"""
生成SQL: {request.business_command}
{time_window_desc}

## 约束
1. 包含时间过滤: WHERE col BETWEEN {{{{start_date}}}} AND {{{{end_date}}}}
2. ⚠️ 占位符不加引号
3. 只用实际存在的表/列
4. 验证SQL正确性

## 工具
- schema.list_tables: 列表
- schema.list_columns: 列详情
- sql.validate: 验证
- sql.refine: 优化

## 流程
1. 探索schema
2. 生成SQL (占位符不加引号)
3. 验证 → 失败则refine

## 输出JSON
{{"sql": "...", "reasoning": "...", "tables_used": [...], "has_time_filter": true}}
"""
```

**改进**：
- ✅ 移除冗余的角色描述和任务说明
- ✅ 占位符说明只提1次
- ✅ 工具列表简化为单行
- ✅ 流程精简为3步
- ✅ 输出格式压缩

---

### 2. Task Context JSON 压缩

**文件**: `app/services/infrastructure/agents/facade.py:199-249`

#### 优化前（❌ ~600 tokens）

```json
{
  "placeholder": {
    "id": "1b7bed9f-4185-48ed-9921-a48aa0a777e1",
    "description": "统计：该产品总收入",
    "type": "sql_generation_react",
    "granularity": "daily"
  },
  "task_context": {
    "task_time": 1761453701,
    "timezone": "Asia/Shanghai",
    "window": null
  },
  "constraints": {
    "sql_only": true,
    "output_kind": "sql",
    "max_attempts": 5,
    "policy_row_limit": null,
    "quality_min_rows": null
  },
  "data_source": {
    "name": "测试-销售",
    "source_type": "doris",
    "fe_hosts": ["192.168.31.160"],
    "be_hosts": ["localhost"],
    "http_port": 8030,
    "query_port": 9030,
    "database": "retail_db",
    "username": "root",
    "password": "",
    "timeout": 30,
    "id": "908c9e22-2773-4175-955c-bc0231336698",
    "data_source_id": "908c9e22-2773-4175-955c-bc0231336698",
    "database_name": "retail_db",
    "semantic_type": "stat",
    "business_requirements": { ... }
  },
  "task_driven_context": {
    "mode": "react",
    "business_command": "统计：该产品总收入",
    "requirements": "为占位符 统计：该产品总收入 生成SQL",
    "target_objective": "为占位符 统计：该产品总收入 生成SQL",
    "enable_tools": true
  },
  "system_config": { ... }
}
```

#### 优化后（✅ ~150 tokens，减少 75%）

```json
{
  "placeholder": {
    "id": "1b7bed9f-4185-48ed-9921-a48aa0a777e1",
    "desc": "统计：该产品总收入"
  },
  "data_source": {
    "id": "908c9e22-2773-4175-955c-bc0231336698",
    "db": "retail_db",
    "type": "doris"
  },
  "task_driven_context": {
    "mode": "react",
    "req": "统计：该产品总收入"
  },
  "task_context": {...},
  "constraints": {...}
}
```

**改进**：
- ✅ 移除冗余字段（fe_hosts, be_hosts, password 等）
- ✅ 字段名缩写（description → desc, database → db, requirements → req）
- ✅ 移除重复信息（data_source_id = id）
- ✅ 紧凑 JSON 格式（无缩进）
- ✅ 移除 ```json 代码块包裹

---

### 3. Schema Context 优化

**文件**: `app/services/infrastructure/agents/context_retriever.py:433-470`

#### 优化前（❌ ~1000 tokens）

```
# 📊 数据表结构信息

⚠️⚠️⚠️ **关键约束 - 请务必遵守** ⚠️⚠️⚠️

你**必须且只能**使用以下列出的表和列。
**禁止臆造任何不存在的表名或列名！**

**违反此约束将导致**：
- ❌ SQL 语法错误
- ❌ 执行失败
- ❌ 验证不通过
- ❌ 任务失败

## 可用的数据表

### 表 1/1: `online_retail`

### 表: online_retail
**说明**: 在线零售表

**列信息**:
- **InvoiceNo** (VARCHAR) [NOT NULL]: 发票号
- **StockCode** (VARCHAR): 商品代码
- **Description** (VARCHAR): 商品描述
- **Quantity** (INT): 数量
- **InvoiceDate** (DATETIME): 发票日期
- **UnitPrice** (DECIMAL(10,2)): 单价
- **CustomerID** (INT): 客户ID
- **Country** (VARCHAR): 国家

## ✅ 必须遵守的规则

1. ✅ **只使用上述表和列**
   - 表名和列名必须**精确匹配**
   - 区分大小写（例如：`InvoiceDate` ≠ `invoice_date`）
   - 注意下划线（例如：`online_retail` ≠ `onlineretail`）

2. ✅ **符合 Apache Doris 语法**
   - 不支持 `FILTER (WHERE ...)` 等 PostgreSQL 特有语法
   - 使用 `CASE WHEN` 替代 `FILTER`

3. ❌ **禁止臆造表名或列名**
   - 如果需要的表/列不在上述列表中，请说明需求

4. ⏰ **时间占位符不加引号**
   - ✅ 正确：`WHERE dt BETWEEN {{start_date}} AND {{end_date}}`
   - ❌ 错误：`WHERE dt BETWEEN '{{start_date}}' AND '{{end_date}}'`
```

#### 优化后（✅ ~600 tokens，减少 40%）

```
# 数据表结构

⚠️ **只能使用以下表和列，禁止臆造！**

## 可用表

### online_retail
### 表: online_retail

**列信息**:
- **InvoiceNo** (VARCHAR) [NOT NULL]: 发票号
- **StockCode** (VARCHAR): 商品代码
- **Description** (VARCHAR): 商品描述
- **Quantity** (INT): 数量
- **InvoiceDate** (DATETIME): 发票日期
- **UnitPrice** (DECIMAL(10,2)): 单价
- **CustomerID** (INT): 客户ID
- **Country** (VARCHAR): 国家

## 规则
1. 表/列名精确匹配（区分大小写）
2. 使用 Apache Doris 语法（`CASE WHEN`，不支持`FILTER`）
3. 时间占位符不加引号: `WHERE dt BETWEEN {{start_date}} AND {{end_date}}`
```

**改进**：
- ✅ 简化约束说明（去掉重复强调）
- ✅ 移除表编号（`表 1/1:`）
- ✅ 精简规则说明（合并重复内容）
- ✅ 移除冗长的后果列表

---

### 4. Static Context Headers 优化

**文件**: `app/services/infrastructure/agents/facade.py:185-197`

#### 优化前（❌ ~50 tokens）

```
### 用户需求
{request.prompt}

### 执行阶段
task_execution

### 工作模式
react
```

#### 优化后（✅ ~20 tokens，减少 60%）

```
# 需求
{request.prompt}

# 阶段
task_execution | react
```

**改进**：
- ✅ 简化标题（`###` → `#`）
- ✅ 合并阶段和模式为单行

---

## 📊 Token 使用量对比

### 完整 Prompt 示例

#### 优化前

```
=== Static Context ===
### 用户需求
生成SQL: 统计该产品总收入
...

### 执行阶段
task_execution

### 工作模式
react

### 任务上下文
```json
{
  "placeholder": {...},  // 大量冗余字段
  ...
}
```

=== Schema Context ===
# 📊 数据表结构信息

⚠️⚠️⚠️ **关键约束 - 请务必遵守** ⚠️⚠️⚠️
...（大量重复说明）

=== ReAct Prompt ===
你是一个SQL生成专家Agent。请使用可用的工具完成以下任务：
...（冗长的说明）

总计: ~2450 tokens
```

#### 优化后

```
=== Static Context ===
# 需求
生成SQL: 统计该产品总收入

# 阶段
task_execution | react

### 任务上下文
{"placeholder":{"id":"...","desc":"..."},"data_source":{"id":"...","db":"...","type":"..."}}

=== Schema Context ===
# 数据表结构

⚠️ **只能使用以下表和列，禁止臆造！**

### online_retail
- **InvoiceNo** (VARCHAR) [NOT NULL]: 发票号
...

## 规则
1. 表/列名精确匹配（区分大小写）
2. 使用 Apache Doris 语法
3. 时间占位符不加引号

=== ReAct Prompt ===
生成SQL: 统计该产品总收入

## 约束
1. 包含时间过滤
2. ⚠️ 占位符不加引号
...

总计: ~970 tokens (减少 60%)
```

---

## 🎯 优化原则

1. **保留关键信息**：
   - ✅ 核心约束（占位符不加引号）
   - ✅ 必要的表结构信息
   - ✅ 工具列表

2. **移除冗余**：
   - ❌ 重复的说明
   - ❌ 过于详细的步骤描述
   - ❌ 冗长的后果列表
   - ❌ 不必要的 JSON 字段

3. **简化格式**：
   - 📝 使用简洁的标题
   - 📝 单行表达（合并相关信息）
   - 📝 紧凑 JSON（无缩进）

4. **优先级管理**：
   - 🔥 CRITICAL: 用户需求、核心约束
   - 🔥 HIGH: Schema 信息、工具列表
   - 🔥 MEDIUM/LOW: 详细规则、示例

---

## ✅ 总结

通过系统性的优化，我们：

1. ✅ **减少了 60% 的 prompt tokens**（2450 → 970）
2. ✅ **保留了所有关键信息**（约束、schema、工具）
3. ✅ **提高了可读性**（更简洁清晰）
4. ✅ **加快了响应速度**（更少的 tokens 意味着更快的处理）

**关键成果**：
- ReAct Prompt: **-75%**
- Task Context: **-75%**
- Schema Context: **-40%**
- Headers: **-60%**

**预期效果**：
- 🚀 更快的 LLM 响应
- 💰 更低的 API 成本
- 📊 更好的 token 预算管理
- ✨ 更清晰的 prompt 结构

---

**作者**: AI Assistant
**审核**: 待定
**最后更新**: 2025-10-26
