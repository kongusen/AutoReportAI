/**
 * AutoReportAI API服务类
 * 基于统一接口文档的完整API服务封装
 */

import { apiClient } from '@/lib/api-client'
import type {
  APIResponse,
  PaginatedResponse,
  QueryParams,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  User,
  DataSource,
  CreateDataSourceRequest,
  UpdateDataSourceRequest,
  DataSourceTestResult,
  DataSourceSchema,
  Template,
  CreateTemplateRequest,
  UpdateTemplateRequest,
  TemplatePreview,
  Report,
  GenerateReportRequest,
  Task,
  CreateTaskRequest,
  TaskProgress,
  HealthStatus,
  DashboardStats,
  LLMServer,
  UserLLMPreferences,
  ETLJob
} from '@/types/api'

// ============================================================================
// 认证服务
// ============================================================================

class AuthService {
  /**
   * 用户登录
   */
  static async login(credentials: LoginRequest): Promise<LoginResponse> {
    return apiClient.login(credentials)
  }

  /**
   * 用户注册
   */
  static async register(userData: RegisterRequest): Promise<User> {
    return apiClient.register(userData)
  }

  /**
   * 用户登出
   */
  static async logout(): Promise<void> {
    return apiClient.logout()
  }

  /**
   * 获取当前用户信息
   */
  static async getCurrentUser(): Promise<User> {
    return apiClient.getCurrentUser()
  }

  /**
   * 刷新访问令牌
   */
  static async refreshToken(): Promise<LoginResponse> {
    return apiClient.refreshToken()
  }

  /**
   * 修改密码
   */
  static async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    return apiClient.request('POST', '/auth/change-password', {
      data: { current_password: currentPassword, new_password: newPassword }
    })
  }

  /**
   * 重置密码
   */
  static async resetPassword(email: string): Promise<void> {
    return apiClient.request('POST', '/auth/reset-password', {
      data: { email },
      skipAuth: true
    })
  }
}

// ============================================================================
// 数据源服务
// ============================================================================

class DataSourceService {
  /**
   * 获取数据源列表
   */
  static async list(params?: QueryParams): Promise<PaginatedResponse<DataSource>> {
    return apiClient.getDataSources(params)
  }

  /**
   * 获取单个数据源
   */
  static async get(id: string): Promise<DataSource> {
    return apiClient.getDataSource(id)
  }

  /**
   * 创建数据源
   */
  static async create(dataSource: CreateDataSourceRequest): Promise<DataSource> {
    return apiClient.createDataSource(dataSource)
  }

  /**
   * 更新数据源
   */
  static async update(id: string, dataSource: UpdateDataSourceRequest): Promise<DataSource> {
    return apiClient.updateDataSource(id, dataSource)
  }

  /**
   * 删除数据源
   */
  static async delete(id: string): Promise<void> {
    return apiClient.deleteDataSource(id)
  }

  /**
   * 测试数据源连接
   */
  static async test(id: string): Promise<DataSourceTestResult> {
    return apiClient.testDataSource(id)
  }

  /**
   * 获取数据源结构
   */
  static async getSchema(id: string): Promise<DataSourceSchema> {
    return apiClient.getDataSourceSchema(id)
  }

  /**
   * 执行SQL查询
   */
  static async executeQuery(id: string, sql: string, parameters?: Record<string, any>): Promise<any> {
    return apiClient.request('POST', `/data-sources/${id}/query`, {
      data: { sql, parameters }
    })
  }

  /**
   * 获取数据源表列表
   */
  static async getTables(id: string): Promise<string[]> {
    return apiClient.request('GET', `/data-sources/${id}/tables`, { cache: true })
  }

  /**
   * 获取表字段列表
   */
  static async getFields(id: string, tableName: string): Promise<string[]> {
    return apiClient.request('GET', `/data-sources/${id}/fields`, {
      params: { table_name: tableName },
      cache: true
    })
  }
}

// ============================================================================
// 模板服务
// ============================================================================

