/**
 * API适配器 - 前端与新后端接口的适配层
 * 支持新的APIResponse格式和错误处理
 */

import { api } from '@/lib/api'
import toast from 'react-hot-toast'

// 新的API响应格式
interface APIResponse<T = any> {
  success: boolean
  data: T
  message: string
  errors?: Array<{
    field?: string
    message: string
  }>
  warnings?: string[]
}

// 前端数据格式
interface FrontendChartData {
  echartsConfig: any
  chartType: string
  chartData: any[]
  metadata?: {
    data_points?: number
    chart_elements?: any
    data_summary?: any
    generation_time?: string
    data_source?: {
      sql_query?: string
      execution_time_ms?: number
      row_count?: number
      data_quality_score?: number
    }
  }
  title?: string
}

interface PlaceholderDisplayInfo {
  text: string
  kind: string
  display_name: string
  description?: string
  status: string
  confidence?: number
  needs_reanalysis: boolean
  badge_color: string
  icon?: string
  tooltip?: string
}

interface AnalysisProgressInfo {
  current_step: number
  total_steps: number
  step_name: string
  progress_percent: number
  status: string
  estimated_remaining?: number
  steps: Array<{
    name: string
    description: string
    status: string
  }>
}

interface ErrorDisplayInfo {
  error_code: string
  error_message: string
  user_friendly_message: string
  error_type: string
  severity: string
  details?: any
  suggestions: string[]
  support_info?: {
    contact: string
    documentation: string
    status_page: string
  }
}

// API适配器类
export class APIAdapter {
  /**
   * 模板占位符分析 - 适配新的后端接口
   */
  static async analyzeTemplatePlaceholders(
    templateId: string,
    dataSourceId: string,
    options: {
      forceReanalyze?: boolean
      optimizationLevel?: string
      targetExpectations?: any
    } = {}
  ): Promise<{
    success: boolean
    data?: {
      items: PlaceholderDisplayInfo[]
      stats: {
        total: number
        need_reanalysis: number
        by_kind: Record<string, number>
      }
      task_id?: string
    }
    progress?: AnalysisProgressInfo
    error?: ErrorDisplayInfo
  }> {
    try {
      const response: APIResponse = await api.post(
        `/templates/${templateId}/analyze`,
        {
          target_expectations: options.targetExpectations
        },
        {
          params: {
            data_source_id: dataSourceId,
            force_reanalyze: options.forceReanalyze || false,
            optimization_level: options.optimizationLevel || 'enhanced'
          }
        }
      )

      if (response.success) {
        return {
          success: true,
          data: response.data,
          progress: response.data.progress
        }
      } else {
        return {
          success: false,
          error: response.data as ErrorDisplayInfo
        }
      }
    } catch (error: any) {
      console.error('Template analysis failed:', error)
      return {
        success: false,
        error: {
          error_code: 'template_analysis_failed',
          error_message: error.message || '模板分析失败',
          user_friendly_message: '模板分析过程中出现错误，请稍后重试',
          error_type: 'system',
          severity: 'error',
          suggestions: ['检查网络连接', '稍后重试', '联系技术支持']
        }
      }
    }
  }

  /**
   * 图表测试 - 适配新的图表测试接口
   */
  static async testChartGeneration(
    placeholderId: string,
    dataSourceId: string,
    executionMode: 'sql_only' | 'test_with_chart' = 'test_with_chart'
  ): Promise<{
    success: boolean
    data?: FrontendChartData | any
    error?: ErrorDisplayInfo
  }> {
    try {
      const response: APIResponse = await api.post(
        `/chart-test/placeholders/${placeholderId}/test-chart`,
        {
          data_source_id: dataSourceId,
          execution_mode: executionMode
        }
      )

      if (response.success) {
        // 如果返回的是图表数据，确保格式正确
        if (response.data.echartsConfig) {
          return {
            success: true,
            data: response.data as FrontendChartData
          }
        } else {
          // 处理非图表响应
          return {
            success: true,
            data: response.data
          }
        }
      } else {
        return {
          success: false,
          error: response.data as ErrorDisplayInfo
        }
      }
    } catch (error: any) {
      console.error('Chart test failed:', error)
      return {
        success: false,
        error: {
          error_code: 'chart_test_failed',
          error_message: error.message || '图表测试失败',
          user_friendly_message: '图表生成过程中出现错误，请检查配置后重试',
          error_type: 'system',
          severity: 'error',
          suggestions: ['检查占位符配置', '验证数据源连接', '联系技术支持']
        }
      }
    }
  }

