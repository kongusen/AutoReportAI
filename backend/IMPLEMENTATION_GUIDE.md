# SQL-First 架构实施指南

## 🎯 核心理念

**明确失败优于低质量降级**

```
SQLCoordinator.generate() {
    ├─ Phase 1: 依赖解决（同步）
    │   ├─ TimeResolver: 解决时间窗口
    │   └─ SchemaResolver: 解决Schema信息
    │
    ├─ Phase 2: 结构化SQL生成（最多3次）
    │   └─ StructuredSQLGenerator: 强制JSON输出
    │
    ├─ Phase 3: 三层验证
    │   ├─ 语法验证 (sqlparse)
    │   ├─ Schema一致性检查
    │   └─ DryRun验证 (EXPLAIN)
    │
    ├─ Phase 4: 智能修复（可选，最多2次）
    │   └─ 自动修正表名、括号等常见问题
    │
    └─ 成功 or 明确报错（附详细原因和建议）
}
```

---

## 📋 架构对比

### ❌ 旧架构（PTAV多轮循环）

**流程**：
```
Plan → 发现缺Schema → 调用schema.get_columns →
Plan → 发现缺Time → 调用time.window →
Plan → 生成SQL →
Plan → 验证SQL → 发现问题 →
Plan → 修复SQL →
Plan → 再次验证 → 成功
```

**问题**：
- ❌ 平均3-5轮迭代
- ❌ 依赖被动解决（每次等一轮）
- ❌ LLM自由文本生成，解析失败率高
- ❌ Context在多轮中丢失
- ❌ 无兜底保护

**数据**：
- 迭代次数：3-5轮
- SQL有效率：~60%
- 平均耗时：15-30秒

---

### ✅ 新架构（SQL-First）

**流程**：
```
SQLCoordinator.generate() {
    同步解决全部依赖 → 生成SQL（强制JSON） →
    三层验证 → 智能修复（如需要） →
    返回有效SQL or 详细错误
}
```

**优势**：
- ✅ 1-2轮完成
- ✅ 依赖主动前置（一次性解决）
- ✅ 结构化输出（JSON Schema约束）
- ✅ 分层验证（快速失败，精准修复）
- ✅ 明确失败（详细错误+建议）

**预期数据**：
- 迭代次数：1-2轮（↓60%）
- SQL有效率：90%+（↑50%）
- 平均耗时：5-10秒（↓67%）

---

## 🔧 核心组件

### 1. SQLGenerationCoordinator

**职责**：统一管理SQL生成的完整流程

**位置**：`backend/app/services/infrastructure/agents/sql_generation/coordinator.py`

**关键方法**：
```python
async def generate(
    query: str,              # 用户查询文本
    context_snapshot: Dict,  # 执行上下文
) -> SQLGenerationResult:
    """
    返回：
    - success=True: 有效SQL + 元数据
    - success=False: 详细错误 + 建议
    """
```

---

### 2. StructuredSQLGenerator

**职责**：强制LLM返回JSON格式的SQL

**位置**：`backend/app/services/infrastructure/agents/sql_generation/generators.py`

**输出格式**：
```json
{
  "sql": "SELECT ... FROM ... WHERE ...",
  "explanation": "查询逻辑说明",
  "tables_used": ["table1", "table2"],
  "confidence": 0.9
}
```

**关键特性**：
- 使用 `response_format={"type": "json_object"}` 约束LLM
- 低温度（0.05）首次尝试，确保稳定性
- 基础语法检查（防止DROP/DELETE等）

---

### 3. SQLValidator

**职责**：三层验证SQL合法性（不执行）

**位置**：`backend/app/services/infrastructure/agents/sql_generation/validators.py`

**验证层级**：
1. **语法验证**（sqlparse）
   - SQL结构完整性
   - 危险操作检测
   - 括号匹配

2. **Schema一致性**
   - 表名是否存在
   - 字段名是否存在
   - 智能相似匹配

3. **DryRun验证**（EXPLAIN）
   - 不执行实际查询
   - 验证SQL可执行性
   - 快速（通常<1s）

---

### 4. TimeResolver & SchemaResolver

**职责**：主动解决SQL生成的依赖

**位置**：`backend/app/services/infrastructure/agents/sql_generation/resolvers.py`

**TimeResolver**：
- 从查询文本推断时间范围
- 或使用已有的时间窗口

**SchemaResolver**：
- 调用 SchemaGetColumnsTool
- 获取表结构信息