class TemplateService {
  /**
   * 获取模板列表
   */
  static async list(params?: QueryParams): Promise<PaginatedResponse<Template>> {
    return apiClient.getTemplates(params)
  }

  /**
   * 获取单个模板
   */
  static async get(id: string): Promise<Template> {
    return apiClient.getTemplate(id)
  }

  /**
   * 创建模板
   */
  static async create(template: CreateTemplateRequest): Promise<Template> {
    return apiClient.createTemplate(template)
  }

  /**
   * 更新模板
   */
  static async update(id: string, template: UpdateTemplateRequest): Promise<Template> {
    return apiClient.updateTemplate(id, template)
  }

  /**
   * 删除模板
   */
  static async delete(id: string): Promise<void> {
    return apiClient.deleteTemplate(id)
  }

  /**
   * 复制模板
   */
  static async duplicate(id: string): Promise<Template> {
    return apiClient.duplicateTemplate(id)
  }

  /**
   * 预览模板
   */
  static async preview(id: string): Promise<TemplatePreview> {
    return apiClient.previewTemplate(id)
  }

  /**
   * 上传模板文件
   */
  static async uploadFile(file: File): Promise<Template> {
    return apiClient.uploadFile(file, 'templates/')
  }

  /**
   * 解析模板占位符
   */
  static async parsePlaceholders(templateId: string): Promise<any> {
    return apiClient.request('POST', `/templates/${templateId}/parse`)
  }
}

// ============================================================================
// 占位符服务
// ============================================================================

class PlaceholderService {
  /**
   * 获取模板占位符列表
   */
  static async list(templateId: string): Promise<any[]> {
    return apiClient.request('GET', `/placeholders/${templateId}`)
  }

  /**
   * 创建占位符
   */
  static async create(placeholder: any): Promise<any> {
    return apiClient.request('POST', '/placeholders/', { data: placeholder })
  }

  /**
   * 更新占位符
   */
  static async update(id: string, placeholder: any): Promise<any> {
    return apiClient.request('PUT', `/placeholders/${id}`, { data: placeholder })
  }

  /**
   * 删除占位符
   */
  static async delete(id: string): Promise<void> {
    return apiClient.request('DELETE', `/placeholders/${id}`)
  }

  /**
   * 智能分析占位符
   */
  static async analyze(id: string): Promise<any> {
    return apiClient.request('POST', `/placeholders/${id}/analyze`)
  }

  /**
   * 生成SQL查询
   */
  static async generateSQL(id: string): Promise<any> {
    return apiClient.request('POST', `/placeholders/${id}/generate-sql`)
  }

  /**
   * 测试占位符图表生成
   */
  static async testChart(id: string, request: any): Promise<any> {
    return apiClient.request('POST', `/placeholders/${id}/test-chart`, { data: request })
  }
}

// ============================================================================
// 报告服务
// ============================================================================

class ReportService {
  /**
   * 获取报告列表
   */
  static async list(params?: QueryParams): Promise<PaginatedResponse<Report>> {
    return apiClient.getReports(params)
  }

  /**
   * 获取单个报告
   */
  static async get(id: string): Promise<Report> {
    return apiClient.getReport(id)
  }

  /**
   * 生成报告
   */
  static async generate(request: GenerateReportRequest): Promise<Report> {
    return apiClient.generateReport(request)
  }

  /**
   * 下载报告
   */
  static async download(id: string): Promise<Blob> {
    return apiClient.downloadReport(id)
  }

  /**
   * 删除报告
   */
  static async delete(id: string): Promise<void> {
    return apiClient.deleteReport(id)
  }

  /**
   * 重新生成报告
   */
  static async regenerate(id: string): Promise<Report> {
    return apiClient.regenerateReport(id)
  }

  /**
   * 获取报告历史记录
   */
  static async getHistory(params?: QueryParams): Promise<PaginatedResponse<any>> {
    return apiClient.request('GET', '/history/', { params, cache: true })
  }
}

