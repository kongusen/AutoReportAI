'use client'

import { useEffect, useState } from 'react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { LLMService } from '@/services/apiService'
import { LLMServer } from '@/types/api'
import { ModelList } from '@/components/llm/ModelList'
import { ModelForm } from '@/components/llm/ModelForm'
import { PlusIcon } from '@heroicons/react/24/outline'

export default function LLMManagementPage() {
  const [servers, setServers] = useState<LLMServer[]>([])
  const [activeServerId, setActiveServerId] = useState<string | null>(null)
  const [showModelForm, setShowModelForm] = useState(false)
  const [editingModel, setEditingModel] = useState<any | undefined>(undefined)

  const loadServers = async () => {
    const data = await LLMService.getServers()
    setServers(data)
    if (!activeServerId && data.length > 0) {
      setActiveServerId(data[0].id)
    }
  }

  useEffect(() => {
    loadServers()
  }, [])

  const currentServer = servers.find(s => s.id === activeServerId)

  return (
    <div className="space-y-6">
      <PageHeader
        title="LLM 管理"
        description="按供应商分组管理模型，支持一供应商多模型配置"
        breadcrumbs={[{ label: '设置', href: '/settings' }, { label: 'LLM 管理' }]}
        actions={
          currentServer ? (
            <Button onClick={() => { setEditingModel(undefined); setShowModelForm(true) }}>
              <PlusIcon className="w-4 h-4 mr-2" />
              添加模型
            </Button>
          ) : undefined
        }
      />

      <Card>
        <div className="p-4">
          <div className="flex flex-wrap gap-2 mb-4">
            {servers.map(s => (
              <Button
                key={s.id}
                variant={s.id === activeServerId ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveServerId(s.id)}
              >
                {s.name}
              </Button>
            ))}
          </div>

          {currentServer ? (
            <ModelList
              serverId={currentServer.id}
              serverName={currentServer.name}
              onAddModel={() => { setEditingModel(undefined); setShowModelForm(true) }}
              onEditModel={(m) => { setEditingModel(m); setShowModelForm(true) }}
            />
          ) : (
            <div className="text-gray-600">请先创建或选择一个 LLM 服务器</div>
          )}
        </div>
      </Card>

      <Modal
        isOpen={showModelForm}
        onClose={() => setShowModelForm(false)}
        title={editingModel ? '编辑模型' : '添加模型'}
        size="lg"
      >
        {currentServer && (
          <ModelForm
            serverId={currentServer.id}
            model={editingModel}
            mode={editingModel ? 'edit' : 'create'}
            providerName={currentServer.name}
            onSubmit={() => { setShowModelForm(false) }}
            onCancel={() => setShowModelForm(false)}
          />
        )}
      </Modal>
    </div>
  )
}