---

## 🚀 集成步骤

### Step 1: 启用Coordinator

**方式1：Feature Flag（推荐，灰度发布）**

在 `user_custom_settings` 表中配置：
```sql
-- 对特定用户启用
UPDATE user_custom_settings
SET settings = JSON_SET(settings, '$.enable_sql_generation_coordinator', true)
WHERE user_id = 'test_user_1';
```

**方式2：强制启用（测试阶段）**

在 `task_driven_context` 中传递：
```python
task_driven_context = {
    "force_sql_generation_coordinator": True,
    # ... 其他context
}
```

---

### Step 2: 验证集成

**测试脚本**（`backend/app/tests/test_sql_coordinator.py`）：

```python
import pytest
from app.services.infrastructure.agents.sql_generation import (
    SQLGenerationCoordinator,
    SQLGenerationConfig
)
from app.core.container import Container

@pytest.mark.asyncio
async def test_sql_coordinator_success():
    """测试成功场景"""
    container = Container()

    coordinator = SQLGenerationCoordinator(
        container=container,
        llm_client=container.llm_service,
        db_connector=container.data_source,
        config=SQLGenerationConfig()
    )

    result = await coordinator.generate(
        query="统计昨日销售总额",
        context_snapshot={
            "time_window": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-02"
            },
            "column_details": {
                "ods_sales": ["sale_date", "amount", "product_id"]
            },
            "data_source": {
                "id": "test_ds_id",
                "source_type": "doris",
                "host": "localhost"
            }
        }
    )

    assert result.success
    assert "SELECT" in result.sql
    assert "{{start_date}}" in result.sql
    print(f"✅ 生成的SQL: {result.sql}")

@pytest.mark.asyncio
async def test_sql_coordinator_failure():
    """测试失败场景"""
    coordinator = SQLGenerationCoordinator(...)

    result = await coordinator.generate(
        query="模糊不清的需求",
        context_snapshot={}  # 缺少依赖
    )

    assert not result.success
    assert result.error
    assert result.metadata.get("suggestions")
    print(f"❌ 错误信息: {result.error}")
    print(f"💡 建议: {result.metadata['suggestions']}")
```

**运行测试**：
```bash
cd backend
pytest app/tests/test_sql_coordinator.py -v -s
```

---

### Step 3: 监控日志

**关键日志标识**：
```
🚀 [SQLCoordinator] 开始生成SQL
🔍 [SQLCoordinator] 解决时间依赖
✅ [SQLCoordinator] 时间窗口: {...}
🔍 [SQLCoordinator] 解决Schema依赖
✅ [SQLCoordinator] Schema: 5个表
🔧 [SQLCoordinator] 第1次生成尝试
✅ [SQLCoordinator] SQL生成并验证成功
❌ [SQLCoordinator] 3次尝试后仍无法生成有效SQL
```

**日志位置**：
- 应用日志：查看 `[SQLCoordinator]` 关键词
- 错误日志：查看失败原因和建议

---

### Step 4: 灰度发布策略

**阶段1：内部测试（1-2天）**
```sql
-- 对1-2个测试用户启用
UPDATE user_custom_settings
SET settings = JSON_SET(settings, '$.enable_sql_generation_coordinator', true)
WHERE user_id IN ('test_user_1', 'test_user_2');
```

**观察指标**：
- SQL生成成功率
- 平均响应时间
- 错误日志

**阶段2：小范围扩大（3-5天）**
```sql
-- 对10%用户启用（按user_id哈希）
UPDATE user_custom_settings
SET settings = JSON_SET(settings, '$.enable_sql_generation_coordinator', true)
WHERE MOD(CAST(user_id AS UNSIGNED), 10) = 0;
```

**阶段3：全量上线**
```sql
-- 对所有用户启用
UPDATE user_custom_settings
SET settings = JSON_SET(settings, '$.enable_sql_generation_coordinator', true);
```

---

## 📊 监控指标

### 核心指标

**成功率**：
```python
success_rate = (成功生成数 / 总请求数) * 100%
目标：≥ 90%
```

**平均迭代次数**：
```python
avg_iterations = Σ(attempt) / 总请求数
目标：≤ 2轮
```

**平均响应时间**：
```python
avg_time = Σ(耗时) / 总请求数
目标：≤ 10秒
```

### 告警阈值