// ============================================================================
// 任务服务
// ============================================================================

class TaskService {
  /**
   * 获取任务列表
   */
  static async list(params?: QueryParams): Promise<PaginatedResponse<Task>> {
    return apiClient.getTasks(params)
  }

  /**
   * 获取单个任务
   */
  static async get(id: string): Promise<Task> {
    return apiClient.getTask(id)
  }

  /**
   * 创建任务
   */
  static async create(task: CreateTaskRequest): Promise<Task> {
    return apiClient.createTask(task)
  }

  /**
   * 更新任务
   */
  static async update(id: string, task: Partial<CreateTaskRequest>): Promise<Task> {
    return apiClient.updateTask(id, task)
  }

  /**
   * 删除任务
   */
  static async delete(id: string): Promise<void> {
    return apiClient.deleteTask(id)
  }

  /**
   * 立即执行任务
   */
  static async execute(id: string): Promise<void> {
    return apiClient.executeTask(id)
  }

  /**
   * 暂停任务
   */
  static async pause(id: string): Promise<void> {
    return apiClient.pauseTask(id)
  }

  /**
   * 恢复任务
   */
  static async resume(id: string): Promise<void> {
    return apiClient.resumeTask(id)
  }

  /**
   * 获取任务进度
   */
  static async getProgress(id: string): Promise<TaskProgress> {
    return apiClient.getTaskProgress(id)
  }

  /**
   * 获取任务调度信息
   */
  static async getSchedule(): Promise<any[]> {
    return apiClient.request('GET', '/scheduler/tasks')
  }

  /**
   * 更新任务调度
   */
  static async updateSchedule(id: string, cronExpression: string): Promise<void> {
    return apiClient.request('POST', `/celery/tasks/${id}/schedule`, {
      data: { cron_expression: cronExpression }
    })
  }
}

// ============================================================================
// 系统服务
// ============================================================================

class SystemService {
  /**
   * 获取系统健康状态
   */
  static async getHealth(): Promise<HealthStatus> {
    return apiClient.getHealthStatus()
  }

  /**
   * 获取仪表板统计数据
   */
  static async getDashboardStats(): Promise<DashboardStats> {
    return apiClient.getDashboardStats()
  }

  /**
   * 获取系统信息
   */
  static async getInfo(): Promise<any> {
    return apiClient.request('GET', '/system/info', { cache: true, cacheTTL: 300000 })
  }

  /**
   * 获取最近活动
   */
  static async getRecentActivity(params?: QueryParams): Promise<any[]> {
    return apiClient.request('GET', '/dashboard/recent-activity', { 
      params,
      cache: true,
      cacheTTL: 60000 
    })
  }

  /**
   * 获取图表数据
   */
  static async getChartData(params?: any): Promise<any> {
    return apiClient.request('GET', '/dashboard/chart-data', { 
      params,
      cache: true,
      cacheTTL: 300000 
    })
  }

  /**
   * 获取系统健康详情
   */
  static async getDetailedHealth(): Promise<any> {
    return apiClient.request('GET', '/health/detailed', { 
      skipAuth: true,
      cache: true,
      cacheTTL: 30000 
    })
  }
}

// ============================================================================
// LLM服务
// ============================================================================

class LLMService {
  /**
   * 获取LLM服务器列表
   */
  static async getServers(): Promise<LLMServer[]> {
    return apiClient.getLLMServers()
  }

  /**
   * 获取用户LLM偏好设置
   */
  static async getUserPreferences(): Promise<UserLLMPreferences> {
    return apiClient.getUserLLMPreferences()
  }

  /**
   * 更新用户LLM偏好设置
   */
  static async updateUserPreferences(preferences: Partial<UserLLMPreferences>): Promise<UserLLMPreferences> {
    return apiClient.updateUserLLMPreferences(preferences)
  }

  /**
   * 获取LLM使用配额
   */
  static async getUsageQuota(): Promise<any> {
    return apiClient.request('GET', '/user-llm/usage-quota')
  }

