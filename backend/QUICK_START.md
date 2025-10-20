# SQL-First 架构快速开始 🚀

## 5分钟快速验证

### Step 1: 运行测试（2分钟）

```bash
cd backend

# 运行基础测试
pytest app/tests/test_sql_coordinator.py::TestSQLGenerationCoordinator::test_simple_query_success -v -s

# 运行完整测试套件
pytest app/tests/test_sql_coordinator.py -v -s
```

**预期结果**：
```
✅ 成功生成SQL:
SELECT
    SUM(amount) AS total_amount
FROM ods_sales
WHERE sale_date BETWEEN '{{start_date}}' AND '{{end_date}}'

📊 元数据: {'attempt': 1, 'confidence': 0.92}
```

---

### Step 2: 启用Feature Flag（1分钟）

**方式A：对特定用户启用（推荐）**

```sql
-- 在数据库中执行
UPDATE user_custom_settings
SET settings = JSON_SET(COALESCE(settings, '{}'), '$.enable_sql_generation_coordinator', true)
WHERE user_id = 'YOUR_USER_ID';
```

**方式B：代码中强制启用（测试用）**

```python
# 在调用Orchestrator时
task_driven_context = {
    "force_sql_generation_coordinator": True,
    # ... 其他context
}
```

---

### Step 3: 验证日志（2分钟）

**启动应用后，观察日志**：

```bash
# 查看SQL生成日志
tail -f logs/application.log | grep "SQLCoordinator"
```

**成功日志示例**：
```
2024-01-20 10:00:00 INFO [SQLCoordinator] 开始生成SQL: 统计销售额
2024-01-20 10:00:01 INFO [SQLCoordinator] 解决时间依赖
2024-01-20 10:00:01 INFO [SQLCoordinator] 时间窗口: {'start_date': '2024-01-01', ...}
2024-01-20 10:00:02 INFO [SQLCoordinator] 解决Schema依赖
2024-01-20 10:00:02 INFO [SQLCoordinator] Schema: 5个表
2024-01-20 10:00:03 INFO [SQLCoordinator] 第1次生成尝试
2024-01-20 10:00:05 INFO [SQLCoordinator] SQL生成并验证成功
```

**失败日志示例**：
```
2024-01-20 10:00:10 ERROR [SQLCoordinator] 3次尝试后仍无法生成有效SQL
2024-01-20 10:00:10 ERROR [SQLCoordinator] 错误: SQL生成失败（3次尝试）: 验证失败 - 表名不存在: sales
```

---

## 架构对比速查

### ❌ 旧流程（多轮迭代）

```
请求 → Plan → 缺Schema → Get Schema →
      Plan → 缺Time → Get Time →
      Plan → 生成SQL →
      Plan → 验证失败 →
      Plan → 修复SQL →
      完成（共5轮，20秒）
```

### ✅ 新流程（一次完成）

```
请求 → Coordinator {
         同步解决依赖 →
         生成SQL(JSON) →
         三层验证 →
         智能修复 →
         完成
       } （共1轮，5秒）
```

---

## 核心代码位置

```
backend/app/services/infrastructure/agents/sql_generation/
├── coordinator.py          # 核心协调器 ⭐
├── generators.py           # 结构化生成器
├── validators.py           # 三层验证器 ⭐
├── resolvers.py            # 依赖解决器
└── context.py              # 数据结构定义
```

---

## 配置调整

### 调整重试次数

```python
# 在 executor.py 中
config = SQLGenerationConfig(
    max_generation_attempts=5,  # 默认3，可增加到5
    max_fix_attempts=3,         # 默认2，可增加到3
)
```

### 禁用DryRun验证（加快速度）

```python
config = SQLGenerationConfig(
    enable_dry_run_validation=False,  # 跳过EXPLAIN验证
)
```

---

## 故障排查速查表

| 症状 | 可能原因 | 解决方案 |
|------|---------|---------|
| Coordinator未被调用 | Feature Flag未启用 | 检查数据库配置或设置force flag |
| 依赖解决失败 | context缺少信息 | 确保传递time_window和column_details |
| LLM返回非JSON | 不支持json_object | 检查LLM服务配置 |
| SQL验证总失败 | Schema未加载 | 检查SchemaGetColumnsTool |
| 响应时间过长 | DryRun验证慢 | 禁用dry_run或优化数据库 |

---

## 预期改进数据

| 指标 | 改进前 | 改进后 | 提升 |
|------|--------|--------|------|
| 迭代次数 | 3-5轮 | 1-2轮 | ↓60% |
| SQL有效率 | 60% | 90%+ | ↑50% |
| 平均耗时 | 15-30s | 5-10s | ↓67% |

---

## 下一步

1. ✅ 运行测试确认工作
2. ✅ 启用Feature Flag
3. ✅ 观察日志和指标
4. ✅ 收集反馈
5. ✅ 逐步扩大范围

**详细文档**：查看 `IMPLEMENTATION_GUIDE.md`

**遇到问题**？搜索日志中的 `[SQLCoordinator]` 关键词 🔍
