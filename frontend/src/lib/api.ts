import axios, { AxiosResponse, AxiosError } from 'axios'
import toast from 'react-hot-toast'

// 创建axios实例
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 添加认证token和元数据
apiClient.interceptors.request.use(
  (config) => {
    // 从localStorage获取token
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('authToken')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    
    // 添加API版本和请求ID
    config.headers['API-Version'] = 'v1'
    config.headers['X-Request-ID'] = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    config.headers['X-Client-Version'] = process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0'
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 统一错误处理和元数据处理 (DDD架构v2.0)
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // 记录API版本和请求ID（如果需要调试）
    const apiVersion = response.headers['api-version']
    const requestId = response.headers['x-request-id']
    
    if (process.env.NODE_ENV === 'development') {
      console.debug(`API Response [${apiVersion}] [${requestId}]:`, {
        status: response.status,
        url: response.config.url,
        data: response.data
      })
    }
    
    // DDD架构v2.0: 处理新的APIResponse格式
    const apiResponse = response.data
    if (apiResponse && typeof apiResponse === 'object') {
      // 如果响应包含warnings，在开发环境显示
      if (apiResponse.warnings && apiResponse.warnings.length > 0 && process.env.NODE_ENV === 'development') {
        console.warn('API Warnings:', apiResponse.warnings)
      }
      
      // 如果响应不成功但HTTP状态是200，处理为业务逻辑错误
      if (!apiResponse.success && response.status === 200) {
        // 这是DDD架构的业务逻辑错误，不应该抛出HTTP异常
        // 让调用方处理业务逻辑错误
        console.warn('Business Logic Error:', apiResponse.errors)
      }
    }
    
    return response
  },
  (error: AxiosError) => {
    // 处理401未授权错误
    if (error.response?.status === 401) {
      // 清除认证信息
      if (typeof window !== 'undefined') {
        localStorage.removeItem('authToken')
        localStorage.removeItem('user')
        // 重定向到登录页面
        window.location.href = '/login'
      }
    }

    // 处理网络错误
    if (!error.response) {
      toast.error('网络连接失败，请检查网络连接')
      return Promise.reject(error)
    }

    // 处理服务器错误
    const { status } = error.response
    const errorData = error.response.data as any
    
    // 适配现代化的 ApiResponse 格式
    const errorMessage = errorData?.message || errorData?.error || errorData?.detail || '请求失败'
    const errorCode = errorData?.code
    const errorDetails = errorData?.details
    const errors = errorData?.errors
    
    switch (status) {
      case 400:
        // 处理现代化的错误格式
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
        // 处理表单验证错误
        if (errors && Array.isArray(errors)) {
          errors.forEach((err: any) => {
            const fieldPrefix = err.field ? `${err.field}: ` : ''
            toast.error(`${fieldPrefix}${err.message}`)
          })
        } else if (errorDetails) {
          // 兼容旧的验证错误格式
          if (Array.isArray(errorDetails)) {
            errorDetails.forEach((err: any) => {
              toast.error(`${err.loc?.join(' ')}: ${err.msg}`)
            })
          } else if (typeof errorDetails === 'string') {
            toast.error(errorDetails)
          }
        } else {
          toast.error(errorMessage || '请求参数验证失败')
        }
        break
      case 500:
        toast.error(errorMessage || '服务器内部错误')
        break
      default:
        toast.error(errorMessage || `请求失败: ${status}`)
        break
    }

    return Promise.reject(error)
  }
)

// 封装常用的HTTP方法
export const api = {
  get: <T = any>(url: string, config = {}) => 
    apiClient.get<T>(url, config).then(response => response.data),
    
  post: <T = any>(url: string, data = {}, config = {}) => 
    apiClient.post<T>(url, data, config).then(response => response.data),
    
  put: <T = any>(url: string, data = {}, config = {}) => 
    apiClient.put<T>(url, data, config).then(response => response.data),
    
  patch: <T = any>(url: string, data = {}, config = {}) => 
    apiClient.patch<T>(url, data, config).then(response => response.data),
    
  delete: <T = any>(url: string, config = {}) => 
    apiClient.delete<T>(url, config).then(response => response.data),
}

export default apiClient