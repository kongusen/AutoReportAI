'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Switch } from '@/components/ui/Switch'
import { Select } from '@/components/ui/Select'
import { Card } from '@/components/ui/Card'
import toast from 'react-hot-toast'
import { SettingsService } from '@/services/apiService'
import { LLMServer, LLMProvider } from '@/types/api'

interface LLMServerCreate {
  name: string
  base_url: string
  api_key?: string
  provider: LLMProvider
  description?: string
  is_active: boolean
  auth_enabled?: boolean
  timeout_seconds?: number
  max_retries?: number
}

interface LLMServerFormProps {
  server?: LLMServer
  onSubmit?: (server: LLMServer) => void
  onCancel?: () => void
  mode?: 'create' | 'edit'
}

export function LLMServerForm({ server, onSubmit, onCancel, mode = 'create' }: LLMServerFormProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState<LLMServerCreate>({
    name: server?.name || '',
    description: server?.description || '',
    base_url: server?.base_url || '',
    provider: server?.provider || 'openai',
    api_key: server?.api_key || '',
    is_active: server?.is_active ?? true,
    auth_enabled: server?.auth_enabled ?? true  // 默认启用认证
  })

  const providerOptions = [
    { value: 'openai', label: 'OpenAI (GPT系列)' },
    { value: 'anthropic', label: 'Anthropic (Claude)' },
    { value: 'google', label: 'Google (Gemini)' },
    { value: 'cohere', label: 'Cohere' },
    { value: 'huggingface', label: 'HuggingFace' },
    { value: 'custom', label: '自定义格式' }
  ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      let result: LLMServer
      
      if (mode === 'edit' && server) {
        result = await SettingsService.updateServer(server.id, formData)
        toast.success('服务器更新成功')
      } else {
        result = await SettingsService.createServer(formData)
        toast.success('服务器创建成功')
      }
      
      onSubmit?.(result)
    } catch (error) {
      console.error('操作失败:', error)
      toast.error('操作失败')
    } finally {
      setIsLoading(false)
    }
  }

  const handleInputChange = (field: keyof LLMServerCreate, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900">
          {mode === 'create' ? '添加LLM服务器' : '编辑LLM服务器'}
        </h3>
        <p className="mt-1 text-sm text-gray-600">
          {mode === 'create' ? '配置新的LLM服务器连接' : '修改现有LLM服务器配置'}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 基本设置 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-medium text-gray-900 mb-4">基本设置</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                服务器名称 *
              </label>
              <Input
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                placeholder="输入服务器名称"
                required
                className="mt-1"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                基础URL *
              </label>
              <Input
                type="url"
                value={formData.base_url}
                onChange={(e) => handleInputChange('base_url', e.target.value)}
                placeholder="https://api.example.com"
                required
                className="mt-1"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                提供商类型 *
              </label>
              <Select
                options={providerOptions}
                value={formData.provider}
                onChange={(value) => handleInputChange('provider', value as LLMProvider)}
                className="mt-1"
              />
            </div>
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700">
              描述
            </label>
            <Textarea
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              placeholder="服务器描述信息"
              rows={3}
              className="mt-1"
            />
          </div>
        </div>

        {/* 认证设置 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-medium text-gray-900 mb-4">认证设置</h4>
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Switch
                checked={formData.auth_enabled}
                onChange={(checked) => handleInputChange('auth_enabled', checked)}
              />
              <label className="text-sm font-medium text-gray-700">启用认证</label>
            </div>

            {formData.auth_enabled && (
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  API密钥
                </label>
                <Input
                  type="password"
                  value={formData.api_key}
                  onChange={(e) => handleInputChange('api_key', e.target.value)}
                  placeholder="输入API密钥"
                  className="mt-1"
                />
              </div>
            )}
          </div>
        </div>

        {/* 高级设置 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-medium text-gray-900 mb-4">高级设置</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                超时时间（秒）
              </label>
              <Input
                type="number"
                min="1"
                max="600"
                value={formData.timeout_seconds}
                onChange={(e) => handleInputChange('timeout_seconds', parseInt(e.target.value))}
                className="mt-1"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                最大重试次数
              </label>
              <Input
                type="number"
                min="0"
                max="10"
                value={formData.max_retries}
                onChange={(e) => handleInputChange('max_retries', parseInt(e.target.value))}
                className="mt-1"
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
          <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading}>
            取消
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? '处理中...' : mode === 'create' ? '创建服务器' : '更新服务器'}
          </Button>
        </div>
      </form>
    </div>
  )
}