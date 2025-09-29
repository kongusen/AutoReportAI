/**
 * 前端基础API服务 - DDD架构v2.0
 * 与后端DDD架构对齐的前端服务基类
 */

import { AxiosResponse } from 'axios'
import toast from 'react-hot-toast'
import { APIResponse, ApplicationResult, OperationResult } from '@/types/api'

/**
 * 基础API服务类
 * 提供统一的错误处理、类型安全和DDD架构对齐
 */
export abstract class BaseApiService {
  protected serviceName: string

  constructor(serviceName: string) {
    this.serviceName = serviceName
  }

  /**
   * 处理API响应 - DDD架构v2.0兼容
   * @param response Axios响应
   * @returns 处理后的API响应
   */
  protected handleApiResponse<T>(response: AxiosResponse<APIResponse<T>>): APIResponse<T> {
    const apiResponse = response.data

    // 验证响应格式
    if (!apiResponse || typeof apiResponse !== 'object') {
      throw new Error(`Invalid API response format from ${this.serviceName}`)
    }

    // 处理业务逻辑错误
    if (!apiResponse.success) {
      this.handleBusinessErrors(apiResponse)
    }

    // 处理警告
    if (apiResponse.warnings && apiResponse.warnings.length > 0) {
      this.handleWarnings(apiResponse.warnings)
    }

    return apiResponse
  }

  /**
   * 处理应用结果 - 对应后端ApplicationResult
   * @param appResult 应用结果
   * @returns 处理后的结果
   */
  protected handleApplicationResult<T>(appResult: ApplicationResult<T>): T | null {
    // 记录执行时间（如果有）
    if (appResult.execution_time_ms && process.env.NODE_ENV === 'development') {
      console.debug(`${this.serviceName} execution time: ${appResult.execution_time_ms}ms`)
    }

    // 处理不同的操作结果
    switch (appResult.result) {
      case OperationResult.SUCCESS:
        if (appResult.warnings.length > 0) {
          this.handleWarnings(appResult.warnings)
        }
        return appResult.data || null

      case OperationResult.VALIDATION_ERROR:
        this.handleValidationErrors(appResult.errors)
        throw new Error(`Validation failed: ${appResult.message}`)

      case OperationResult.NOT_FOUND:
        this.handleNotFoundError(appResult.message)
        throw new Error(`Resource not found: ${appResult.message}`)

      case OperationResult.PERMISSION_DENIED:
        this.handlePermissionError(appResult.message)
        throw new Error(`Permission denied: ${appResult.message}`)

      case OperationResult.PARTIAL_SUCCESS:
        this.handlePartialSuccess(appResult.warnings, appResult.errors)
        return appResult.data || null

      case OperationResult.FAILURE:
      default:
        this.handleBusinessFailure(appResult.errors)
        throw new Error(`Operation failed: ${appResult.message}`)
    }
  }

  /**
   * 处理业务逻辑错误
   * @param apiResponse API响应
   */
  private handleBusinessErrors(apiResponse: APIResponse<any>): void {
    const errorMessage = apiResponse.message || 'Operation failed'
    const errors = apiResponse.errors || []

    // 显示主要错误消息
    toast.error(errorMessage)

    // 在开发环境显示详细错误
    if (process.env.NODE_ENV === 'development' && errors.length > 0) {
      console.error(`${this.serviceName} errors:`, errors)
    }
  }

  /**
   * 处理验证错误
   * @param errors 错误列表
   */
  private handleValidationErrors(errors: string[]): void {
    const message = errors.length > 0 ? errors[0] : 'Validation failed'
    toast.error(`Validation Error: ${message}`)
    
    if (process.env.NODE_ENV === 'development') {
      console.error(`${this.serviceName} validation errors:`, errors)
    }
  }

  /**
   * 处理未找到错误
   * @param message 错误消息
   */
  private handleNotFoundError(message: string): void {
    toast.error(`Not Found: ${message}`)
  }

