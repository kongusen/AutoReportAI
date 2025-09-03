/**
 * AutoReportAI 前端 TypeScript 类型定义
 * 基于后端API接口文档自动生成
 * 版本: v2.0.0
 */

// ============================================================================
// 基础类型和通用接口
// ============================================================================

/**
 * 统一API响应格式
 */
export interface APIResponse<T = any> {
  success: boolean
  data?: T
  message: string
  error?: string
  errors?: Array<{
    field?: string
    message: string
    code?: string
  }>
  meta?: PaginationMeta
  timestamp: string
  request_id?: string
  version?: string
}

/**
 * 分页元数据
 */
export interface PaginationMeta {
  total: number
  page: number
  size: number
  pages: number
  has_next: boolean
  has_prev: boolean
}

/**
 * 分页响应格式
 */
export interface PaginatedResponse<T = any> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
  has_next: boolean
  has_prev: boolean
}

/**
 * 查询参数
 */
export interface QueryParams {
  page?: number
  size?: number
  search?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  [key: string]: any
}

// ============================================================================
// 用户认证和管理
// ============================================================================

/**
 * 用户信息
 */
export interface User {
  id: string
  username: string
  email: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at?: string
  full_name?: string
  bio?: string
  avatar_url?: string
}

/**
 * 用户配置
 */
export interface UserProfile {
  id: string
  user_id: string
  full_name?: string
  bio?: string
  avatar_url?: string
  created_at: string
  updated_at?: string
}

/**
 * 登录请求
 */
export interface LoginRequest {
  username: string
  password: string
}

/**
 * 登录响应
 */
export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

/**
 * 注册请求
 */
export interface RegisterRequest {
  username: string
  email: string
  password: string
  full_name?: string
}

/**
 * 密码重置请求
 */
export interface ResetPasswordRequest {
  email: string
}

/**
 * 修改密码请求
 */
export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

/**
 * 刷新令牌请求
 */
export interface RefreshTokenRequest {
  refresh_token: string
}

// ============================================================================
// 数据源管理
// ============================================================================

/**
 * 数据源类型
 */
export type DataSourceType = 'mysql' | 'postgresql' | 'doris' | 'csv' | 'api'

/**
 * 数据源信息
 */
export interface DataSource {
  id: string
  name: string
  source_type: DataSourceType
  host?: string
  port?: number
  database?: string
  username?: string
  password?: string // 只在创建时使用，获取时为空
  is_active: boolean
  description?: string
  created_at: string
  updated_at?: string
  user_id: string
  
  // 特定于数据源类型的字段
  doris_fe_hosts?: string[]
  doris_query_port?: number
  csv_file_path?: string
  api_base_url?: string
  api_headers?: Record<string, string>
}

/**
 * 创建数据源请求
 */
export interface CreateDataSourceRequest {
  name: string
  source_type: DataSourceType
  host?: string
  port?: number
  database?: string
  username?: string
  password?: string
  is_active?: boolean
  description?: string
  doris_fe_hosts?: string[]
  doris_query_port?: number
  csv_file_path?: string
  api_base_url?: string
  api_headers?: Record<string, string>
}

/**
 * 更新数据源请求
 */
export interface UpdateDataSourceRequest extends Partial<CreateDataSourceRequest> {}

/**
 * 数据源连接测试结果
 */
export interface DataSourceTestResult {
  success: boolean
  message: string
  connection_time?: number
  error?: string
}

/**
 * 数据源结构信息
 */
export interface DataSourceSchema {
  tables: TableSchema[]
  total_tables: number
}

/**
 * 表结构信息
 */
export interface TableSchema {
  table_name: string
  columns: ColumnSchema[]
  row_count?: number
  table_comment?: string
}

/**
 * 列结构信息
 */
export interface ColumnSchema {
  column_name: string
  data_type: string
  is_nullable: boolean
  column_default?: string
  column_comment?: string
}

