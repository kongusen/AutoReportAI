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
import { LLMModelCreate, ModelType, LLMModel } from '@/types/api'

interface ModelFormProps {
  serverId: string
  model?: any
  onSubmit?: (model: any) => void
  onCancel?: () => void
  mode?: 'create' | 'edit'
  providerName?: string
}

export function ModelForm({ serverId, model, onSubmit, onCancel, mode = 'create', providerName }: ModelFormProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState<LLMModelCreate>({
    server_id: serverId,
    name: model?.name || '',
    display_name: model?.display_name || '',
    description: model?.description || '',
    model_type: model?.model_type || 'default',
    provider_name: model?.provider_name || '',
    priority: model?.priority || 1,
    max_tokens: model?.max_tokens || 4096,
    temperature_default: model?.temperature_default || 0.7,
    supports_system_messages: model?.supports_system_messages ?? true,
    supports_function_calls: model?.supports_function_calls ?? false,
    supports_thinking: model?.supports_thinking ?? false
  })

  const modelTypes: { value: ModelType; label: string }[] = [
    { value: 'default', label: '默认模型' },
    { value: 'think', label: '思考模型' }
  ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      let result: LLMModel
      const payload: LLMModelCreate = {
        ...formData,
        // 自动填充：显示名称默认等于模型名称
        display_name: formData.display_name || formData.name,
        // 自动填充：供应商名称来自父级（服务器）或保留原值
        provider_name: formData.provider_name || providerName || model?.provider_name || 'default',
        // 强制使用小写以匹配后端/数据库的枚举
        model_type: (formData.model_type as string).toLowerCase() as ModelType
      }
      
      if (mode === 'edit' && model) {
        result = await SettingsService.updateServerModel(serverId, model.id, {
          display_name: payload.display_name,
          description: payload.description,
          priority: payload.priority,
          max_tokens: payload.max_tokens,
          temperature_default: payload.temperature_default,
          supports_system_messages: payload.supports_system_messages,
          supports_function_calls: payload.supports_function_calls,
          supports_thinking: payload.supports_thinking,
          is_active: payload.is_active
        })
        toast.success('模型更新成功')
      } else {
        result = await SettingsService.createServerModel(serverId, payload)
        toast.success('模型创建成功')
      }
      
      onSubmit?.(result)
    } catch (error: any) {
      console.error('操作失败:', error)
      const detail = error?.response?.data?.detail || error?.message || '操作失败'
      toast.error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    } finally {
      setIsLoading(false)
    }
  }

  const handleInputChange = (field: keyof LLMModelCreate, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900">
          {mode === 'create' ? '添加LLM模型' : '编辑LLM模型'}
        </h3>
        <p className="mt-1 text-sm text-gray-600">
          {mode === 'create' ? '配置新的LLM模型' : '修改现有LLM模型配置'}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 基本设置 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-medium text-gray-900 mb-4">基本设置</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                模型名称 *
              </label>
              <Input
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                placeholder="输入模型名称"
                required
                className="mt-1"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                模型类型 *
              </label>
              <Select
                value={formData.model_type}
                onChange={(value) => handleInputChange('model_type', value as ModelType)}
                options={modelTypes}
                className="mt-1"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                优先级
              </label>
              <Input
                type="number"
                min="1"
                max="100"
                value={formData.priority}
                onChange={(e) => handleInputChange('priority', parseInt(e.target.value))}
                className="mt-1"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                最大tokens
              </label>
              <Input
                type="number"
                min="1"
                max="1000000"
                value={formData.max_tokens}
                onChange={(e) => handleInputChange('max_tokens', parseInt(e.target.value))}
                className="mt-1"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                默认温度
              </label>
              <Input
                type="number"
                min="0"
                max="2"
                step="0.1"
                value={formData.temperature_default}
                onChange={(e) => handleInputChange('temperature_default', parseFloat(e.target.value))}
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
              placeholder="模型描述信息"
              rows={3}
              className="mt-1"
            />
          </div>
        </div>

        {/* 功能支持 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-medium text-gray-900 mb-4">功能支持</h4>
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Switch
                checked={formData.supports_system_messages}
                onChange={(checked) => handleInputChange('supports_system_messages', checked)}
              />
              <label className="text-sm font-medium text-gray-700">支持系统消息</label>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                checked={formData.supports_function_calls}
                onChange={(checked) => handleInputChange('supports_function_calls', checked)}
              />
              <label className="text-sm font-medium text-gray-700">支持函数调用</label>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                checked={formData.supports_thinking}
                onChange={(checked) => handleInputChange('supports_thinking', checked)}
              />
              <label className="text-sm font-medium text-gray-700">支持思考模式</label>
            </div>
          </div>
        </div>

        <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
          <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading}>
            取消
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? '处理中...' : mode === 'create' ? '创建模型' : '更新模型'}
          </Button>
        </div>
      </form>
    </div>
  )
}