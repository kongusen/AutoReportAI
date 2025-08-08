'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import toast from 'react-hot-toast'
import { SettingsService, AIProvider, AIProviderCreate } from '@/services/settingsService'
import { PlusIcon, TrashIcon, EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline'

export function AIProviderSettings() {
  const [providers, setProviders] = useState<AIProvider[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set())

  const [newProvider, setNewProvider] = useState({
    provider_name: '',
    provider_type: 'openai',
    api_key: '',
    api_base_url: '',
    default_model_name: '',
    is_active: true
  })

  useEffect(() => {
    loadProviders()
  }, [])

  const loadProviders = async () => {
    try {
      setIsLoading(true)
      console.log('开始加载AI提供商列表...')
      const data = await SettingsService.getAIProviders()
      console.log('获取到的AI提供商数据:', data)
      setProviders(data)
      console.log('设置providers状态完成，providers数量:', data.length)
    } catch (error) {
      console.error('加载AI提供商失败:', error)
      toast.error('加载AI提供商失败')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAddProvider = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const createData: AIProviderCreate = {
        provider_name: newProvider.provider_name,
        provider_type: newProvider.provider_type,
        api_key: newProvider.api_key,
        api_base_url: newProvider.api_base_url || undefined,
        default_model_name: newProvider.default_model_name || undefined,
        is_active: newProvider.is_active
      }
      await SettingsService.createAIProvider(createData)
      toast.success('AI提供商添加成功')
      setShowAddForm(false)
      setNewProvider({
        provider_name: '',
        provider_type: 'openai',
        api_key: '',
        api_base_url: '',
        default_model_name: '',
        is_active: true
      })
      loadProviders()
    } catch (error) {
      toast.error('添加AI提供商失败')
    }
  }

  const handleDeleteProvider = async (id: number) => {
    if (!confirm('确定要删除这个AI提供商吗？')) return
    
    try {
      await SettingsService.deleteAIProvider(id)
      toast.success('AI提供商已删除')
      loadProviders()
    } catch (error) {
      toast.error('删除AI提供商失败')
    }
  }

  const testProvider = async (id: number) => {
    try {
      await SettingsService.testAIProvider(id.toString())
      toast.success('AI提供商连接测试成功')
    } catch (error) {
      toast.error('AI提供商连接测试失败')
    }
  }

  const toggleKeyVisibility = (id: number) => {
    const newVisibleKeys = new Set(visibleKeys)
    if (newVisibleKeys.has(id.toString())) {
      newVisibleKeys.delete(id.toString())
    } else {
      newVisibleKeys.add(id.toString())
    }
    setVisibleKeys(newVisibleKeys)
  }

  const formatApiKey = (key: string, isVisible: boolean) => {
    if (isVisible) return key
    if (!key) {
      return '未提供API Key'
    }
    return key.slice(0, 8) + '*'.repeat(20) + key.slice(-4)
  }

  if (isLoading) {
    console.log('组件状态: 正在加载...')
    return (
      <div className="flex items-center justify-center py-8">
        <LoadingSpinner />
      </div>
    )
  }

  console.log('组件渲染状态:')
  console.log('- isLoading:', isLoading)
  console.log('- providers:', providers)
  console.log('- providers.length:', providers.length)

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
                  value={newProvider.provider_name}
                  onChange={(e) => setNewProvider(prev => ({ ...prev, provider_name: e.target.value }))}
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
                  <option value="azure_openai">Azure OpenAI</option>
                  <option value="mock">Mock (测试)</option>
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
                  value={newProvider.api_base_url}
                  onChange={(e) => setNewProvider(prev => ({ ...prev, api_base_url: e.target.value }))}
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
                  value={newProvider.default_model_name}
                  onChange={(e) => setNewProvider(prev => ({ ...prev, default_model_name: e.target.value }))}
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
                          {provider.provider_name}
                        </p>
                        {!provider.is_active && (
                          <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            未启用
                          </span>
                        )}
                      </div>
                      <div className="mt-1 flex items-center text-sm text-gray-500">
                        <span className="capitalize">{provider.provider_type}</span>
                        {provider.default_model_name && (
                          <>
                            <span className="mx-2">•</span>
                            <span>{provider.default_model_name}</span>
                          </>
                        )}
                      </div>
                      <div className="mt-1 flex items-center text-sm text-gray-500">
                        <span className="font-mono">
                          API Key已配置
                        </span>
                        <button
                          onClick={() => toggleKeyVisibility(provider.id)}
                          className="ml-2 p-1 text-gray-400 hover:text-gray-600"
                        >
                          {visibleKeys.has(provider.id.toString()) ? (
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
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => testProvider(provider.id)}
                  >
                    测试连接
                  </Button>
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