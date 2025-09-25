/**
 * Agent API服务
 * 适配新的稳定别名路由和弃用接口处理
 */

import { api } from '@/lib/api'

export interface AgentTaskRequest {
  task_description: string
  context_data?: Record<string, any>
  coordination_mode?: 'intelligent' | 'standard' | 'simple'
  enable_streaming?: boolean
  sql_preview?: boolean
  template_id?: string
  data_source_id?: string
}

export interface AgentRunRequest {
  user_id?: string
  template_id: string
  data_source_id: string
  placeholder_name: string
  task_definition?: Record<string, any>
  output_kind?: 'sql' | 'chart' | 'report'
  sql_only?: boolean
  overrides?: Record<string, any>
  force_refresh?: boolean
  enable_observations?: boolean
}

export interface AgentRunResponse {
  success: boolean
  result?: string
  metadata?: Record<string, any>
  context_id?: string
  stage?: string
  observations?: string[]
  dynamic_user_prompt?: string
  available_tools?: Array<Record<string, string>>
  error?: string
  warnings?: string[]
  execution_time_ms?: number
  request_id: string
}

export interface AgentModel {
  id: string
  server_name: string
  model_name: string
  display_name: string
  model_type: string
  is_active: boolean
  is_healthy: boolean
  priority: number
  provider_name: string
}

export interface AgentModelsResponse {
  models: AgentModel[]
  total: number
  default_model?: string
}

export interface AgentHealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  checks: Record<string, Record<string, any>>
  timestamp: string
}

export interface AsyncTaskResponse {
  success: boolean
  task_id?: string
  error?: string
  status_url?: string
  stream_url?: string
}

export interface TaskStatusResponse {
  task_id: string
  status: string
  progress: number
  current_step: string
  created_at: string
  updated_at: string
  result?: Record<string, any>
  error?: string
}

/**
 * Agent服务类
 * 使用稳定的/api/agent/*别名路由（无版本号）
 */
export class AgentService {
  private static readonly BASE_PATH = '/agent' // 使用新的无版本别名路径

  /**
   * 获取Agent健康状态
   */
  static async getHealth(): Promise<AgentHealthResponse> {
    return api.get(`${this.BASE_PATH}/health`)
  }

  /**
   * 获取可用模型列表
   */
  static async getModels(): Promise<AgentModelsResponse> {
    return api.get(`${this.BASE_PATH}/models`)
  }

  /**
   * 同步执行Agent任务（完整版）
   */
  static async run(request: AgentRunRequest): Promise<AgentRunResponse> {
    return api.post(`${this.BASE_PATH}/run`, request)
  }

  /**
   * 启动异步Agent任务
   */
  static async runAsync(request: AgentRunRequest): Promise<AsyncTaskResponse> {
    return api.post(`${this.BASE_PATH}/run-async`, request)
  }

  /**
   * 获取异步任务状态
   */
  static async getAsyncTaskStatus(taskId: string): Promise<TaskStatusResponse> {
    return api.get(`${this.BASE_PATH}/run-async/${taskId}/status`)
  }

  /**
   * 创建异步任务的SSE流
   */
  static createAsyncTaskStream(taskId: string, token: string): EventSource {
    const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'}${this.BASE_PATH}/run-async/${taskId}/stream`

    return new EventSource(url, {
      withCredentials: true,
      headers: {
        'Authorization': `Bearer ${token}`,
      } as any
    })
  }

  /**
   * 取消异步任务
   */
  static async cancelAsyncTask(taskId: string): Promise<{ success: boolean; message: string }> {
    return api.delete(`${this.BASE_PATH}/run-async/${taskId}`)
  }

  /**
   * 获取异步系统状态
   */
  static async getAsyncSystemStatus(): Promise<{
    active_tasks: number
    max_active_tasks: number
    status_breakdown: Record<string, number>
    system_healthy: boolean
  }> {
    return api.get(`${this.BASE_PATH}/system/async-status`)
  }

  /**
   * 处理弃用接口的优雅降级
   * 自动处理410响应并提供迁移指导
   */
  static async handleDeprecatedEndpoint<T>(
    deprecatedPath: string,
    modernAlternative: () => Promise<T>,
    options: {
      showWarning?: boolean
      onDeprecationDetected?: (info: {
        endpoint: string
        message?: string
        replacement?: Record<string, string>
      }) => void
    } = {}
  ): Promise<T> {
    try {
      // 尝试现代接口
      return await modernAlternative()
    } catch (error: any) {
      // 如果是410错误（弃用接口），显示迁移提示
      if (error?.response?.status === 410) {
        const isDeprecated = error.response.headers?.['x-deprecated'] === 'true'
        const deprecationInfo = error.response.data

        if (options.showWarning !== false) {
          console.warn(`⚠️ API Deprecation Warning:`, {
            endpoint: deprecatedPath,
            deprecated: isDeprecated,
            message: deprecationInfo?.message,
            replacement: deprecationInfo?.replacement
          })
        }

        // 通知前端组件有弃用接口被调用
        if (options.onDeprecationDetected && isDeprecated) {
          options.onDeprecationDetected({
            endpoint: deprecatedPath,
            message: deprecationInfo?.message,
            replacement: deprecationInfo?.replacement
          })
        }

        // 对于已知的弃用接口，提供用户友好的错误信息
        throw new Error(`接口已升级：${deprecationInfo?.message || '请使用新的API接口'}`)
      }

      throw error
    }
  }

  /**
   * 向后兼容方法：执行流式任务（旧接口迁移）
   * 自动重定向到新的异步+流式架构
   */
  static async executeStreamCompat(request: AgentTaskRequest): Promise<AsyncTaskResponse> {
    return this.handleDeprecatedEndpoint(
      '/api/v1/agent/execute-stream',
      async () => {
        // 转换为新的AgentRunRequest格式
        const modernRequest: AgentRunRequest = {
          template_id: request.template_id || 'default-template',
          data_source_id: request.data_source_id || 'default-datasource',
          placeholder_name: 'main_content',
          task_definition: {
            description: request.task_description,
            ...request.context_data
          },
          output_kind: 'sql',
          sql_only: false,
          force_refresh: true,
          enable_observations: true
        }

        // 使用新的异步接口
        return await this.runAsync(modernRequest)
      }
    )
  }

  /**
   * 向后兼容方法：执行任务（旧接口迁移）
   */
  static async executeCompat(request: AgentTaskRequest): Promise<AgentRunResponse> {
    return this.handleDeprecatedEndpoint(
      '/api/v1/agent/execute',
      async () => {
        const modernRequest: AgentRunRequest = {
          template_id: request.template_id || 'default-template',
          data_source_id: request.data_source_id || 'default-datasource',
          placeholder_name: 'main_content',
          task_definition: {
            description: request.task_description,
            ...request.context_data
          },
          output_kind: 'sql',
          sql_only: false
        }

        return await this.run(modernRequest)
      }
    )
  }

  /**
   * 向后兼容方法：获取任务状态（旧接口迁移）
   */
  static async getTaskStatusCompat(taskId: string): Promise<TaskStatusResponse> {
    return this.handleDeprecatedEndpoint(
      `/api/v1/agent/status/${taskId}`,
      () => this.getAsyncTaskStatus(taskId)
    )
  }

  /**
   * 向后兼容方法：获取协调器状态（旧接口迁移）
   */
  static async getCoordinatorStatusCompat(): Promise<any> {
    return this.handleDeprecatedEndpoint(
      '/api/v1/agent/coordinator/status',
      () => this.getAsyncSystemStatus()
    )
  }
}

export default AgentService