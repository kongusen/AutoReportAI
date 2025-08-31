# Agents系统输出控制实现

## 🎯 实现原理

**控制目标而非控制流程** - agents系统正常执行完整的DAG流程，但最后根据上下文工程中的 `output_control` 参数调整最终输出内容。

## 🔧 实现方式

### 执行流程
```
1. 接收placeholder任务 → 
2. 正常执行DAG流程（Background Controller + Execution Engine）→ 
3. 检查output_control参数 → 
4. 根据mode调整最终输出格式和内容 → 
5. 返回定制化结果
```

### 核心方法
```python
# backend/app/services/agents/core/execution_engine.py

async def execute_placeholder_task(self, task_context):
    # 1. 正常执行完整DAG流程
    result = await self._execute_full_mode(task_context, control_context)
    
    # 2. 检查输出控制参数
    output_control = task_context.context_engine.get("output_control", {})
    mode = output_control.get("mode", "full")
    
    # 3. 应用输出控制
    if mode != "full":
        return await self._apply_output_control(result, output_control, data_context, task_context)
    
    return result
```

## 📊 四种输出模式

### 1. SQL生成模式 (`sql_only`)

**用于**: 模板编辑时生成高质量SQL并存储

```python
# 输入控制参数
output_control = {
    "mode": "sql_only",
    "sql_storage": True,
    "target_system": "storage"
}

# 输出结果
{
    "task_id": "template_123",
    "mode": "sql_only",
    "status": "success",
    "sql_generated": True,
    "sql_query": "SELECT SUM(amount) FROM sales WHERE date >= '2024-01-01'",
    "quality_score": 0.85,
    "storage_success": True,
    "storage_id": "sql_template_123_1677649200",
    "next_step": "manual_testing_required",
    "target_system": "storage"
}
```

### 2. 图表测试模式 (`chart_test`)

**用于**: 前端点击测试图表，基于存储SQL生成图表预览

```python
# 输入控制参数
output_control = {
    "mode": "chart_test",
    "data_source": "stored_sql",
    "target_system": "frontend"
}

data_context = {
    "stored_sql_id": "sql_template_123_1677649200",
    "test_data": [
        {"category": "产品A", "value": 1200},
        {"category": "产品B", "value": 1500}
    ]
}

# 输出结果
{
    "task_id": "template_123",
    "mode": "chart_test",
    "status": "success",
    "sql_used": "sql_template_123_1677649200",
    "chart_config": {
        "title": {"text": "销售对比"},
        "xAxis": {"type": "category", "data": ["产品A", "产品B"]},
        "yAxis": {"type": "value"},
        "series": [{"data": [1200, 1500], "type": "bar"}]
    },
    "frontend_ready": True,
    "target_system": "frontend"
}
```

### 3. SQL验证模式 (`sql_validation`)

**用于**: 任务执行前检查存储SQL是否过时

```python
# 输入控制参数
output_control = {
    "mode": "sql_validation",
    "validation_only": True,
    "target_system": "task_scheduler"
}

data_context = {
    "task_id": "monthly_report",
    "execution_date": "2024-04-01",
    "task_period_config": {
        "period_type": "monthly",
        "report_offset": 1
    }
}

# 输出结果
{
    "task_id": "monthly_report",
    "mode": "sql_validation",
    "status": "success",
    "validation_result": {
        "is_current": False,
        "needs_update": True,
        "confidence": 0.8,
        "reason": "时间范围过时，需要更新",
        "suggested_updates": ["更新时间范围", "调整WHERE条件"]
    },
    "task_info": {
        "task_id": "monthly_report",
        "execution_date": "2024-04-01",
        "period_config": {"period_type": "monthly", "report_offset": 1}
    }
}
```

### 4. ETL图表模式 (`chart_etl`)

**用于**: 任务执行时基于ETL数据生成图表给报告系统

