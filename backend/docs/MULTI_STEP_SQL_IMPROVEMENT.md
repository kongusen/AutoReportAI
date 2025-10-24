# 多步骤SQL生成改进说明

## 问题背景

之前的系统存在SQL质量问题，主要表现为：
- Agent生成的SQL引用了不存在的列名（如 `refund_date`）
- 导致ETL执行失败：`Unknown column 'refund_date' in 'table list'`
- 一次性生成SQL，缺乏验证机制

## 解决方案

基于Loom框架（类似Claude Code的多步骤能力），实现了多步骤SQL生成流程：

### 核心流程

```
Step 1: Schema Discovery
├─ 获取数据库所有表
├─ 分析业务需求，选择相关表
└─ 获取相关表的精确列信息

Step 2: SQL Generation
├─ 基于Step 1的精确schema
├─ 生成SQL（确保只使用存在的列）
└─ 记录生成reasoning

Step 3: SQL Validation
├─ 语法检查
├─ Schema验证（列名、表名）
└─ 逻辑检查

Step 4: SQL Test (可选)
├─ 数据库上执行小样本测试
└─ 确认SQL可执行
```

## 代码修改

### 修改的文件

1. **`backend/app/services/application/placeholder/placeholder_service.py`**
   - 修改 `analyze_placeholder` 方法，改为多步骤流程
   - 添加辅助方法：
     - `_build_data_source_config`: 构建数据源配置
     - `_discover_schema`: Schema发现
     - `_select_relevant_tables`: 智能选表
     - `_generate_sql_with_schema`: 基于schema生成SQL
     - `_build_schema_prompt`: 构建schema提示
     - `_validate_sql`: SQL验证
     - `_test_sql`: SQL测试

## 使用方式

### 默认使用（自动启用）

现有代码**无需修改**，系统会自动使用新的多步骤生成：

```python
from app.services.application.placeholder.placeholder_service import PlaceholderApplicationService

service = PlaceholderApplicationService(user_id="user-123")

request = PlaceholderAnalysisRequest(
    placeholder_id="test-001",
    business_command="统计退货申请",
    target_objective="获取退货量最高的州市",
    requirements="查询ods_refund表",
    data_source_info={
        "id": "ds-001",
        "database_name": "yjg",
        "host": "192.168.61.30",
        # ... 其他配置
    }
)

# 流式输出，自动执行多步骤生成
async for event in service.analyze_placeholder(request):
    print(event)
```

### 事件流

生成过程中会产生以下事件：

1. **analysis_started** - 分析开始
   ```json
   {
     "type": "analysis_started",
     "placeholder_id": "test-001",
     "mode": "multi_step_sql_generation"
   }
   ```

2. **stage_started** - 阶段开始
   ```json
   {
     "type": "stage_started",
     "stage": "schema_discovery",
     "message": "探索数据库schema..."
   }
   ```

3. **stage_completed** - 阶段完成
   ```json
   {
     "type": "stage_completed",
     "stage": "schema_discovery",
     "message": "Schema探索完成: 3个表, 25列",
     "data": {
       "tables": ["ods_refund", "ods_order"],
       "total_columns": 25
     }
   }
   ```

4. **sql_generation_complete** - SQL生成完成
   ```json
   {
     "type": "sql_generation_complete",
     "placeholder_id": "test-001",
     "content": {
       "sql_query": "SELECT ...",
       "validation_status": "valid",
       "metadata": {
         "quality_score": 100.0,
         "generation_method": "multi_step",
         "schema_discovery": true,
         "validation_performed": true,
         "test_performed": true
       }
     },
     "quality_score": 100.0
   }
   ```

### 质量分数

系统会自动计算SQL质量分数（0-100）：

- **Schema Discovery成功**: +20分
- **SQL生成成功**: +20分
- **验证完全通过**: +30分（部分通过: +15分）
- **测试通过**: +30分

**质量评级**：
- ≥80分: good (可直接使用)
- 60-79分: medium (建议审核)
- <60分: poor (需要优化)

### 可选配置

#### 禁用SQL测试（加快速度）

```python
request.context = {
    "enable_sql_test": False  # 禁用测试步骤
}
```

## 优势

### 1. 精确的Schema信息

之前：
```python
# 可能只有部分schema或过时的信息
schema_info.columns = {"ods_refund": ["refund_date", ...]}  # refund_date不存在！
```

