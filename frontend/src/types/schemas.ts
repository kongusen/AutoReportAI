/**
 * TypeScript types generated from backend Pydantic schemas
 * This file provides type-safe interfaces that match the backend API schemas
 * 
 * Generated from backend schemas - DO NOT EDIT MANUALLY
 * Last updated: 2025-01-15
 */

// Base types
export interface APIResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  errors?: Array<Record<string, any>>;
  meta?: Record<string, any>;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface APIListResponse<T> extends APIResponse<PaginatedResponse<T>> {}

export interface HealthCheckResponse {
  status: string;
  version: string;
  timestamp: string;
  services: Record<string, string>;
}

export interface ErrorDetail {
  code: string;
  message: string;
  field?: string;
  details?: Record<string, any>;
}

export interface ValidationErrorResponse {
  success: false;
  message: string;
  errors: ErrorDetail[];
  timestamp: string;
}

// User schemas
export interface UserBase {
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
}

export interface UserCreate extends UserBase {
  password: string;
}

export interface UserUpdate {
  username?: string;
  email?: string;
  full_name?: string;
  password?: string;
  is_active?: boolean;
  is_superuser?: boolean;
}

export interface User extends UserBase {
  id: string; // UUID
  created_at: string;
  updated_at?: string;
}

// Template schemas
export interface TemplateBase {
  name: string;
  description?: string;
  template_type: string;
  content?: string;
  original_filename?: string;
  file_size?: number;
  is_public: boolean;
  is_active: boolean;
}

export interface TemplateCreate extends TemplateBase {}

export interface TemplateUpdate {
  name?: string;
  description?: string;
  content?: string;
  template_type?: string;
  original_filename?: string;
  file_size?: number;
  is_public?: boolean;
  is_active?: boolean;
}

export interface Template extends TemplateBase {
  id: string; // UUID
  user_id: string; // UUID
  created_at: string;
  updated_at?: string;
}

export interface TemplateUpload {
  name: string;
  description?: string;
  is_public: boolean;
}

// Data Source schemas
export interface DataSourceBase {
  name: string;
  source_type: 'sql' | 'csv' | 'api';
  connection_string?: string;
  db_query?: string;
  file_path?: string;
  api_url?: string;
  api_method?: string;
  api_headers?: Record<string, any>;
  api_body?: Record<string, any>;
}

export interface DataSourceCreate extends DataSourceBase {}

export interface DataSourceUpdate {
  name?: string;
  source_type?: 'sql' | 'csv' | 'api';
  connection_string?: string;
  db_query?: string;
  file_path?: string;
  api_url?: string;
  api_method?: string;
  api_headers?: Record<string, any>;
  api_body?: Record<string, any>;
}

export interface DataSource extends DataSourceBase {
  id: number;
}

// AI Provider schemas
export type AIProviderType = 'openai' | 'azure_openai' | 'mock';

export interface AIProviderBase {
  provider_name: string;
  provider_type: AIProviderType;
  api_base_url?: string;
  default_model_name?: string;
  is_active?: boolean;
}

export interface AIProviderCreate extends AIProviderBase {
  api_key: string;
}

export interface AIProviderUpdate extends AIProviderBase {
  api_key?: string;
}

export interface AIProvider extends AIProviderBase {
  id: number;
  user_id: string; // UUID
}

export interface AIProviderInResponse extends AIProviderBase {
  id: number;
  // Note: api_key is excluded from response for security
}

// Task schemas
export interface TaskBase {
  name: string;
  description?: string;
  template_id: string; // UUID
  data_source_id: number;
  schedule?: string;
  recipients?: string[];
}

export interface TaskCreate extends TaskBase {}

export interface TaskUpdate {
  name?: string;
  description?: string;
  template_id?: string; // UUID
  data_source_id?: number;
  schedule?: string;
  recipients?: string[];
}

export interface Task extends TaskBase {
  id: number;
  owner_id: string; // UUID
}

export interface TaskRead extends TaskBase {
  id: number;
  owner_id: string; // UUID
  is_active: boolean;
}

// Report History schemas
export interface ReportHistoryBase {
  task_id: number;
  user_id: string; // UUID
  status: string;
  file_path?: string;
  error_message?: string;
}

export interface ReportHistoryCreate extends ReportHistoryBase {}

export interface ReportHistory extends ReportHistoryBase {
  id: number;
  generated_at: string;
}

// Placeholder Mapping schemas
export interface PlaceholderMappingBase {
  placeholder_signature: string;
  data_source_id: number;
  matched_field: string;
  confidence_score: number; // 0.0 to 1.0
  transformation_config?: Record<string, any>;
}

export interface PlaceholderMappingCreate extends PlaceholderMappingBase {
  usage_count: number;
}

export interface PlaceholderMappingUpdate {
  matched_field?: string;
  confidence_score?: number; // 0.0 to 1.0
  transformation_config?: Record<string, any>;
  usage_count?: number;
}

export interface PlaceholderMapping extends PlaceholderMappingBase {
  id: number;
  usage_count: number;
  last_used_at: string;
  created_at: string;
}

// Enhanced Data Source schemas
export type DataSourceType = 'sql' | 'csv' | 'api' | 'push';
export type SQLQueryType = 'single_table' | 'multi_table' | 'custom_view';

export interface EnhancedDataSourceBase {
  name: string;
  source_type: DataSourceType;
  connection_string?: string;
  sql_query_type: SQLQueryType;
  base_query?: string;
  join_config?: Record<string, any>;
  column_mapping?: Record<string, any>;
  where_conditions?: Record<string, any>;
  wide_table_name?: string;
  wide_table_schema?: Record<string, any>;
  api_url?: string;
  api_method?: string;
  api_headers?: Record<string, any>;
  api_body?: Record<string, any>;
  push_endpoint?: string;
  push_auth_config?: Record<string, any>;
  is_active: boolean;
  last_sync_time?: string;
}

