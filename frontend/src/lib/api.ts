import axios, { AxiosResponse, AxiosError } from 'axios'
import toast from 'react-hot-toast'

// 创建axios实例 - 支持新的稳定别名路由
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 为了兼容性，也创建一个V1客户端
const apiClientV1 = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL_V1 || 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 通用请求拦截器配置
const setupRequestInterceptor = (client: typeof apiClient, apiVersion: string = 'stable') => {
  client.interceptors.request.use(
    (config) => {
      // 从localStorage获取token
      if (typeof window !== 'undefined') {
        const token = localStorage.getItem('authToken')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
      }

      // 添加API版本和请求ID
      config.headers['API-Version'] = apiVersion
      config.headers['X-Request-ID'] = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      config.headers['X-Client-Version'] = process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0'

      return config
    },
    (error) => {
      return Promise.reject(error)
    }
  )
}

// 设置拦截器
setupRequestInterceptor(apiClient, 'stable') // 稳定别名路由
setupRequestInterceptor(apiClientV1, 'v1')   // V1路由

// 通用响应拦截器配置
const setupResponseInterceptor = (client: typeof apiClient) => {
  client.interceptors.response.use(
    (response: AxiosResponse) => {
      // 记录API版本和请求ID（如果需要调试）
      const apiVersion = response.headers['api-version']
      const requestId = response.headers['x-request-id']
      const isDeprecated = response.headers['x-deprecated'] === 'true'

      if (process.env.NODE_ENV === 'development') {
        console.debug(`API Response [${apiVersion}] [${requestId}]:`, {
          status: response.status,
          url: response.config.url,
          deprecated: isDeprecated,
          data: response.data
        })
      }

      // 处理弃用警告
      if (isDeprecated) {
        console.warn(`⚠️ API Deprecation Warning: ${response.config.url}`, {
          status: response.status,
          headers: response.headers
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
      // 处理410 Gone（弃用接口）
      if (error.response?.status === 410) {
        const isDeprecated = error.response.headers?.['x-deprecated'] === 'true'
        const deprecationData = error.response.data as any

        if (isDeprecated) {
          console.warn('🚨 Deprecated API Called:', {
            url: error.config?.url,
            message: deprecationData?.message,
            replacement: deprecationData?.replacement
          })

          // 显示用户友好的弃用提示
          if (deprecationData?.replacement) {
            toast.error(`API已升级，请使用新接口：${JSON.stringify(deprecationData.replacement)}`)
          } else {
            toast.error('此API接口已废弃，请联系管理员更新')
          }
        }

        return Promise.reject(error)
      }

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
}

// 设置响应拦截器
setupResponseInterceptor(apiClient)
setupResponseInterceptor(apiClientV1)

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
export { apiClientV1 }