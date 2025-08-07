'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  PlusIcon,
  MagnifyingGlassIcon,
  CircleStackIcon,
  CheckCircleIcon,
  XCircleIcon,
  PlayIcon,
  PencilIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import { AppLayout } from '@/components/layout/AppLayout'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { Empty } from '@/components/ui/Empty'
import { useDataSourceStore } from '@/features/data-sources/dataSourceStore'
import { getDataSourceTypeName, formatRelativeTime } from '@/utils'
import { DataSource } from '@/types'

export default function DataSourcesPage() {
  const router = useRouter()
  const { dataSources, loading, fetchDataSources, deleteDataSource, testConnection } = useDataSourceStore()
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedType, setSelectedType] = useState<string>('all')
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [selectedDataSource, setSelectedDataSource] = useState<DataSource | null>(null)
  const [testingConnections, setTestingConnections] = useState<Set<string>>(new Set())

  useEffect(() => {
    fetchDataSources()
  }, [fetchDataSources])

  // 过滤数据源
  const filteredDataSources = dataSources.filter(ds => {
    const matchesSearch = ds.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         ds.display_name?.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesType = selectedType === 'all' || ds.source_type === selectedType
    return matchesSearch && matchesType
  })

  // 获取数据源类型列表
  const dataSourceTypes = [...new Set(dataSources.map(ds => ds.source_type))]

  const handleDeleteConfirm = async () => {
    if (!selectedDataSource) return
    
    try {
      await deleteDataSource(selectedDataSource.id)
      setDeleteModalOpen(false)
      setSelectedDataSource(null)
    } catch (error) {
      // 错误处理已在store中处理
    }
  }

  const handleTestConnection = async (dataSource: DataSource) => {
    setTestingConnections(prev => new Set(prev).add(dataSource.id))
    try {
      await testConnection(dataSource.id)
    } finally {
      setTestingConnections(prev => {
        const newSet = new Set(prev)
        newSet.delete(dataSource.id)
        return newSet
      })
    }
  }

  const getStatusBadge = (dataSource: DataSource) => {
    if (!dataSource.is_active) {
      return <Badge variant="secondary">已停用</Badge>
    }
    
    // 这里可以根据实际连接状态显示
    return <Badge variant="success">正常</Badge>
  }

  return (
    <AppLayout>
      <PageHeader
        title="数据源管理"
        description="管理您的数据源连接，支持SQL数据库、Doris、API接口等多种数据源类型"
        actions={
          <Button onClick={() => router.push('/data-sources/create')}>
            <PlusIcon className="w-4 h-4 mr-2" />
            添加数据源
          </Button>
        }
      />

      {/* 搜索和筛选 */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <Input
            placeholder="搜索数据源..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            leftIcon={<MagnifyingGlassIcon className="w-4 h-4 text-gray-400" />}
          />
        </div>
        <div className="sm:w-48">
          <select
            className="w-full rounded-md border border-gray-300 bg-white py-2 pl-3 pr-10 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
          >
            <option value="all">全部类型</option>
            {dataSourceTypes.map(type => (
              <option key={type} value={type}>
                {getDataSourceTypeName(type)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 数据源列表 */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="space-y-3">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                  <div className="flex space-x-2">
                    <div className="h-6 bg-gray-200 rounded w-16"></div>
                    <div className="h-6 bg-gray-200 rounded w-12"></div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredDataSources.length === 0 ? (
        <Empty
          title={searchTerm || selectedType !== 'all' ? '未找到匹配的数据源' : '还没有数据源'}
          description={searchTerm || selectedType !== 'all' ? '尝试调整搜索条件或筛选器' : '创建您的第一个数据源以开始使用'}
          action={
            <Button onClick={() => router.push('/data-sources/create')}>
              <PlusIcon className="w-4 h-4 mr-2" />
              添加数据源
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDataSources.map((dataSource) => (
            <Card key={dataSource.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center">
                    <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center mr-3">
                      <CircleStackIcon className="w-5 h-5 text-gray-600" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-sm font-medium text-gray-900 truncate">
                        {dataSource.display_name || dataSource.name}
                      </h3>
                      <p className="text-xs text-gray-500">
                        {getDataSourceTypeName(dataSource.source_type)}
                      </p>
                    </div>
                  </div>
                  {getStatusBadge(dataSource)}
                </div>

                <div className="space-y-2 mb-4">
                  <p className="text-xs text-gray-500">
                    创建时间: {formatRelativeTime(dataSource.created_at)}
                  </p>
                  {dataSource.updated_at && (
                    <p className="text-xs text-gray-500">
                      更新时间: {formatRelativeTime(dataSource.updated_at)}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleTestConnection(dataSource)}
                    disabled={testingConnections.has(dataSource.id)}
                    loading={testingConnections.has(dataSource.id)}
                  >
                    <PlayIcon className="w-3 h-3 mr-1" />
                    测试连接
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => router.push(`/data-sources/${dataSource.id}/edit`)}
                  >
                    <PencilIcon className="w-3 h-3 mr-1" />
                    编辑
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedDataSource(dataSource)
                      setDeleteModalOpen(true)
                    }}
                  >
                    <TrashIcon className="w-3 h-3 mr-1" />
                    删除
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 删除确认对话框 */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        title="删除数据源"
        description={`确定要删除数据源"${selectedDataSource?.display_name || selectedDataSource?.name}"吗？此操作无法撤销。`}
      >
        <div className="flex justify-end space-x-3">
          <Button
            variant="outline"
            onClick={() => setDeleteModalOpen(false)}
          >
            取消
          </Button>
          <Button
            variant="destructive"
            onClick={handleDeleteConfirm}
          >
            删除
          </Button>
        </div>
      </Modal>
    </AppLayout>
  )
}