'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import toast from 'react-hot-toast'
import { SettingsService as LLMService, LLMServer } from '@/services/settingsService'
import { formatDateTime } from '@/utils'
import { PlusIcon, ArrowPathIcon, TrashIcon } from '@heroicons/react/24/outline'

interface LLMServerListProps {
  onSelectServer?: (server: LLMServer) => void
  onAddServer?: () => void
}

export function LLMServerList({ onSelectServer, onAddServer }: LLMServerListProps) {
  const [servers, setServers] = useState<LLMServer[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const loadServers = async () => {
    try {
      setIsLoading(true)
      const data = await LLMService.getServers()
      setServers(data)
    } catch (error) {
      console.error('加载LLM服务器失败:', error)
      toast.error('加载LLM服务器失败')
    } finally {
      setIsLoading(false)
      setRefreshing(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await loadServers()
  }

  const handleHealthCheckAll = async () => {
    try {
      await LLMService.healthCheckAllServers()
      toast.success('已启动所有服务器健康检查')
      // 稍后刷新列表
      setTimeout(() => loadServers(), 3000)
    } catch (error) {
      console.error('健康检查失败:', error)
      toast.error('健康检查失败')
    }
  }

  const handleDeleteServer = async (serverId: number, serverName: string) => {
    if (!confirm(`确定要删除服务器"${serverName}"吗？此操作不可撤销。`)) {
      return
    }

    try {
      await LLMService.deleteServer(serverId)
      toast.success('服务器删除成功')
      await loadServers()
    } catch (error) {
      console.error('删除服务器失败:', error)
      toast.error('删除服务器失败')
    }
  }

  useEffect(() => {
    loadServers()
  }, [])

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900">LLM服务器管理</h3>
        <p className="mt-1 text-sm text-gray-600">
          管理您的LLM服务器和提供商配置
        </p>
      </div>

      <div className="flex justify-between items-center">
        <div className="flex space-x-2">
          <Button variant="outline" onClick={handleRefresh} disabled={refreshing}>
            <ArrowPathIcon className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button variant="outline" onClick={handleHealthCheckAll}>
            <ArrowPathIcon className="w-4 h-4 mr-2" />
            健康检查
          </Button>
        </div>
        <Button onClick={onAddServer}>
          <PlusIcon className="w-4 h-4 mr-2" />
          添加服务器
        </Button>
      </div>

      <div className="bg-gray-50 rounded-lg p-4">
        {servers.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-gray-500 mb-4">暂无LLM服务器</div>
            <Button onClick={onAddServer}>
              <PlusIcon className="w-4 h-4 mr-2" />
              添加第一个服务器
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {servers.map((server) => (
              <div key={server.id} className="bg-white rounded-lg p-4 border border-gray-200 hover:border-gray-300 transition-colors">
                <div className="flex justify-between items-start mb-3">
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900">{server.name}</h4>
                    <p className="text-sm text-gray-600 mt-1">{server.description || '无描述'}</p>
                  </div>
                  <div className="flex space-x-1 ml-4">
                    <Badge variant={server.is_healthy ? 'success' : 'destructive'}>
                      {server.is_healthy ? '健康' : '异常'}
                    </Badge>
                    <Badge variant={server.is_active ? 'default' : 'secondary'}>
                      {server.is_active ? '活跃' : '禁用'}
                    </Badge>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">URL:</span>
                    <div className="font-medium truncate">{server.base_url}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">模型:</span>
                    <div className="font-medium">{server.models_count || 0} 个</div>
                  </div>
                  {server.last_health_check && (
                    <div>
                      <span className="text-gray-500">最后检查:</span>
                      <div className="font-medium">
                        {formatDateTime(server.last_health_check)}
                      </div>
                    </div>
                  )}
                  {server.success_rate !== undefined && (
                    <div>
                      <span className="text-gray-500">成功率:</span>
                      <div className="font-medium">{(server.success_rate * 100).toFixed(1)}%</div>
                    </div>
                  )}
                </div>

                <div className="flex justify-between items-center mt-4 pt-3 border-t border-gray-100">
                  <div className="flex space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onSelectServer?.(server)}
                    >
                      查看详情
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => LLMService.checkServerHealth(server.id)}
                    >
                      健康检查
                    </Button>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeleteServer(server.id, server.name)}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <TrashIcon className="w-4 h-4" />
                    删除
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}