// ============================================================================
// 模板系统
// ============================================================================

/**
 * 模板信息
 */
export interface Template {
  id: string
  name: string
  description?: string
  content: string
  template_type: 'report' | 'dashboard' | 'chart'
  is_active: boolean
  created_at: string
  updated_at?: string
  user_id: string
  tags?: string[]
  version: number
  parent_id?: string // 用于复制关系
}

/**
 * 创建模板请求
 */
export interface CreateTemplateRequest {
  name: string
  description?: string
  content: string
  template_type: 'report' | 'dashboard' | 'chart'
  is_active?: boolean
  tags?: string[]
}

/**
 * 更新模板请求
 */
export interface UpdateTemplateRequest extends Partial<CreateTemplateRequest> {}

/**
 * 模板预览结果
 */
export interface TemplatePreview {
  html_content: string
  placeholders: string[]
  estimated_generation_time: number
}

/**
 * 占位符类型
 */
export type PlaceholderType = 'text' | 'number' | 'chart' | 'table' | 'image' | 'date'

/**
 * 占位符信息
 */
export interface Placeholder {
  id: string
  template_id: string
  name: string
  placeholder_type: PlaceholderType
  content?: string
  sql_query?: string
  data_source_id?: string
  chart_config?: ChartConfig
  is_active: boolean
  created_at: string
  updated_at?: string
  order_index: number
}

/**
 * 图表配置
 */
export interface ChartConfig {
  chart_type: 'bar' | 'line' | 'pie' | 'scatter' | 'area' | 'table'
  x_axis?: string
  y_axis?: string[]
  title?: string
  width?: number
  height?: number
  colors?: string[]
  options?: Record<string, any>
}

/**
 * 创建占位符请求
 */
export interface CreatePlaceholderRequest {
  template_id: string
  name: string
  placeholder_type: PlaceholderType
  content?: string
  sql_query?: string
  data_source_id?: string
  chart_config?: ChartConfig
  is_active?: boolean
  order_index?: number
}

/**
 * 占位符分析结果
 */
export interface PlaceholderAnalysis {
  placeholder_id: string
  analysis_result: {
    sql_validity: boolean
    data_preview?: any[]
    column_info?: ColumnSchema[]
    estimated_rows: number
    suggestions?: string[]
    errors?: string[]
  }
  analyzed_at: string
}

// ============================================================================
// 报告生成
// ============================================================================

/**
 * 报告状态
 */
export type ReportStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'

/**
 * 报告格式
 */
export type ReportFormat = 'pdf' | 'docx' | 'html' | 'xlsx' | 'png' | 'jpg'

/**
 * 报告信息
 */
export interface Report {
  id: string
  name: string
  template_id: string
  template_name?: string
  status: ReportStatus
  format: ReportFormat
  file_path?: string
  file_size?: number
  parameters?: Record<string, any>
  error_message?: string
  generated_at?: string
  created_at: string
  user_id: string
  download_count: number
}

/**
 * 生成报告请求
 */
export interface GenerateReportRequest {
  template_id: string
  name: string
  format: ReportFormat
  parameters?: Record<string, any>
  scheduled_at?: string // 定时生成
}

/**
 * 报告历史记录
 */
export interface ReportHistory {
  id: string
  report_id: string
  report_name: string
  template_name: string
  status: ReportStatus
  format: ReportFormat
  file_size?: number
  generated_at?: string
  user_name: string
}

// ============================================================================
// 任务管理
// ============================================================================

/**
 * 任务状态
 */
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused'

/**
 * 任务类型
 */
export type TaskType = 'report_generation' | 'data_sync' | 'backup' | 'cleanup' | 'custom'

/**
 * 任务信息
 */
export interface Task {
  id: string
  name: string
  task_type: TaskType
  description?: string
  status: TaskStatus
  cron_expression?: string
  parameters?: Record<string, any>
  next_run_time?: string
  last_run_time?: string
  last_run_status?: TaskStatus
  error_message?: string
  created_at: string
  updated_at?: string
  user_id: string
  is_active: boolean
}

