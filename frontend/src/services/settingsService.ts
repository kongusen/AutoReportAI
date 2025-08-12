import { api } from '@/lib/api'
import { ApiResponse, AIProvider } from '@/types'

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

  // AI提供商管理
  static async getAIProviders(): Promise<AIProvider[]> {
    console.log('正在请求AI提供商列表...')
    const response = await api.get('/ai-providers/')
    console.log('API响应:', response)
    
    // 处理不同的响应格式
    let items: AIProvider[] = []
    
    if (response.data) {
      // 如果是ApiResponse格式
      if (Array.isArray(response.data)) {
        items = response.data
      } else if (response.data.items && Array.isArray(response.data.items)) {
        // 如果是分页格式
        items = response.data.items
      } else if (response.data.data && Array.isArray(response.data.data)) {
        // 如果是嵌套data格式
        items = response.data.data
      }
    } else if (Array.isArray(response)) {
      // 如果直接返回数组
      items = response
    }
    
    console.log('提取的items:', items)
    return items
  }

  static async createAIProvider(data: AIProviderCreate): Promise<AIProvider> {
    const response = await api.post<ApiResponse<AIProvider>>('/ai-providers/', data)
    if (!response.data) {
      throw new Error('Failed to create AI provider')
    }
    return response.data
  }

  static async updateAIProvider(id: string, data: AIProviderUpdate): Promise<AIProvider> {
    const response = await api.put<ApiResponse<AIProvider>>(`/ai-providers/${id}`, data)
    if (!response.data) {
      throw new Error('Failed to update AI provider')
    }
    return response.data
  }

  static async deleteAIProvider(id: string): Promise<void> {
    await api.delete(`/ai-providers/${id}`)
  }

  static async testAIProvider(id: string): Promise<any> {
    const response = await api.post<ApiResponse<any>>(`/ai-providers/${id}/test`)
    return response.data || {}
  }

  static async enableAIProvider(id: string): Promise<AIProvider> {
    const response = await api.post<ApiResponse<AIProvider>>(`/ai-providers/${id}/enable`)
    if (!response.data) {
      throw new Error('Failed to enable AI provider')
    }
    return response.data
  }

  static async disableAIProvider(id: string): Promise<AIProvider> {
    const response = await api.post<ApiResponse<AIProvider>>(`/ai-providers/${id}/disable`)
    if (!response.data) {
      throw new Error('Failed to disable AI provider')
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
}