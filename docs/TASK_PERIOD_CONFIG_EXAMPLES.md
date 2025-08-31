# 任务周期配置示例

## 🎯 任务周期配置参数

现在任务的时间上下文可以基于任务设置的周期参数来生成，支持日、周、月、季、年等多种周期。

## 📋 配置参数说明

```python
task_period_config = {
    "period_type": "daily|weekly|monthly|quarterly|yearly",  # 周期类型
    "report_offset": 1,                                      # 报告偏移量
    "start_day_of_week": 1,                                  # 周报开始星期（1=周一）
    "fiscal_year_start_month": 1,                            # 财年开始月份
    "custom_period": {...}                                   # 自定义周期设置
}
```

## 🗓️ 使用示例

### 1. 日报任务

```python
# 每天早上9点生成昨天的日报
daily_task_config = {
    "period_type": "daily",
    "report_offset": 1  # 报告昨天的数据
}

# 调用示例
result = await placeholder_service.analyze_task_for_sql_validation(
    task_id="daily_sales_report",
    execution_date=datetime(2024, 3, 15, 9, 0, 0),  # 2024-03-15 09:00
    template_content=template_content,
    task_period_config=daily_task_config
)

# 生成的时间上下文:
# report_period: "2024-03-14"
# start_date: 2024-03-14 00:00:00
# end_date: 2024-03-14 23:59:59
# previous_period: 2024-03-13
```

### 2. 周报任务（周一到周日）

```python
# 每周一早上生成上周的周报
weekly_task_config = {
    "period_type": "weekly",
    "report_offset": 1,      # 报告上一周
    "start_day_of_week": 1   # 周一开始（1=Monday, 7=Sunday）
}

# 调用示例 - 2024年3月18日周一执行
result = await placeholder_service.analyze_task_for_chart_generation(
    placeholder_text="{{图表：上周销售趋势}}",
    template_content=template_content,
    etl_data=etl_data,
    task_id="weekly_sales_chart",
    execution_date=datetime(2024, 3, 18, 8, 0, 0),
    task_period_config=weekly_task_config
)

# 生成的时间上下文:
# report_period: "2024-03-11_to_2024-03-17"  # 上周一到周日
# start_date: 2024-03-11 (周一)
# end_date: 2024-03-17 (周日)
# previous_period: 2024-03-04 到 2024-03-10
```

### 3. 月报任务

```python
# 每月1号生成上个月的月报
monthly_task_config = {
    "period_type": "monthly",
    "report_offset": 1  # 报告上个月
}

# 调用示例 - 2024年4月1日执行
result = await placeholder_service.analyze_task_for_sql_validation(
    task_id="monthly_financial_report",
    execution_date=datetime(2024, 4, 1, 6, 0, 0),
    template_content=template_content,
    task_period_config=monthly_task_config
)

# 生成的时间上下文:
# report_period: "2024-03"
# start_date: 2024-03-01
# end_date: 2024-03-31
# previous_period: 2024-02-01 到 2024-02-29
```

### 4. 季报任务

```python
# 每季度第一个月的1号生成上季度的季报
quarterly_task_config = {
    "period_type": "quarterly",
    "report_offset": 1  # 报告上个季度
}

# 调用示例 - 2024年4月1日执行Q1季报
result = await placeholder_service.analyze_task_for_chart_generation(
    placeholder_text="{{图表：Q1业绩总览}}",
    template_content=template_content,
    etl_data=quarterly_etl_data,
    task_id="quarterly_performance_chart",
    execution_date=datetime(2024, 4, 1, 7, 0, 0),
    task_period_config=quarterly_task_config
)

# 生成的时间上下文:
# report_period: "2024-Q1"
# start_date: 2024-01-01
# end_date: 2024-03-31
# previous_period: 2023-10-01 到 2023-12-31 (上一季度)
```

### 5. 年报任务（自然年）

```python
# 每年1月1日生成上一年的年报
yearly_natural_config = {
    "period_type": "yearly",
    "report_offset": 1,
    "fiscal_year_start_month": 1  # 自然年，1月开始
}

# 调用示例 - 2024年1月1日执行2023年年报
result = await placeholder_service.analyze_task_for_sql_validation(
    task_id="yearly_annual_report",
    execution_date=datetime(2024, 1, 1, 8, 0, 0),
    template_content=template_content,
    task_period_config=yearly_natural_config
)

# 生成的时间上下文:
# report_period: "FY2023"
# start_date: 2023-01-01
# end_date: 2023-12-31
# previous_period: 2022-01-01 到 2022-12-31
```

### 6. 年报任务（财年）