export interface EnhancedDataSourceCreate extends EnhancedDataSourceBase {}

export interface EnhancedDataSourceUpdate {
  name?: string;
  source_type?: DataSourceType;
  connection_string?: string;
  sql_query_type?: SQLQueryType;
  base_query?: string;
  join_config?: Record<string, any>;
  column_mapping?: Record<string, any>;
  where_conditions?: Record<string, any>;
  wide_table_name?: string;
  wide_table_schema?: Record<string, any>;
  api_url?: string;
  api_method?: string;
  api_headers?: Record<string, any>;
  api_body?: Record<string, any>;
  push_endpoint?: string;
  push_auth_config?: Record<string, any>;
  is_active?: boolean;
  last_sync_time?: string;
}

export interface EnhancedDataSource extends EnhancedDataSourceBase {
  id: number;
  user_id: string; // UUID
}

// ETL Job schemas
export interface ETLJobBase {
  name: string;
  description?: string;
  enhanced_source_id: number;
  destination_table_name: string;
  source_query: string;
  transformation_config?: Record<string, any>;
  schedule?: string;
  enabled: boolean;
}

export interface ETLJobCreate extends ETLJobBase {}

export interface ETLJobUpdate {
  name?: string;
  description?: string;
  enhanced_source_id?: number;
  destination_table_name?: string;
  source_query?: string;
  transformation_config?: Record<string, any>;
  schedule?: string;
  enabled?: boolean;
}

export interface ETLJob extends ETLJobBase {
  id: string; // UUID
  user_id: string; // UUID
}

// Analytics Data schemas
export interface AnalyticsDataBase {
  record_id: string;
  data: Record<string, any>;
  data_source_id: number;
}

export interface AnalyticsDataCreate extends AnalyticsDataBase {}

export interface AnalyticsDataUpdate {
  record_id?: string;
  data?: Record<string, any>;
}

export interface AnalyticsData extends AnalyticsDataBase {
  id: number;
  created_at: string;
}

// User Profile schemas
export interface UserProfileBase {
  language: string;
  theme: string;
  email_notifications: boolean;
  report_notifications: boolean;
  system_notifications: boolean;
  default_storage_days: number; // 1-365
  auto_cleanup_enabled: boolean;
  default_report_format: string;
  default_ai_provider?: string;
  custom_css?: string;
  dashboard_layout?: string;
  timezone: string;
  date_format: string;
}

export interface UserProfileCreate extends UserProfileBase {}

export interface UserProfileUpdate extends UserProfileBase {}

export interface UserProfile extends UserProfileBase {
  id: number;
  user_id: string; // UUID
  created_at: string;
  updated_at?: string;
}

// Token schemas
export interface Token {
  access_token: string;
  token_type: string;
}

export interface TokenPayload {
  sub?: number;
}

export interface Msg {
  msg: string;
}

// Utility types for API operations
export type CreateRequest<T> = T extends { id: any; created_at: any; updated_at?: any }
  ? Omit<T, 'id' | 'created_at' | 'updated_at'>
  : T;

export type UpdateRequest<T> = Partial<CreateRequest<T>>;

// Type guards for runtime type checking
export function isAPIResponse<T>(obj: any): obj is APIResponse<T> {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    typeof obj.success === 'boolean' &&
    typeof obj.message === 'string' &&
    typeof obj.timestamp === 'string'
  );
}

export function isPaginatedResponse<T>(obj: any): obj is PaginatedResponse<T> {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    Array.isArray(obj.items) &&
    typeof obj.total === 'number' &&
    typeof obj.page === 'number' &&
    typeof obj.size === 'number' &&
    typeof obj.pages === 'number' &&
    typeof obj.has_next === 'boolean' &&
    typeof obj.has_prev === 'boolean'
  );
}

export function isValidationErrorResponse(obj: any): obj is ValidationErrorResponse {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    obj.success === false &&
    typeof obj.message === 'string' &&
    Array.isArray(obj.errors) &&
    typeof obj.timestamp === 'string'
  );
}

// Response type helpers
export type UserResponse = APIResponse<User>;
export type UserListResponse = APIListResponse<User>;
export type TemplateResponse = APIResponse<Template>;
export type TemplateListResponse = APIListResponse<Template>;
export type DataSourceResponse = APIResponse<DataSource>;
export type DataSourceListResponse = APIListResponse<DataSource>;
export type EnhancedDataSourceResponse = APIResponse<EnhancedDataSource>;
export type EnhancedDataSourceListResponse = APIListResponse<EnhancedDataSource>;
export type AIProviderResponse = APIResponse<AIProvider>;
export type AIProviderListResponse = APIListResponse<AIProvider>;
export type TaskResponse = APIResponse<Task>;
export type TaskListResponse = APIListResponse<Task>;
export type ReportHistoryResponse = APIResponse<ReportHistory>;
export type ReportHistoryListResponse = APIListResponse<ReportHistory>;
export type PlaceholderMappingResponse = APIResponse<PlaceholderMapping>;
export type PlaceholderMappingListResponse = APIListResponse<PlaceholderMapping>;
export type ETLJobResponse = APIResponse<ETLJob>;
export type ETLJobListResponse = APIListResponse<ETLJob>;
export type AnalyticsDataResponse = APIResponse<AnalyticsData>;
export type AnalyticsDataListResponse = APIListResponse<AnalyticsData>;
export type UserProfileResponse = APIResponse<UserProfile>;
export type UserProfileListResponse = APIListResponse<UserProfile>;