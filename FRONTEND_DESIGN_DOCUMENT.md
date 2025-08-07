# AutoReportAI 前端设计文档

## 🎯 项目概述

基于 AutoReportAI 后端API构建的现代化、极简风格的多用户报告生成平台前端应用。

### 技术栈
- **框架**: Next.js 14 + React 18 + TypeScript
- **样式**: Tailwind CSS + Headless UI
- **HTTP客户端**: Axios
- **实时通信**: WebSocket
- **状态管理**: Zustand (轻量级)
- **表单处理**: React Hook Form + Zod
- **图标**: Lucide React
- **构建工具**: Turbopack

## 🎨 设计系统

### 配色方案（极简黑白灰）
```css
/* 主色调 */
--color-black: #000000
--color-white: #ffffff
--color-gray-50: #fafafa
--color-gray-100: #f5f5f5
--color-gray-200: #e5e5e5
--color-gray-300: #d4d4d4
--color-gray-400: #a3a3a3
--color-gray-500: #737373
--color-gray-600: #525252
--color-gray-700: #404040
--color-gray-800: #262626
--color-gray-900: #171717

/* 功能色彩 */
--color-success: #22c55e
--color-warning: #f59e0b
--color-error: #ef4444
--color-info: #3b82f6
```

### 字体系统
```css
/* 字体族 */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif

/* 字体大小 */
--text-xs: 0.75rem     /* 12px */
--text-sm: 0.875rem    /* 14px */
--text-base: 1rem      /* 16px */
--text-lg: 1.125rem    /* 18px */
--text-xl: 1.25rem     /* 20px */
--text-2xl: 1.5rem     /* 24px */
--text-3xl: 1.875rem   /* 30px */
--text-4xl: 2.25rem    /* 36px */
```

### 间距系统
```css
--space-1: 0.25rem    /* 4px */
--space-2: 0.5rem     /* 8px */
--space-3: 0.75rem    /* 12px */
--space-4: 1rem       /* 16px */
--space-5: 1.25rem    /* 20px */
--space-6: 1.5rem     /* 24px */
--space-8: 2rem       /* 32px */
--space-10: 2.5rem    /* 40px */
--space-12: 3rem      /* 48px */
--space-16: 4rem      /* 64px */
```

## 📱 页面架构设计

### 1. 认证页面
```
/auth
├── /login          # 登录页面
├── /register       # 注册页面
└── /forgot-password # 忘记密码
```

### 2. 主应用页面
```
/dashboard          # 仪表板首页
/data-sources       # 数据源管理
├── /              # 数据源列表
├── /create        # 创建数据源
└── /[id]/edit     # 编辑数据源

/templates          # 模板管理
├── /              # 模板列表
├── /create        # 创建模板
└── /[id]/edit     # 编辑模板

/tasks             # 任务管理
├── /              # 任务列表
├── /create        # 创建任务
├── /[id]          # 任务详情
└── /[id]/edit     # 编辑任务

/reports           # 报告中心
├── /              # 报告列表
└── /[id]          # 报告详情

/ai-providers      # AI提供商配置
/settings          # 系统设置
/profile           # 个人资料
```

## 🧩 组件架构

### 布局组件
```typescript
// Layout 层级结构
AppLayout
├── Header           # 顶部导航栏
├── Sidebar          # 侧边栏导航
├── MainContent      # 主内容区域
│   ├── PageHeader   # 页面标题区域
│   └── PageContent  # 页面内容
└── Footer           # 底部信息
```

### 通用组件库
```typescript
// UI 组件
Button              # 按钮组件
Input               # 输入框
Select              # 选择器
Modal               # 模态框
Drawer              # 抽屉
Table               # 数据表格
Card                # 卡片
Badge               # 标签
Avatar              # 头像
Loading             # 加载指示器
Toast               # 消息提示
Breadcrumb          # 面包屑导航
Pagination          # 分页器
Empty               # 空状态
ErrorBoundary       # 错误边界

// 业务组件
DataSourceCard      # 数据源卡片
TemplateEditor      # 模板编辑器
TaskProgress        # 任务进度
ReportViewer        # 报告查看器
SystemMonitor       # 系统监控
NotificationCenter  # 通知中心
```