  /**
   * 处理权限错误
   * @param message 错误消息
   */
  private handlePermissionError(message: string): void {
    toast.error(`Access Denied: ${message}`)
    
    // 可能需要重定向到登录页
    if (message.includes('authentication') || message.includes('token')) {
      // 这里可以触发登录重定向
      console.warn('Authentication required, consider redirecting to login')
    }
  }

  /**
   * 处理部分成功
   * @param warnings 警告列表
   * @param errors 错误列表
   */
  private handlePartialSuccess(warnings: string[], errors: string[]): void {
    if (warnings.length > 0) {
      toast.success(`Completed with warnings: ${warnings[0]}`)
    }
    
    if (errors.length > 0) {
      toast.error(`Some operations failed: ${errors[0]}`)
    }
  }

  /**
   * 处理业务失败
   * @param errors 错误列表
   */
  private handleBusinessFailure(errors: string[]): void {
    const message = errors.length > 0 ? errors[0] : 'Operation failed'
    toast.error(message)
  }

  /**
   * 处理警告
   * @param warnings 警告列表
   */
  private handleWarnings(warnings: string[]): void {
    if (warnings.length > 0 && process.env.NODE_ENV === 'development') {
      console.warn(`${this.serviceName} warnings:`, warnings)
      
      // 在开发环境显示第一个警告
      toast(`Warning: ${warnings[0]}`)
    }
  }

  /**
   * 处理网络错误
   * @param error 错误对象
   */
  protected handleNetworkError(error: any): never {
    let message = 'Network error occurred'
    
    if (error.response) {
      // HTTP错误状态码
      const status = error.response.status
      switch (status) {
        case 400:
          message = 'Bad request - please check your input'
          break
        case 401:
          message = 'Authentication required - please log in'
          break
        case 403:
          message = 'Access forbidden - insufficient permissions'
          break
        case 404:
          message = 'Resource not found'
          break
        case 429:
          message = 'Too many requests - please try again later'
          break
        case 500:
          message = 'Server error - please try again later'
          break
        case 502:
        case 503:
        case 504:
          message = 'Service unavailable - please try again later'
          break
        default:
          message = `HTTP ${status}: ${error.response.statusText || 'Unknown error'}`
      }
    } else if (error.request) {
      // 网络连接问题
      message = 'Network connection failed - please check your internet connection'
    } else {
      // 其他错误
      message = error.message || 'An unexpected error occurred'
    }

    toast.error(message)
    
    if (process.env.NODE_ENV === 'development') {
      console.error(`${this.serviceName} network error:`, error)
    }

    throw new Error(message)
  }

  /**
   * 记录操作
   * @param operation 操作名称
   * @param params 参数
   */
  protected logOperation(operation: string, params?: Record<string, any>): void {
    if (process.env.NODE_ENV === 'development') {
      console.debug(`${this.serviceName}.${operation}`, params || {})
    }
  }

  /**
   * 验证必需参数
   * @param params 参数对象
   * @throws 如果有缺失的必需参数
   */
  protected validateRequiredParams(params: Record<string, any>): void {
    const missingParams: string[] = []
    
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === '') {
        missingParams.push(key)
      }
    }
    
    if (missingParams.length > 0) {
      const message = `Missing required parameters: ${missingParams.join(', ')}`
      toast.error(message)
      throw new Error(message)
    }
  }
}

/**
 * 分页API服务基类
 */
export abstract class PaginatedApiService extends BaseApiService {
  /**
   * 构建分页参数
   * @param page 页码
   * @param size 页面大小
   * @param filters 过滤参数
   */
  protected buildPaginationParams(
    page: number = 1, 
    size: number = 20, 
    filters?: Record<string, any>
  ): Record<string, any> {
    const params: Record<string, any> = {
      page: Math.max(1, page),
      size: Math.min(Math.max(1, size), 100) // 限制最大页面大小
    }
    
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params[key] = value
        }
      })
    }
    
    return params
  }
}

export default BaseApiService