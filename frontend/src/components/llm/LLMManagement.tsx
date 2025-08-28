'use client'

import { useEffect, useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { SettingsService, LLMServer, LLMModel } from '@/services/settingsService'
import { ModelList } from '@/components/llm/ModelList'
import { ModelForm } from '@/components/llm/ModelForm'
import { LLMServerList } from '@/components/settings/LLMServerList'
import { LLMServerForm } from '@/components/settings/LLMServerForm'
import { PlusIcon, ServerIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

export function LLMManagement() {
  const [servers, setServers] = useState<LLMServer[]>([])
  const [showModelForm, setShowModelForm] = useState(false)
  const [showServerForm, setShowServerForm] = useState(false)
  const [editingModel, setEditingModel] = useState<LLMModel | undefined>(undefined)
  const [editingServer, setEditingServer] = useState<LLMServer | undefined>(undefined)
  const [selectedServerId, setSelectedServerId] = useState<number | null>(null)

  const loadServers = async () => {
    const data = await SettingsService.getServers()
    setServers(data)
  }

  useEffect(() => {
    loadServers()
  }, [])

  const handleServerSubmit = (server: LLMServer) => {
    setShowServerForm(false)
    setEditingServer(undefined)
    loadServers()
  }

  const handleModelSubmit = () => {
    setShowModelForm(false)
    setEditingModel(undefined)
    setSelectedServerId(null)
    loadServers()
  }

  const renderServerCard = (server: LLMServer) => {
    return (
      <Card key={server.id} className="mb-4">
        <div className="p-6">
          {/* 服务器信息头部 */}
          <div className="flex justify-between items-start mb-4">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h3 className="text-lg font-medium text-gray-900">{server.name}</h3>
                <div className="flex space-x-2">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    server.is_healthy 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {server.is_healthy ? '健康' : '异常'}
                  </span>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    server.is_active 
                      ? 'bg-blue-100 text-blue-800' 
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {server.is_active ? '活跃' : '禁用'}
                  </span>
                </div>
              </div>
              <p className="text-sm text-gray-600 mb-2">{server.description || '无描述'}</p>
              <div className="text-sm text-gray-500">
                <div>URL: {server.base_url}</div>
                <div>模型数量: {server.models_count || 0} 个</div>
                {server.last_health_check && (
                  <div>最后检查: {new Date(server.last_health_check).toLocaleString()}</div>
                )}
              </div>
            </div>
            
            <div className="flex space-x-2 ml-4">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => {
                  setEditingServer(server)
                  setShowServerForm(true)
                }}
              >
                编辑
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                onClick={async () => {
                  try {
                    await SettingsService.checkServerHealth(server.id)
                    loadServers()
                  } catch (error) {
                    console.error('健康检查失败:', error)
                  }
                }}
              >
                健康检查
              </Button>
              <Button 
                variant="destructive" 
                size="sm"
                onClick={async () => {
                  if (confirm(`确定要删除服务器 "${server.name}" 吗？这将删除该服务器及其所有模型配置。`)) {
                    try {
                      await SettingsService.deleteServer(server.id)
                      toast.success('LLM服务器已删除')
                      loadServers()
                    } catch (error) {
                      console.error('删除服务器失败:', error)
                      toast.error('删除服务器失败')
                    }
                  }
                }}
              >
                删除
              </Button>
            </div>
          </div>

          {/* 该服务器的模型列表 */}
          <div className="border-t border-gray-200 pt-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-md font-medium text-gray-900">模型配置</h4>
              <Button 
                size="sm"
                onClick={() => {
                  setSelectedServerId(server.id)
                  setEditingModel(undefined)
                  setShowModelForm(true)
                }}
              >
                <PlusIcon className="w-4 h-4 mr-1" />
                添加模型
              </Button>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-3">
              <ModelList
                serverId={server.id}
                serverName={server.name}
                onAddModel={() => {
                  setSelectedServerId(server.id)
                  setEditingModel(undefined)
                  setShowModelForm(true)
                }}
                onEditModel={(model) => {
                  setSelectedServerId(server.id)
                  setEditingModel(model)
                  setShowModelForm(true)
                }}
              />
            </div>
          </div>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* 页面标题和添加按钮 */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium text-gray-900">LLM 管理</h3>
          <p className="mt-1 text-sm text-gray-600">
            管理LLM服务器供应商和模型配置
          </p>
        </div>
        <Button 
          onClick={() => {
            setEditingServer(undefined)
            setShowServerForm(true)
          }}
          className="bg-gray-900 hover:bg-gray-800"
        >
          <ServerIcon className="w-4 h-4 mr-2" />
          添加供应商
        </Button>
      </div>

      {/* 服务器卡片列表 */}
      <div>
        {servers.length === 0 ? (
          <div className="text-center py-12">
            <ServerIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">暂无LLM服务器供应商</h3>
            <p className="mt-1 text-sm text-gray-500">开始添加您的第一个LLM服务器供应商</p>
            <div className="mt-6">
              <Button 
                onClick={() => {
                  setEditingServer(undefined)
                  setShowServerForm(true)
                }}
              >
                <ServerIcon className="w-4 h-4 mr-2" />
                添加第一个供应商
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {servers.map(server => renderServerCard(server))}
          </div>
        )}
      </div>

      {/* 模型表单模态框 */}
      <Modal
        isOpen={showModelForm}
        onClose={() => setShowModelForm(false)}
        title={editingModel ? '编辑模型' : '添加模型'}
        size="lg"
      >
        {selectedServerId && (
          <ModelForm
            serverId={selectedServerId}
            model={editingModel}
            mode={editingModel ? 'edit' : 'create'}
            providerName={servers.find(s => s.id === selectedServerId)?.name || ''}
            onSubmit={handleModelSubmit}
            onCancel={() => setShowModelForm(false)}
          />
        )}
      </Modal>

      {/* 服务器表单模态框 */}
      <Modal
        isOpen={showServerForm}
        onClose={() => setShowServerForm(false)}
        title={editingServer ? '编辑LLM服务器' : '添加LLM服务器'}
        size="lg"
      >
        <LLMServerForm
          server={editingServer}
          mode={editingServer ? 'edit' : 'create'}
          onSubmit={handleServerSubmit}
          onCancel={() => setShowServerForm(false)}
        />
      </Modal>
    </div>
  )
}