### 页面组件结构
```typescript
// 页面组件示例：数据源管理
DataSourcesPage
├── DataSourcesHeader    # 页面头部（标题+操作按钮）
├── DataSourcesFilter    # 筛选器
├── DataSourcesGrid      # 数据源网格
│   └── DataSourceCard   # 单个数据源卡片
└── CreateDataSourceModal # 创建数据源弹窗
```

## 🔄 状态管理设计

### Store 结构（使用 Zustand）
```typescript
// stores/index.ts
export interface AppState {
  // 用户状态
  auth: AuthState
  user: UserState
  
  // 业务数据状态  
  dataSources: DataSourceState
  templates: TemplateState
  tasks: TaskState
  reports: ReportState
  
  // UI 状态
  ui: UIState
  notifications: NotificationState
}

// 认证状态
interface AuthState {
  isAuthenticated: boolean
  token: string | null
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
}

// 用户状态
interface UserState {
  currentUser: User | null
  profile: UserProfile | null
  updateProfile: (data: UserProfileUpdate) => Promise<void>
}

// 数据源状态
interface DataSourceState {
  dataSources: DataSource[]
  currentDataSource: DataSource | null
  loading: boolean
  fetchDataSources: () => Promise<void>
  createDataSource: (data: DataSourceCreate) => Promise<void>
  updateDataSource: (id: string, data: DataSourceUpdate) => Promise<void>
  deleteDataSource: (id: string) => Promise<void>
  testConnection: (id: string) => Promise<boolean>
}
```

## 🌐 API 集成设计

### HTTP 客户端配置
```typescript
// lib/api.ts
import axios from 'axios'

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 添加认证token
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器 - 统一错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      router.push('/auth/login')
    }
    return Promise.reject(error)
  }
)
```

### API 服务封装
```typescript
// services/dataSourceService.ts
export class DataSourceService {
  static async getAll(): Promise<DataSource[]> {
    const response = await apiClient.get('/data-sources')
    return response.data.data
  }

  static async create(data: DataSourceCreate): Promise<DataSource> {
    const response = await apiClient.post('/data-sources', data)
    return response.data.data
  }

  static async update(id: string, data: DataSourceUpdate): Promise<DataSource> {
    const response = await apiClient.put(`/data-sources/${id}`, data)
    return response.data.data
  }

  static async delete(id: string): Promise<void> {
    await apiClient.delete(`/data-sources/${id}`)
  }

  static async testConnection(id: string): Promise<boolean> {
    const response = await apiClient.post(`/data-sources/${id}/test`)
    return response.data.success
  }
}
```

### WebSocket 连接管理
```typescript
// lib/websocket.ts
export class WebSocketManager {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5

  constructor(url: string) {
    this.url = url
  }

  connect(): void {
    try {
      this.ws = new WebSocket(this.url)
      
      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
      }

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        this.handleMessage(data)
      }

      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
        this.reconnect()
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
    }
  }

  private handleMessage(data: any): void {
    // 根据消息类型分发到相应的store
    switch (data.type) {
      case 'task_progress':
        useTaskStore.getState().updateTaskProgress(data.payload)
        break
      case 'system_notification':
        useNotificationStore.getState().addNotification(data.payload)
        break
      case 'report_completed':
        useReportStore.getState().addReport(data.payload)
        break
    }
  }
}
```

## 📄 页面设计详情

### 1. 登录页面
```
布局：居中单列布局
组件：
- Logo + 标题
- 登录表单（邮箱/用户名 + 密码）
- 登录按钮
- "忘记密码" 链接
- "注册账号" 链接
```

### 2. 仪表板页面
```
布局：网格布局（4列）
组件：
- 统计卡片组（4个）
  - 数据源数量
  - 模板数量  
  - 活跃任务
  - 本月报告
- 最近活动列表
- 系统状态监控
- 快速操作按钮组
```

### 3. 数据源管理页面
```
布局：卡片网格布局
组件：
- 页面头部（标题 + "添加数据源"按钮）
- 搜索和筛选栏
- 数据源卡片网格
  - 数据源名称
  - 类型标签
  - 连接状态指示器
  - 操作按钮（编辑/删除/测试连接）
```

