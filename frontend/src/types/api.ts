// API Types - 确保与后端 Pydantic schemas 一致

export interface User {
  id: string
  username: string
  email: string
  full_name?: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at?: string
}

export interface UserCreate {
  username: string
  email: string
  full_name?: string
  password: string
  is_active?: boolean
  is_superuser?: boolean
}

export interface UserProfile {
  id: number
  user_id: string
  language: string
  theme: string
  email_notifications: boolean
  report_notifications: boolean
  system_notifications: boolean
  default_storage_days: number
  auto_cleanup_enabled: boolean
  default_report_format: string
  default_ai_provider?: string
  custom_css?: string
  dashboard_layout?: string
  timezone: string
  date_format: string
  created_at: string
  updated_at?: string
}

export interface Template {
  id: string // UUID
  name: string
  description?: string
  template_type: string
  content?: string
  original_filename?: string
  file_size?: number
  is_public: boolean
  is_active: boolean
  user_id: string
  created_at: string
  updated_at?: string
}

export interface TemplateCreate {
  name: string
  description?: string
  template_type?: string
  content?: string
  original_filename?: string
  file_size?: number
  is_public?: boolean
  is_active?: boolean
}

export interface DataSource {
  id: string // UUID
  name: string
  source_type: 'sql' | 'csv' | 'api' | 'push'
  connection_string?: string
  sql_query_type: 'single_table' | 'multi_table' | 'custom_view'
  base_query?: string
  join_config?: Record<string, unknown>
  column_mapping?: Record<string, unknown>
  where_conditions?: Record<string, unknown>
  wide_table_name?: string
  wide_table_schema?: Record<string, unknown>
  api_url?: string
  api_method?: string
  api_headers?: Record<string, string>
  api_body?: Record<string, unknown>
  push_endpoint?: string
  push_auth_config?: Record<string, unknown>
  is_active: boolean
  last_sync_time?: string
  created_at: string
  updated_at?: string
}

export interface DataSourceCreate {
  name: string
  source_type: 'sql' | 'csv' | 'api' | 'push'
  connection_string?: string
  sql_query_type?: 'single_table' | 'multi_table' | 'custom_view'
  base_query?: string
  join_config?: Record<string, unknown>
  column_mapping?: Record<string, unknown>
  where_conditions?: Record<string, unknown>
  wide_table_name?: string
  api_url?: string
  api_method?: string
  api_headers?: Record<string, string>
  api_body?: Record<string, unknown>
  push_endpoint?: string
  push_auth_config?: Record<string, unknown>
  is_active?: boolean
}

export interface Task {
  id: number
  name: string
  description?: string
  template_id: string // UUID
  data_source_id: string // UUID
  schedule?: string
  recipients?: string[]
  is_active: boolean
  owner_id: string
}

export interface TaskCreate {
  name: string
  description?: string
  template_id: string // UUID
  data_source_id: string // UUID
  schedule?: string
  recipients?: string[]
}

export interface ETLJob {
  id: string // UUID
  name: string
  description?: string
  data_source_id: string // UUID
  destination_table_name: string
  source_query: string
  transformation_config?: Record<string, unknown>
  schedule?: string
  enabled: boolean
  created_at: string
  updated_at?: string
}

export interface ETLJobCreate {
  name: string
  description?: string
  data_source_id: string // UUID
  destination_table_name: string
  source_query: string
  transformation_config?: Record<string, unknown>
  schedule?: string
  enabled?: boolean
}

export interface AIProvider {
  id: number
  provider_name: string
  provider_type: 'openai' | 'azure_openai' | 'mock'
  api_base_url?: string
  default_model_name?: string
  is_active: boolean
}

export interface AIProviderCreate {
  provider_name: string
  provider_type: 'openai' | 'azure_openai' | 'mock'
  api_base_url?: string
  api_key: string
  default_model_name?: string
  is_active?: boolean
}

export interface ReportHistory {
  id: number
  task_id: number
  status: string
  file_path?: string
  error_message?: string
  generated_at: string
}

export interface PlaceholderMapping {
  id: number
  template_id: string // UUID
  placeholder_name: string
  placeholder_description?: string
  placeholder_type: 'text' | 'image' | 'table' | 'chart'
  data_source_id?: string // UUID
}

export interface Token {
  access_token: string
  token_type: string
}

export interface Msg {
  msg: string
}

// Generic API response types
export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

// 统一分页响应类型
export interface PaginatedResponse<T = unknown> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages?: number;
  hasNext?: boolean;
  hasPrev?: boolean;
}

export interface ErrorResponse {
  detail: string
  status_code: number
}

// 将所有 any 替换为 unknown 或更具体类型，空接口用 type 或移除
export interface DataSourceConfig {
  [key: string]: string | number | boolean | Record<string, unknown>
}

export interface TemplateConfig {
  [key: string]: string | number | boolean | Record<string, unknown>
}

export interface AIProviderConfig {
  [key: string]: string | number | boolean | Record<string, unknown>
}

export interface ExportConfig {
  [key: string]: string | number | boolean | Record<string, unknown>
}

export interface ValidationResult {
  [key: string]: string | number | boolean | Record<string, unknown>
}

export interface ProcessingResult {
  [key: string]: string | number | boolean | Record<string, unknown>
}

export interface AnalysisResult {
  [key: string]: string | number | boolean | Record<string, unknown>
}

export interface GenerationResult {
  [key: string]: string | number | boolean | Record<string, unknown>
}

export interface NotificationConfig {
  [key: string]: string | number | boolean | Record<string, unknown>
}

export interface SystemConfig {
  [key: string]: string | number | boolean | Record<string, unknown>
}

// API Response types for specific endpoints
export interface AnalysisResponse {
  placeholder: string
  task_type: string
  description: string
  ai_generated_params: Record<string, unknown>
  result: Record<string, unknown>
}

export interface DataResponse {
  data: Record<string, unknown>
  error?: string
}

// Intelligent Placeholder Types
export interface PlaceholderInfo {
  placeholder_text: string
  placeholder_type: string
  description: string
  position: number
  context_before: string
  context_after: string
  confidence: number
}

export interface PlaceholderAnalysisResponse {
  success: boolean
  placeholders: PlaceholderInfo[]
  total_count: number
  type_distribution: Record<string, number>
  validation_result: Record<string, unknown>
  processing_errors: Array<Record<string, unknown>>
  estimated_processing_time: number
}

export interface FieldSuggestion {
  field_name: string
  match_score: number
  match_reason: string
  data_transformation?: string
  validation_rules: string[]
}

export interface FieldMatchingResponse {
  success: boolean
  placeholder_understanding: Record<string, unknown>
  field_suggestions: FieldSuggestion[]
  best_match?: FieldSuggestion
  confidence_score: number
  processing_metadata: Record<string, unknown>
}

export interface IntelligentReportRequest {
  template_id: string
  data_source_id: string // UUID
  processing_config?: Record<string, unknown>
  output_config?: Record<string, unknown>
  email_config?: Record<string, unknown>
}

export interface IntelligentReportResponse {
  success: boolean
  task_id: string
  report_id?: string
  processing_summary: Record<string, unknown>
  placeholder_results: Array<Record<string, unknown>>
  quality_assessment?: Record<string, unknown>
  file_path?: string
  email_status?: Record<string, unknown>
}
