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
  id: number
  name: string
  source_type: 'sql' | 'csv' | 'api'
  connection_string?: string
  db_query?: string
  file_path?: string
  api_url?: string
  api_method?: string
  api_headers?: Record<string, string>
  api_body?: Record<string, unknown>
}

export interface DataSourceCreate {
  name: string
  source_type: 'sql' | 'csv' | 'api'
  connection_string?: string
  db_query?: string
  file_path?: string
  api_url?: string
  api_method?: string
  api_headers?: Record<string, string>
  api_body?: Record<string, unknown>
}

export interface EnhancedDataSource {
  id: number
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
}

export interface Task {
  id: number
  name: string
  description?: string
  template_id: string // UUID
  data_source_id: number
  schedule?: string
  recipients?: string[]
  is_active: boolean
  owner_id: string
}

export interface TaskCreate {
  name: string
  description?: string
  template_id: string // UUID
  data_source_id: number
  schedule?: string
  recipients?: string[]
}

export interface ETLJob {
  id: string // UUID
  name: string
  description?: string
  enhanced_source_id: number
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
  enhanced_source_id: number
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
  data_source_id?: number
}

export interface Token {
  access_token: string
  token_type: string
}

export interface Msg {
  msg: string
}

// Generic API response types
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

export interface ErrorResponse {
  detail: string | string[] | Record<string, unknown>
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
  validation_result: Record<string, any>
  processing_errors: Array<Record<string, any>>
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
  placeholder_understanding: Record<string, any>
  field_suggestions: FieldSuggestion[]
  best_match?: FieldSuggestion
  confidence_score: number
  processing_metadata: Record<string, any>
}

export interface IntelligentReportRequest {
  template_id: string
  data_source_id: number
  processing_config?: Record<string, any>
  output_config?: Record<string, any>
  email_config?: Record<string, any>
}

export interface IntelligentReportResponse {
  success: boolean
  task_id: string
  report_id?: string
  processing_summary: Record<string, any>
  placeholder_results: Array<Record<string, any>>
  quality_assessment?: Record<string, any>
  file_path?: string
  email_status?: Record<string, any>
}