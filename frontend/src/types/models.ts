/**
 * Frontend Data Models
 * 
 * This file contains TypeScript interfaces for frontend data models.
 * These models use camelCase naming convention and are transformed from
 * the backend snake_case models defined in schemas.ts.
 */

// Base types
export interface ApiResponse<T = any> {
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
  hasNext: boolean;
  hasPrev: boolean;
}

export interface ApiListResponse<T> extends ApiResponse<PaginatedResponse<T>> {}

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

// User models
export interface UserBase {
  username: string;
  email: string;
  fullName?: string;
  isActive: boolean;
  isSuperuser: boolean;
}

export interface UserCreate extends UserBase {
  password: string;
}

export interface UserUpdate {
  username?: string;
  email?: string;
  fullName?: string;
  password?: string;
  isActive?: boolean;
  isSuperuser?: boolean;
}

export interface User extends UserBase {
  id: string; // UUID
  createdAt: Date;
  updatedAt?: Date;
}

// Template models
export interface TemplateBase {
  name: string;
  description?: string;
  templateType: string;
  content?: string;
  originalFilename?: string;
  fileSize?: number;
  isPublic: boolean;
  isActive: boolean;
}

export interface TemplateCreate extends TemplateBase {}

export interface TemplateUpdate {
  name?: string;
  description?: string;
  content?: string;
  templateType?: string;
  originalFilename?: string;
  fileSize?: number;
  isPublic?: boolean;
  isActive?: boolean;
}

export interface Template extends TemplateBase {
  id: string; // UUID
  userId: string; // UUID
  createdAt: Date;
  updatedAt?: Date;
}

export interface TemplateUpload {
  name: string;
  description?: string;
  isPublic: boolean;
}

// Data Source models
export interface DataSourceBase {
  name: string;
  sourceType: 'sql' | 'csv' | 'api';
  connectionString?: string;
  dbQuery?: string;
  filePath?: string;
  apiUrl?: string;
  apiMethod?: string;
  apiHeaders?: Record<string, any>;
  apiBody?: Record<string, any>;
}

export interface DataSourceCreate extends DataSourceBase {}

export interface DataSourceUpdate {
  name?: string;
  sourceType?: 'sql' | 'csv' | 'api';
  connectionString?: string;
  dbQuery?: string;
  filePath?: string;
  apiUrl?: string;
  apiMethod?: string;
  apiHeaders?: Record<string, any>;
  apiBody?: Record<string, any>;
}

export interface DataSource extends DataSourceBase {
  id: number;
}

// AI Provider models
export type AiProviderType = 'openai' | 'azure_openai' | 'mock';

export interface AiProviderBase {
  providerName: string;
  providerType: AiProviderType;
  apiBaseUrl?: string;
  defaultModelName?: string;
  isActive?: boolean;
}

export interface AiProviderCreate extends AiProviderBase {
  apiKey: string;
}

export interface AiProviderUpdate extends AiProviderBase {
  apiKey?: string;
}

export interface AiProvider extends AiProviderBase {
  id: number;
  userId: string; // UUID
}

export interface AiProviderInResponse extends AiProviderBase {
  id: number;
  // Note: apiKey is excluded from response for security
}

// Task models
export interface TaskBase {
  name: string;
  description?: string;
  templateId: string; // UUID
  dataSourceId: number;
  schedule?: string;
  recipients?: string[];
}

export interface TaskCreate extends TaskBase {}

export interface TaskUpdate {
  name?: string;
  description?: string;
  templateId?: string; // UUID
  dataSourceId?: number;
  schedule?: string;
  recipients?: string[];
}

export interface Task extends TaskBase {
  id: number;
  ownerId: string; // UUID
}

export interface TaskRead extends TaskBase {
  id: number;
  ownerId: string; // UUID
  isActive: boolean;
}

// Report History models
export interface ReportHistoryBase {
  taskId: number;
  userId: string; // UUID
  status: string;
  filePath?: string;
  errorMessage?: string;
}

export interface ReportHistoryCreate extends ReportHistoryBase {}

export interface ReportHistory extends ReportHistoryBase {
  id: number;
  generatedAt: Date;
}

// Placeholder Mapping models
export interface PlaceholderMappingBase {
  placeholderSignature: string;
  dataSourceId: number;
  matchedField: string;
  confidenceScore: number; // 0.0 to 1.0
  transformationConfig?: Record<string, any>;
}

export interface PlaceholderMappingCreate extends PlaceholderMappingBase {
  usageCount: number;
}

export interface PlaceholderMappingUpdate {
  matchedField?: string;
  confidenceScore?: number; // 0.0 to 1.0
  transformationConfig?: Record<string, any>;
  usageCount?: number;
}

export interface PlaceholderMapping extends PlaceholderMappingBase {
  id: number;
  usageCount: number;
  lastUsedAt: Date;
  createdAt: Date;
}

// Enhanced Data Source models
export type DataSourceType = 'sql' | 'csv' | 'api' | 'push';
export type SqlQueryType = 'single_table' | 'multi_table' | 'custom_view';

