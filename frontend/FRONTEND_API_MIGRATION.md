# 前端API适配迁移指南

## 概览

本次更新将前端适配了新的后端API接口，包括：
- 新的APIResponse格式
- 前端数据适配器
- 实时WebSocket通知
- 用户友好的错误处理

## 主要更改

### 1. 新增文件

#### `/src/services/apiAdapter.ts`
- 统一的API适配器类
- 处理新的APIResponse格式
- 前端数据格式转换
- 用户友好的错误处理

#### `/src/services/websocketAdapter.ts`
- WebSocket流水线通知适配器
- 实时任务状态更新
- 任务进度监听
- 自动重连和订阅管理

#### `/src/app/test-new-api/page.tsx`
- API测试页面
- 验证所有新接口功能
- WebSocket连接测试
- 实时更新展示

### 2. 更新的组件

#### `/src/components/templates/ReactAgentTemplateAnalyzer.tsx`
- 使用新的APIAdapter
- 集成WebSocket实时进度更新
- 改进的错误处理和用户反馈

#### `/src/components/templates/ETLScriptManager.tsx`
- 使用新的图表测试API
- 支持FrontendChartData格式
- 统一的错误处理

#### `/src/components/ui/ChartPreview.tsx`
- 已兼容新的数据格式
- 支持metadata字段
- 改进的图表统计信息显示

## 新的数据格式

### APIResponse格式
```typescript
interface APIResponse<T = any> {
  success: boolean
  data: T
  message: string
  errors?: Array<{
    field?: string
    message: string
  }>
  warnings?: string[]
}
```

### 前端图表数据格式
```typescript
interface FrontendChartData {
  echartsConfig: any
  chartType: string
  chartData: any[]
  metadata?: {
    data_points?: number
    chart_elements?: any
    data_summary?: any
    generation_time?: string
    data_source?: {
      sql_query?: string
      execution_time_ms?: number
      row_count?: number
      data_quality_score?: number
    }
  }
  title?: string
}
```

### 占位符显示信息
```typescript
interface PlaceholderDisplayInfo {
  text: string
  kind: string
  display_name: string
  description?: string
  status: string
  confidence?: number
  needs_reanalysis: boolean
  badge_color: string
  icon?: string
  tooltip?: string
}
```

## WebSocket集成

### 实时任务更新
- 支持模板分析任务的实时进度更新
- 自动订阅任务状态变化
- 用户友好的进度显示

### 使用方法
```typescript
import { subscribeToTask } from '@/services/websocketAdapter'

// 订阅任务更新
await subscribeToTask(
  taskId,
  (update) => {
    // 处理任务更新
    console.log('任务进度:', update.progress)
  },
  (taskId, result) => {
    // 处理任务完成
    console.log('任务完成:', result)
  },
  (taskId, error) => {
    // 处理任务错误
    console.error('任务失败:', error)
  }
)
```

## 错误处理

### 统一的错误格式
```typescript
interface ErrorDisplayInfo {
  error_code: string
  error_message: string
  user_friendly_message: string
  error_type: string
  severity: string
  suggestions: string[]
  support_info?: {
    contact: string
    documentation: string
    status_page: string
  }
}
```

### 使用方法
```typescript
if (!result.success && result.error) {
  APIAdapter.handleError(result.error)
}
```

## 测试

### 运行API测试页面
1. 启动后端服务
2. 确保WebSocket服务正常运行
3. 访问 `/test-new-api` 页面
4. 选择测试类型并执行测试

### 测试覆盖
- ✅ 占位符API测试
- ✅ 模板分析API测试
- ✅ 图表生成API测试
- ✅ WebSocket连接测试
- ✅ 实时任务更新测试

## 向后兼容性

- 保持了与现有API的兼容性
- 逐步迁移，不影响现有功能
- 可以同时使用新旧API

## 部署注意事项

1. **环境变量**
   - 确保`NEXT_PUBLIC_API_URL`正确配置
   - WebSocket连接地址需要匹配后端配置

2. **依赖检查**
   - 所有现有依赖仍然有效
   - 新增的类型定义已包含在项目中

3. **测试验证**
   - 使用测试页面验证所有功能
   - 检查WebSocket连接状态
   - 确认实时更新正常工作

## 故障排除

### WebSocket连接问题
- 检查后端WebSocket服务是否启动
- 验证认证token是否有效
- 确认防火墙和代理设置

### API调用失败
- 检查后端API服务状态
- 验证请求参数格式
- 查看浏览器控制台错误信息

### 图表显示问题
- 确认ECharts库正确加载
- 检查图表配置数据格式
- 验证ChartPreview组件props

## 后续计划

- [ ] 完善错误重试机制
- [ ] 添加更多图表类型支持
- [ ] 实现离线缓存功能
- [ ] 优化WebSocket重连逻辑
- [ ] 添加性能监控和日志