/**
 * 创建任务请求
 */
export interface CreateTaskRequest {
  name: string
  task_type: TaskType
  description?: string
  cron_expression?: string
  parameters?: Record<string, any>
  is_active?: boolean
}

/**
 * 任务执行结果
 */
export interface TaskExecutionResult {
  task_id: string
  execution_id: string
  status: TaskStatus
  started_at: string
  completed_at?: string
  result?: any
  error_message?: string
}

/**
 * 任务进度信息
 */
export interface TaskProgress {
  task_id: string
  progress: number
  status: TaskStatus
  message?: string
  current_step?: string
  updated_at: string
}

// ============================================================================
// 系统监控
// ============================================================================

/**
 * 系统健康状态
 */
export interface HealthStatus {
  status: 'healthy' | 'unhealthy' | 'degraded'
  version: string
  uptime: number
  services: {
    database: 'healthy' | 'unhealthy'
    redis: 'healthy' | 'unhealthy'
    ai_service: 'healthy' | 'unhealthy'
    file_storage: 'healthy' | 'unhealthy'
  }
  checks: {
    [key: string]: {
      status: 'pass' | 'fail' | 'warn'
      time: string
      output?: string
    }
  }
}

/**
 * 系统信息
 */
export interface SystemInfo {
  version: string
  environment: string
  python_version: string
  database_version: string
  total_users: number
  total_reports: number
  total_templates: number
  disk_usage: {
    total: number
    used: number
    free: number
  }
  memory_usage: {
    total: number
    used: number
    free: number
  }
}

/**
 * 仪表板统计数据
 */
export interface DashboardStats {
  total_users: number
  total_reports: number
  total_templates: number
  total_data_sources: number
  recent_reports: number
  recent_tasks: number
  system_load: number
  memory_usage: number
  disk_usage: number
}

/**
 * 系统活动记录
 */
export interface ActivityRecord {
  id: string
  user_name: string
  action: string
  resource_type: string
  resource_id?: string
  description: string
  ip_address?: string
  user_agent?: string
  created_at: string
}

// ============================================================================
// LLM 集成
// ============================================================================

/**
 * LLM 提供商类型
 */
export type LLMProvider = 'openai' | 'anthropic' | 'google' | 'azure' | 'local'

/**
 * 模型类型
 */
export type ModelType = 'default' | 'think'

/**
 * LLM 服务器信息
 */
export interface LLMServer {
  id: string
  name: string
  provider: LLMProvider
  base_url: string
  api_key?: string // 只在创建时使用
  is_active: boolean
  description?: string
  max_requests_per_minute?: number
  health_status: 'healthy' | 'degraded' | 'unhealthy'
  last_health_check?: string
  models_count?: number
  success_rate?: number
  avg_response_time?: number
  created_at: string
  updated_at?: string
}

/**
 * LLM 模型信息
 */
export interface LLMModel {
  id: string
  server_id: string
  name: string
  model_type: ModelType
  max_tokens?: number
  cost_per_token?: number
  is_active: boolean
  capabilities: string[]
  created_at: string
}

export interface LLMModelCreate {
  server_id: string
  name: string
  display_name?: string
  description?: string
  model_type: ModelType
  provider_name?: string
  priority?: number
  max_tokens?: number
  temperature_default?: number
  cost_per_token?: number
  is_active?: boolean
  capabilities?: string[]
  supports_system_messages?: boolean
  supports_function_calls?: boolean
  supports_thinking?: boolean
}

/**
 * 用户 LLM 偏好设置
 */
export interface UserLLMPreferences {
  id: string
  user_id: string
  preferred_chat_model?: string
  preferred_embedding_model?: string
  max_tokens: number
  temperature: number
  custom_api_keys: Record<string, string>
  budget_limit?: number
  created_at: string
  updated_at?: string
}

