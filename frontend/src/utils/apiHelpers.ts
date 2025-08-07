import { ApiResponse, PaginatedResponse } from '@/types'

/**
 * 标准化API响应处理
 * 处理后端可能返回的不同格式：直接数据、ApiResponse包装、分页响应等
 */
export function normalizeApiResponse<T>(response: any): T {
  // 如果response直接就是我们需要的数据类型
  if (response && typeof response === 'object') {
    // 检查是否是ApiResponse格式
    if ('success' in response && 'data' in response) {
      return response.data as T
    }
    // 直接返回响应数据
    return response as T
  }
  
  return response as T
}

/**
 * 处理分页响应
 */
export function normalizePaginatedResponse<T>(response: any): T[] {
  // 如果是分页响应格式
  if (response?.data?.items) {
    return response.data.items as T[]
  }
  
  // 如果是ApiResponse包装的分页数据
  if (response?.data && Array.isArray(response.data)) {
    return response.data as T[]
  }
  
  // 如果直接是数组
  if (Array.isArray(response)) {
    return response as T[]
  }
  
  // 如果是单个对象，转换为数组
  if (response && typeof response === 'object') {
    return [response] as T[]
  }
  
  return [] as T[]
}

/**
 * 提取错误消息
 */
export function extractErrorMessage(error: any): string {
  // 从不同的错误响应格式中提取错误消息
  if (error?.response?.data?.message) {
    return error.response.data.message
  }
  
  if (error?.response?.data?.error) {
    return error.response.data.error
  }
  
  if (error?.response?.data?.detail) {
    return error.response.data.detail
  }
  
  if (error?.message) {
    return error.message
  }
  
  return '操作失败，请重试'
}

/**
 * 提取成功消息
 */
export function extractSuccessMessage(response: any): string {
  if (response?.message) {
    return response.message
  }
  
  if (response?.data?.message) {
    return response.data.message
  }
  
  return '操作成功'
}

/**
 * 检查响应是否成功
 */
export function isResponseSuccess(response: any): boolean {
  // 检查ApiResponse格式的success字段
  if (typeof response?.success === 'boolean') {
    return response.success
  }
  
  // 检查HTTP状态码
  if (response?.status) {
    return response.status >= 200 && response.status < 300
  }
  
  // 如果没有明确的失败标识，默认认为成功
  return true
}

/**
 * 处理API调用的通用包装器
 */
export async function handleApiCall<T>(
  apiCall: () => Promise<any>,
  options: {
    successMessage?: string
    errorMessage?: string
    showToast?: boolean
  } = {}
): Promise<T> {
  try {
    const response = await apiCall()
    
    if (options.showToast && options.successMessage) {
      const message = extractSuccessMessage(response) || options.successMessage
      // 这里可以集成toast通知
      console.log('Success:', message)
    }
    
    return normalizeApiResponse<T>(response)
  } catch (error) {
    const errorMessage = extractErrorMessage(error)
    
    if (options.showToast) {
      const message = options.errorMessage || errorMessage
      // 这里可以集成toast通知
      console.error('Error:', message)
    }
    
    throw error
  }
}