```python
# 输入控制参数
output_control = {
    "mode": "chart_etl",
    "data_source": "etl_data",
    "target_system": "reporting"
}

data_context = {
    "task_id": "monthly_report",
    "execution_date": "2024-04-01",
    "etl_data": [
        {"month": "2024-01", "sales": 150000, "profit": 30000},
        {"month": "2024-02", "sales": 180000, "profit": 36000},
        {"month": "2024-03", "sales": 200000, "profit": 40000}
    ]
}

# 输出结果
{
    "task_id": "monthly_report",
    "mode": "chart_etl",
    "status": "success",
    "chart_config": {
        "title": {"text": "月度销售趋势"},
        "xAxis": {"type": "category", "data": ["2024-01", "2024-02", "2024-03"]},
        "yAxis": {"type": "value"},
        "series": [{"data": [150000, 180000, 200000], "type": "line"}]
    },
    "reporting_ready": True,
    "etl_data_applied": True,
    "target_system": "reporting"
}
```

## 🚀 实际使用示例

### 模板场景调用

```python
# backend/app/services/domain/template/enhanced_template_parser.py

async def generate_sql_for_template(template_id: str, template_content: str):
    """模板编辑时生成SQL"""
    
    placeholder_service = IntelligentPlaceholderService()
    
    # 调用会自动设置output_control = {"mode": "sql_only"}
    result = await placeholder_service.analyze_template_for_sql_generation(
        template_content=template_content,
        template_id=template_id,
        user_id=user_id
    )
    
    # agents系统会返回SQL生成结果
    return {
        "sql_generated": result.analysis_results[0].generated_sql,
        "storage_id": "...",  # 从agents输出中提取
        "next_step": "manual_testing"
    }

async def test_chart_for_template(template_id: str, placeholder_text: str, stored_sql_id: str):
    """前端测试图表"""
    
    # 调用会自动设置output_control = {"mode": "chart_test"}
    result = await placeholder_service.analyze_template_for_chart_testing(
        placeholder_text=placeholder_text,
        template_content=template_content,
        stored_sql_id=stored_sql_id,
        test_data=test_data,
        template_id=template_id,
        user_id=user_id
    )
    
    # agents系统会返回图表配置
    return {
        "chart_config": result.chart_config,  # 从agents输出中提取
        "frontend_ready": True
    }
```

### 任务场景调用

```python
# backend/app/services/application/workflows/enhanced_report_generation_workflow.py

async def execute_monthly_task(task_id: str, execution_date: datetime):
    """执行月度任务"""
    
    # 1. 验证SQL时效性
    # 调用会自动设置output_control = {"mode": "sql_validation"}
    validation_result = await placeholder_service.analyze_task_for_sql_validation(
        task_id=task_id,
        execution_date=execution_date,
        template_content=template_content,
        task_period_config={"period_type": "monthly", "report_offset": 1}
    )
    
    # agents返回验证结果
    needs_update = validation_result.validation_result["needs_update"]
    
    if needs_update:
        # 更新过时的SQL
        await update_outdated_sqls(task_id)
    
    # 2. ETL处理
    etl_data = await process_etl_data(task_id, execution_date)
    
    # 3. 生成图表
    # 调用会自动设置output_control = {"mode": "chart_etl"}
    chart_result = await placeholder_service.analyze_task_for_chart_generation(
        placeholder_text="{{图表：月度销售趋势}}",
        template_content=template_content,
        etl_data=etl_data,
        task_id=task_id,
        execution_date=execution_date,
        task_period_config={"period_type": "monthly", "report_offset": 1}
    )
    
    # agents返回报告系统需要的图表配置
    return {
        "charts_for_reporting": [chart_result.chart_config],
        "ready_for_reporting_system": True
    }
```

## 💡 核心优势

### 1. **保持DAG完整性**
- agents系统内部的DAG流程完全不变
- Background Controller和Execution Engine正常工作
- 只在最后调整输出格式

### 2. **精确控制输出**
- 同样的DAG执行，不同的输出内容
- 模板场景：高质量SQL + 存储信息
- 测试场景：图表配置 + 前端渲染数据
- 任务场景：时效性验证 + 更新建议
- ETL场景：报告图表 + 系统集成信息

### 3. **完美的架构分离**
- placeholder构建上下文工程（包含控制参数）
- agents执行DAG处理（完整流程）
- 输出控制器调整最终结果（定制化输出）

### 4. **Token高效使用**
- DAG正常执行，充分利用推理能力
- 根据需要返回不同信息，避免浪费
- 上下文信息得到充分利用

这个实现完美地满足了你的需求：**控制目标而非控制流程**！agents系统保持其强大的DAG处理能力，同时能够根据不同场景返回精确定制的结果。