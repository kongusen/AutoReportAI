// 基础类型定义
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
  errors?: string[]
  timestamp?: string
  request_id?: string
  version?: string
}

// 分页响应类型
export interface PaginatedResponse<T = any> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
  has_next: boolean
  has_prev: boolean
}

// 用户相关类型
export interface User {
  id: string
  username: string
  email: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at?: string
}

export interface UserProfile {
  id: string
  user_id: string
  full_name?: string
  bio?: string
  avatar_url?: string
  created_at: string
  updated_at?: string
}

// 数据源类型
export type DataSourceType = 'sql' | 'csv' | 'api' | 'push' | 'doris'

export interface DataSource {
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
  doris_http_port?: number
  doris_query_port?: number
  doris_database?: string
  doris_username?: string
  doris_password?: string
  
  is_active: boolean
  created_at: string
  updated_at?: string
  
  // 新增与后端一致的字段
  unique_id?: string
  table_name?: string
}

export interface DataSourceCreate extends Omit<DataSource, 'id' | 'user_id' | 'created_at' | 'updated_at'> {}
export interface DataSourceUpdate extends Partial<DataSourceCreate> {}

// 模板占位符类型
export interface Placeholder {
  type: '统计' | '图表' | '文本' | string;
  description: string;
  placeholder_text: string;
  requirements?: Record<string, any>;
}

// 模板预览响应类型
export interface TemplatePreview {
  template_type: string;
  placeholders: Placeholder[];
  total_count: number;
  stats_count: number;
  chart_count: number;
}


// 模板类型
export interface Template {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  content: string;
  template_type: string;
  variables?: Record<string, any>;
  created_at: string;
  updated_at?: string;
  original_filename?: string;
  file_size?: number;
}

export interface TemplateCreate extends Omit<Template, 'id' | 'user_id' | 'created_at' | 'updated_at'> {
  file?: File;
}
export interface TemplateUpdate extends Partial<Omit<TemplateCreate, 'file'>> {}

// 任务类型
export interface Task {
  id: number
  owner_id: string
  unique_id: string
  name: string
  description?: string
  template_id: string
  data_source_id: string
  schedule?: string
  recipients?: string[]
  is_active: boolean
  created_at: string
  updated_at?: string
}

export interface TaskCreate extends Omit<Task, 'id' | 'owner_id' | 'unique_id' | 'created_at' | 'updated_at'> {}
export interface TaskUpdate extends Partial<TaskCreate> {}

// 任务进度类型
export interface TaskProgress {
  task_id: string
  progress: number
  status: 'pending' | 'analyzing' | 'querying' | 'processing' | 'generating' | 'completed' | 'failed' | 'retrying'
  message?: string
  current_step?: string
  estimated_time?: number
  updated_at?: string
}

// 报告类型
export interface Report {
  id: string
  task_id: string
  name: string
  file_path: string
  file_size: number
  status: 'generating' | 'completed' | 'failed'
  content?: string  // 报告内容 (HTML/markdown)
  created_at: string
}

// AI提供商类型
export interface AIProvider {
  id: number
  user_id: string
  provider_name: string
  provider_type: string
  api_base_url?: string
  default_model_name?: string
  is_active: boolean
  created_at: string
  updated_at?: string
}

// 系统信息类型
export interface SystemInfo {
  version: string
  uptime: string
  features: string[]
}

export interface SystemStats {
  total_users: number
  total_data_sources: number
  total_templates: number
  total_tasks: number
  status: 'operational'
}

export interface DashboardStats {
  system_stats: SystemStats
  system_info: SystemInfo
}

// WebSocket消息类型
export interface WebSocketMessage {
  type: 'task_progress' | 'system_notification' | 'report_completed' | 'pong'
  payload: any
  timestamp: string
  user_id?: string
}

export interface TaskProgressMessage extends WebSocketMessage {
  type: 'task_progress'
  payload: TaskProgress
}

export interface SystemNotificationMessage extends WebSocketMessage {
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

export interface ReportCompletedMessage extends WebSocketMessage {
  type: 'report_completed'
  payload: Report
}

// 表单类型
export interface LoginForm {
  username: string
  password: string
}

export interface RegisterForm {
  username: string
  email: string
  password: string
  confirmPassword: string
}

// UI状态类型
export interface UIState {
  sidebarOpen: boolean
  theme: 'light' | 'dark'
  loading: boolean
}

// 通知类型
export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  timestamp: string
  read: boolean
}