  /**
   * 占位符管理 - 获取占位符列表
   */
  static async getPlaceholders(
    templateId?: string,
    skip: number = 0,
    limit: number = 100
  ): Promise<{
    success: boolean
    data?: PlaceholderDisplayInfo[]
    error?: ErrorDisplayInfo
  }> {
    try {
      const params: any = { skip, limit }
      if (templateId) {
        params.template_id = templateId
      }

      const response: APIResponse = await api.get('/placeholders', {
        params
      })

      if (response.success) {
        return {
          success: true,
          data: response.data as PlaceholderDisplayInfo[]
        }
      } else {
        return {
          success: false,
          error: response.data as ErrorDisplayInfo
        }
      }
    } catch (error: any) {
      console.error('Failed to get placeholders:', error)
      return {
        success: false,
        error: {
          error_code: 'get_placeholders_failed',
          error_message: error.message || '获取占位符列表失败',
          user_friendly_message: '无法获取占位符列表，请刷新页面重试',
          error_type: 'system',
          severity: 'error',
          suggestions: ['刷新页面', '检查网络连接', '联系技术支持']
        }
      }
    }
  }

  /**
   * 占位符分析 - 使用Agent Pipeline
   */
  static async analyzeePlaceholder(
    placeholderName: string,
    placeholderText: string,
    templateId: string,
    dataSourceId?: string,
    options: {
      templateContext?: any
      timeColumn?: string
      dataRange?: string
      requirements?: string
    } = {}
  ): Promise<{
    success: boolean
    data?: {
      placeholder: PlaceholderDisplayInfo
      progress: AnalysisProgressInfo
      analysis_result: any
      generated_sql: any
    }
    error?: ErrorDisplayInfo
  }> {
    try {
      const response: APIResponse = await api.post('/placeholders/analyze', {
        placeholder_name: placeholderName,
        placeholder_text: placeholderText,
        template_id: templateId,
        data_source_id: dataSourceId,
        template_context: options.templateContext,
        time_column: options.timeColumn,
        data_range: options.dataRange,
        requirements: options.requirements
      })

      if (response.success) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: response.data as ErrorDisplayInfo
        }
      }
    } catch (error: any) {
      console.error('Placeholder analysis failed:', error)
      return {
        success: false,
        error: {
          error_code: 'placeholder_analysis_failed',
          error_message: error.message || '占位符分析失败',
          user_friendly_message: '占位符分析过程中出现错误，请检查输入后重试',
          error_type: 'system',
          severity: 'error',
          suggestions: ['检查占位符格式', '验证模板ID', '联系技术支持']
        }
      }
    }
  }

  /**
   * WebSocket管理 - 获取任务状态
   */
  static async getTaskStatus(taskId: string): Promise<{
    success: boolean
    data?: {
      task_id: string
      task_type: string
      status: string
      progress: number
      message: string
      started_at?: string
      completed_at?: string
    }
    error?: ErrorDisplayInfo
  }> {
    try {
      const response: APIResponse = await api.get(`/pipeline/ws/tasks/${taskId}/status`)

      if (response.success) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: response.data as ErrorDisplayInfo
        }
      }
    } catch (error: any) {
      console.error('Failed to get task status:', error)
      return {
        success: false,
        error: {
          error_code: 'task_status_failed',
          error_message: error.message || '获取任务状态失败',
          user_friendly_message: '无法获取任务状态，请稍后重试',
          error_type: 'system',
          severity: 'error',
          suggestions: ['稍后重试', '检查任务ID', '联系技术支持']
        }
      }
    }
  }

  /**
   * WebSocket管理 - 订阅任务更新
   */
  static async subscribeToTask(taskId: string): Promise<{
    success: boolean
    data?: {
      task_id: string
      user_id: string
      subscribed: boolean
    }
    error?: ErrorDisplayInfo
  }> {
    try {
      const response: APIResponse = await api.post(`/pipeline/ws/tasks/${taskId}/subscribe`)

      if (response.success) {
        return {
          success: true,
          data: response.data
        }
      } else {
        return {
          success: false,
          error: response.data as ErrorDisplayInfo
        }
      }
    } catch (error: any) {
      console.error('Failed to subscribe to task:', error)
      return {
        success: false,
        error: {
          error_code: 'task_subscribe_failed',
          error_message: error.message || '订阅任务失败',
          user_friendly_message: '无法订阅任务更新，请稍后重试',
          error_type: 'system',
          severity: 'error',
          suggestions: ['稍后重试', '检查任务ID', '联系技术支持']
        }
      }
    }
  }

  /**
   * 用户友好的错误处理
   */
  static handleError(error: ErrorDisplayInfo): void {
    // 显示用户友好的错误消息
    toast.error(error.user_friendly_message)

    // 在开发环境显示详细错误信息
    if (process.env.NODE_ENV === 'development') {
      console.error('API Error Details:', error)
    }

    // 根据错误类型提供特定建议
    if (error.suggestions.length > 0) {
      error.suggestions.slice(0, 2).forEach(suggestion => {
        toast(suggestion, { icon: '💡', duration: 4000 })
      })
    }
  }

  /**
   * 显示成功消息
   */
  static handleSuccess(message: string): void {
    toast.success(message)
  }
}

// 导出类型定义
export type {
  APIResponse,
  FrontendChartData,
  PlaceholderDisplayInfo,
  AnalysisProgressInfo,
  ErrorDisplayInfo
}

// 默认导出
export default APIAdapter