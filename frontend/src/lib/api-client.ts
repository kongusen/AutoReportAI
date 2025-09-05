/**
 * AutoReportAI 增强API客户端 v2.0
 * 基于详细的后端接口文档构建
 * 提供完整的类型安全和统一的响应格式
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import toast from 'react-hot-toast'
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
  FileUploadResponse,
  WebSocketConnectionInfo
} from '@/types/api'

// ============================================================================
// 配置和接口定义
// ============================================================================

export interface ApiClientConfig {
  baseURL?: string
  timeout?: number
  retryCount?: number
  enableCache?: boolean
  showToast?: boolean
  debug?: boolean
}

export interface RequestOptions extends AxiosRequestConfig {
  showToast?: boolean
  retryCount?: number
  cache?: boolean
  cacheTTL?: number
  skipAuth?: boolean
}

// ============================================================================
// 缓存管理
// ============================================================================

class ApiCache {
  private cache = new Map<string, { data: any; timestamp: number; ttl: number }>()

  set(key: string, data: any, ttl: number = 5 * 60 * 1000) {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl
    })
  }

  get(key: string) {
    const item = this.cache.get(key)
    if (!item) return null

    if (Date.now() - item.timestamp > item.ttl) {
      this.cache.delete(key)
      return null
    }

    return item.data
  }

  invalidatePattern(pattern: string) {
    const regex = new RegExp(pattern)
    for (const key of this.cache.keys()) {
      if (regex.test(key)) {
        this.cache.delete(key)
      }
    }
  }

  clear() {
    this.cache.clear()
  }
}

// ============================================================================
// 主API客户端类
// ============================================================================

export class AutoReportAPIClient {
  private axiosInstance: AxiosInstance
  private cache = new ApiCache()
  private config: Required<ApiClientConfig>

  constructor(config: ApiClientConfig = {}) {
    this.config = {
      baseURL: config.baseURL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
      timeout: config.timeout || 30000,
      retryCount: config.retryCount || 3,
      enableCache: config.enableCache ?? true,
      showToast: config.showToast ?? true,
      debug: config.debug ?? (process.env.NODE_ENV === 'development')
    }

    this.axiosInstance = axios.create({
      baseURL: this.config.baseURL,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
        'X-Client-Version': process.env.NEXT_PUBLIC_APP_VERSION || '2.0.0',
        'X-Client-Platform': 'web'
      }
    })

    this.setupInterceptors()
  }

  // ============================================================================
  // 拦截器设置
  // ============================================================================

  private setupInterceptors() {
    // 请求拦截器
    this.axiosInstance.interceptors.request.use(
      (config) => {
        // 添加认证token
        if (typeof window !== 'undefined' && !config.headers['skip-auth']) {
          const token = localStorage.getItem('authToken')
          if (token) {
            config.headers.Authorization = `Bearer ${token}`
          }
        }

        // 添加请求ID
        const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        config.headers['X-Request-ID'] = requestId

        // 记录请求开始时间
        ;(config as any).metadata = {
          requestId,
          startTime: Date.now()
        }

        if (this.config.debug) {
          console.debug(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
            params: config.params,
            data: config.data
          })
        }

        return config
      },
      (error) => Promise.reject(error)
    )

    // 响应拦截器
    this.axiosInstance.interceptors.response.use(
      (response: AxiosResponse) => {
        const duration = Date.now() - ((response.config as any).metadata?.startTime || 0)
        const requestId = (response.config as any).metadata?.requestId

        if (this.config.debug) {
          console.debug(`[API Response] ${requestId} (${duration}ms)`, {
            status: response.status,
            data: response.data
          })
        }

        return response
      },
      async (error) => {
        const duration = Date.now() - ((error.config as any)?.metadata?.startTime || 0)
        const requestId = (error.config as any)?.metadata?.requestId

        if (this.config.debug) {
          console.error(`[API Error] ${requestId} (${duration}ms)`, {
            status: error.response?.status,
            error: error.response?.data
          })
        }

        // 处理401未授权错误
        if (error.response?.status === 401) {
          this.handleAuthError()
          return Promise.reject(error)
        }

        // 显示错误提示
        if (this.config.showToast) {
          this.handleErrorToast(error)
        }

        return Promise.reject(error)
      }
    )
  }

  // ============================================================================
  // 错误处理
  // ============================================================================

  private handleAuthError() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('authToken')
      localStorage.removeItem('user')
      this.cache.clear()
      window.location.href = '/login'
    }
  }

  private handleErrorToast(error: any) {
    const status = error.response?.status
    const errorData = error.response?.data

    let message = errorData?.message || errorData?.error || errorData?.detail || '请求失败'

    // 处理验证错误
    if (errorData?.errors && Array.isArray(errorData.errors)) {
      errorData.errors.forEach((err: any) => {
        const fieldPrefix = err.field ? `${err.field}: ` : ''
        toast.error(`${fieldPrefix}${err.message}`)
      })
      return
    }

    // 根据状态码显示不同消息
    switch (status) {
      case 400:
        toast.error(message || '请求参数错误')
        break
      case 403:
        toast.error('权限不足')
        break
      case 404:
        toast.error('资源不存在')
        break
      case 422:
        toast.error(message || '数据验证失败')
        break
      case 429:
        toast.error('请求过于频繁，请稍后再试')
        break
      case 500:
        toast.error('服务器内部错误')
        break
      default:
        if (!error.response) {
          toast.error('网络连接失败')
        } else {
          toast.error(message)
        }
        break
    }
  }

  // ============================================================================
  // 通用请求方法
  // ============================================================================

  public async request<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    url: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const {
      data,
      cache = false,
      cacheTTL = 5 * 60 * 1000,
      showToast = this.config.showToast,
      retryCount = method === 'GET' ? this.config.retryCount : 1,
      skipAuth = false,
      ...axiosConfig
    } = options

    // 检查缓存（仅GET请求）
    if (method === 'GET' && cache && this.config.enableCache) {
      const cacheKey = `${method}_${url}_${JSON.stringify(axiosConfig.params || {})}`
      const cachedData = this.cache.get(cacheKey)
      if (cachedData) {
        return cachedData
      }
    }

    // 设置请求配置
    const requestConfig: AxiosRequestConfig = {
      method,
      url,
      ...axiosConfig
    }

    if (data) {
      requestConfig.data = data
    }

    if (skipAuth) {
      requestConfig.headers = { ...requestConfig.headers, 'skip-auth': 'true' }
    }

    // 执行请求（带重试）
    let lastError: any
    for (let attempt = 1; attempt <= retryCount; attempt++) {
      try {
        const response = await this.axiosInstance.request<APIResponse<T>>(requestConfig)
        
        // 处理后端 ApiResponse[T] 格式
        let result: T
        if (response.data && typeof response.data === 'object' && 'success' in response.data) {
          // 后端返回的是 ApiResponse[T] 格式
          if (response.data.success === false) {
            throw new Error(response.data.error || response.data.message || '请求失败')
          }
          result = response.data.data as T
        } else {
          // 直接返回数据（用于某些特殊端点）
          result = response.data as T
        }

        // 缓存响应（仅GET请求）
        if (method === 'GET' && cache && this.config.enableCache) {
          const cacheKey = `${method}_${url}_${JSON.stringify(axiosConfig.params || {})}`
          this.cache.set(cacheKey, result, cacheTTL)
        }

        // 显示成功消息
        if (showToast && response.data && typeof response.data === 'object' && 'success' in response.data && response.data.success && response.data.message && method !== 'GET') {
          toast.success(response.data.message)
        }

        // 清除相关缓存（非GET请求）
        if (method !== 'GET') {
          this.cache.invalidatePattern(`GET_${url.split('/')[0]}`)
        }

        return result
      } catch (error: any) {
        lastError = error

        // 不重试的错误类型
        if (
          error.response?.status === 401 ||
          error.response?.status === 403 ||
          error.response?.status === 404 ||
          attempt === retryCount
        ) {
          break
        }

        // 等待后重试
        const delay = Math.pow(2, attempt - 1) * 1000 + Math.random() * 1000
        await new Promise(resolve => setTimeout(resolve, delay))

        if (this.config.debug) {
          console.log(`重试 ${attempt}/${retryCount}: ${method} ${url}`)
        }
      }
    }

    throw lastError
  }

  // ============================================================================
  // 便捷HTTP方法
  // ============================================================================

  async get<T>(url: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('GET', url, options)
  }

  async post<T>(url: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('POST', url, options)
  }

  async put<T>(url: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('PUT', url, options)
  }

  async patch<T>(url: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('PUT', url, options) // 使用PUT代替PATCH，因为request方法只支持这4种
  }

  async delete<T>(url: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('DELETE', url, options)
  }

  // ============================================================================
  // 认证API
  // ============================================================================

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    // 使用 form data 格式，因为后端期望 OAuth2PasswordRequestForm
    const formData = new URLSearchParams()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password)
    
    const response = await this.axiosInstance.post('/auth/login', formData, {
      headers: { 
        'Content-Type': 'application/x-www-form-urlencoded',
        'skip-auth': 'true' 
      }
    })
    
    // 处理后端响应格式
    let loginData: any
    if (response.data && typeof response.data === 'object' && 'success' in response.data) {
      if (!response.data.success) {
        throw new Error(response.data.error || response.data.message || '登录失败')
      }
      loginData = response.data.data
    } else {
      loginData = response.data
    }
    
    // 构建符合前端期望的响应格式
    const result: LoginResponse = {
      access_token: loginData.access_token,
      refresh_token: loginData.refresh_token || '', // 后端可能没有提供
      token_type: loginData.token_type || 'bearer',
      expires_in: loginData.expires_in || 3600, // 默认1小时
      user: loginData.user
    }
    
    // 存储token
    if (typeof window !== 'undefined' && result.access_token) {
      localStorage.setItem('authToken', result.access_token)
      if (result.refresh_token) {
        localStorage.setItem('refreshToken', result.refresh_token)
      }
      localStorage.setItem('user', JSON.stringify(result.user))
    }
    
    // 显示成功消息
    if (this.config.showToast && response.data?.message) {
      toast.success(response.data.message)
    }
    
    return result
  }

  async register(userData: RegisterRequest): Promise<User> {
    const response = await this.request<{user: User}>('POST', '/auth/register', {
      data: userData,
      skipAuth: true
    })
    
    // 后端返回 {user: User} 格式，我们需要提取用户对象
    return response.user || response as any
  }

  async logout(): Promise<void> {
    try {
      await this.request<void>('POST', '/auth/logout')
    } finally {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('authToken')
        localStorage.removeItem('refreshToken')
        localStorage.removeItem('user')
        this.cache.clear()
      }
    }
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('GET', '/auth/me', { cache: true, cacheTTL: 60000 })
  }

  async refreshToken(): Promise<LoginResponse> {
    const refreshToken = typeof window !== 'undefined' ? localStorage.getItem('refreshToken') : null
    if (!refreshToken) {
      throw new Error('No refresh token available')
    }

    return this.request<LoginResponse>('POST', '/auth/refresh', {
      data: { refresh_token: refreshToken },
      skipAuth: true
    })
  }

  // ============================================================================
  // 数据源API
  // ============================================================================

  async getDataSources(params?: QueryParams): Promise<PaginatedResponse<DataSource>> {
    return this.request<PaginatedResponse<DataSource>>('GET', '/data-sources/', {
      params,
      cache: true
    })
  }

  async getDataSource(id: string): Promise<DataSource> {
    return this.request<DataSource>('GET', `/data-sources/${id}`, { cache: true })
  }

  async createDataSource(dataSource: CreateDataSourceRequest): Promise<DataSource> {
    return this.request<DataSource>('POST', '/data-sources/', { data: dataSource })
  }

  async updateDataSource(id: string, dataSource: UpdateDataSourceRequest): Promise<DataSource> {
    return this.request<DataSource>('PUT', `/data-sources/${id}`, { data: dataSource })
  }

  async deleteDataSource(id: string): Promise<void> {
    return this.request<void>('DELETE', `/data-sources/${id}`)
  }

  async testDataSource(id: string): Promise<DataSourceTestResult> {
    return this.request<DataSourceTestResult>('POST', `/data-sources/${id}/test`)
  }

  async getDataSourceSchema(id: string): Promise<DataSourceSchema> {
    return this.request<DataSourceSchema>('GET', `/data-sources/${id}/schema`, { cache: true })
  }

  // ============================================================================
  // 模板API
  // ============================================================================

  async getTemplates(params?: QueryParams): Promise<PaginatedResponse<Template>> {
    return this.request<PaginatedResponse<Template>>('GET', '/templates/', {
      params,
      cache: true
    })
  }

  async getTemplate(id: string): Promise<Template> {
    return this.request<Template>('GET', `/templates/${id}`, { cache: true })
  }

  async createTemplate(template: CreateTemplateRequest): Promise<Template> {
    return this.request<Template>('POST', '/templates/', { data: template })
  }

  async updateTemplate(id: string, template: UpdateTemplateRequest): Promise<Template> {
    return this.request<Template>('PUT', `/templates/${id}`, { data: template })
  }

  async deleteTemplate(id: string): Promise<void> {
    return this.request<void>('DELETE', `/templates/${id}`)
  }

  async duplicateTemplate(id: string): Promise<Template> {
    return this.request<Template>('POST', `/templates/${id}/duplicate`)
  }

  async previewTemplate(id: string): Promise<TemplatePreview> {
    return this.request<TemplatePreview>('GET', `/templates/${id}/preview`)
  }

  async analyzeTemplatePlaceholders(
    templateId: string, 
    dataSourceId: string, 
    options?: {
      forceReanalyze?: boolean
      optimizationLevel?: string
      targetExpectations?: any
    }
  ): Promise<any> {
    const params: any = {
      data_source_id: dataSourceId
    }
    
    if (options?.forceReanalyze) {
      params.force_reanalyze = options.forceReanalyze
    }
    if (options?.optimizationLevel) {
      params.optimization_level = options.optimizationLevel
    }
    
    return this.request<any>('POST', `/templates/${templateId}/analyze`, { 
      params,
      data: options?.targetExpectations ? { target_expectations: options.targetExpectations } : undefined
    })
  }


  async uploadTemplateFile(templateId: string, file: File): Promise<Template> {
    const formData = new FormData()
    formData.append('file', file)

    return this.request<Template>('POST', `/templates/${templateId}/upload`, {
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }

  async downloadTemplateFile(templateId: string): Promise<Blob> {
    const response = await this.axiosInstance.get(`/templates/${templateId}/download`, {
      responseType: 'blob'
    })
    return response.data
  }

  // ============================================================================
  // 报告API
  // ============================================================================

  async getReports(params?: QueryParams): Promise<PaginatedResponse<Report>> {
    return this.request<PaginatedResponse<Report>>('GET', '/reports/', {
      params,
      cache: true
    })
  }

  async getReport(id: string): Promise<Report> {
    return this.request<Report>('GET', `/reports/${id}`, { cache: true })
  }

  async generateReport(request: GenerateReportRequest): Promise<Report> {
    return this.request<Report>('POST', '/reports/generate', { data: request })
  }

  async downloadReport(id: string): Promise<Blob> {
    const response = await this.axiosInstance.get(`/reports/${id}/download`, {
      responseType: 'blob'
    })
    return response.data
  }

  async getReportDownloadInfo(id: string): Promise<any> {
    return this.request<any>('GET', `/reports/${id}/download-info`)
  }

  async deleteReport(id: string): Promise<void> {
    return this.request<void>('DELETE', `/reports/${id}`)
  }

  async regenerateReport(id: string): Promise<Report> {
    return this.request<Report>('POST', `/reports/${id}/regenerate`)
  }

  // ============================================================================
  // 任务API
  // ============================================================================

  async getTasks(params?: QueryParams): Promise<PaginatedResponse<Task>> {
    return this.request<PaginatedResponse<Task>>('GET', '/tasks/', {
      params,
      cache: true
    })
  }

  async getTask(id: string): Promise<Task> {
    return this.request<Task>('GET', `/tasks/${id}`, { cache: true })
  }

  async createTask(task: CreateTaskRequest): Promise<Task> {
    return this.request<Task>('POST', '/tasks/', { data: task })
  }

  async updateTask(id: string, task: Partial<CreateTaskRequest>): Promise<Task> {
    return this.request<Task>('PUT', `/tasks/${id}`, { data: task })
  }

  async deleteTask(id: string): Promise<void> {
    return this.request<void>('DELETE', `/tasks/${id}`)
  }

  async executeTask(id: string): Promise<void> {
    return this.request<void>('POST', `/tasks/${id}/execute`)
  }

  async pauseTask(id: string): Promise<void> {
    return this.request<void>('POST', `/tasks/${id}/pause`)
  }

  async resumeTask(id: string): Promise<void> {
    return this.request<void>('POST', `/tasks/${id}/resume`)
  }

  async getTaskProgress(id: string): Promise<TaskProgress> {
    return this.request<TaskProgress>('GET', `/scheduler/tasks/${id}/status`)
  }

  // ============================================================================
  // 系统API
  // ============================================================================

  async getHealthStatus(): Promise<HealthStatus> {
    return this.request<HealthStatus>('GET', '/health', { 
      skipAuth: true, 
      cache: true, 
      cacheTTL: 30000 
    })
  }

  async getDashboardStats(): Promise<DashboardStats> {
    return this.request<DashboardStats>('GET', '/dashboard/stats', { 
      cache: true, 
      cacheTTL: 60000 
    })
  }

  // ============================================================================
  // LLM API
  // ============================================================================

  async getLLMServers(): Promise<LLMServer[]> {
    return this.request<LLMServer[]>('GET', '/llm-servers/', { cache: true })
  }

  async getUserLLMPreferences(): Promise<UserLLMPreferences> {
    return this.request<UserLLMPreferences>('GET', '/user-llm-preferences/', { cache: true })
  }

  async updateUserLLMPreferences(preferences: Partial<UserLLMPreferences>): Promise<UserLLMPreferences> {
    return this.request<UserLLMPreferences>('PUT', '/user-llm-preferences/', { data: preferences })
  }

  // ============================================================================
  // 系统洞察API - React Agent集成
  // ============================================================================

  async getSystemPerformance(integrationMode: string = 'intelligent'): Promise<any> {
    return this.request<any>('GET', '/react-agent/system-performance', { 
      params: { performance_type: integrationMode },
      cache: true,
      cacheTTL: 60000 
    })
  }

  async getReactAgentStats(): Promise<any> {
    return this.request<any>('GET', '/react-agent/agent-stats', { 
      cache: true,
      cacheTTL: 30000 
    })
  }

  async getRecentActivities(limit: number = 10): Promise<any> {
    return this.request<any>('GET', '/react-agent/recent-activities', { 
      params: { limit },
      cache: true,
      cacheTTL: 30000 
    })
  }

  async getOptimizationSettings(): Promise<any> {
    return this.request<any>('GET', '/system-insights/context-system/optimization-settings', { 
      cache: true,
      cacheTTL: 300000 // 5分钟缓存
    })
  }

  async testSystemConfiguration(testConfig: any): Promise<any> {
    return this.request<any>('POST', '/system-insights/context-system/test-configuration', { 
      data: testConfig 
    })
  }

  async getSystemHealth(): Promise<any> {
    return this.request<any>('GET', '/system-insights/context-system/health', { 
      cache: true,
      cacheTTL: 30000 // 30秒缓存
    })
  }

  // ============================================================================
  // 文件API
  // ============================================================================

  async uploadFile(file: File, path?: string, overwrite?: boolean): Promise<FileUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    if (path) formData.append('path', path)
    if (overwrite !== undefined) formData.append('overwrite', overwrite.toString())

    const response = await this.axiosInstance.post<APIResponse<FileUploadResponse>>('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    return (response.data as any).data || response.data
  }

  async downloadFile(filePath: string): Promise<Blob> {
    const response = await this.axiosInstance.get(`/files/download/${filePath}`, {
      responseType: 'blob'
    })
    return response.data
  }

  // ============================================================================
  // WebSocket API
  // ============================================================================

  async getWebSocketStatus(): Promise<WebSocketConnectionInfo> {
    return this.request<WebSocketConnectionInfo>('GET', '/ws/status')
  }

  async sendWebSocketNotification(notification: {
    title: string
    message: string
    type: 'info' | 'success' | 'warning' | 'error'
    target_user_id?: string
  }): Promise<void> {
    return this.request<void>('POST', '/ws/send-notification', { data: notification })
  }

  // ============================================================================
  // 工具方法
  // ============================================================================

  /**
   * 清除缓存
   */
  clearCache(): void {
    this.cache.clear()
  }

  /**
   * 清除指定模式的缓存
   */
  clearCachePattern(pattern: string): void {
    this.cache.invalidatePattern(pattern)
  }

  /**
   * 设置认证token
   */
  setAuthToken(token: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('authToken', token)
    }
  }

  /**
   * 检查是否已认证
   */
  isAuthenticated(): boolean {
    if (typeof window === 'undefined') return false
    return !!localStorage.getItem('authToken')
  }

  /**
   * 获取当前token
   */
  getAuthToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('authToken')
  }
}

// ============================================================================
// 导出单例实例
// ============================================================================

export const apiClient = new AutoReportAPIClient()
export default apiClient