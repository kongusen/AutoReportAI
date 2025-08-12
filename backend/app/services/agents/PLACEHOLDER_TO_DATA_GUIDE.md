# 占位符到数据查询 - 实现指南

您的第一目标：**基于占位符和其中的提示词构建正确的数据查询，然后进行工具分析得到正确的数据**

## 🎯 核心流程概览

```
占位符 → 智能解析 → 构建查询 → 执行查询 → 数据验证 → 返回结果
   ↓         ↓         ↓         ↓         ↓         ↓
{{...}}   提取意图    SQL查询    数据库     质量检查    准确数据
```

## 🔧 快速使用

### 1. 基础使用方式

```python
from backend.app.services.agents.core.placeholder_processor import PlaceholderProcessor

# 创建处理器
processor = PlaceholderProcessor()

# 处理单个占位符
placeholder = "{{销售数据分析:查询最近3个月的销售额,按地区分组,包含同比增长率}}"
result = await processor.process_placeholder(placeholder)

# 获取数据
if result.success:
    data = result.data  # 实际的数据列表
    print(f"获得 {result.row_count} 条记录")
    print(f"数据质量: {result.data_quality.get('quality_score', 0):.2f}")
```

### 2. 支持的占位符格式

#### 标准格式：`{{分析类型:具体需求}}`

```python
# 销售分析
"{{销售数据分析:查询最近3个月的销售额,按地区分组,包含同比增长率}}"

# 客户分析  
"{{客户分析:统计本年度客户数,按客户类型分组,计算平均客单价}}"

# 产品分析
"{{产品分析:获取最近6个月产品销售量,按产品类别分组,包含占比}}"

# 财务分析
"{{财务分析:查询本季度收入和成本,按月份分组,计算利润率}}"
```

## 🧠 智能解析能力

### 自动识别的关键词

#### 时间范围
- `最近3个月` → 查询3个月内数据
- `本年度` → 查询当年数据
- `本季度` → 查询当前季度数据
- `去年同期` → 查询同比数据

#### 指标类型
- `销售额` → sum(sales_amount)
- `订单数` → count(orders) 
- `客户数` → count(distinct customer_id)
- `平均客单价` → avg(order_value)

#### 维度分组
- `按地区分组` → group by region
- `按产品分组` → group by product_name
- `按月份分组` → group by month

#### 计算要求
- `同比增长率` → 与去年同期对比
- `环比增长率` → 与上期对比
- `占比` → 百分比计算
- `累计值` → 运行总计

## 📊 实际示例

### 示例1：销售趋势分析

```python
# 占位符
placeholder = "{{销售数据分析:查询最近6个月的销售额,按月份分组,包含环比增长率}}"

# 自动解析为：
{
    "analysis_type": "sales_analysis",
    "time_range": {"type": "relative", "value": 6, "unit": "month"},
    "metrics": [{"field": "sales_amount", "aggregation": "sum"}],
    "dimensions": [{"field": "month", "type": "date_part"}],
    "calculations": [{"type": "mom_growth"}]
}

# 自动构建查询：
SELECT 
    DATE_FORMAT(date, '%Y-%m') as month,
    SUM(sales_amount) as total_sales,
    LAG(SUM(sales_amount)) OVER (ORDER BY DATE_FORMAT(date, '%Y-%m')) as prev_sales
FROM sales_data 
WHERE date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
GROUP BY DATE_FORMAT(date, '%Y-%m')
ORDER BY month

# 返回数据：
[
    {"month": "2024-01", "total_sales": 150000, "growth_rate": 15.2},
    {"month": "2024-02", "total_sales": 180000, "growth_rate": 20.0},
    {"month": "2024-03", "total_sales": 165000, "growth_rate": -8.3}
]
```

### 示例2：地区销售对比

```python
# 占位符
placeholder = "{{销售数据分析:查询本季度各地区销售额,包含占比,按销售额降序排列}}"

# 自动解析并执行，返回：
[
    {"region": "华南", "sales_amount": 500000, "percentage": 35.2},
    {"region": "华东", "sales_amount": 450000, "percentage": 31.7}, 
    {"region": "华北", "sales_amount": 300000, "percentage": 21.1},
    {"region": "西南", "sales_amount": 170000, "percentage": 12.0}
]
```

### 示例3：客户价值分析

```python
# 占位符  
placeholder = "{{客户分析:统计最近1年各客户类型的客户数和平均消费额}}"

# 返回数据：
[
    {"customer_type": "VIP", "customer_count": 150, "avg_consumption": 8500},
    {"customer_type": "普通", "customer_count": 1200, "avg_consumption": 2300},
    {"customer_type": "新客户", "customer_count": 800, "avg_consumption": 1100}
]
```

## 🔍 数据质量保证

### 自动验证机制

```python
result = await processor.process_placeholder(placeholder)

# 数据质量报告
data_quality = result.data_quality
{
    "quality_score": 0.95,        # 质量分数 (0-1)
    "total_records": 1000,        # 总记录数
    "valid_records": 980,         # 有效记录数  
    "completeness": 0.98,         # 完整性
    "consistency": 0.96,          # 一致性
    "issues": ["2% missing values"] # 发现的问题
}

# 处理日志
processing_log = result.processing_log
[
    "开始执行查询: {{...}}",
    "构建语义查询请求完成", 
    "数据库查询执行完成",
    "获取原始数据: 1000 条记录",
    "数据验证完成: 质量分数 0.95",
    "数据处理完成: 980 条记录"
]
```

