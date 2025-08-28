import { api } from '@/lib/api'
import { ApiResponse } from '@/types'

// LLM提供商类型枚举
export type ProviderType = 'openai' | 'anthropic' | 'google' | 'cohere' | 'huggingface' | 'custom'

// LLM Server 相关接口
export interface LLMServer {
  id: number
  server_id: string
  name: string
  description?: string
  base_url: string
  provider_type: ProviderType
  auth_enabled: boolean
  is_active: boolean
  is_healthy: boolean
  last_health_check?: string
  timeout_seconds: number
  max_retries: number
  server_version?: string
  created_at: string
  updated_at: string
  // 统计信息
  models_count?: number
  healthy_models_count?: number
  providers_count?: number
  total_requests?: number
  success_rate?: number
}

export interface LLMServerCreate {
  name: string
  description?: string
  base_url: string
  provider_type?: ProviderType
  api_key?: string
  auth_enabled?: boolean
  timeout_seconds?: number
  max_retries?: number
}

export interface LLMServerUpdate {
  name?: string
  description?: string
  base_url?: string
  provider_type?: ProviderType
  api_key?: string
  auth_enabled?: boolean
  is_active?: boolean
  timeout_seconds?: number
  max_retries?: number
}

// LLM Model 相关接口
export type ModelType = 'chat' | 'think' | 'embed' | 'image'

export interface LLMModel {
  id: number
  server_id: number
  name: string
  display_name: string
  description?: string
  model_type: ModelType
  provider_name: string
  is_active: boolean
  priority: number
  is_healthy: boolean
  last_health_check?: string
  health_check_message?: string
  max_tokens?: number
  temperature_default: number
  supports_system_messages: boolean
  supports_function_calls: boolean
  supports_thinking: boolean
  created_at: string
  updated_at: string
}

export interface LLMModelCreate {
  server_id: number
  name: string
  display_name: string
  description?: string
  model_type: ModelType
  provider_name: string
  priority?: number
  max_tokens?: number
  temperature_default?: number
  supports_system_messages?: boolean
  supports_function_calls?: boolean
  supports_thinking?: boolean
}

export interface LLMModelUpdate {
  display_name?: string
  description?: string
  is_active?: boolean
  priority?: number
  max_tokens?: number
  temperature_default?: number
  supports_system_messages?: boolean
  supports_function_calls?: boolean
  supports_thinking?: boolean
}

// 健康检查相关接口
export interface LLMModelHealthResponse {
  model_id: number
  model_name: string
  is_healthy: boolean
  response_time_ms: number
  test_message: string
  response_content?: string
  error_message?: string
  last_check: string
}

export interface LLMServerHealthResponse {
  server_id: number
  server_name: string
  is_healthy: boolean
  healthy_models: number
  total_models: number
  response_time_ms: number
  last_check: string
  models: LLMModelHealthResponse[]
}

export interface LLMUsageRecord {
  id: number
  record_id: string
  server_id: number
  user_id?: string
  provider_name: string
  model_name: string
  request_type: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  response_time_ms: number
  estimated_cost: number
  success: boolean
  error_message?: string
  error_type?: string
  created_at: string
}

export interface LLMUsageStats {
  period_hours: number
  total_requests: number
  successful_requests: number
  failed_requests: number
  success_rate: number
  total_tokens: number
  prompt_tokens: number
  completion_tokens: number
  total_cost: number
  avg_response_time_ms: number
  provider_stats: Record<string, any>
  model_stats: Record<string, any>
}

export interface LLMServerHealthStatus {
  server_id: number
  server_name: string
  is_healthy: boolean
  status_message: string
  response_time_ms: number
  uptime_seconds: number
  models_healthy: number
  models_total: number
  total_requests: number
  success_rate: number
  last_check: string
  model_details: Record<string, any>
}

export interface UserProfile {
  id: string
  user_id: string
  language: string
  theme: string
  email_notifications: boolean
  report_notifications: boolean
  system_notifications: boolean
  default_storage_days: number
  auto_cleanup_enabled: boolean
  default_report_format: string
  default_ai_provider?: string
  custom_css?: string
  dashboard_layout?: string
  timezone: string
  date_format: string
  created_at: string
  updated_at: string
}

export interface UserProfileUpdate {
  language?: string
  theme?: string
  email_notifications?: boolean
  report_notifications?: boolean
  system_notifications?: boolean
  default_storage_days?: number
  auto_cleanup_enabled?: boolean
  default_report_format?: string
  default_ai_provider?: string
  custom_css?: string
  dashboard_layout?: string
  timezone?: string
  date_format?: string
}


export class SettingsService {
  // 用户配置管理
  static async getUserProfile(): Promise<UserProfile> {
    const response = await api.get<ApiResponse<UserProfile>>('/settings/profile')
    if (!response.data) {
      throw new Error('Failed to get user profile')
    }
    return response.data
  }

  static async updateUserProfile(data: UserProfileUpdate): Promise<UserProfile> {
    const response = await api.patch<ApiResponse<UserProfile>>('/settings/profile', data)
    if (!response.data) {
      throw new Error('Failed to update user profile')
    }
    return response.data
  }


  // 密码管理
  static async changePassword(data: {
    current_password: string
    new_password: string
  }): Promise<void> {
    await api.post('/settings/change-password', data)
  }

