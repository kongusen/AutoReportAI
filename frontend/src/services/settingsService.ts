import { api } from '@/lib/api'

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

export interface AIProvider {
  id: number
  provider_name: string
  provider_type: string
  api_base_url?: string
  default_model_name?: string
  is_active: boolean
}

export interface AIProviderCreate {
  provider_name: string
  provider_type: string
  api_key: string
  api_base_url?: string
  default_model_name?: string
  is_active?: boolean
}

export interface AIProviderUpdate {
  provider_name?: string
  provider_type?: string
  api_key?: string
  api_base_url?: string
  default_model_name?: string
  is_active?: boolean
}

export class SettingsService {
  // 用户配置管理
  static async getUserProfile(): Promise<UserProfile> {
    const response = await api.get<UserProfile>('/settings/profile')
    return response.data
  }

  static async updateUserProfile(data: UserProfileUpdate): Promise<UserProfile> {
    const response = await api.patch<UserProfile>('/settings/profile', data)
    return response.data
  }

  // AI提供商管理
  static async getAIProviders(): Promise<AIProvider[]> {
    console.log('正在请求AI提供商列表...')
    const response = await api.get('/ai-providers/')
    console.log('API响应:', response)
    // api.get已经返回了response.data，所以这里的response就是后端的ApiResponse
    const items = response.data?.items || []
    console.log('提取的items:', items)
    return items // 从PaginatedResponse中提取items
  }

  static async createAIProvider(data: AIProviderCreate): Promise<AIProvider> {
    const response = await api.post('/ai-providers/', data)
    return response.data // api.post已经返回了response.data，这里的response是ApiResponse
  }

  static async updateAIProvider(id: string, data: AIProviderUpdate): Promise<AIProvider> {
    const response = await api.put(`/ai-providers/${id}`, data)
    return response.data // 从ApiResponse中提取data字段
  }

  static async deleteAIProvider(id: string): Promise<void> {
    await api.delete(`/ai-providers/${id}`)
  }

  static async testAIProvider(id: string): Promise<any> {
    const response = await api.post(`/ai-providers/${id}/test`)
    return response.data // 从ApiResponse中提取data字段
  }

  static async enableAIProvider(id: string): Promise<AIProvider> {
    const response = await api.post(`/ai-providers/${id}/enable`)
    return response.data // 从ApiResponse中提取data字段
  }

  static async disableAIProvider(id: string): Promise<AIProvider> {
    const response = await api.post(`/ai-providers/${id}/disable`)
    return response.data // 从ApiResponse中提取data字段
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
}