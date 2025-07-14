# 增强版数据源配置指南

## 概述
本指南介绍了AutoReportAI系统中增强版数据源配置功能的使用方法，包括复杂SQL配置、多表联查、宽表构建以及基于MCP的统计分析工具。

## 功能特性

### 1. 增强版数据源配置
- **多数据源类型支持**：SQL数据库、CSV文件、API接口、数据推送
- **复杂SQL配置**：支持多表联查、自定义视图、宽表构建
- **动态字段映射**：灵活的字段映射和转换配置
- **条件过滤**：支持复杂的WHERE条件配置

### 2. 基于MCP的统计分析工具
- **环比分析**：计算相邻时间段的数值变化
- **同比分析**：计算与去年同期相比的变化
- **汇总统计**：计数、求和、均值、标准差等基础统计
- **增长率计算**：时间序列的增长率分析
- **比例分析**：各部分占总体的比例计算
- **趋势分析**：线性趋势和R²计算
- **移动平均**：平滑数据波动
- **百分位数**：数据分布分析

## API端点

### 增强版数据源API
- `POST /api/v1/enhanced-data-sources` - 创建增强版数据源
- `GET /api/v1/enhanced-data-sources` - 获取数据源列表
- `GET /api/v1/enhanced-data-sources/{id}` - 获取指定数据源
- `PUT /api/v1/enhanced-data-sources/{id}` - 更新数据源
- `POST /api/v1/enhanced-data-sources/{id}/build-query` - 构建宽表查询
- `POST /api/v1/enhanced-data-sources/{id}/validate-sql` - 验证SQL查询

### MCP统计分析API
- `POST /api/v1/mcp-analytics/analyze` - 执行单种统计分析
- `POST /api/v1/mcp-analytics/analyze/batch` - 批量执行多种统计分析
- `GET /api/v1/mcp-analytics/operations` - 获取支持的统计分析操作
- `POST /api/v1/mcp-analytics/analyze/sample` - 获取示例分析数据

## 使用示例

### 1. 创建增强版数据源

```json
POST /api/v1/enhanced-data-sources
{
  "name": "销售数据宽表",
  "source_type": "sql",
  "sql_query_type": "multi_table",
  "connection_string": "postgresql://user:pass@localhost/sales_db",
  "base_query": "SELECT o.order_id, c.customer_name, p.product_name, o.quantity, o.price FROM orders o JOIN customers c ON o.customer_id = c.id JOIN products p ON o.product_id = p.id",
  "wide_table_name": "fact_sales_wide",
  "is_active": true
}
```

### 2. 执行环比分析

```json
POST /api/v1/mcp-analytics/analyze
{
  "data": {
    "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
    "sales": [100, 120, 110]
  },
  "operation": "period_comparison",
  "date_column": "date",
  "value_columns": ["sales"]
}
```

### 3. 执行同比分析

```json
POST /api/v1/mcp-analytics/analyze
{
  "data": {
    "date": ["2024-01-01", "2024-02-01", "2024-03-01"],
    "sales": [1000, 1200, 1100]
  },
  "operation": "year_over_year",
  "date_column": "date",
  "value_columns": ["sales"]
}
```

### 4. 批量统计分析

```json
POST /api/v1/mcp-analytics/analyze/batch
{
  "data": {
    "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
    "sales": [100, 120, 110],
    "category": ["A", "B", "A"]
  },
  "operations": ["summary_statistics", "proportion", "trend_analysis"],
  "date_column": "date",
  "value_columns": ["sales"],
  "group_columns": ["category"]
}
```

## 前端组件使用

### EnhancedDataSourceForm组件
```tsx
import { EnhancedDataSourceForm } from '@/components/EnhancedDataSourceForm'

function DataSourcePage() {
  const handleSubmit = (values) => {
    // 处理表单提交
    console.log(values)
  }

  return (
    <EnhancedDataSourceForm 
      onSubmit={handleSubmit}
      defaultValues={{
        name: '示例数据源',
        source_type: 'sql'
      }}
    />
  )
}
```

## 配置说明

### SQL配置参数
- **connection_string**: 数据库连接字符串
- **base_query**: 基础SQL查询
- **sql_query_type**: 查询类型（single_table/multi_table/custom_view）
- **join_config**: 联表配置（JSON格式）
- **column_mapping**: 字段映射配置（JSON格式）
- **where_conditions**: 条件配置（JSON格式）
- **wide_table_name**: 生成的宽表名称

### API配置参数
- **api_url**: API端点URL
- **api_method**: 请求方法（GET/POST/PUT/DELETE）
- **api_headers**: 请求头（JSON格式）
- **api_body**: 请求体（JSON格式）

### 推送配置参数
- **push_endpoint**: 推送接收端点
- **push_auth_config**: 认证配置（JSON格式）

## 统计分析参数

### 通用参数
- **data**: 分析数据（字典格式）
- **operation**: 分析操作类型
- **date_column**: 日期列名
- **value_columns**: 数值列名列表
- **group_columns**: 分组列名列表
- **parameters**: 分析参数

### 特定参数
- **period_type**: 周期类型（daily/weekly/monthly/yearly）
- **window**: 移动平均窗口大小
- **percentiles**: 百分位数列表

## 部署说明

1. 运行数据库迁移：
```bash
cd backend
alembic upgrade head
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 启动服务：
```bash
uvicorn app.main:app --reload
```

## 注意事项

1. SQL查询验证：系统会自动验证SQL查询的安全性，禁止危险操作
2. 数据格式：JSON数据需要符合标准格式
3. 性能优化：对于大数据集，建议使用分页或采样
4. 错误处理：所有API都有完善的错误处理和返回信息
