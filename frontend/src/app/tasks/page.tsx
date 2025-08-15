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
import { 
  getTaskStatusInfo, 
  formatRelativeTime, 
  getProcessingModeInfo, 
  getWorkflowTypeInfo,
  formatExecutionTime,
  formatSuccessRate 
} from '@/utils'
import { Task, TaskStatus } from '@/types'

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
      // 优先显示Agent工作流步骤
      if (progress.workflow_step) {
        return progress.workflow_step
      }
      
      if (progress.current_step && progress.current_step !== progress.message) {
        return progress.current_step
      }
      
      // 根据状态显示默认消息
      const statusMessages: Record<string, string> = {
        'agent_orchestrating': 'AI智能编排中...',
        'processing': '数据处理中...',
        'generating': '报告生成中...',
        'analyzing': '数据分析中...',
        'querying': '数据查询中...'
      }
      
      return statusMessages[progress.status] || progress.message || '处理中...'
    }

    // 获取错误详情
    const getErrorDetails = () => {
      if (progress.status === 'failed') {
        // 优先显示error_details
        if (progress.error_details) {
          return progress.error_details
        }
        
        // 尝试从各个可能的字段获取错误详情
        const details = (progress as any).error || 
                       (progress as any).traceback ||
                       (progress as any).details
        return details
      }
      
      // 警告状态的详情 - 显示占位符处理结果
      if (progress.status === 'completed' && progress.has_errors && progress.placeholder_results) {
        const failedPlaceholders = progress.placeholder_results.filter(p => !p.success)
        if (failedPlaceholders.length > 0) {
          return `${failedPlaceholders.length} 个占位符处理失败:\n${failedPlaceholders.map(p => `- ${p.placeholder_name}: ${p.error || p.content}`).join('\n')}`
        }
      }
      
      return null
    }

    const determineStatus = () => {
      if (progress.status === 'completed' && progress.has_errors) {
        return 'warning'
      }
      return progress.status as any
    }

    const getAgentExecutionInfo = () => {
      if (progress.agent_execution_times && Object.keys(progress.agent_execution_times).length > 0) {
        return Object.entries(progress.agent_execution_times)
          .map(([agent, time]) => `${agent}: ${formatExecutionTime(time)}`)
          .join('\n')
      }
      return null
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
        
        {/* Agent执行信息 */}
        {progress.status === 'agent_orchestrating' && getAgentExecutionInfo() && (
          <div className="mt-1 text-xs text-gray-500">
            <details className="cursor-pointer">
              <summary className="hover:text-gray-700">Agent执行详情</summary>
              <div className="mt-1 p-2 bg-gray-50 rounded text-xs font-mono whitespace-pre-line">
                {getAgentExecutionInfo()}
              </div>
            </details>
          </div>
        )}
        
        {/* 占位符处理结果 */}
        {progress.placeholder_results && progress.placeholder_results.length > 0 && (
          <div className="mt-1 text-xs text-gray-500">
            <details className="cursor-pointer">
              <summary className="hover:text-gray-700">
                占位符处理 ({progress.placeholder_results.filter(p => p.success).length}/{progress.placeholder_results.length})
              </summary>
              <div className="mt-1 space-y-1">
                {progress.placeholder_results.map((result, index) => (
                  <div key={index} className={`flex items-center gap-2 text-xs ${result.success ? 'text-green-600' : 'text-red-600'}`}>
                    <span className={`w-2 h-2 rounded-full ${result.success ? 'bg-green-500' : 'bg-red-500'}`} />
                    <span className="truncate">{result.placeholder_name}</span>
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}
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
      key: 'workflow_info',
      title: 'AI工作流',
      dataIndex: 'workflow_type',
      render: (workflowType: string, record: Task) => {
        const workflowInfo = getWorkflowTypeInfo(workflowType || 'simple_report')
        const modeInfo = getProcessingModeInfo(record.processing_mode || 'intelligent')
        
        return (
          <div className="space-y-1">
            <div className="flex items-center">
              <Badge variant="outline" className={`text-${workflowInfo.color}-600 border-${workflowInfo.color}-200`}>
                {workflowInfo.label}
              </Badge>
            </div>
            <div className="text-xs text-gray-500">
              {modeInfo.label}
            </div>
          </div>
        )
      },
    },
    {
      key: 'status',
      title: '执行状态',
      dataIndex: 'status',
      render: (status: TaskStatus, record: Task) => {
        const progress = getTaskProgress(record.id.toString())
        
        if (progress) {
          return <TaskProgressIndicator taskId={record.id.toString()} />
        }
        
        // 显示任务状态和激活状态
        const statusInfo = getTaskStatusInfo(status || 'pending')
        
        return (
          <div className="space-y-1">
            <Badge variant={statusInfo.color as any}>
              {statusInfo.label}
            </Badge>
            <div className="text-xs text-gray-500">
              {record.is_active ? '已启用' : '已停用'}
            </div>
          </div>
        )
      },
    },
    {
      key: 'execution_stats',
      title: '执行统计',
      dataIndex: 'execution_count',
      render: (executionCount: number, record: Task) => {
        const successRate = record.success_rate || 0
        const avgTime = record.average_execution_time || 0
        
        return (
          <div className="space-y-1 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-gray-600">执行:</span>
              <span className="font-medium">{executionCount || 0}次</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-600">成功率:</span>
              <span className={`font-medium ${successRate >= 0.8 ? 'text-green-600' : successRate >= 0.5 ? 'text-yellow-600' : 'text-red-600'}`}>
                {formatSuccessRate(successRate)}
              </span>
            </div>
            {avgTime > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-gray-600">平均:</span>
                <span className="font-medium text-blue-600">
                  {formatExecutionTime(avgTime)}
                </span>
              </div>
            )}
          </div>
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