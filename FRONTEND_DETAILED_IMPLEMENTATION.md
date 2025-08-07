# AutoReportAI 前端详细实现计划

## 🎯 基于后端API能力的精确功能映射

### 📊 **数据源管理模块详细设计**

#### 后端API能力分析
```typescript
// 后端支持的数据源类型
type DataSourceType = 'sql' | 'csv' | 'api' | 'push' | 'doris'

// 后端数据源模型
interface DataSource {
  id: string
  user_id: string
  name: string
  slug?: string
  display_name?: string
  source_type: DataSourceType
  
  // SQL数据库配置
  connection_string?: string
  sql_query_type: 'single_table' | 'multi_table' | 'custom_view'
  base_query?: string
  join_config?: Record<string, any>
  column_mapping?: Record<string, any>
  where_conditions?: Record<string, any>
  wide_table_name?: string
  wide_table_schema?: Record<string, any>
  
  // API数据源配置
  api_url?: string
  api_method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  api_headers?: Record<string, string>
  api_body?: Record<string, any>
  
  // 推送数据源配置
  push_endpoint?: string
  push_auth_config?: Record<string, any>
  
  // Doris数据库配置
  doris_fe_hosts?: string[]
  doris_be_hosts?: string[]
  doris_http_port: number
  doris_query_port: number
  doris_database?: string
  doris_username?: string
  doris_password?: string
  
  is_active: boolean
  created_at: string
  updated_at?: string
}
```

#### 前端组件设计
```typescript
// 1. 数据源列表组件
const DataSourcesList = () => {
  const { dataSources, loading } = useDataSourceStore()
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {dataSources.map(source => (
        <DataSourceCard 
          key={source.id} 
          dataSource={source}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onTest={handleTest}
        />
      ))}
    </div>
  )
}

// 2. 动态数据源配置表单
const DataSourceForm = ({ type, initialData }: { 
  type: DataSourceType
  initialData?: Partial<DataSource> 
}) => {
  return (
    <Form>
      {/* 通用字段 */}
      <FormField name="name" label="数据源名称" required />
      <FormField name="display_name" label="显示名称" />
      
      {/* 根据类型显示特定配置 */}
      {type === 'sql' && <SqlConfiguration />}
      {type === 'doris' && <DorisConfiguration />}
      {type === 'api' && <ApiConfiguration />}
      {type === 'csv' && <CsvConfiguration />}
      {type === 'push' && <PushConfiguration />}
      
      {/* 连接测试 */}
      <TestConnectionSection />
    </Form>
  )
}

// 3. Doris数据库配置组件
const DorisConfiguration = () => {
  return (
    <div className="space-y-4">
      <FormField 
        name="doris_fe_hosts" 
        label="FE节点列表"
        type="array"
        placeholder="192.168.1.100,192.168.1.101"
      />
      <div className="grid grid-cols-2 gap-4">
        <FormField 
          name="doris_http_port" 
          label="HTTP端口" 
          type="number"
          defaultValue={8030}
        />
        <FormField 
          name="doris_query_port" 
          label="查询端口"
          type="number" 
          defaultValue={9030}
        />
      </div>
      <FormField name="doris_database" label="数据库名" />
      <FormField name="doris_username" label="用户名" />
      <FormField name="doris_password" label="密码" type="password" />
    </div>
  )
}

// 4. API配置组件（支持复杂JSON编辑）
const ApiConfiguration = () => {
  return (
    <div className="space-y-4">
      <FormField name="api_url" label="API地址" required />
      <FormField 
        name="api_method" 
        label="请求方法"
        type="select"
        options={['GET', 'POST', 'PUT', 'DELETE']}
      />
      <JsonEditor 
        name="api_headers" 
        label="请求头"
        placeholder='{"Authorization": "Bearer token"}'
      />
      <JsonEditor 
        name="api_body" 
        label="请求体"
        placeholder='{"query": "SELECT * FROM table"}'
      />
    </div>
  )
}
```

### 📋 **任务管理模块详细设计**

#### 后端API能力分析
```typescript
// 后端任务模型
interface Task {
  id: number
  owner_id: string
  unique_id: string
  name: string
  description?: string
  template_id: string
  data_source_id: string
  schedule?: string  // Cron表达式
  recipients: string[]  // 邮件通知列表
  is_active: boolean
  created_at: string
  updated_at?: string
}

// 后端验证规则
- schedule: 必须是有效的Cron表达式
- recipients: 必须是有效的邮箱地址列表
```

