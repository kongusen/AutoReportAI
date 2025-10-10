/**
 * 任务API服务 - DDD架构v2.0
 * 对应后端 TaskApplicationService
 */

import { AxiosResponse } from 'axios'
import { BaseApiService, PaginatedApiService } from './baseApiService'
import { apiClientV1 as apiClient } from '@/lib/api'
import { APIResponse, PaginatedResponse } from '@/types/api'
// 统一使用与后端一致的Task类型定义
import { Task, ProcessingMode, AgentWorkflowType, ReportPeriod } from '@/types'

export interface TaskCreateRequest {
  name: string
  description?: string
  template_id: string
  data_source_id: string
  schedule?: string
  report_period?: ReportPeriod
  recipients?: string[]
  is_active?: boolean
  processing_mode?: ProcessingMode
  workflow_type?: AgentWorkflowType
  max_context_tokens?: number
  enable_compression?: boolean
}

export interface TaskUpdateRequest extends Partial<TaskCreateRequest> {
  id: number
}

export interface TaskExecutionRequest {
  task_id: number
  execution_context?: Record<string, any>
}

export interface TaskAnalysisResult {
  task_info: {
    id: number
    name: string
    status: string
  }
  execution_requirements: {
    complexity: string
    execution_strategy: string
    resource_requirements: Record<string, any>
    dependencies: Record<string, any>
    estimated_duration: Record<string, any>
    business_priority: string
    risk_assessment: Record<string, any>
  }
  feasibility_check: {
    is_feasible: boolean
    blocking_issues: string[]
    warnings: string[]
    recommendations: string[]
  }
  placeholder_analysis?: Record<string, any>
  recommendations: string[]
  estimated_agents_needed: string[]
}

export interface TaskExecutionResult {
  task_id: number
  execution_plan_id: string
  overall_success: boolean
  step_results: Array<{
    step_id: string
    success: boolean
    agents_used: string[]
    execution_time: number
    output: Record<string, any>
    errors: string[]
  }>
  execution_summary: {
    total_steps: number
    successful_steps: number
    failed_steps: number
  }
  agents_used: string[]
}

/**
 * 任务API服务类
 * 与后端TaskApplicationService对应的前端服务
 */
export class TasksApiService extends PaginatedApiService {
  constructor() {
    super('TasksApiService')
  }

  /**
   * 获取任务列表
   * @param params 查询参数
   */
  async getTasks(params: {
    page?: number
    size?: number
    is_active?: boolean
    search?: string
  } = {}): Promise<PaginatedResponse<Task>> {
    try {
      this.logOperation('getTasks', params)
      
      const queryParams = this.buildPaginationParams(
        params.page, 
        params.size, 
        {
          is_active: params.is_active,
          search: params.search
        }
      )

      const response: AxiosResponse<any> = await apiClient.get('/tasks', { params: queryParams })
      // 后端返回 PaginatedAPIResponse: { success, data: Task[], pagination }
      const payload = response.data
      if (payload && payload.success && Array.isArray(payload.data) && payload.pagination) {
        const p = payload.pagination
        return {
          items: payload.data as Task[],
          total: p.total,
          page: p.page,
          size: p.size,
          pages: p.pages,
          has_next: p.has_next,
          has_prev: p.has_prev
        }
      }

      // 兼容旧格式或异常情况
      if (Array.isArray(payload?.data)) {
        return { items: payload.data as Task[], total: payload.data.length, page: 1, size: payload.data.length, pages: 1, has_next: false, has_prev: false }
      }

      return { items: [], total: 0, page: 1, size: 20, pages: 0, has_next: false, has_prev: false }
    } catch (error) {
      this.handleNetworkError(error)
    }
  }

  /**
   * 创建任务
   * @param taskData 任务数据
   */
  async createTask(taskData: TaskCreateRequest): Promise<Task> {
    try {
      this.logOperation('createTask', { name: taskData.name })
      
      this.validateRequiredParams({
        name: taskData.name,
        template_id: taskData.template_id,
        data_source_id: taskData.data_source_id
      })

      const response: AxiosResponse<APIResponse<Task>> = 
        await apiClient.post('/tasks', taskData)

      const apiResponse = this.handleApiResponse(response)
      
      if (!apiResponse.data) {
        throw new Error('No task data returned from server')
      }

      return apiResponse.data
    } catch (error) {
      this.handleNetworkError(error)
    }
  }