/**
 * LLM 使用配额
 */
export interface LLMUsageQuota {
  user_id: string
  period: 'daily' | 'weekly' | 'monthly'
  current_usage: {
    requests: number
    tokens: number
    cost: number
  }
  limits: {
    max_requests?: number
    max_tokens?: number
    max_cost?: number
  }
  remaining: {
    requests: number
    tokens: number
    cost: number
  }
  reset_at: string
}

/**
 * 模型推荐结果
 */
export interface ModelRecommendation {
  model_id: string
  model_name: string
  confidence: number
  reasoning: string
  estimated_cost?: number
  estimated_time?: number
}

// ============================================================================
// 文件处理
// ============================================================================

/**
 * 文件信息
 */
export interface FileInfo {
  path: string
  size: number
  content_type: string
  created_at: string
  updated_at?: string
  checksum?: string
  url?: string
}

/**
 * 文件上传请求
 */
export interface FileUploadRequest {
  file: File
  path?: string
  overwrite?: boolean
}

/**
 * 文件上传响应
 */
export interface FileUploadResponse {
  path: string
  size: number
  content_type: string
  url: string
  checksum: string
}

/**
 * 文件列表响应
 */
export interface FileListResponse {
  files: FileInfo[]
  total_count: number
  total_size: number
}

/**
 * 存储状态
 */
export interface StorageStatus {
  backend_type: 'local' | 'minio' | 's3'
  total_space: number
  used_space: number
  free_space: number
  file_count: number
  is_healthy: boolean
}

// ============================================================================
// WebSocket 消息
// ============================================================================

/**
 * WebSocket 消息类型
 */
export enum WebSocketMessageType {
  PING = 'ping',
  PONG = 'pong',
  AUTH = 'auth',
  ERROR = 'error',
  NOTIFICATION = 'notification',
  TASK_UPDATE = 'task_update',
  REPORT_UPDATE = 'report_update',
  SYSTEM_ALERT = 'system_alert',
  SUBSCRIBE = 'subscribe',
  UNSUBSCRIBE = 'unsubscribe'
}

/**
 * WebSocket 基础消息
 */
export interface WebSocketMessage {
  id?: string
  type: WebSocketMessageType
  message?: string
  data?: any
  timestamp?: string
  priority?: number
  expires_at?: string
}

/**
 * 通知消息
 */
export interface NotificationMessage extends WebSocketMessage {
  type: WebSocketMessageType.NOTIFICATION
  title: string
  message: string
  notification_type: 'info' | 'success' | 'warning' | 'error'
  category?: string
  action_url?: string
  user_id?: string
}

/**
 * 任务更新消息
 */
export interface TaskUpdateMessage extends WebSocketMessage {
  type: WebSocketMessageType.TASK_UPDATE
  task_id: string
  status: TaskStatus
  progress: number
  current_step?: string
  result?: any
}

/**
 * 报告更新消息
 */
export interface ReportUpdateMessage extends WebSocketMessage {
  type: WebSocketMessageType.REPORT_UPDATE
  report_id: string
  status: ReportStatus
  progress?: number
  file_url?: string
}

/**
 * WebSocket 连接信息
 */
export interface WebSocketConnectionInfo {
  session_id: string
  connected_at: string
  last_ping: string
  subscriptions: string[]
  messages_sent: number
  messages_received: number
  is_alive: boolean
}

// ============================================================================
// 其他业务类型
// ============================================================================

/**
 * ETL 作业信息
 */
export interface ETLJob {
  id: string
  name: string
  description?: string
  source_config: Record<string, any>
  target_config: Record<string, any>
  transformation_script?: string
  schedule?: string
  is_active: boolean
  last_run_time?: string
  last_run_status?: 'success' | 'failed' | 'running'
  created_at: string
  updated_at?: string
  user_id: string
}

/**
 * 图表测试请求
 */
