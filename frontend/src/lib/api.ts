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

// 请求拦截器 - 添加认证token
apiClient.interceptors.request.use(
  (config) => {
    // 从localStorage获取token
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('authToken')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 统一错误处理
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
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
    
    // 检查是否是新的 ApiResponse 格式
    const errorMessage = errorData?.message || errorData?.error || errorData?.detail
    const errorDetail = errorData?.data?.detail || errorData?.detail
    
    switch (status) {
      case 400:
        toast.error(errorMessage || '请求参数错误')
        break
      case 403:
        toast.error(errorMessage || '没有权限访问此资源')
        break
      case 404:
        toast.error(errorMessage || '请求的资源不存在')
        break
      case 422:
        // 处理表单验证错误
        if (errorDetail) {
          if (Array.isArray(errorDetail)) {
            errorDetail.forEach((err: any) => {
              toast.error(`${err.loc?.join(' ')}: ${err.msg}`)
            })
          } else if (typeof errorDetail === 'string') {
            toast.error(errorDetail)
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