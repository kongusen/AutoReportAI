/**
 * 增强的API客户端
 * 提供更好的错误处理、重试机制、进度追踪和缓存
 */

import axios, { AxiosResponse, AxiosError, AxiosRequestConfig, AxiosProgressEvent } from 'axios'
import toast from 'react-hot-toast'

export interface ApiRequestOptions extends Omit<AxiosRequestConfig, 'onUploadProgress' | 'onDownloadProgress'> {
  showToast?: boolean
  retries?: number
  retryDelay?: number
  cache?: boolean
  cacheTTL?: number
  onProgress?: (progress: number) => void
  onUploadProgress?: (progressEvent: AxiosProgressEvent) => void
  onDownloadProgress?: (progressEvent: AxiosProgressEvent) => void
}

export interface ApiResponse<T = any> {
  success: boolean
  data: T
  message?: string
  error?: string
  timestamp?: string
  requestId?: string
}

// 简单的内存缓存
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

  delete(key: string) {
    this.cache.delete(key)
  }

  clear() {
    this.cache.clear()
  }

  invalidatePattern(pattern: string) {
    const regex = new RegExp(pattern)
    for (const key of this.cache.keys()) {
      if (regex.test(key)) {
        this.cache.delete(key)
      }
    }
  }
}

// 全局缓存实例
const apiCache = new ApiCache()

// 请求队列和状态管理
const requestQueue = new Map<string, Promise<any>>()
const pendingRequests = new Set<string>()

// 创建axios实例
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 生成缓存键
const getCacheKey = (method: string, url: string, data?: any) => {
  const dataHash = data ? JSON.stringify(data) : ''
  return `${method.toUpperCase()}_${url}_${dataHash}`
}

// 延迟函数
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

// 重试逻辑
async function withRetry<T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  retryDelay: number = 1000
): Promise<T> {
  let lastError: any
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation()
    } catch (error: any) {
      lastError = error
      
      // 不重试的错误类型
      if (error.response?.status === 401 || 
          error.response?.status === 403 || 
          error.response?.status === 404 ||
          attempt === maxRetries) {
        throw error
      }
      
      // 计算退避延迟 (指数退避)
      const delayMs = retryDelay * Math.pow(2, attempt - 1) + Math.random() * 1000
      await delay(delayMs)
      
      console.log(`API请求重试 ${attempt}/${maxRetries}, ${delayMs}ms后重试`)
    }
  }
  
  throw lastError
}

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 添加认证token
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('authToken')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    
    // 添加请求元数据
    const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    config.headers['X-Request-ID'] = requestId
    config.headers['X-Client-Version'] = process.env.NEXT_PUBLIC_APP_VERSION || '2.0.0'
    config.headers['X-Client-Platform'] = 'web'
    
    // 添加时间戳用于缓存失效（使用自定义属性）
    ;(config as any).metadata = {
      requestId,
      startTime: Date.now()
    }
    
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    const duration = Date.now() - ((response.config as any).metadata?.startTime || 0)
    const requestId = (response.config as any).metadata?.requestId
    
    if (process.env.NODE_ENV === 'development') {
      console.debug(`API Success [${requestId}] ${duration}ms:`, {
        url: response.config.url,
        method: response.config.method,
        status: response.status,
        data: response.data
      })
    }
    
    return response
  },
  async (error: AxiosError) => {
    const duration = Date.now() - ((error.config as any)?.metadata?.startTime || 0)
    const requestId = (error.config as any)?.metadata?.requestId
    
    // 记录错误详情
    if (process.env.NODE_ENV === 'development') {
      console.error(`API Error [${requestId}] ${duration}ms:`, {
        url: error.config?.url,
        method: error.config?.method,
        status: error.response?.status,
        error: error.response?.data
      })
    }
    
    // 处理401未授权错误
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('authToken')
        localStorage.removeItem('user')
        // 清除API缓存
        apiCache.clear()
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }

    // 处理网络错误
    if (!error.response) {
      if (error.code === 'ECONNABORTED') {
        toast.error('请求超时，请检查网络连接')
      } else {
        toast.error('网络连接失败，请检查网络连接')
      }
      return Promise.reject(error)
    }

    // 处理服务器错误
    const { status } = error.response
    const errorData = error.response.data as any
    
    const errorMessage = errorData?.message || errorData?.error || errorData?.detail || '请求失败'
    const errorCode = errorData?.code
    const errors = errorData?.errors
    
    // 根据状态码显示不同的错误信息
    switch (status) {
      case 400:
        if (errors && Array.isArray(errors)) {
          errors.forEach((err: any) => {
            const fieldPrefix = err.field ? `${err.field}: ` : ''
            toast.error(`${fieldPrefix}${err.message}`)
          })
        } else {
          toast.error(errorMessage || '请求参数错误')
        }
        break
        
      case 403:
        toast.error(errorMessage || '没有权限访问此资源')
        break
        
      case 404:
        toast.error(errorMessage || '请求的资源不存在')
        break
        
      case 422:
        if (errors && Array.isArray(errors)) {
          errors.forEach((err: any) => {
            const fieldPrefix = err.field ? `${err.field}: ` : ''
            toast.error(`${fieldPrefix}${err.message}`)
          })
        } else {
          toast.error(errorMessage || '请求参数验证失败')
        }
        break
        
      case 429:
        toast.error('请求过于频繁，请稍后再试')
        break
        
      case 500:
        toast.error(errorMessage || '服务器内部错误')
        break
        
      case 502:
        toast.error('服务暂时不可用')
        break
        
      case 503:
        toast.error('服务暂时维护中')
        break
        
      default:
        if (status >= 500) {
          toast.error('服务器错误，请稍后重试')
        } else {
          toast.error(errorMessage || `请求失败: ${status}`)
        }
        break
    }

    return Promise.reject(error)
  }
)