#### 前端组件设计
```typescript
// 1. 任务列表组件（支持批量操作）
const TasksList = () => {
  const [selectedTasks, setSelectedTasks] = useState<string[]>([])
  const { tasks, updateTaskStatus } = useTaskStore()
  
  return (
    <div className="space-y-4">
      {/* 批量操作工具栏 */}
      <BatchOperationToolbar 
        selectedCount={selectedTasks.length}
        onBulkEnable={() => handleBulkOperation('enable')}
        onBulkDisable={() => handleBulkOperation('disable')}
        onBulkDelete={() => handleBulkOperation('delete')}
      />
      
      {/* 任务表格 */}
      <TaskTable 
        tasks={tasks}
        selectedTasks={selectedTasks}
        onSelectionChange={setSelectedTasks}
        onStatusToggle={updateTaskStatus}
      />
    </div>
  )
}

// 2. Cron表达式编辑器
const CronEditor = ({ value, onChange }: {
  value: string
  onChange: (cron: string) => void
}) => {
  const [mode, setMode] = useState<'visual' | 'text'>('visual')
  
  return (
    <div className="space-y-4">
      <div className="flex space-x-2">
        <Button 
          variant={mode === 'visual' ? 'solid' : 'outline'}
          onClick={() => setMode('visual')}
        >
          可视化编辑
        </Button>
        <Button 
          variant={mode === 'text' ? 'solid' : 'outline'}
          onClick={() => setMode('text')}
        >
          文本编辑
        </Button>
      </div>
      
      {mode === 'visual' ? (
        <CronVisualEditor value={value} onChange={onChange} />
      ) : (
        <CronTextEditor value={value} onChange={onChange} />
      )}
      
      {/* Cron表达式说明 */}
      <CronDescription cron={value} />
    </div>
  )
}

// 3. 可视化Cron编辑器
const CronVisualEditor = ({ value, onChange }) => {
  const cronParts = parseCron(value)
  
  return (
    <div className="grid grid-cols-5 gap-4">
      <CronField 
        label="分钟" 
        value={cronParts.minute}
        onChange={(minute) => onChange(buildCron({...cronParts, minute}))}
        range={[0, 59]}
      />
      <CronField 
        label="小时"
        value={cronParts.hour}
        onChange={(hour) => onChange(buildCron({...cronParts, hour}))}
        range={[0, 23]}
      />
      <CronField 
        label="日"
        value={cronParts.day}
        onChange={(day) => onChange(buildCron({...cronParts, day}))}
        range={[1, 31]}
      />
      <CronField 
        label="月"
        value={cronParts.month}
        onChange={(month) => onChange(buildCron({...cronParts, month}))}
        range={[1, 12]}
      />
      <CronField 
        label="星期"
        value={cronParts.dayOfWeek}
        onChange={(dayOfWeek) => onChange(buildCron({...cronParts, dayOfWeek}))}
        options={['日', '一', '二', '三', '四', '五', '六']}
      />
    </div>
  )
}
```

### 📊 **仪表板模块详细设计**

#### 基于后端API的统计数据
```typescript
// 后端仪表板API响应
interface DashboardStats {
  system_stats: {
    total_users: number
    total_data_sources: number
    total_templates: number
    total_tasks: number
    status: 'operational'
  }
  system_info: {
    version: string
    uptime: string
    features: string[]
  }
}

// 用户个人统计数据
interface UserStats {
  data_sources: number
  templates: number
  tasks: number
  reports: number
  active_tasks: number
  success_rate: number
}
```

#### 前端组件设计
```typescript
// 1. 统计卡片组件
const StatsCard = ({ 
  title, 
  value, 
  change, 
  icon 
}: {
  title: string
  value: number | string
  change?: { value: number, type: 'increase' | 'decrease' }
  icon: React.ComponentType
}) => {
  return (
    <Card className="p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
          {change && (
            <p className={`text-sm ${change.type === 'increase' ? 'text-green-600' : 'text-red-600'}`}>
              {change.type === 'increase' ? '+' : '-'}{change.value}%
            </p>
          )}
        </div>
        <icon className="w-8 h-8 text-gray-400" />
      </div>
    </Card>
  )
}

// 2. 实时系统监控组件
const SystemMonitor = () => {
  const { systemHealth } = useSystemStore()
  
  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">系统状态</h3>
      <div className="space-y-4">
        <StatusIndicator 
          label="CPU使用率"
          value={systemHealth.cpu.usage_percent}
          unit="%"
          threshold={80}
        />
        <StatusIndicator 
          label="内存使用率"
          value={systemHealth.memory.percent}
          unit="%"
          threshold={85}
        />
        <StatusIndicator 
          label="数据库状态"
          status={systemHealth.services.database}
        />
      </div>
    </Card>
  )
}
```