  /**
   * 更新任务
   * @param taskData 任务更新数据
   */
  async updateTask(taskData: TaskUpdateRequest): Promise<Task> {
    try {
      this.logOperation('updateTask', { id: taskData.id })
      
      this.validateRequiredParams({ id: taskData.id })

      const { id, ...updateData } = taskData
      const response: AxiosResponse<APIResponse<Task>> = 
        await apiClient.put(`/tasks/${id}`, updateData)

      const apiResponse = this.handleApiResponse(response)
      
      if (!apiResponse.data) {
        throw new Error('No task data returned from server')
      }

      return apiResponse.data
    } catch (error) {
      this.handleNetworkError(error)
    }
  }

  /**
   * 删除任务
   * @param taskId 任务ID
   */
  async deleteTask(taskId: number): Promise<boolean> {
    try {
      this.logOperation('deleteTask', { taskId })
      
      this.validateRequiredParams({ taskId })

      const response: AxiosResponse<APIResponse<boolean>> = 
        await apiClient.delete(`/tasks/${taskId}`)

      const apiResponse = this.handleApiResponse(response)
      return apiResponse.data || false
    } catch (error) {
      this.handleNetworkError(error)
    }
  }

  /**
   * 获取任务详情
   * @param taskId 任务ID
   */
  async getTask(taskId: number): Promise<Task> {
    try {
      this.logOperation('getTask', { taskId })
      
      this.validateRequiredParams({ taskId })

      const response: AxiosResponse<APIResponse<Task>> = 
        await apiClient.get(`/tasks/${taskId}`)

      const apiResponse = this.handleApiResponse(response)
      
      if (!apiResponse.data) {
        throw new Error('Task not found')
      }

      return apiResponse.data
    } catch (error) {
      this.handleNetworkError(error)
    }
  }

  /**
   * 使用领域服务分析任务 - DDD架构v2.0新功能
   * @param taskId 任务ID
   */
  async analyzeTaskWithDomainServices(_taskId: number): Promise<TaskAnalysisResult> {
    // 后端未实现 /tasks/{id}/analyze，标记为未实现，避免误用
    throw new Error('analyzeTaskWithDomainServices is not available: backend endpoint is not implemented')
  }

  /**
   * 通过agents执行任务 - DDD架构v2.0新功能
   * @param executionData 执行数据
   */
  async executeTaskThroughAgents(_executionData: TaskExecutionRequest): Promise<TaskExecutionResult> {
    // 后端未实现 /tasks/{id}/execute-agents，标记为未实现，避免误用
    throw new Error('executeTaskThroughAgents is not available: backend endpoint is not implemented')
  }

  /**
   * 立即执行任务 - 传统方式
   * @param executionData 执行数据
   */
  async executeTaskImmediately(executionData: TaskExecutionRequest): Promise<any> {
    try {
      this.logOperation('executeTaskImmediately', { taskId: executionData.task_id })
      
      this.validateRequiredParams({ task_id: executionData.task_id })

      const response: AxiosResponse<APIResponse<any>> = 
        await apiClient.post(`/tasks/${executionData.task_id}/execute`, {
          execution_context: executionData.execution_context
        })

      const apiResponse = this.handleApiResponse(response)
      return apiResponse.data
    } catch (error) {
      this.handleNetworkError(error)
    }
  }

  /**
   * 验证任务占位符
   * @param taskId 任务ID
   */
  async validateTaskPlaceholders(taskId: number): Promise<any> {
    try {
      this.logOperation('validateTaskPlaceholders', { taskId })
      
      this.validateRequiredParams({ taskId })

      const response: AxiosResponse<APIResponse<any>> = 
        await apiClient.post(`/tasks/${taskId}/validate`)

      const apiResponse = this.handleApiResponse(response)
      return apiResponse.data
    } catch (error) {
      this.handleNetworkError(error)
    }
  }

  /**
   * 设置任务调度
   * @param taskId 任务ID
   * @param schedule 调度表达式
   */
  async scheduleTask(taskId: number, schedule: string): Promise<any> {
    try {
      this.logOperation('scheduleTask', { taskId, schedule })
      
      this.validateRequiredParams({ taskId, schedule })

      // 后端使用 Query 参数接收 schedule，需放在 params 中
      const response: AxiosResponse<APIResponse<any>> = 
        await apiClient.post(`/tasks/${taskId}/schedule`, undefined as any, { params: { schedule } })

      const apiResponse = this.handleApiResponse(response)
      return apiResponse.data
    } catch (error) {
      this.handleNetworkError(error)
    }
  }
}

// 创建单例实例
export const tasksApiService = new TasksApiService()
export default tasksApiService