### 4. 模板编辑器页面
```
布局：分屏布局（左右分栏）
组件：
- 工具栏（保存/预览/设置按钮）
- 左侧：模板编辑器（代码编辑器）
- 右侧：
  - 占位符面板
  - 实时预览
  - 变量说明
```

### 5. 任务管理页面
```
布局：列表布局 + 详情面板
组件：
- 任务列表（表格形式）
  - 任务名称
  - 状态标签
  - 进度条
  - 创建时间
  - 操作按钮
- 任务详情侧边栏
  - 任务信息
  - 执行日志
  - 生成的报告列表
```

## 🎭 用户交互设计

### 状态反馈
```typescript
// 加载状态
<Button loading={isSubmitting} disabled={isSubmitting}>
  {isSubmitting ? '处理中...' : '提交'}
</Button>

// 操作结果提示
const handleSubmit = async () => {
  try {
    await submitAction()
    toast.success('操作成功')
  } catch (error) {
    toast.error('操作失败：' + error.message)
  }
}

// 确认对话框
const handleDelete = async () => {
  const confirmed = await confirm('确定要删除这个数据源吗？')
  if (confirmed) {
    await deleteDataSource(id)
  }
}
```

### 响应式设计
```css
/* 断点系统 */
/* Mobile: < 768px */
/* Tablet: 768px - 1024px */  
/* Desktop: > 1024px */

/* 响应式网格 */
.data-source-grid {
  @apply grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6;
}

/* 响应式侧边栏 */
.sidebar {
  @apply w-64 lg:block hidden;
}

.mobile-sidebar {
  @apply lg:hidden fixed inset-0 z-50;
}
```

## 📁 项目结构
```
frontend/
├── src/
│   ├── app/                 # Next.js App Router
│   │   ├── (auth)/         # 认证页面组
│   │   ├── dashboard/      # 仪表板页面
│   │   ├── data-sources/   # 数据源页面
│   │   ├── templates/      # 模板页面
│   │   ├── tasks/         # 任务页面
│   │   ├── reports/       # 报告页面
│   │   └── layout.tsx     # 根布局
│   ├── components/        # 组件目录
│   │   ├── ui/           # 基础UI组件
│   │   ├── layout/       # 布局组件
│   │   └── features/     # 业务组件
│   ├── lib/              # 工具库
│   │   ├── api.ts        # API客户端
│   │   ├── websocket.ts  # WebSocket管理
│   │   ├── utils.ts      # 工具函数
│   │   └── validations.ts # 表单验证
│   ├── stores/           # 状态管理
│   ├── services/         # API服务
│   ├── types/            # TypeScript类型
│   ├── hooks/            # 自定义hooks
│   └── styles/           # 样式文件
├── public/               # 静态资源
└── tailwind.config.js    # Tailwind配置
```

## 🚀 开发计划

### Phase 1: 基础架构 (1-2周)
- [x] 项目初始化和配置
- [x] 设计系统和组件库
- [x] 认证系统
- [x] 路由和布局

### Phase 2: 核心功能 (2-3周)
- [x] 数据源管理
- [x] 模板管理  
- [x] 任务管理
- [x] API集成

### Phase 3: 高级功能 (2周)
- [x] 报告生成和查看
- [x] 实时通知
- [x] 系统监控
- [x] 文件管理

### Phase 4: 优化和发布 (1周)
- [x] 性能优化
- [x] 测试和调试
- [x] 部署配置
- [x] 文档完善

---

## 🔗 后端API映射

### 已确认支持的后端功能
- ✅ 用户认证与授权 (`/auth`, `/users`)
- ✅ 数据源管理 (`/data-sources`)
- ✅ 模板管理 (`/templates`)
- ✅ AI提供商配置 (`/ai-providers`)
- ✅ 任务调度与管理 (`/tasks`)
- ✅ 报告生成与查看 (`/reports`)
- ✅ 智能占位符处理 (`/intelligent-placeholders`)
- ✅ 文件上传下载 (`/files`)
- ✅ 系统监控 (`/system`, `/dashboard`)
- ✅ 历史记录 (`/history`)
- ✅ 邮件通知系统
- ✅ WebSocket实时通信

---

*此设计文档基于AutoReportAI后端API能力制定，确保前端功能与后端完全匹配*