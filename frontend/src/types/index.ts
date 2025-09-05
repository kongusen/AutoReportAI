// 基础类型定义
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message: string | null
  error?: string | null
  errors?: Array<{
    field?: string
    message: string
    code?: string
  }> | null
  meta?: Record<string, any> | null
  timestamp: string
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

// 数据源类型 - 与api.ts和后端保持一致
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

// 数据源连接测试结果
export interface ConnectionTestResult {
  connection_status: 'success' | 'failed'
  response_time: number
  data_source_name: string
  message?: string
  error?: string
  details?: Record<string, any>
}

// 表结构信息
export interface TableSchema {
  table_name: string
  columns: TableColumn[]
  total_columns: number
  estimated_rows?: number
  table_size?: number
  last_analyzed?: string
}

export interface TableColumn {
  name: string
  type: string
  nullable: boolean
  key: string
  default: string | null
  extra: string
}

// 数据源表列表响应
export interface DataSourceTablesResponse {
  tables: string[]
  databases: string[]
  total_tables: number
  total_databases: number
  response_time: number
  data_source_name: string
}

// 数据源字段列表响应
export interface DataSourceFieldsResponse {
  fields: string[]
  table_name?: string
  total_fields: number
  response_time: number
  data_source_name: string
}

// 查询执行结果
export interface QueryExecutionResult {
  rows: Record<string, any>[]
  columns: string[]
  row_count: number
  response_time: number
  execution_time?: number
  data_source_name: string
}

// 查询请求
export interface QueryRequest {
  sql: string
  parameters?: Record<string, any>
}

// 模板占位符类型 - 扩展支持新解析器的所有类型
export interface Placeholder {
  type: '统计' | '图表' | '表格' | '分析' | '日期时间' | '标题' | '摘要' | '作者' | '变量' | '中文' | '文本' | '错误' | '系统错误' | string;
  description: string;
  placeholder_text: string;
  requirements?: {
    content_type?: string;
    original_type?: string;
    required?: boolean;
    error?: string;
    template_type?: string;
    fallback_mode?: boolean;
  };
}

// 扩展的占位符配置类型 - 基于后端持久化能力
export interface PlaceholderConfig {
  id: string
  template_id: string
  placeholder_name: string
  placeholder_text: string
  placeholder_type: string
  content_type: string
  description?: string  // 占位符描述
  
  // Agent分析结果
  agent_analyzed: boolean
  target_database?: string
  target_table?: string
  required_fields?: Record<string, any>
  generated_sql?: string
  sql_validated: boolean
  confidence_score: number
  
  // ETL配置
  execution_order: number
  cache_ttl_hours: number
  agent_config?: Record<string, any>
  agent_workflow_id?: string
  
  // 状态
  is_active: boolean
  analyzed_at?: string
  created_at: string
  updated_at?: string
  
  // 解析元数据
  content_hash?: string
  original_type?: string
  extracted_description?: string
  parsing_metadata?: Record<string, any>
}

// 占位符值缓存类型
export interface PlaceholderValue {
  id: string
  placeholder_id: string
  data_source_id: string
  raw_query_result: any
  processed_value: any
  formatted_text: string
  execution_sql: string
  execution_time_ms: number
  row_count: number
  success: boolean
  error_message?: string
  cache_key: string
  expires_at: string
  hit_count: number
  last_hit_at?: string
  created_at: string
  
  // 图表相关字段
  chart_ready?: boolean
  chart_type?: string
  chart_config?: any
  echarts_config?: any
  data?: any[]
  
  // 执行相关字段
  sql_executed?: string
  
  // 占位符类型信息
  is_chart_placeholder?: boolean
  placeholder_type_info?: {
    is_chart_placeholder: boolean
    content_type: string
    placeholder_type: string
    message?: string
    expected_mode?: string
  }
  
  // 数据库和表信息
  target_database?: string
  target_table?: string
  actual_result_value?: string
  
  // 测试摘要
  test_summary?: string
  full_result?: any
}

// 占位符分析统计类型
export interface PlaceholderAnalytics {
  total_placeholders: number
  analyzed_placeholders: number
  sql_validated_placeholders: number
  average_confidence_score: number
  cache_hit_rate: number
  analysis_coverage: number
  execution_stats: {
    total_executions: number
    successful_executions: number
    failed_executions: number
    average_execution_time_ms: number
  }
}

// 模板预览响应类型
export interface TemplatePreview {
  template_type: string;
  placeholders: Placeholder[];
  total_count: number;
  stats_count: number;
  chart_count: number;
  // 新增统计字段
  table_count?: number;
  analysis_count?: number;
  datetime_count?: number;
  title_count?: number;
  variable_count?: number;
  // 按内容类型统计
  content_type_stats?: Record<string, number>;
  // 错误信息
  has_errors?: boolean;
  error_count?: number;
}


// 模板类型 - 与api.ts保持一致
export interface Template {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  content?: string;
  template_type: string;
  is_active?: boolean;
  is_public?: boolean;
  created_at: string;
  updated_at?: string;
  original_filename?: string;
  file_path?: string;  // MinIO/storage file path for original uploaded files
  file_size?: number;
  unique_id?: string;
  variables?: Record<string, any>;
}

export interface TemplateCreate extends Omit<Template, 'id' | 'user_id' | 'created_at' | 'updated_at'> {
  file?: File;
}
export interface TemplateUpdate extends Partial<Omit<TemplateCreate, 'file'>> {}

// Agent编排相关枚举
export type TaskStatus = 'pending' | 'processing' | 'agent_orchestrating' | 'generating' | 'completed' | 'failed' | 'cancelled'
export type ProcessingMode = 'simple' | 'intelligent' | 'hybrid'
export type AgentWorkflowType = 'simple_report' | 'statistical_analysis' | 'chart_generation' | 'comprehensive_analysis' | 'custom_workflow'

// 报告周期类型
export type ReportPeriod = 'daily' | 'weekly' | 'monthly' | 'yearly'

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
  report_period?: ReportPeriod  // 新增：报告周期字段
  recipients?: string[]
  is_active: boolean
  created_at: string
  updated_at?: string
  
  // 新增：Agent编排相关字段
  status?: TaskStatus
  processing_mode?: ProcessingMode
  workflow_type?: AgentWorkflowType
  
  // 新增：执行统计字段
  execution_count?: number
  success_count?: number
  failure_count?: number
  success_rate?: number
  last_execution_at?: string
  average_execution_time?: number
  
  // 新增：配置字段
  max_context_tokens?: number
  enable_compression?: boolean
}

export interface TaskCreate extends Omit<Task, 'id' | 'owner_id' | 'unique_id' | 'created_at' | 'updated_at'> {}
export interface TaskUpdate extends Partial<TaskCreate> {}

// 任务进度类型
export interface TaskProgress {
  task_id: string
  progress: number
  status: TaskStatus | 'queued' | 'analyzing' | 'querying' | 'retrying'
  message?: string
  current_step?: string
  estimated_time?: number
  updated_at?: string
  
  // Agent编排相关进度信息
  workflow_step?: string
  agent_execution_times?: Record<string, number>
  placeholder_results?: Array<{
    placeholder_name: string
    success: boolean
    content?: string
    error?: string
  }>
  has_errors?: boolean
  error_details?: string
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