  // 会话管理
  static async logoutAllDevices(): Promise<void> {
    await api.post('/settings/logout-all-devices')
  }

  // 数据导出
  static async exportAccountData(): Promise<void> {
    await api.post('/settings/export-data')
  }

  // 删除账户
  static async deleteAccount(): Promise<void> {
    await api.delete('/settings/account')
  }

  // === LLM服务器管理 ===
  
  static async getServers(params?: {
    skip?: number
    limit?: number
    is_active?: boolean
    is_healthy?: boolean
  }): Promise<LLMServer[]> {
    const response = await api.get<LLMServer[]>('/llm-servers/', { params })
    return response || []
  }

  static async getServer(id: number): Promise<LLMServer> {
    const response = await api.get<LLMServer>(`/llm-servers/${id}`)
    if (!response) {
      throw new Error('Failed to get LLM server')
    }
    return response
  }

  static async createServer(data: LLMServerCreate): Promise<LLMServer> {
    const response = await api.post<LLMServer>('/llm-servers/', data)
    if (!response) {
      throw new Error('Failed to create LLM server')
    }
    return response
  }

  static async updateServer(id: number, data: LLMServerUpdate): Promise<LLMServer> {
    const response = await api.put<LLMServer>(`/llm-servers/${id}`, data)
    if (!response) {
      throw new Error('Failed to update LLM server')
    }
    return response
  }

  static async deleteServer(id: number): Promise<void> {
    await api.delete(`/llm-servers/${id}`)
  }

  // === LLM模型管理 ===

  static async getServerModels(serverId: number, params?: {
    model_type?: ModelType
    is_active?: boolean
    provider_name?: string
  }): Promise<LLMModel[]> {
    const response = await api.get<LLMModel[]>(
      `/llm-servers/${serverId}/models`,
      { params }
    )
    return response || []
  }

  static async getAllModels(params?: {
    model_type?: ModelType
    supports_thinking?: boolean
    is_active?: boolean
  }): Promise<LLMModel[]> {
    const response = await api.get<LLMModel[]>('/llm-servers/models', { params })
    return response || []
  }

  static async getModel(serverId: number, modelId: number): Promise<LLMModel> {
    const response = await api.get<LLMModel>(`/llm-servers/${serverId}/models/${modelId}`)
    if (!response) {
      throw new Error('Failed to get LLM model')
    }
    return response
  }

  static async createModel(data: LLMModelCreate): Promise<LLMModel> {
    const response = await api.post<LLMModel>(
      `/llm-servers/${data.server_id}/models`,
      data
    )
    if (!response) {
      throw new Error('Failed to create LLM model')
    }
    return response
  }

  static async updateModel(
    serverId: number,
    modelId: number,
    data: LLMModelUpdate
  ): Promise<LLMModel> {
    const response = await api.put<LLMModel>(
      `/llm-servers/${serverId}/models/${modelId}`,
      data
    )
    if (!response) {
      throw new Error('Failed to update LLM model')
    }
    return response
  }

  static async deleteModel(serverId: number, modelId: number): Promise<void> {
    await api.delete(`/llm-servers/${serverId}/models/${modelId}`)
  }

  // === 健康检查和监控 ===

  static async checkServerHealth(serverId: number): Promise<LLMServerHealthResponse> {
    const response = await api.get<LLMServerHealthResponse>(
      `/llm-servers/${serverId}/health`
    )
    if (!response) {
      throw new Error('Failed to check server health')
    }
    return response
  }

  static async checkModelHealth(serverId: number, modelId: number, testMessage?: string): Promise<LLMModelHealthResponse> {
    const url = `/llm-servers/${serverId}/models/${modelId}/health`
    // 若未提供消息，直接无请求体调用，适配后端 Optional body
    const response = testMessage
      ? await api.post<LLMModelHealthResponse>(url, { test_message: testMessage })
      : await api.post<LLMModelHealthResponse>(url)
    if (!response) {
      throw new Error('Failed to check model health')
    }
    return response
  }

  static async healthCheckAllServers(): Promise<void> {
    await api.post('/llm-servers/health-check-all')
  }

  // === 使用统计 ===

  static async getServerUsageStats(serverId: number, hours: number = 24): Promise<LLMUsageStats> {
    const response = await api.get<LLMUsageStats>(
      `/llm-servers/${serverId}/usage`,
      { params: { hours } }
    )
    if (!response) {
      throw new Error('Failed to get usage stats')
    }
    return response
  }

  static async getServerUsageRecords(
    serverId: number,
    params?: {
      skip?: number
      limit?: number
      provider_name?: string
      model_name?: string
      success?: boolean
      start_date?: string
      end_date?: string
    }
  ): Promise<LLMUsageRecord[]> {
    const response = await api.get<LLMUsageRecord[]>(
      `/llm-servers/${serverId}/usage/records`,
      { params }
    )
    return response || []
  }

  // === 系统级统计 ===

  static async getSystemOverview(): Promise<any> {
    const response = await api.get<any>('/llm-servers/stats/overview')
    return response || {}
  }

  // === 批量操作 ===

  static async batchServerOperation(operation: string, serverIds: number[]): Promise<any> {
    const response = await api.post<any>('/llm-servers/batch', {
      operation,
      server_ids: serverIds
    })
    return response || {}
  }
}