  /**
   * 智能模型推荐
   */
  static async recommendModel(params: any): Promise<any> {
    return apiClient.request('POST', '/user-llm/recommend-model', { data: params })
  }

  /**
   * 获取可用模型列表
   */
  static async getAvailableModels(): Promise<any[]> {
    return apiClient.request('GET', '/user-llm/available-models', { cache: true })
  }

  /**
   * 获取LLM监控状态
   */
  static async getMonitorStatus(): Promise<any> {
    return apiClient.request('GET', '/llm-monitor/status')
  }

  /**
   * 获取AI服务连接池状态
   */
  static async getServicePoolStatus(): Promise<any> {
    return apiClient.request('GET', '/llm-monitor/ai-service-pool')
  }

  /**
   * 获取LLM服务健康检查
   */
  static async getHealthCheck(): Promise<any> {
    return apiClient.request('GET', '/llm-monitor/health')
  }

  /**
   * 获取服务器的模型列表
   */
  static async getServerModels(serverId: string): Promise<any[]> {
    return apiClient.request('GET', `/llm-servers/${serverId}/models`, { cache: true })
  }
}

// ============================================================================
// 文件服务
// ============================================================================

class FileService {
  /**
   * 上传文件
   */
  static async upload(file: File, path?: string, overwrite?: boolean): Promise<any> {
    return apiClient.uploadFile(file, path, overwrite)
  }

  /**
   * 下载文件
   */
  static async download(filePath: string): Promise<Blob> {
    return apiClient.downloadFile(filePath)
  }

  /**
   * 获取文件URL
   */
  static async getFileUrl(filePath: string): Promise<string> {
    const result = await apiClient.request('GET', `/files/url/${filePath}`)
    return result.url
  }

  /**
   * 删除文件
   */
  static async delete(filePath: string): Promise<void> {
    return apiClient.request('DELETE', `/files/${filePath}`)
  }

  /**
   * 获取文件列表
   */
  static async list(params?: any): Promise<any> {
    return apiClient.request('GET', '/files/list', { params, cache: true })
  }

  /**
   * 获取存储状态
   */
  static async getStorageStatus(): Promise<any> {
    return apiClient.request('GET', '/files/status', { cache: true, cacheTTL: 60000 })
  }

  /**
   * 批量上传文件
   */
  static async batchUpload(files: File[]): Promise<any[]> {
    const results = []
    for (const file of files) {
      const result = await this.upload(file)
      results.push(result)
    }
    return results
  }
}

// ============================================================================
// ETL作业服务
// ============================================================================

class ETLService {
  /**
   * 获取ETL作业列表
   */
  static async list(params?: QueryParams): Promise<PaginatedResponse<ETLJob>> {
    return apiClient.request('GET', '/etl-jobs/', { params, cache: true })
  }

  /**
   * 获取单个ETL作业
   */
  static async get(id: string): Promise<ETLJob> {
    return apiClient.request('GET', `/etl-jobs/${id}`, { cache: true })
  }

  /**
   * 创建ETL作业
   */
  static async create(job: any): Promise<ETLJob> {
    return apiClient.request('POST', '/etl-jobs/', { data: job })
  }

  /**
   * 运行ETL作业
   */
  static async run(id: string): Promise<void> {
    return apiClient.request('POST', `/etl-jobs/${id}/run`)
  }

  /**
   * 启用ETL作业
   */
  static async enable(id: string): Promise<void> {
    return apiClient.request('POST', `/etl-jobs/${id}/enable`)
  }

  /**
   * 禁用ETL作业
   */
  static async disable(id: string): Promise<void> {
    return apiClient.request('POST', `/etl-jobs/${id}/disable`)
  }
}

// ============================================================================
// 图表测试服务
// ============================================================================

class ChartTestService {
  /**
   * 测试图表生成
   */
  static async testChart(request: any): Promise<any> {
    return apiClient.request('POST', '/chart-test/test-chart', { data: request })
  }