export interface EnhancedDataSourceBase {
  name: string;
  sourceType: DataSourceType;
  connectionString?: string;
  sqlQueryType: SqlQueryType;
  baseQuery?: string;
  joinConfig?: Record<string, any>;
  columnMapping?: Record<string, any>;
  whereConditions?: Record<string, any>;
  wideTableName?: string;
  wideTableSchema?: Record<string, any>;
  apiUrl?: string;
  apiMethod?: string;
  apiHeaders?: Record<string, any>;
  apiBody?: Record<string, any>;
  pushEndpoint?: string;
  pushAuthConfig?: Record<string, any>;
  isActive: boolean;
  lastSyncTime?: Date;
}

export interface EnhancedDataSourceCreate extends EnhancedDataSourceBase {}

export interface EnhancedDataSourceUpdate {
  name?: string;
  sourceType?: DataSourceType;
  connectionString?: string;
  sqlQueryType?: SqlQueryType;
  baseQuery?: string;
  joinConfig?: Record<string, any>;
  columnMapping?: Record<string, any>;
  whereConditions?: Record<string, any>;
  wideTableName?: string;
  wideTableSchema?: Record<string, any>;
  apiUrl?: string;
  apiMethod?: string;
  apiHeaders?: Record<string, any>;
  apiBody?: Record<string, any>;
  pushEndpoint?: string;
  pushAuthConfig?: Record<string, any>;
  isActive?: boolean;
  lastSyncTime?: Date;
}

export interface EnhancedDataSource extends EnhancedDataSourceBase {
  id: number;
  userId: string; // UUID
}

// ETL Job models
export interface EtlJobBase {
  name: string;
  description?: string;
  enhancedSourceId: number;
  destinationTableName: string;
  sourceQuery: string;
  transformationConfig?: Record<string, any>;
  schedule?: string;
  enabled: boolean;
}

export interface EtlJobCreate extends EtlJobBase {}

export interface EtlJobUpdate {
  name?: string;
  description?: string;
  enhancedSourceId?: number;
  destinationTableName?: string;
  sourceQuery?: string;
  transformationConfig?: Record<string, any>;
  schedule?: string;
  enabled?: boolean;
}

export interface EtlJob extends EtlJobBase {
  id: string; // UUID
  userId: string; // UUID
}

// Analytics Data models
export interface AnalyticsDataBase {
  recordId: string;
  data: Record<string, any>;
  dataSourceId: number;
}

export interface AnalyticsDataCreate extends AnalyticsDataBase {}

export interface AnalyticsDataUpdate {
  recordId?: string;
  data?: Record<string, any>;
}

export interface AnalyticsData extends AnalyticsDataBase {
  id: number;
  createdAt: Date;
}

// User Profile models
export interface UserProfileBase {
  language: string;
  theme: string;
  emailNotifications: boolean;
  reportNotifications: boolean;
  systemNotifications: boolean;
  defaultStorageDays: number; // 1-365
  autoCleanupEnabled: boolean;
  defaultReportFormat: string;
  defaultAiProvider?: string;
  customCss?: string;
  dashboardLayout?: string;
  timezone: string;
  dateFormat: string;
}

export interface UserProfileCreate extends UserProfileBase {}

export interface UserProfileUpdate extends UserProfileBase {}

export interface UserProfile extends UserProfileBase {
  id: number;
  userId: string; // UUID
  createdAt: Date;
  updatedAt?: Date;
}

// Token models
export interface Token {
  accessToken: string;
  tokenType: string;
}

export interface TokenPayload {
  sub?: number;
}

export interface Msg {
  msg: string;
}

// Response type helpers
export type UserResponse = ApiResponse<User>;
export type UserListResponse = ApiListResponse<User>;
export type TemplateResponse = ApiResponse<Template>;
export type TemplateListResponse = ApiListResponse<Template>;
export type DataSourceResponse = ApiResponse<DataSource>;
export type DataSourceListResponse = ApiListResponse<DataSource>;
export type EnhancedDataSourceResponse = ApiResponse<EnhancedDataSource>;
export type EnhancedDataSourceListResponse = ApiListResponse<EnhancedDataSource>;
export type AiProviderResponse = ApiResponse<AiProvider>;
export type AiProviderListResponse = ApiListResponse<AiProvider>;
export type TaskResponse = ApiResponse<Task>;
export type TaskListResponse = ApiListResponse<Task>;
export type ReportHistoryResponse = ApiResponse<ReportHistory>;
export type ReportHistoryListResponse = ApiListResponse<ReportHistory>;
export type PlaceholderMappingResponse = ApiResponse<PlaceholderMapping>;
export type PlaceholderMappingListResponse = ApiListResponse<PlaceholderMapping>;
export type EtlJobResponse = ApiResponse<EtlJob>;
export type EtlJobListResponse = ApiListResponse<EtlJob>;
export type AnalyticsDataResponse = ApiResponse<AnalyticsData>;
export type AnalyticsDataListResponse = ApiListResponse<AnalyticsData>;
export type UserProfileResponse = ApiResponse<UserProfile>;
export type UserProfileListResponse = ApiListResponse<UserProfile>;