- ⚠️ 成功率 < 80%：检查LLM服务状态
- ⚠️ 平均迭代 > 2.5轮：检查依赖解决逻辑
- ⚠️ 平均耗时 > 15秒：检查数据库响应

---

## 🔍 故障排查

### Q1: Coordinator没有被调用？

**检查**：
```python
# 在 executor.py 中添加日志
logger.info(f"Feature flag enabled: {self._should_use_sql_coordinator(ai, context)}")
```

**可能原因**：
- Feature flag未启用
- user_id未正确传递

---

### Q2: 依赖解决失败？

**检查**：
```python
# 查看context_snapshot内容
logger.info(f"Context keys: {list(context_snapshot.keys())}")
logger.info(f"Time window: {context_snapshot.get('time_window')}")
logger.info(f"Schema: {context_snapshot.get('column_details')}")
```

**可能原因**：
- time_window缺失
- data_source配置不完整
- SchemaGetColumnsTool未返回数据

---

### Q3: LLM返回非JSON？

**检查**：
```python
# 查看原始响应
logger.info(f"LLM raw response: {response.get('response')}")
```

**解决方案**：
- 确认LLM支持 `response_format={"type": "json_object"}`
- 降低temperature（已设置为0.05）
- 调整prompt，强调JSON格式

---

### Q4: 生成的SQL总是验证失败？

**检查**：
```python
# 查看验证详情
logger.info(f"Validation issues: {validation.issues}")
logger.info(f"Schema tables: {list(schema.keys())}")
```

**解决方案**：
- 检查Schema是否正确加载
- 检查表名/字段名大小写
- 启用智能修复（max_fix_attempts=2）

---

## 💡 最佳实践

### 1. Prompt优化

**基于失败案例调整**：
```python
# 在 _build_generation_prompt() 中
if "对比" in sql_context.query:
    base_prompt += """
## 特别提示（对比查询）
- 必须包含baseline和compare两列
- 计算差值：compare - baseline AS diff
- 计算百分比变化率
"""
```

### 2. Schema预加载

**在Orchestrator启动时**：
```python
# 对常用表预加载schema
if not context.get("column_details"):
    # 主动调用SchemaResolver
    schema_result = await self.schema_resolver.resolve(context)
    context["column_details"] = schema_result.schema
```

### 3. 错误分类

**构建错误知识库**：
```python
# 分类常见错误
ERROR_CATEGORIES = {
    "schema_mismatch": "Schema不匹配",
    "syntax_error": "SQL语法错误",
    "json_parse_error": "JSON解析失败",
    "dependency_missing": "依赖信息缺失",
}
```

---

## 🎯 预期改进

| 指标 | 旧架构 | 新架构 | 改进 |
|------|--------|--------|------|
| **平均迭代次数** | 3-5轮 | 1-2轮 | ↓60% |
| **SQL有效率** | 60% | 90%+ | ↑50% |
| **平均响应时间** | 15-30s | 5-10s | ↓67% |
| **明确错误率** | N/A | 10% | 新增 |
| **用户满意度** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 显著提升 |

---

## 📌 重要提醒

### ✅ 保留的组件（不受影响）

1. **单占位符分析**
   - `PlaceholderApplicationService`
   - `PlaceholderIntelligentProcessor`
   - 用于模板文档中的文本智能替换

2. **Schema/Time工具**
   - `SchemaGetColumnsTool`
   - `TimeWindowTool`
   - 被Coordinator复用

3. **PTAV Orchestrator**
   - 其他非SQL任务继续使用PTAV循环
   - SQL生成部分被Coordinator接管

### ❌ 移除的机制

1. **模板降级**
   - 不再使用 `TemplateSQLGenerator`
   - 失败明确报错，不做低质量降级

2. **多轮被动依赖解决**
   - 不再在PTAV循环中被动等待
   - Coordinator主动同步解决

---

## 🚀 下一步

1. ✅ 运行测试验证Coordinator
2. ✅ 启用Feature Flag（1个测试用户）
3. ✅ 观察日志，确认成功率
4. ✅ 逐步扩大到10% → 50% → 100%
5. ✅ 收集反馈，优化Prompt
6. ✅ 文档沉淀，培训团队

---

## 📞 联系支持

遇到问题？
- 查看日志：搜索 `[SQLCoordinator]`
- 检查测试：运行 `pytest app/tests/test_sql_coordinator.py`
- 调整配置：修改 `SQLGenerationConfig`

**核心原则：明确失败优于低质量降级！** 🎯