  /**
   * 获取支持的图表类型
   */
  static async getChartTypes(): Promise<any[]> {
    return apiClient.request('GET', '/chart-test/chart-types', { cache: true })
  }
}

// ============================================================================
// 设置服务
// ============================================================================

class SettingsService {
  /**
   * 获取用户配置
   */
  static async getProfile(): Promise<any> {
    return apiClient.request('GET', '/settings/profile', { cache: true })
  }

  /**
   * 更新用户配置
   */
  static async updateProfile(profile: any): Promise<any> {
    return apiClient.request('PUT', '/settings/profile', { data: profile })
  }

  /**
   * 获取可用LLM服务器
   */
  static async getLLMServers(): Promise<LLMServer[]> {
    return apiClient.request('GET', '/settings/llm-servers', { cache: true })
  }

  /**
   * 重置为默认设置
   */
  static async resetToDefaults(): Promise<void> {
    return apiClient.request('POST', '/settings/reset-to-defaults')
  }

  /**
   * 创建LLM服务器
   */
  static async createServer(server: any): Promise<LLMServer> {
    return apiClient.request('POST', '/settings/llm-servers', { data: server })
  }

  /**
   * 更新LLM服务器
   */
  static async updateServer(id: string, server: any): Promise<LLMServer> {
    return apiClient.request('PUT', `/settings/llm-servers/${id}`, { data: server })
  }

  /**
   * 删除LLM服务器
   */
  static async deleteServer(id: string): Promise<void> {
    return apiClient.request('DELETE', `/settings/llm-servers/${id}`)
  }

  /**
   * 获取LLM服务器模型列表
   */
  static async getServerModels(serverId: string): Promise<any[]> {
    return apiClient.request('GET', `/settings/llm-servers/${serverId}/models`, { cache: true })
  }

  /**
   * 创建LLM服务器模型
   */
  static async createServerModel(serverId: string, model: any): Promise<any> {
    return apiClient.request('POST', `/settings/llm-servers/${serverId}/models`, { data: model })
  }

  /**
   * 更新LLM服务器模型
   */
  static async updateServerModel(serverId: string, modelId: string, model: any): Promise<any> {
    return apiClient.request('PUT', `/settings/llm-servers/${serverId}/models/${modelId}`, { data: model })
  }

  /**
   * 删除LLM服务器模型
   */
  static async deleteServerModel(serverId: string, modelId: string): Promise<void> {
    return apiClient.request('DELETE', `/settings/llm-servers/${serverId}/models/${modelId}`)
  }
}

// ============================================================================
// WebSocket服务
// ============================================================================

class WebSocketService {
  /**
   * 获取WebSocket状态
   */
  static async getStatus(): Promise<any> {
    return apiClient.getWebSocketStatus()
  }

  /**
   * 发送WebSocket通知
   */
  static async sendNotification(notification: {
    title: string
    message: string
    type: 'info' | 'success' | 'warning' | 'error'
    target_user_id?: string
  }): Promise<void> {
    return apiClient.sendWebSocketNotification(notification)
  }

  /**
   * 订阅频道
   */
  static async subscribe(channel: string): Promise<void> {
    return apiClient.request('POST', '/ws/subscribe', { data: { channel } })
  }

  /**
   * 取消订阅频道
   */
  static async unsubscribe(channel: string): Promise<void> {
    return apiClient.request('POST', '/ws/unsubscribe', { data: { channel } })
  }

  /**
   * 获取用户连接信息
   */
  static async getConnections(): Promise<any[]> {
    return apiClient.request('GET', '/ws/connections')
  }

  /**
   * 断开指定会话
   */
  static async disconnectSession(sessionId: string): Promise<void> {
    return apiClient.request('DELETE', `/ws/connections/${sessionId}`)
  }
}

// ============================================================================
// 通知服务
// ============================================================================