// 增强的API方法
export class ApiClient {
  // GET请求
  static async get<T = any>(
    url: string, 
    options: ApiRequestOptions = {}
  ): Promise<T> {
    const {
      showToast = true,
      retries = 3,
      retryDelay = 1000,
      cache = false,
      cacheTTL = 5 * 60 * 1000,
      onProgress,
      onUploadProgress,
      onDownloadProgress,
      ...config
    } = options


    // 检查缓存
    if (cache) {
      const cacheKey = getCacheKey('GET', url, config.params)
      const cachedData = apiCache.get(cacheKey)
      if (cachedData) {
        onProgress?.(100)
        return cachedData
      }
    }

    // 防止重复请求
    const requestKey = `GET_${url}_${JSON.stringify(config.params || {})}`
    if (requestQueue.has(requestKey)) {
      return requestQueue.get(requestKey)!
    }

    const requestPromise = withRetry(async () => {
      onProgress?.(30)
      const response = await apiClient.get<ApiResponse<T>>(url, config)
      onProgress?.(100)
      
      const data = response.data.data || response.data
      
      // 缓存响应
      if (cache) {
        const cacheKey = getCacheKey('GET', url, config.params)
        apiCache.set(cacheKey, data, cacheTTL)
      }
      
      return data as T
    }, retries, retryDelay)

    requestQueue.set(requestKey, requestPromise)

    try {
      const result = await requestPromise
      return result as T
    } finally {
      requestQueue.delete(requestKey)
    }
  }

  // POST请求
  static async post<T = any>(
    url: string,
    data = {},
    options: ApiRequestOptions = {}
  ): Promise<T> {
    const {
      showToast = true,
      retries = 1, // POST请求默认不重试
      retryDelay = 1000,
      onProgress,
      onUploadProgress,
      onDownloadProgress,
      cache,
      cacheTTL,
      ...config
    } = options

    

    return withRetry(async () => {
      onProgress?.(30)
      const response = await apiClient.post<ApiResponse<T>>(url, data, config)
      onProgress?.(100)
      
      const result = response.data.data || response.data
      
      // 清除相关缓存
      apiCache.invalidatePattern(`GET_${url.split('/')[0]}`)
      
      if (showToast && response.data.success && response.data.message) {
        toast.success(response.data.message)
      }
      
      return result as T
    }, retries, retryDelay)
  }

  // PUT请求
  static async put<T = any>(
    url: string,
    data = {},
    options: ApiRequestOptions = {}
  ): Promise<T> {
    const {
      showToast = true,
      retries = 1,
      retryDelay = 1000,
      onProgress,
      onUploadProgress,
      ...config
    } = options


    return withRetry(async () => {
      onProgress?.(30)
      const response = await apiClient.put<ApiResponse<T>>(url, data, config)
      onProgress?.(100)
      
      const result = response.data.data || response.data
      
      // 清除相关缓存
      apiCache.invalidatePattern(`GET_${url}`)
      
      if (showToast && response.data.success && response.data.message) {
        toast.success(response.data.message)
      }
      
      return result as T
    }, retries, retryDelay)
  }

  // DELETE请求
  static async delete<T = any>(
    url: string,
    options: ApiRequestOptions = {}
  ): Promise<T> {
    const {
      showToast = true,
      retries = 1,
      retryDelay = 1000,
      onProgress,
      ...config
    } = options

    return withRetry(async () => {
      onProgress?.(30)
      const response = await apiClient.delete<ApiResponse<T>>(url, config)
      onProgress?.(100)
      
      const result = response.data.data || response.data
      
      // 清除相关缓存
      apiCache.invalidatePattern(`GET_${url.split('/').slice(0, -1).join('/')}`)
      
      if (showToast && response.data.success && response.data.message) {
        toast.success(response.data.message)
      }
      
      return result as T
    }, retries, retryDelay)
  }

  // 批量请求
  static async batch<T = any>(
    requests: Array<{ method: 'GET' | 'POST' | 'PUT' | 'DELETE', url: string, data?: any, options?: ApiRequestOptions }>,
    onProgress?: (completed: number, total: number) => void
  ): Promise<T[]> {
    const results: T[] = []
    let completed = 0
    
    for (const request of requests) {
      try {
        let result: T
        switch (request.method) {
          case 'GET':
            result = await this.get<T>(request.url, request.options)
            break
          case 'POST':
            result = await this.post<T>(request.url, request.data, request.options)
            break
          case 'PUT':
            result = await this.put<T>(request.url, request.data, request.options)
            break
          case 'DELETE':
            result = await this.delete<T>(request.url, request.options)
            break
        }
        results.push(result)
        completed++
        onProgress?.(completed, requests.length)
      } catch (error) {
        console.error(`批量请求失败:`, request, error)
        throw error
      }
    }
    
    return results
  }

  // 获取缓存统计
  static getCacheStats() {
    return {
      size: apiCache['cache'].size,
      clear: () => apiCache.clear(),
      invalidatePattern: (pattern: string) => apiCache.invalidatePattern(pattern)
    }
  }

  // 检查网络状态
  static async checkHealth(): Promise<{ status: string, version: string }> {
    try {
      const response = await apiClient.get('/health')
      return response.data
    } catch (error) {
      throw new Error('服务不可用')
    }
  }
}

// 导出便捷方法
export const api = ApiClient
export default ApiClient