```python
# 财年从4月1日开始，每年4月1日生成上一财年的年报
yearly_fiscal_config = {
    "period_type": "yearly",
    "report_offset": 1,
    "fiscal_year_start_month": 4  # 财年4月开始
}

# 调用示例 - 2024年4月1日执行FY2023年报
result = await placeholder_service.analyze_task_for_chart_generation(
    placeholder_text="{{图表：FY2023年度总结}}",
    template_content=template_content,
    etl_data=yearly_etl_data,
    task_id="fiscal_year_summary_chart",
    execution_date=datetime(2024, 4, 1, 9, 0, 0),
    task_period_config=yearly_fiscal_config
)

# 生成的时间上下文:
# report_period: "FY2023"
# start_date: 2023-04-01
# end_date: 2024-03-31
# previous_period: 2022-04-01 到 2023-03-31
```

## 🔧 实际使用场景

### 任务调度系统集成

```python
# backend/app/services/application/workflows/enhanced_report_generation_workflow.py

class EnhancedReportGenerationWorkflow:
    async def execute_scheduled_task(
        self,
        task_id: str,
        execution_date: datetime,
        task_config: Dict[str, Any]  # 包含period_config
    ):
        """执行定时任务"""
        
        # 从任务配置中提取周期配置
        task_period_config = task_config.get("period_config", {
            "period_type": "monthly",
            "report_offset": 1
        })
        
        # 1. 验证SQL时效性
        validation_result = await placeholder_service.analyze_task_for_sql_validation(
            task_id=task_id,
            execution_date=execution_date,
            template_content=task_config["template_content"],
            task_period_config=task_period_config  # 传递周期配置
        )
        
        # 2. 生成图表（如果需要）
        if task_config.get("has_charts"):
            chart_results = []
            
            for chart_placeholder in task_config["chart_placeholders"]:
                result = await placeholder_service.analyze_task_for_chart_generation(
                    placeholder_text=chart_placeholder["text"],
                    template_content=task_config["template_content"],
                    etl_data=etl_data[chart_placeholder["data_key"]],
                    task_id=task_id,
                    execution_date=execution_date,
                    task_period_config=task_period_config  # 传递同样的周期配置
                )
                chart_results.append(result)
        
        return {
            "task_completed": True,
            "period_info": {
                "type": task_period_config.get("period_type"),
                "report_period": validation_result.analysis_results[0].context_analysis.time_context.report_period if validation_result.analysis_results else None
            },
            "validation_result": validation_result,
            "chart_results": chart_results
        }
```

### 任务配置示例

```python
# 任务配置数据库或配置文件中的示例

task_configurations = {
    "daily_sales_summary": {
        "template_content": "今日销售总结: {{统计：销售总额}} {{图表：销售趋势}}",
        "period_config": {
            "period_type": "daily",
            "report_offset": 1
        },
        "schedule": "0 9 * * *",  # 每天9点执行
        "has_charts": True,
        "chart_placeholders": [
            {"text": "{{图表：销售趋势}}", "data_key": "daily_sales"}
        ]
    },
    
    "weekly_performance_report": {
        "template_content": "周度绩效报告: {{统计：本周业绩}} {{图表：部门对比}}",
        "period_config": {
            "period_type": "weekly",
            "report_offset": 1,
            "start_day_of_week": 1  # 周一开始
        },
        "schedule": "0 8 * * MON",  # 每周一8点执行
        "has_charts": True,
        "chart_placeholders": [
            {"text": "{{图表：部门对比}}", "data_key": "weekly_performance"}
        ]
    },
    
    "monthly_financial_report": {
        "template_content": "月度财务报告: {{统计：月度收入}} {{统计：月度支出}} {{图表：财务趋势}}",
        "period_config": {
            "period_type": "monthly",
            "report_offset": 1
        },
        "schedule": "0 6 1 * *",  # 每月1号6点执行
        "has_charts": True,
        "chart_placeholders": [
            {"text": "{{图表：财务趋势}}", "data_key": "monthly_financial"}
        ]
    }
}
```

## ✨ 优势

### 1. **灵活的周期支持**
- 支持日、周、月、季、年等标准周期
- 支持自然年和财年
- 支持自定义周开始日期

### 2. **智能时间计算**
- 自动计算报告期间的开始和结束日期
- 自动计算上一个周期用于对比
- 正确处理跨年、跨月的边界情况

### 3. **任务配置驱动**
- 任务配置决定时间上下文生成方式
- 支持不同任务使用不同的周期配置
- 便于任务调度系统集成

### 4. **SQL时效性精确判断**
- 基于任务周期配置判断SQL是否过时
- 只更新需要更新的SQL，节约Token
- 确保生成的SQL时间范围正确

这个改进完全满足了你的需求，现在任务的时间上下文可以基于任务设置的具体参数来生成，而不是固定的月度逻辑！