export interface NotificationListResponse {
  notifications: Notification[]
  total: number
  unread_count: number
  page: number
  size: number
  has_more: boolean
}

export interface NotificationStatsResponse {
  total_notifications: number
  unread_count: number
  today_count: number
  this_week_count: number
  by_type: Record<string, number>
  by_status: Record<string, number>
}

export interface NotificationPreference {
  user_id: string
  enable_websocket: boolean
  enable_email: boolean
  enable_browser: boolean
  enable_sound: boolean
  enable_task_notifications: boolean
  enable_report_notifications: boolean
  enable_system_notifications: boolean
  enable_error_notifications: boolean
  quiet_hours_start?: string
  quiet_hours_end?: string
  max_notifications_per_day: number
  updated_at?: string
}

class NotificationService {
  /**
   * 获取通知列表
   */
  static async getNotifications(params?: {
    skip?: number
    limit?: number
    status?: string
    type?: string
    include_read?: boolean
  }): Promise<NotificationListResponse> {
    const searchParams = new URLSearchParams()
    if (params?.skip !== undefined) searchParams.set('skip', params.skip.toString())
    if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString())
    if (params?.status) searchParams.set('status', params.status)
    if (params?.type) searchParams.set('type', params.type)
    if (params?.include_read !== undefined) searchParams.set('include_read', params.include_read.toString())
    
    const url = `/v1/notifications/${searchParams.toString() ? '?' + searchParams.toString() : ''}`
    return apiClient.get<NotificationListResponse>(url)
  }

  /**
   * 获取通知统计
   */
  static async getStats(): Promise<NotificationStatsResponse> {
    return apiClient.get<NotificationStatsResponse>('/v1/notifications/stats')
  }

  /**
   * 获取未读通知数量
   */
  static async getUnreadCount(): Promise<{ unread_count: number }> {
    return apiClient.get<{ unread_count: number }>('/v1/notifications/unread-count')
  }

  /**
   * 获取单个通知详情
   */
  static async getNotification(id: string): Promise<Notification> {
    return apiClient.get<Notification>(`/v1/notifications/${id}`)
  }

  /**
   * 标记通知为已读
   */
  static async markAsRead(id: string): Promise<Notification> {
    return apiClient.patch<Notification>(`/v1/notifications/${id}/read`, {})
  }

  /**
   * 忽略通知
   */
  static async dismissNotification(id: string): Promise<Notification> {
    return apiClient.patch<Notification>(`/v1/notifications/${id}/dismiss`, {})
  }

  /**
   * 标记所有通知为已读
   */
  static async markAllAsRead(): Promise<{ updated_count: number }> {
    return apiClient.patch<{ updated_count: number }>('/v1/notifications/mark-all-read', {})
  }

  /**
   * 删除通知
   */
  static async deleteNotification(id: string): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/v1/notifications/${id}`)
  }

  /**
   * 获取通知偏好设置
   */
  static async getPreferences(): Promise<NotificationPreference> {
    return apiClient.get<NotificationPreference>('/v1/notifications/preferences/')
  }

  /**
   * 更新通知偏好设置
   */
  static async updatePreferences(preferences: Partial<NotificationPreference>): Promise<NotificationPreference> {
    return apiClient.patch<NotificationPreference>('/v1/notifications/preferences/', preferences)
  }

  /**
   * 发送测试通知
   */
  static async sendTestNotification(message?: string): Promise<{ message: string; notification_id: number }> {
    const params = new URLSearchParams()
    if (message) params.set('message', message)
    return apiClient.post<{ message: string; notification_id: number }>(`/v1/notifications/test?${params.toString()}`, {})
  }
}

// ============================================================================
// 导出所有服务
// ============================================================================

export {
  AuthService,
  DataSourceService,  
  TemplateService,
  PlaceholderService,
  ReportService,
  TaskService,
  SystemService,
  LLMService,
  FileService,
  ETLService,
  ChartTestService,
  SettingsService,
  WebSocketService,
  NotificationService
}