现在：
```python
# Step 1 实时获取精确schema
schema_info.columns = {
    "ods_refund": ["refund_id", "refund_time", "refund_amount", ...]  # 真实存在的列
}
```

### 2. Schema驱动的SQL生成

之前：
```python
# Agent自由发挥，可能使用不存在的列
sql = "SELECT refund_date FROM ods_refund"  # ❌ refund_date不存在
```

现在：
```python
# Agent被明确告知只能使用这些列
prompt = f"""
## 可用的数据库Schema（请严格使用以下表和列）
### 表: ods_refund
列: refund_id, refund_time, refund_amount, ...

## 要求
1. **只能使用上述Schema中存在的表和列**
"""

sql = "SELECT refund_time FROM ods_refund"  # ✅ 使用存在的列
```

### 3. 多层验证

```python
# Step 3: 验证SQL
validation_result = {
    "is_valid": False,
    "errors": ["使用了不存在的列: refund_date"],
    "suggestions": ["可用的列: refund_id, refund_time, ..."]
}
```

### 4. 实际测试

```python
# Step 4: 在数据库上测试
test_result = {
    "success": True,
    "row_count": 5,
    "columns": ["refund_time", "count"]
}
```

## 与现有系统的兼容性

### 完全向后兼容

- ✅ API接口不变
- ✅ 事件类型扩展（新增stage相关事件）
- ✅ 返回结果格式兼容
- ✅ 现有调用代码无需修改

### 集成点

系统会在以下场景自动使用多步骤生成：

1. **Placeholder分析**
   ```python
   service.analyze_placeholder(request)  # 自动使用
   ```

2. **报告生成任务**
   ```python
   # backend/app/services/infrastructure/task_queue/tasks.py
   # generate_report_task 调用 placeholder service
   ```

3. **API端点**
   ```python
   # backend/app/api/endpoints/placeholders.py
   # POST /api/placeholders/analyze
   ```

## 性能考虑

### 增加的时间开销

- Schema Discovery: ~1-2秒
- SQL Validation: <0.1秒
- SQL Test: ~0.5-1秒

**总增加**: 约2-3秒

### 优化建议

1. **缓存Schema信息**（适用于同一数据源的多次查询）
2. **并行处理多个占位符**
3. **可选禁用测试步骤**（通过 `enable_sql_test: false`）

## 监控和调试

### 日志输出

```log
[INFO] 🔍 Step 1: Schema Discovery - 开始探索数据库schema
[INFO] 📊 发现 10 个表: ['ods_refund', 'ods_order', ...]
[INFO] 🎯 选择了 3 个相关表: ['ods_refund', 'ods_order', 'ods_product']
[INFO] 📝 Step 2: SQL Generation - 基于schema生成SQL
[INFO] ✅ Step 3: SQL Validation - 验证SQL
[INFO] 🧪 Step 4: SQL Test - 测试SQL执行
```

### 事件监听

```python
async for event in service.analyze_placeholder(request):
    if event.get("type") == "stage_completed":
        stage = event.get("stage")
        data = event.get("data")
        print(f"✅ {stage} 完成: {data}")

    elif event.get("type") == "stage_failed":
        stage = event.get("stage")
        error = event.get("error")
        print(f"❌ {stage} 失败: {error}")
```

## 故障排除

### Q: Schema Discovery失败

**问题**: `获取表列表失败: connection timeout`

**解决**:
1. 检查数据源配置是否正确
2. 确认数据库连接正常
3. 检查网络和防火墙设置

### Q: SQL验证发现不存在的列

**问题**: `使用了不存在的列: xxx`

**说明**: 这正是系统在工作！它阻止了错误的SQL被执行

**处理**:
- 系统会在日志中显示可用的列
- Agent会基于反馈优化SQL

### Q: SQL测试失败

**问题**: `SQL测试失败: syntax error`

**解决**:
1. 检查验证结果中的错误信息
2. 确认SQL语法正确
3. 检查数据库方言差异

## 总结

通过多步骤SQL生成，系统现在能够：

1. ✅ **精确获取schema** - 确保只使用存在的表和列
2. ✅ **Schema驱动生成** - Agent被明确告知可用的列
3. ✅ **多层验证** - 语法、schema、逻辑三重检查
4. ✅ **实际测试** - 在数据库上验证SQL可执行
5. ✅ **质量评分** - 量化SQL质量，便于监控

这从根本上解决了"Unknown column"等错误，显著提高了SQL生成的可靠性。