### 数据清理功能

- **空值处理**：自动清理或填充空值
- **格式标准化**：统一日期、数值格式
- **异常值检测**：识别并标记异常数据
- **重复值去除**：自动去重处理

## 🚀 高级功能

### 1. 批量处理

```python
# 处理多个占位符
placeholders = [
    "{{销售数据分析:查询最近3个月销售额,按地区分组}}",
    "{{客户分析:统计客户数,按类型分组}}",
    "{{产品分析:获取产品销量,按类别分组}}"
]

results = await processor.process_multiple_placeholders(placeholders)

# 获取所有成功的结果
successful_results = [r for r in results if r.success]
```

### 2. 知识学习

系统会自动学习和优化：
- **查询模式学习**：记住常用的查询模式
- **字段映射优化**：自动推断最佳字段映射
- **性能优化**：学习并应用查询优化策略

### 3. 错误处理

```python
result = await processor.process_placeholder(placeholder)

if not result.success:
    print(f"处理失败: {result.error_message}")
    
    # 查看详细的处理日志
    for log_entry in result.processing_log:
        print(f"  {log_entry}")
```

## 📈 实际业务场景

### 场景1：日常销售报告

```python
daily_reports = [
    "{{销售数据分析:查询昨天各渠道销售额,包含同比增长率}}",
    "{{订单分析:统计昨天订单完成情况,按状态分组}}",
    "{{客户分析:新增客户数量和来源分析}}"
]

for placeholder in daily_reports:
    result = await processor.process_placeholder(placeholder)
    if result.success:
        # 将数据发送到报告系统
        generate_report(result.data)
```

### 场景2：业务监控仪表板

```python
dashboard_queries = [
    "{{实时监控:当前在线用户数,按地区分布}}",
    "{{性能监控:最近1小时系统响应时间,按服务分组}}",
    "{{业务监控:今日GMV完成情况,与目标对比}}"
]

dashboard_data = {}
for query in dashboard_queries:
    result = await processor.process_placeholder(query)
    if result.success:
        dashboard_data[query] = result.data
```

### 场景3：临时分析需求

```python
# 临时业务问题：分析特定时期的异常
ad_hoc_query = "{{异常分析:查询上周销售额低于平均值的产品,按降幅排序,包含可能原因}}"

result = await processor.process_placeholder(ad_hoc_query)
if result.success:
    # 快速获得分析结果
    anomaly_products = result.data
    print(f"发现 {len(anomaly_products)} 个异常产品")
```

## ⚙️ 配置和自定义

### 1. 自定义字段映射

```python
# 在 QueryBuilder 中自定义字段映射
processor.query_builder.field_mapping.update({
    "revenue": "total_revenue",
    "profit": "net_profit",
    "custom_metric": "business_specific_field"
})
```

### 2. 自定义表映射

```python
# 配置数据表映射
processor.query_builder.table_mapping.update({
    "sales_analysis": "fact_sales",
    "customer_analysis": "dim_customer",
    "product_analysis": "fact_product_sales"
})
```

### 3. 添加新的关键词

```python
# 扩展时间关键词
processor.parser.time_keywords.update({
    "上半年": {"type": "custom", "start_month": 1, "end_month": 6},
    "下半年": {"type": "custom", "start_month": 7, "end_month": 12}
})
```

## 💡 最佳实践

### 1. 占位符编写规范

✅ **推荐写法**：
```
{{销售数据分析:查询最近3个月的销售额,按地区分组,包含同比增长率}}
```

❌ **避免写法**：
```
{{查询销售数据}}  # 太模糊
{{获取所有数据,所有字段,所有时间}}  # 太宽泛
```

### 2. 性能优化建议

- **时间范围**：指定合理的时间范围，避免全表扫描
- **分组维度**：选择基数适中的分组字段
- **指标选择**：明确需要的指标，避免不必要的计算

### 3. 数据质量监控

```python
# 定期检查数据质量
for placeholder in critical_queries:
    result = await processor.process_placeholder(placeholder)
    
    if result.data_quality.get('quality_score', 0) < 0.8:
        # 数据质量告警
        alert_data_quality_issue(placeholder, result.data_quality)
```

## 🎯 总结

通过这个占位符处理系统，您可以：

1. **简化查询构建**：用自然语言描述需求，自动生成查询
2. **确保数据准确**：自动验证和清理数据，保证质量
3. **提高效率**：一句话完成复杂的数据分析查询
4. **降低门槛**：业务人员也能轻松获取准确数据
5. **持续优化**：系统自动学习，查询越来越智能

**您的第一目标现在可以这样实现**：
```python
# 只需一行代码，从占位符到准确数据
result = await processor.process_placeholder(your_placeholder)
accurate_data = result.data  # 这就是您要的准确数据！
```

系统会自动处理所有复杂的解析、查询构建、执行和验证过程，确保您获得正确、准确、高质量的数据！