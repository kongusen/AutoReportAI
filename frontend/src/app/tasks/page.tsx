'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  PlusIcon,
  MagnifyingGlassIcon,
  PlayIcon,
  PauseIcon,
  TrashIcon,
  PencilIcon,
  EyeIcon,
  ClockIcon,
  CheckIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { AppLayout } from '@/components/layout/AppLayout'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Table } from '@/components/ui/Table'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { Checkbox } from '@/components/ui/Checkbox'
import { Empty } from '@/components/ui/Empty'
import { Progress } from '@/components/ui/Progress'
import { useTaskStore } from '@/features/tasks/taskStore'
import { useDataSourceStore } from '@/features/data-sources/dataSourceStore'
import { useWebSocket } from '@/hooks/useWebSocket'
import { getTaskStatusInfo, formatRelativeTime } from '@/utils'
import { Task } from '@/types'

export default function TasksPage() {
  const router = useRouter()
  const { 
    tasks, 
    loading, 
    fetchTasks, 
    deleteTask, 
    toggleTaskStatus, 
    executeTask,
    batchUpdateStatus,
    batchDeleteTasks,
    getTaskProgress
  } = useTaskStore()
  
  const { dataSources, fetchDataSources } = useDataSourceStore()
  
  // 启用WebSocket连接来接收实时任务更新
  const { connected: wsConnected } = useWebSocket({ enabled: true })
  
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all')
  const [selectedTasks, setSelectedTasks] = useState<string[]>([])
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [batchDeleteModalOpen, setBatchDeleteModalOpen] = useState(false)

  useEffect(() => {
    fetchTasks()
    fetchDataSources()
  }, [fetchTasks, fetchDataSources])

  // 过滤任务
  const filteredTasks = tasks.filter(task => {
    const matchesSearch = task.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         task.description?.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = statusFilter === 'all' || 
                         (statusFilter === 'active' && task.is_active) ||
                         (statusFilter === 'inactive' && !task.is_active)
    return matchesSearch && matchesStatus
  })

  const handleSelectTask = (taskId: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const checked = e.target.checked
    if (checked) {
      setSelectedTasks([...selectedTasks, taskId])
    } else {
      setSelectedTasks(selectedTasks.filter(id => id !== taskId))
    }
  }

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    const checked = e.target.checked
    if (checked) {
      setSelectedTasks(filteredTasks.map(task => task.id.toString()))
    } else {
      setSelectedTasks([])
    }
  }

  const handleDeleteConfirm = async () => {
    if (!selectedTask) return
    
    try {
      await deleteTask(selectedTask.id.toString())
      setDeleteModalOpen(false)
      setSelectedTask(null)
    } catch (error) {
      // 错误处理已在store中处理
    }
  }

  const handleBatchEnable = async () => {
    if (selectedTasks.length === 0) return
    try {
      await batchUpdateStatus(selectedTasks, true)
      setSelectedTasks([])
    } catch (error) {
      // 错误处理已在store中处理
    }
  }

  const handleBatchDisable = async () => {
    if (selectedTasks.length === 0) return
    try {
      await batchUpdateStatus(selectedTasks, false)
      setSelectedTasks([])
    } catch (error) {
      // 错误处理已在store中处理
    }
  }

  const handleBatchDelete = async () => {
    if (selectedTasks.length === 0) return
    try {
      await batchDeleteTasks(selectedTasks)
      setBatchDeleteModalOpen(false)
      setSelectedTasks([])
    } catch (error) {
      // 错误处理已在store中处理
    }
  }

  const getDataSourceName = (dataSourceId: string) => {
    const dataSource = dataSources.find(ds => ds.id === dataSourceId)
    return dataSource?.display_name || dataSource?.name || '未知数据源'
  }

  const TaskProgressIndicator = ({ taskId }: { taskId: string }) => {
    const progress = getTaskProgress(taskId)
    if (!progress) return null

    const handleRetryTask = async () => {
      try {
        await executeTask(taskId)
      } catch (error) {
        // 错误处理已在store中处理
      }
    }

    const getProgressMessage = () => {
      if (progress.current_step && progress.current_step !== progress.message) {
        return progress.current_step
      }
      return progress.message || '处理中...'
    }

    // 获取错误详情
    const getErrorDetails = () => {
      if (progress.status === 'failed') {
        // 尝试从各个可能的字段获取错误详情
        const details = (progress as any).error || 
                       (progress as any).traceback ||
                       (progress as any).details ||
                       (progress as any).error_details
        return details
      }
      
      // 警告状态的详情
      if (progress.status === 'completed' && (progress as any).has_errors) {
        const placeholderResults = (progress as any).placeholder_results
        if (placeholderResults) {
          const failedPlaceholders = placeholderResults.filter((p: any) => !p.success)
          if (failedPlaceholders.length > 0) {
            return `${failedPlaceholders.length} 个占位符处理失败:\n${failedPlaceholders.map((p: any) => `- ${p.placeholder_name}: ${p.error || p.content}`).join('\n')}`
          }
        }
      }
      
      return null
    }

    const determineStatus = () => {
      if (progress.status === 'completed' && (progress as any).has_errors) {
        return 'warning'
      }
      return progress.status as any
    }

    return (
      <div className="w-full max-w-sm">
        <Progress
          value={progress.progress}
          status={determineStatus()}
          message={getProgressMessage()}
          errorDetails={getErrorDetails()}
          showPercent={true}
          showMessage={true}
          size="sm"
          onRetry={progress.status === 'failed' ? handleRetryTask : undefined}
        />
      </div>
    )
  }

  const columns = [
    {
      key: 'selection',
      title: '',
      width: 50,
      render: (_: any, record: Task) => (
        <Checkbox
          checked={selectedTasks.includes(record.id.toString())}
          onChange={(e) => handleSelectTask(record.id.toString(), e)}
        />
      ),
    },
    {
      key: 'name',
      title: '任务名称',
      dataIndex: 'name',
      render: (name: string, record: Task) => (
        <div>
          <div className="font-medium text-gray-900">{name}</div>
          {record.description && (
            <div className="text-sm text-gray-500 truncate max-w-xs">
              {record.description}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'data_source',
      title: '数据源',
      dataIndex: 'data_source_id',
      render: (dataSourceId: string) => (
        <span className="text-sm text-gray-600">
          {getDataSourceName(dataSourceId)}
        </span>
      ),
    },
    {
      key: 'schedule',
      title: '调度',
      dataIndex: 'schedule',
      render: (schedule?: string) => (
        <div className="flex items-center">
          <ClockIcon className="w-4 h-4 text-gray-400 mr-1" />
          <span className="text-sm font-mono text-gray-600">
            {schedule || '手动执行'}
          </span>
        </div>
      ),
    },
    {
      key: 'status',
      title: '状态',
      dataIndex: 'is_active',
      render: (isActive: boolean, record: Task) => {
        const progress = getTaskProgress(record.id.toString())
        
        if (progress) {
          return <TaskProgressIndicator taskId={record.id.toString()} />
        }
        
        return (
          <Badge variant={isActive ? 'success' : 'secondary'}>
            {isActive ? '运行中' : '已停止'}
          </Badge>
        )
      },
    },
    {
      key: 'created_at',
      title: '创建时间',
      dataIndex: 'created_at',
      render: (createdAt: string) => (
        <span className="text-sm text-gray-500">
          {formatRelativeTime(createdAt)}
        </span>
      ),
    },
    {
      key: 'actions',
      title: '操作',
      width: 200,
      render: (_: any, record: Task) => (
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => router.push(`/tasks/${record.id}`)}
          >
            <EyeIcon className="w-3 h-3" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={async () => {
              try {
                await executeTask(record.id.toString())
                // 执行成功后开始显示进度
              } catch (error) {
                // 错误处理已在store中处理
              }
            }}
            disabled={!record.is_active || !!getTaskProgress(record.id.toString())}
            title={
              !record.is_active ? '任务未启用' :
              getTaskProgress(record.id.toString()) ? '任务执行中' : '执行任务'
            }
          >
            <PlayIcon className="w-3 h-3" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => toggleTaskStatus(record.id.toString(), !record.is_active)}
          >
            {record.is_active ? <PauseIcon className="w-3 h-3" /> : <PlayIcon className="w-3 h-3" />}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => router.push(`/tasks/${record.id}/edit`)}
          >
            <PencilIcon className="w-3 h-3" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setSelectedTask(record)
              setDeleteModalOpen(true)
            }}
          >
            <TrashIcon className="w-3 h-3" />
          </Button>
        </div>
      ),
    },
  ]

  return (
    <AppLayout>
      <PageHeader
        title="任务管理"
        description="创建和管理定时任务，支持复杂的Cron调度表达式"
        actions={
          <div className="flex items-center gap-3">
            {/* WebSocket连接状态 */}
            <div className="flex items-center text-sm text-gray-600">
              <div className={`w-2 h-2 rounded-full mr-2 ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              {wsConnected ? '已连接' : '未连接'}
            </div>
            <Button onClick={() => router.push('/tasks/create')}>
              <PlusIcon className="w-4 h-4 mr-2" />
              创建任务
            </Button>
          </div>
        }
      />

      {/* 搜索和筛选 */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <Input
            placeholder="搜索任务..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            leftIcon={<MagnifyingGlassIcon className="w-4 h-4 text-gray-400" />}
          />
        </div>
        <div className="sm:w-48">
          <select
            className="w-full rounded-md border border-gray-300 bg-white py-2 pl-3 pr-10 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
          >
            <option value="all">全部状态</option>
            <option value="active">运行中</option>
            <option value="inactive">已停止</option>
          </select>
        </div>
      </div>

      {/* 批量操作工具栏 */}
      {selectedTasks.length > 0 && (
        <div className="mb-4 p-4 bg-gray-50 rounded-lg flex items-center justify-between">
          <span className="text-sm text-gray-600">
            已选择 {selectedTasks.length} 个任务
          </span>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={handleBatchEnable}>
              <CheckIcon className="w-3 h-3 mr-1" />
              批量启用
            </Button>
            <Button size="sm" variant="outline" onClick={handleBatchDisable}>
              <PauseIcon className="w-3 h-3 mr-1" />
              批量停用
            </Button>
            <Button 
              size="sm" 
              variant="destructive" 
              onClick={() => setBatchDeleteModalOpen(true)}
            >
              <TrashIcon className="w-3 h-3 mr-1" />
              批量删除
            </Button>
          </div>
        </div>
      )}

      {/* 任务表格 */}
      {loading ? (
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded mb-4"></div>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-100 rounded"></div>
            ))}
          </div>
        </div>
      ) : filteredTasks.length === 0 ? (
        <Empty
          title={searchTerm || statusFilter !== 'all' ? '未找到匹配的任务' : '还没有任务'}
          description={searchTerm || statusFilter !== 'all' ? '尝试调整搜索条件或筛选器' : '创建您的第一个定时任务'}
          action={
            <Button onClick={() => router.push('/tasks/create')}>
              <PlusIcon className="w-4 h-4 mr-2" />
              创建任务
            </Button>
          }
        />
      ) : (
        <div>
          <div className="mb-4 flex items-center gap-2">
            <Checkbox
              checked={selectedTasks.length === filteredTasks.length && filteredTasks.length > 0}
              indeterminate={selectedTasks.length > 0 && selectedTasks.length < filteredTasks.length}
              onChange={handleSelectAll}
              label="全选"
            />
            {selectedTasks.length > 0 && (
              <span className="text-sm text-gray-600">
                已选择 {selectedTasks.length} 项
              </span>
            )}
          </div>
          <Table
            columns={columns}
            dataSource={filteredTasks}
            rowKey="id"
          />
        </div>
      )}

      {/* 删除确认对话框 */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        title="删除任务"
        description={`确定要删除任务"${selectedTask?.name}"吗？此操作无法撤销。`}
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

      {/* 批量删除确认对话框 */}
      <Modal
        isOpen={batchDeleteModalOpen}
        onClose={() => setBatchDeleteModalOpen(false)}
        title="批量删除任务"
        description={`确定要删除选中的 ${selectedTasks.length} 个任务吗？此操作无法撤销。`}
      >
        <div className="flex justify-end space-x-3">
          <Button
            variant="outline"
            onClick={() => setBatchDeleteModalOpen(false)}
          >
            取消
          </Button>
          <Button
            variant="destructive"
            onClick={handleBatchDelete}
          >
            批量删除
          </Button>
        </div>
      </Modal>
    </AppLayout>
  )
}