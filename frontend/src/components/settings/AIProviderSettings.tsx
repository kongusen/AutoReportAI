'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/hooks/useToast'
import { SettingsService, AIProvider, AIProviderCreate } from '@/services/settingsService'
import { PlusIcon, TrashIcon, EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline'

export function AIProviderSettings() {
  const [providers, setProviders] = useState<AIProvider[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set())
  const { showToast } = useToast()

  const [newProvider, setNewProvider] = useState({
    name: '',
    provider_type: 'openai',
    api_key: '',
    api_endpoint: '',
    model_name: '',
    is_active: true
  })

  useEffect(() => {
    loadProviders()
  }, [])

  const loadProviders = async () => {
    try {
      setIsLoading(true)
      const data = await SettingsService.getAIProviders()
      setProviders(data)
    } catch (error) {
      showToast('加载AI提供商失败', 'error')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAddProvider = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const createData: AIProviderCreate = {
        name: newProvider.name,
        provider_type: newProvider.provider_type,
        api_key: newProvider.api_key,
        api_endpoint: newProvider.api_endpoint || undefined,
        model_name: newProvider.model_name || undefined,
        is_active: newProvider.is_active
      }
      await SettingsService.createAIProvider(createData)
      showToast('AI提供商添加成功', 'success')
      setShowAddForm(false)
      setNewProvider({
        name: '',
        provider_type: 'openai',
        api_key: '',
        api_endpoint: '',
        model_name: '',
        is_active: true
      })
      loadProviders()
    } catch (error) {
      showToast('添加AI提供商失败', 'error')
    }
  }

  const handleDeleteProvider = async (id: string) => {
    if (!confirm('确定要删除这个AI提供商吗？')) return
    
    try {
      await SettingsService.deleteAIProvider(id)
      showToast('AI提供商已删除', 'success')
      loadProviders()
    } catch (error) {
      showToast('删除AI提供商失败', 'error')
    }
  }

  const handleSetDefault = async (id: string) => {
    try {
      await SettingsService.setDefaultAIProvider(id)
      showToast('默认AI提供商已设置', 'success')
      loadProviders()
    } catch (error) {
      showToast('设置默认AI提供商失败', 'error')
    }
  }

  const toggleKeyVisibility = (id: string) => {
    const newVisibleKeys = new Set(visibleKeys)
    if (newVisibleKeys.has(id)) {
      newVisibleKeys.delete(id)
    } else {
      newVisibleKeys.add(id)
    }
    setVisibleKeys(newVisibleKeys)
  }

  const formatApiKey = (key: string, isVisible: boolean) => {
    if (isVisible) return key
    return key.slice(0, 8) + '*'.repeat(20) + key.slice(-4)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-medium text-gray-900">AI提供商设置</h3>
          <p className="mt-1 text-sm text-gray-600">
            管理您的AI服务提供商配置
          </p>
        </div>
        <Button
          onClick={() => setShowAddForm(true)}
          className="inline-flex items-center"
        >
          <PlusIcon className="w-4 h-4 mr-2" />
          添加提供商
        </Button>
      </div>

      {/* 添加新提供商表单 */}
      {showAddForm && (
        <div className="bg-gray-50 rounded-lg p-6">
          <h4 className="text-md font-medium text-gray-900 mb-4">添加新的AI提供商</h4>
          <form onSubmit={handleAddProvider} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  提供商名称
                </label>
                <input
                  type="text"
                  value={newProvider.name}
                  onChange={(e) => setNewProvider(prev => ({ ...prev, name: e.target.value }))}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  提供商类型
                </label>
                <select
                  value={newProvider.provider_type}
                  onChange={(e) => setNewProvider(prev => ({ ...prev, provider_type: e.target.value }))}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                >
                  <option value="openai">OpenAI</option>
                  <option value="azure">Azure OpenAI</option>
                  <option value="anthropic">Anthropic Claude</option>
                  <option value="google">Google AI</option>
                  <option value="custom">自定义</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700">
                  API Key
                </label>
                <input
                  type="password"
                  value={newProvider.api_key}
                  onChange={(e) => setNewProvider(prev => ({ ...prev, api_key: e.target.value }))}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  API端点 (可选)
                </label>
                <input
                  type="url"
                  value={newProvider.api_endpoint}
                  onChange={(e) => setNewProvider(prev => ({ ...prev, api_endpoint: e.target.value }))}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  placeholder="https://api.openai.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  模型名称 (可选)
                </label>
                <input
                  type="text"
                  value={newProvider.model_name}
                  onChange={(e) => setNewProvider(prev => ({ ...prev, model_name: e.target.value }))}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  placeholder="gpt-4"
                />
              </div>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                checked={newProvider.is_active}
                onChange={(e) => setNewProvider(prev => ({ ...prev, is_active: e.target.checked }))}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label className="ml-2 text-sm text-gray-700">
                启用此提供商
              </label>
            </div>

            <div className="flex justify-end space-x-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowAddForm(false)}
              >
                取消
              </Button>
              <Button type="submit">
                添加提供商
              </Button>
            </div>
          </form>
        </div>
      )}

      {/* 已有提供商列表 */}
      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {providers.map((provider) => (
            <li key={provider.id} className="px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center">
                    <div className="flex-1">
                      <div className="flex items-center">
                        <p className="text-sm font-medium text-gray-900">
                          {provider.name}
                        </p>
                        {provider.is_default && (
                          <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            默认
                          </span>
                        )}
                        {!provider.is_active && (
                          <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            未启用
                          </span>
                        )}
                      </div>
                      <div className="mt-1 flex items-center text-sm text-gray-500">
                        <span className="capitalize">{provider.provider_type}</span>
                        {provider.model_name && (
                          <>
                            <span className="mx-2">•</span>
                            <span>{provider.model_name}</span>
                          </>
                        )}
                      </div>
                      <div className="mt-1 flex items-center text-sm text-gray-500">
                        <span className="font-mono">
                          {formatApiKey(provider.api_key, visibleKeys.has(provider.id))}
                        </span>
                        <button
                          onClick={() => toggleKeyVisibility(provider.id)}
                          className="ml-2 p-1 text-gray-400 hover:text-gray-600"
                        >
                          {visibleKeys.has(provider.id) ? (
                            <EyeSlashIcon className="h-4 w-4" />
                          ) : (
                            <EyeIcon className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {!provider.is_default && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleSetDefault(provider.id)}
                    >
                      设为默认
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeleteProvider(provider.id)}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </li>
          ))}
        </ul>

        {providers.length === 0 && (
          <div className="text-center py-6 text-gray-500">
            <p>还没有配置AI提供商</p>
            <p className="text-sm mt-1">点击上方按钮添加第一个AI提供商</p>
          </div>
        )}
      </div>
    </div>
  )
}