export interface ChartTestRequest {
  chart_type: string
  data_source_id: string
  sql_query: string
  chart_config: ChartConfig
}

/**
 * 图表测试响应
 */
export interface ChartTestResponse {
  success: boolean
  chart_data: any
  chart_config: ChartConfig
  execution_time: number
  data_rows: number
  warnings?: string[]
}

// ============================================================================
// API 客户端类型
// ============================================================================

/**
 * API 客户端配置
 */
export interface APIClientConfig {
  baseURL: string
  timeout?: number
  retryCount?: number
  authToken?: string
}

/**
 * 请求选项
 */
export interface RequestOptions extends RequestInit {
  params?: Record<string, any>
  timeout?: number
  retryCount?: number
}

// ============================================================================
// 表单和验证类型
// ============================================================================

/**
 * 表单验证错误
 */
export interface FormValidationError {
  field: string
  message: string
  code: string
}

/**
 * 表单状态
 */
export type FormStatus = 'idle' | 'submitting' | 'success' | 'error'

/**
 * 搜索过滤器
 */
export interface SearchFilters {
  search?: string
  status?: string
  type?: string
  date_from?: string
  date_to?: string
  user_id?: string
  [key: string]: any
}

// ============================================================================
// API 服务接口
// ============================================================================

/**
 * 认证服务接口
 */
export interface AuthService {
  login(credentials: LoginRequest): Promise<LoginResponse>
  register(userData: RegisterRequest): Promise<User>
  logout(): Promise<void>
  refreshToken(refreshToken: string): Promise<LoginResponse>
  getCurrentUser(): Promise<User>
  changePassword(request: ChangePasswordRequest): Promise<void>
  resetPassword(request: ResetPasswordRequest): Promise<void>
}

/**
 * 数据源服务接口
 */
export interface DataSourceService {
  list(params?: QueryParams): Promise<PaginatedResponse<DataSource>>
  get(id: string): Promise<DataSource>
  create(dataSource: CreateDataSourceRequest): Promise<DataSource>
  update(id: string, dataSource: UpdateDataSourceRequest): Promise<DataSource>
  delete(id: string): Promise<void>
  test(id: string): Promise<DataSourceTestResult>
  getSchema(id: string): Promise<DataSourceSchema>
}

/**
 * 模板服务接口
 */
export interface TemplateService {
  list(params?: QueryParams): Promise<PaginatedResponse<Template>>
  get(id: string): Promise<Template>
  create(template: CreateTemplateRequest): Promise<Template>
  update(id: string, template: UpdateTemplateRequest): Promise<Template>
  delete(id: string): Promise<void>
  duplicate(id: string): Promise<Template>
  preview(id: string): Promise<TemplatePreview>
}

/**
 * 报告服务接口
 */
export interface ReportService {
  list(params?: QueryParams): Promise<PaginatedResponse<Report>>
  get(id: string): Promise<Report>
  generate(request: GenerateReportRequest): Promise<Report>
  download(id: string): Promise<Blob>
  delete(id: string): Promise<void>
  regenerate(id: string): Promise<Report>
}

/**
 * 任务服务接口
 */
export interface TaskService {
  list(params?: QueryParams): Promise<PaginatedResponse<Task>>
  get(id: string): Promise<Task>
  create(task: CreateTaskRequest): Promise<Task>
  update(id: string, task: Partial<CreateTaskRequest>): Promise<Task>
  delete(id: string): Promise<void>
  execute(id: string): Promise<TaskExecutionResult>
  pause(id: string): Promise<void>
  resume(id: string): Promise<void>
  getProgress(id: string): Promise<TaskProgress>
}

// ============================================================================
// 导出所有类型
// ============================================================================

// 重新导出所有类型，保持向后兼容
export type {
  // 向后兼容的别名
  APIResponse as ApiResponse,
  Template as TemplateType,
  Report as ReportType,
  Task as TaskType,
  WebSocketMessage as WSMessage
}