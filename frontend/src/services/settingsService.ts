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
  id: string
  user_id: string
  name: string
  provider_type: string
  api_key: string
  api_endpoint?: string
  model_name?: string
  is_active: boolean
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface AIProviderCreate {
  name: string
  provider_type: string
  api_key: string
  api_endpoint?: string
  model_name?: string
  is_active?: boolean
}

export interface AIProviderUpdate {
  name?: string
  provider_type?: string
  api_key?: string
  api_endpoint?: string
  model_name?: string
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
    const response = await api.get<AIProvider[]>('/settings/ai-providers')
    return response.data
  }

  static async createAIProvider(data: AIProviderCreate): Promise<AIProvider> {
    const response = await api.post<AIProvider>('/settings/ai-providers', data)
    return response.data
  }

  static async updateAIProvider(id: string, data: AIProviderUpdate): Promise<AIProvider> {
    const response = await api.patch<AIProvider>(`/settings/ai-providers/${id}`, data)
    return response.data
  }

  static async deleteAIProvider(id: string): Promise<void> {
    await api.delete(`/settings/ai-providers/${id}`)
  }

  static async setDefaultAIProvider(id: string): Promise<void> {
    await api.post(`/settings/ai-providers/${id}/set-default`)
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