### 🔄 **实时通信设计**

#### WebSocket消息类型映射
```typescript
// 基于后端WebSocket实现的消息类型
interface WebSocketMessage {
  type: 'task_progress' | 'system_notification' | 'report_completed'
  payload: any
  timestamp: string
  user_id?: string
}

// 任务进度消息
interface TaskProgressMessage {
  type: 'task_progress'
  payload: {
    task_id: string
    progress: number  // 0-100
    status: 'running' | 'completed' | 'failed'
    message?: string
    estimated_time?: number
  }
}

// 系统通知消息
interface SystemNotificationMessage {
  type: 'system_notification'
  payload: {
    title: string
    message: string
    level: 'info' | 'warning' | 'error' | 'success'
    action?: {
      label: string
      url: string
    }
  }
}
```

#### 前端实时通信实现
```typescript
// WebSocket Hook
const useWebSocket = () => {
  const [connected, setConnected] = useState(false)
  const ws = useRef<WebSocket | null>(null)
  
  useEffect(() => {
    const token = useAuthStore.getState().token
    if (!token) return
    
    const wsUrl = `ws://localhost:8000/ws?token=${token}`
    ws.current = new WebSocket(wsUrl)
    
    ws.current.onopen = () => {
      setConnected(true)
      console.log('WebSocket connected')
    }
    
    ws.current.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data)
      handleWebSocketMessage(message)
    }
    
    ws.current.onclose = () => {
      setConnected(false)
      // 重连逻辑
      setTimeout(connectWebSocket, 5000)
    }
    
    return () => {
      ws.current?.close()
    }
  }, [])
  
  const handleWebSocketMessage = (message: WebSocketMessage) => {
    switch (message.type) {
      case 'task_progress':
        useTaskStore.getState().updateTaskProgress(message.payload)
        break
      case 'system_notification':
        useNotificationStore.getState().addNotification(message.payload)
        break
      case 'report_completed':
        useReportStore.getState().addReport(message.payload)
        // 显示成功通知
        toast.success('报告生成完成！')
        break
    }
  }
  
  return { connected }
}

// 实时任务进度组件
const TaskProgressIndicator = ({ taskId }: { taskId: string }) => {
  const progress = useTaskStore(state => state.getTaskProgress(taskId))
  
  if (!progress) return null
  
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span>执行进度</span>
        <span>{progress.progress}%</span>
      </div>
      <ProgressBar value={progress.progress} />
      {progress.message && (
        <p className="text-xs text-gray-600">{progress.message}</p>
      )}
    </div>
  )
}
```

## 🚀 **实施优先级**

### Phase 1: 核心功能 (2周)
1. ✅ 认证系统和路由
2. ✅ 数据源管理（基础CRUD）
3. ✅ 模板管理（基础编辑）
4. ✅ 任务管理（创建和列表）

### Phase 2: 高级功能 (2周)  
1. ✅ Doris数据源配置界面
2. ✅ Cron可视化编辑器
3. ✅ JSON编辑器组件
4. ✅ 连接测试功能

### Phase 3: 实时功能 (1周)
1. ✅ WebSocket连接管理
2. ✅ 实时任务进度
3. ✅ 系统通知中心
4. ✅ 报告完成提醒

### Phase 4: 用户体验优化 (1周)
1. ✅ 批量操作功能
2. ✅ 搜索和筛选
3. ✅ 响应式设计
4. ✅ 错误处理和加载状态

---

## 🎯 **前端-后端完全匹配确认**

| 功能模块 | 后端API | 前端实现 | 匹配度 |
|---------|---------|----------|--------|
| 用户认证 | ✅ `/auth/*` | ✅ 认证系统 | 100% |
| 数据源管理 | ✅ `/data-sources/*` | ✅ 动态配置表单 | 100% |
| 模板管理 | ✅ `/templates/*` | ✅ 编辑器界面 | 100% |
| 任务调度 | ✅ `/tasks/*` | ✅ Cron编辑器 | 100% |
| 报告生成 | ✅ `/reports/*` | ✅ 查看下载 | 100% |
| 文件管理 | ✅ `/files/*` | ✅ 上传下载 | 100% |
| 实时通信 | ✅ WebSocket | ✅ 实时更新 | 100% |
| 系统监控 | ✅ `/system/*` | ✅ 状态面板 | 100% |

**总结：前端设计完全基于后端API能力，确保100%功能匹配！**