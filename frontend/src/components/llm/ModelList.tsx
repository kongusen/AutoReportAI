'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Switch } from '@/components/ui/Switch'
import toast from 'react-hot-toast'
import { SettingsService as LLMService, LLMModel } from '@/services/settingsService'
import { PlusIcon, ArrowPathIcon, TrashIcon, CogIcon } from '@heroicons/react/24/outline'

interface ModelListProps {
  serverId: number
  serverName: string
  onAddModel?: () => void
  onEditModel?: (model: LLMModel) => void
}

export function ModelList({ serverId, serverName, onAddModel, onEditModel }: ModelListProps) {
  const [models, setModels] = useState<LLMModel[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const loadModels = async () => {
    try {
      setIsLoading(true)
      const data = await LLMService.getServerModels(serverId)
      setModels(data)
    } catch (error) {
      console.error('加载模型失败:', error)
      toast.error('加载模型失败')
    } finally {
      setIsLoading(false)
      setRefreshing(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await loadModels()
  }

  const handleToggleActive = async (modelId: number, currentActive: boolean) => {
    try {
      await LLMService.updateModel(serverId, modelId, { is_active: !currentActive })
      toast.success(`模型已${!currentActive ? '启用' : '禁用'}`)
      await loadModels()
    } catch (error) {
      console.error('更新模型状态失败:', error)
      toast.error('更新模型状态失败')
    }
  }

  const handleDeleteModel = async (modelId: number, modelName: string) => {
    if (!confirm(`确定要删除模型"${modelName}"吗？此操作不可撤销。`)) {
      return
    }

    try {
      await LLMService.deleteModel(serverId, modelId)
      toast.success('模型删除成功')
      await loadModels()
    } catch (error) {
      console.error('删除模型失败:', error)
      toast.error('删除模型失败')
    }
  }

  const handleHealthCheck = async (modelId: number, modelName: string) => {
    try {
      const res = await LLMService.checkModelHealth(serverId, modelId)
      const isHealthy = !!res?.is_healthy
      // 乐观更新当前列表中的标签与时间
      setModels(prev => prev.map(m => m.id === modelId ? {
        ...m,
        is_healthy: isHealthy,
        last_health_check: new Date().toISOString()
      } : m))
      toast.success(`模型"${modelName}"健康检查${isHealthy ? '通过' : '未通过'}`)
      // 轻量延迟刷新，确保后端状态落库后与服务端同步
      setTimeout(() => loadModels(), 1500)
    } catch (error) {
      console.error('健康检查失败:', error)
      toast.error('健康检查失败')
    }
  }

  useEffect(() => {
    loadModels()
  }, [serverId])

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  const modelsByProvider = models.reduce<Record<string, LLMModel[]>>((acc, m) => {
    const key = m.provider_name || '未指定提供商'
    acc[key] = acc[key] || []
    acc[key].push(m)
    // 排序：活跃优先、优先级高在前
    acc[key].sort((a, b) => (Number(b.is_active) - Number(a.is_active)) || (b.priority - a.priority))
    return acc
  }, {})

  const providerNames = Object.keys(modelsByProvider).sort()

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900">模型管理 - {serverName}</h3>
        <p className="mt-1 text-sm text-gray-600">管理服务器上的LLM模型配置，按供应商分组</p>
      </div>

      <div className="flex justify-between items-center">
        <div className="flex space-x-2">
          <Button variant="outline" onClick={handleRefresh} disabled={refreshing}>
            <ArrowPathIcon className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
        <Button onClick={onAddModel}>
          <PlusIcon className="w-4 h-4 mr-2" />
          添加模型
        </Button>
      </div>

      <div className="bg-gray-50 rounded-lg p-4">
        {models.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-gray-500 mb-4">暂无模型配置</div>
            <Button onClick={onAddModel}>
              <PlusIcon className="w-4 h-4 mr-2" />
              添加第一个模型
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            {providerNames.map((provider) => (
              <div key={provider} className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h4 className="text-md font-semibold text-gray-900">{provider}</h4>
                    <Badge variant="secondary">{modelsByProvider[provider].length} 个模型</Badge>
                  </div>
                  <div>
                    <Button size="sm" variant="outline" onClick={onAddModel}>
                      <PlusIcon className="w-4 h-4 mr-1" />
                      添加该供应商模型
                    </Button>
                  </div>
                </div>

                <div className="space-y-3">
                  {modelsByProvider[provider].map((model) => (
                    <div key={model.id} className="bg-white rounded-lg p-4 border border-gray-200 hover:border-gray-300 transition-colors">
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1">
                          <h5 className="font-medium text-gray-900">{model.display_name}</h5>
                          <p className="text-sm text-gray-600 mt-1">{model.description || '无描述'}</p>
                          <div className="flex flex-wrap gap-2 mt-2 text-xs text-gray-500">
                            <span>{model.name}</span>
                            <span>•</span>
                            <span>优先级 {model.priority}</span>
                            {model.max_tokens ? <><span>•</span><span>Max {model.max_tokens}</span></> : null}
                          </div>
                        </div>
                        <div className="flex space-x-1 ml-4">
                          <Badge variant={model.is_healthy ? 'success' : 'destructive'}>
                            {model.is_healthy ? '健康' : '异常'}
                          </Badge>
                          <Badge variant={model.is_active ? 'default' : 'secondary'}>
                            {model.is_active ? '活跃' : '禁用'}
                          </Badge>
                          <Badge variant="outline">{model.model_type}</Badge>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                        {model.last_health_check && (
                          <div>
                            <span className="text-gray-500">最后检查:</span>
                            <div className="font-medium">{new Date(model.last_health_check).toLocaleString()}</div>
                          </div>
                        )}
                        <div>
                          <span className="text-gray-500">系统消息:</span>
                          <div className="font-medium">{model.supports_system_messages ? '支持' : '不支持'}</div>
                        </div>
                        <div>
                          <span className="text-gray-500">函数调用:</span>
                          <div className="font-medium">{model.supports_function_calls ? '支持' : '不支持'}</div>
                        </div>
                      </div>

                      <div className="flex justify-between items-center mt-4 pt-3 border-t border-gray-100">
                        <div className="flex space-x-2">
                          <Button variant="outline" size="sm" onClick={() => onEditModel?.(model)}>
                            <CogIcon className="w-4 h-4 mr-1" />
                            编辑
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleHealthCheck(model.id, model.display_name)}>
                            <ArrowPathIcon className="w-4 h-4 mr-1" />
                            健康检查
                          </Button>
                          <div className="flex items-center space-x-2">
                            <Switch checked={model.is_active} onChange={() => handleToggleActive(model.id, model.is_active)} size="sm" />
                            <span className="text-sm text-gray-600">{model.is_active ? '启用' : '禁用'}</span>
                          </div>
                        </div>
                        <Button variant="outline" size="sm" onClick={() => handleDeleteModel(model.id, model.display_name)} className="text-red-600 hover:text-red-700 hover:bg-red-50">
                          <TrashIcon className="w-4 h-4" />
                          删除
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}