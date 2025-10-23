'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
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
  StopIcon,
} from '@heroicons/react/24/outline'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { apiClient as api } from '@/lib/api-client'
import { Table } from '@/components/ui/Table'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { Checkbox } from '@/components/ui/Checkbox'
import { Empty } from '@/components/ui/Empty'
import { Progress } from '@/components/ui/Progress'
// 移除列表页任务执行抽屉组件展示
import { useTaskStore } from '@/features/tasks/taskStore'
import { useDataSourceStore } from '@/features/data-sources/dataSourceStore'
import { useTaskUpdates } from '@/hooks/useWebSocket'
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
    getTaskProgress,
    clearTaskProgress
  } = useTaskStore()
  
  const { dataSources, fetchDataSources } = useDataSourceStore()
  
  // 启用WebSocket连接来接收实时任务更新
  const {
    taskUpdates,
    hasTaskUpdate,
    getTaskUpdate,
    clearTaskUpdates
  } = useTaskUpdates()
  
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all')
  const [selectedTasks, setSelectedTasks] = useState<string[]>([])
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [batchDeleteModalOpen, setBatchDeleteModalOpen] = useState(false)
  const [executingTasks, setExecutingTasks] = useState<Set<number>>(new Set())
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    fetchTasks()
    fetchDataSources()
  }, [fetchTasks, fetchDataSources])

  // 检测屏幕尺寸变化
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }

    checkMobile()
    window.addEventListener('resize', checkMobile)

    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  // 同步执行状态：当任务列表更新时，更新本地执行状态
  useEffect(() => {
    const currentlyExecuting = new Set<number>()
    tasks.forEach(task => {
      // 检查任务是否正在执行
      if ((task as any).is_executing || (task as any).current_execution_status === 'processing') {
        currentlyExecuting.add(task.id)
      }
    })

    // 只有状态真正改变时才更新
    if (currentlyExecuting.size !== executingTasks.size ||
        !Array.from(currentlyExecuting).every(id => executingTasks.has(id))) {
      setExecutingTasks(currentlyExecuting)
    }
  }, [tasks])

  // 当WebSocket接收到任务完成/失败消息时，自动刷新任务列表和清除执行状态
  useEffect(() => {
    let hasCompletedTasks = false
    const completedTaskIds: number[] = []

    for (const [taskId, update] of taskUpdates) {
      if (update.status === 'completed' || update.status === 'failed' || update.status === 'cancelled') {
        hasCompletedTasks = true
        completedTaskIds.push(parseInt(taskId))
      }
    }

    if (hasCompletedTasks) {
      // 立即清除本地执行状态
      setExecutingTasks(prev => {
        const newSet = new Set(prev)
        completedTaskIds.forEach(id => newSet.delete(id))
        return newSet
      })

      // 延迟刷新，确保后端状态已更新
      const refreshTimer = setTimeout(() => {
        fetchTasks()
      }, 2000)

      return () => clearTimeout(refreshTimer)
    }
  }, [taskUpdates, fetchTasks])

  // 定期刷新任务状态，特别是在有任务执行时
  useEffect(() => {
    const hasExecutingTasks = executingTasks.size > 0 ||
      tasks.some(task => (task as any).current_execution_status === 'processing')

    if (!hasExecutingTasks) return

    // 如果有任务在执行，每10秒刷新一次（减少频率，因为有WebSocket更新）
    const interval = setInterval(() => {
      fetchTasks()
    }, 10000)

    return () => clearInterval(interval)
  }, [executingTasks.size > 0, tasks.some(task => (task as any).current_execution_status === 'processing'), fetchTasks])

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
    // 优先使用WebSocket实时更新的进度，然后才是本地状态
    const wsProgress = getTaskUpdate(taskId)
    const localProgress = getTaskProgress(taskId)
    const progress = wsProgress || localProgress
    
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
      if ('workflow_step' in progress && progress.workflow_step) {
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
        if ('error_details' in progress && progress.error_details) {
          return progress.error_details
        }
        
        // 尝试从各个可能的字段获取错误详情
        const details = (progress as any).error || 
                       (progress as any).traceback ||
                       (progress as any).details
        return details
      }
      
      // 警告状态的详情 - 显示占位符处理结果
      if (progress.status === 'completed' && 'has_errors' in progress && progress.has_errors && 'placeholder_results' in progress && progress.placeholder_results) {
        const failedPlaceholders = progress.placeholder_results.filter(p => !p.success)
        if (failedPlaceholders.length > 0) {
          return `${failedPlaceholders.length} 个占位符处理失败:\n${failedPlaceholders.map(p => `- ${p.placeholder_name}: ${p.error || p.content}`).join('\n')}`
        }
      }
      
      return null
    }

    const determineStatus = () => {
      if (progress.status === 'completed' && 'has_errors' in progress && progress.has_errors) {
        return 'warning'
      }
      return progress.status as any
    }

    const getAgentExecutionInfo = () => {
      if ('agent_execution_times' in progress && progress.agent_execution_times && Object.keys(progress.agent_execution_times).length > 0) {
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
        {'placeholder_results' in progress && progress.placeholder_results && progress.placeholder_results.length > 0 && (
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
      width: '24px',
      className: 'w-6 p-0',
      render: (_: any, record: Task) => (
        <input
          type="checkbox"
          checked={selectedTasks.includes(record.id.toString())}
          onChange={(e) => handleSelectTask(record.id.toString(), e)}
          className="h-4 w-4 rounded border-gray-300 text-gray-600 focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
        />
      ),
    },
    {
      key: 'name',
      title: '任务名称',
      dataIndex: 'name',
      className: 'min-w-0', // 允许内容收缩
      render: (name: string, record: Task) => (
        <div className="min-w-0">
          <div className="font-medium text-gray-900 truncate">{name}</div>
          {record.description && (
            <div className="text-sm text-gray-500 truncate">
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
      className: 'hidden sm:table-cell', // 小屏幕隐藏
      render: (dataSourceId: string) => (
        <span className="text-sm text-gray-600 truncate block">
          {getDataSourceName(dataSourceId)}
        </span>
      ),
    },
    {
      key: 'schedule',
      title: '调度',
      dataIndex: 'schedule',
      className: 'hidden md:table-cell', // 中等屏幕以下隐藏
      render: (schedule: string, record: Task) => (
        <div className="space-y-1 min-w-0">
          <div className="flex items-center min-w-0">
            <ClockIcon className="w-4 h-4 text-gray-400 mr-1 flex-shrink-0" />
            <span className="text-sm font-mono text-gray-600 truncate">
              {schedule || '手动执行'}
            </span>
          </div>
          {record.report_period && (
            <div className="text-xs text-gray-500 truncate">
              {
                record.report_period === 'daily' ? '每日' :
                record.report_period === 'weekly' ? '每周' :
                record.report_period === 'monthly' ? '每月' :
                record.report_period === 'yearly' ? '每年' : record.report_period
              }
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'workflow_info',
      title: 'AI工作流',
      dataIndex: 'workflow_type',
      className: 'hidden lg:table-cell', // 大屏幕才显示
      render: (workflowType: string, record: Task) => {
        const workflowInfo = getWorkflowTypeInfo(workflowType || 'simple_report')
        const modeInfo = getProcessingModeInfo(record.processing_mode || 'intelligent')

        return (
          <div className="space-y-1">
            <Badge variant="outline" className={`text-${workflowInfo.color}-600 border-${workflowInfo.color}-200 text-xs`}>
              {workflowInfo.label}
            </Badge>
            <div className="text-xs text-gray-500 truncate">
              {modeInfo.label}
            </div>
          </div>
        )
      },
    },
    {
      key: 'status',
      title: '状态',
      dataIndex: 'status',
      className: 'min-w-0',
      render: (status: TaskStatus, record: Task) => {
        const taskId = record.id.toString()
        const wsProgress = getTaskUpdate(taskId)
        const localProgress = getTaskProgress(taskId)
        const progress = wsProgress || localProgress
        const isExecuting = executingTasks.has(record.id)

        // 检查API返回的真实执行状态
        const apiExecutionStatus = (record as any).current_execution_status
        const apiProgress = (record as any).current_execution_progress || 0
        const apiCurrentStep = (record as any).current_execution_step

        // 如果API显示正在执行，显示进度条
        if (apiExecutionStatus === 'processing' || progress || isExecuting) {
          return (
            <div className="space-y-1 min-w-0">
              <Badge variant="info" className="text-xs">执行中</Badge>
              <div className="w-full max-w-24">
                <div className="w-full bg-gray-200 rounded-full h-1.5">
                  <div
                    className="bg-blue-500 h-1.5 rounded-full transition-all duration-500"
                    style={{ width: `${apiProgress || progress?.progress || 0}%` }}
                  ></div>
                </div>
                <div className="text-xs text-gray-500 mt-1 truncate">
                  {apiCurrentStep || progress?.message || '执行中...'}
                </div>
              </div>
            </div>
          )
        }

        // 显示任务状态和激活状态
        const statusInfo = getTaskStatusInfo(status || 'pending')

        return (
          <div className="space-y-1 min-w-0">
            <div className="flex items-center gap-1 flex-wrap">
              <Badge variant={statusInfo.color as any} className="text-xs">
                {statusInfo.label}
              </Badge>
              {!record.is_active && (
                <Badge variant="secondary" className="text-xs">停用</Badge>
              )}
            </div>
            {record.last_execution_at && (
              <div className="text-xs text-gray-500 truncate">
                {formatRelativeTime(record.last_execution_at)}
              </div>
            )}
          </div>
        )
      },
    },
    {
      key: 'execution_stats',
      title: '统计',
      dataIndex: 'execution_count',
      className: 'hidden xl:table-cell', // 超大屏幕才显示
      render: (executionCount: number, record: Task) => {
        const successRate = record.success_rate || 0
        const avgTime = record.average_execution_time || 0

        return (
          <div className="space-y-1 text-xs">
            <div className="flex items-center gap-1">
              <span className="text-gray-600">执行:</span>
              <span className="font-medium">{executionCount || 0}</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-gray-600">成功:</span>
              <span className={`font-medium ${successRate >= 0.8 ? 'text-green-600' : successRate >= 0.5 ? 'text-yellow-600' : 'text-red-600'}`}>
                {formatSuccessRate(successRate)}
              </span>
            </div>
            {avgTime > 0 && (
              <div className="flex items-center gap-1">
                <span className="text-gray-600">耗时:</span>
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
      className: 'hidden lg:table-cell', // 大屏幕才显示
      render: (createdAt: string) => (
        <span className="text-sm text-gray-500">
          {formatRelativeTime(createdAt)}
        </span>
      ),
    },
    {
      key: 'actions',
      title: '操作',
      width: 140,
      fixed: 'right' as const,
      align: 'right' as const,
      className: 'min-w-[140px]',
      render: (_: any, record: Task) => {
        // 使用多种状态源来判断执行状态
        const apiExecutionStatus = (record as any).current_execution_status
        const isExecutingFromAPI = apiExecutionStatus === 'processing' || apiExecutionStatus === 'pending'
        const isExecutingFromLocal = executingTasks.has(record.id)

        // 检查WebSocket任务更新状态
        const wsTaskUpdate = getTaskUpdate(record.id.toString())
        const isExecutingFromWS = wsTaskUpdate &&
          !['completed', 'failed', 'cancelled'].includes(wsTaskUpdate.status)

        // 检查本地任务进度状态
        const localProgress = getTaskProgress(record.id.toString())
        const isExecutingFromProgress = localProgress &&
          !['completed', 'failed', 'cancelled'].includes(localProgress.status)

        const isExecuting = isExecutingFromAPI || isExecutingFromLocal || isExecutingFromWS || isExecutingFromProgress
        const isScheduledTask = Boolean((record.schedule || '').trim())
        const typeLabel = isScheduledTask ? '定时' : '手动'

        const baseIconClass = 'w-3.5 h-3.5'
        const buttonClass = 'h-8 w-8 p-0 flex-shrink-0 rounded-full'

        const handleExecuteNow = async () => {
          try {
            setExecutingTasks(prev => new Set([...prev, record.id]))
            await executeTask(record.id.toString())
          } catch (error) {
            setExecutingTasks(prev => {
              const newSet = new Set(prev)
              newSet.delete(record.id)
              return newSet
            })
          }
        }

        const handleCancelExecution = async () => {
          try {
            const response = await api.post(`/tasks/${record.id}/cancel`) as any

            setExecutingTasks(prev => {
              const newSet = new Set(prev)
              newSet.delete(record.id)
              return newSet
            })

            clearTaskProgress(record.id.toString())
            fetchTasks()

            if (response.data?.success) {
              toast.success('任务已取消')
            } else {
              toast.info(response.data?.message || '任务已结束')
            }
          } catch (error: any) {
            console.error('Failed to cancel task:', error)

            setExecutingTasks(prev => {
              const newSet = new Set(prev)
              newSet.delete(record.id)
              return newSet
            })
            clearTaskProgress(record.id.toString())

            toast.error('取消任务失败')
          }
        }

        const showManualRun = !isScheduledTask && !isExecuting
        const showScheduledRun = isScheduledTask && record.is_active && !isExecuting
        const showResume = isScheduledTask && !record.is_active && !isExecuting
        const showPause = isScheduledTask && record.is_active && !isExecuting
        const showEdit = !isExecuting
        const showDelete = !isExecuting && (!isScheduledTask || !record.is_active)

        return (
          <div className="flex flex-col items-end gap-1">
            <div className="flex items-center gap-2">
              <span className="text-[11px] uppercase tracking-wide text-gray-400">{typeLabel}</span>
              <div className="flex items-center gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => router.push(`/tasks/${record.id}`)}
                  title="查看详情"
                  className={`${buttonClass} hover:bg-gray-100`}
                >
                  <EyeIcon className={baseIconClass} />
                </Button>

                {(showManualRun || showScheduledRun) && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleExecuteNow}
                    title="立即执行"
                    className={`${buttonClass} text-green-600 hover:text-green-700 hover:bg-green-50`}
                  >
                    <PlayIcon className={baseIconClass} />
                  </Button>
                )}

                {showResume && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => toggleTaskStatus(record.id.toString(), true)}
                    title="启用任务"
                    className={`${buttonClass} text-blue-600 hover:text-blue-700 hover:bg-blue-50`}
                  >
                    <CheckIcon className={baseIconClass} />
                  </Button>
                )}

                {showPause && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => toggleTaskStatus(record.id.toString(), false)}
                    title="暂停任务"
                    className={`${buttonClass} text-yellow-600 hover:text-yellow-700 hover:bg-yellow-50`}
                  >
                    <PauseIcon className={baseIconClass} />
                  </Button>
                )}

                {showEdit && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => router.push(`/tasks/${record.id}/edit`)}
                    title="编辑任务"
                    className={`${buttonClass} hidden md:inline-flex hover:bg-gray-100`}
                  >
                    <PencilIcon className={baseIconClass} />
                  </Button>
                )}

                {showDelete && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setSelectedTask(record)
                      setDeleteModalOpen(true)
                    }}
                    title="删除任务"
                    className={`${buttonClass} text-red-600 hover:text-red-700 hover:bg-red-50 hidden lg:inline-flex`}
                  >
                    <TrashIcon className={baseIconClass} />
                  </Button>
                )}

                {isExecuting && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleCancelExecution}
                    title="停止执行"
                    className={`${buttonClass} text-red-600 hover:text-red-700 hover:bg-red-50`}
                  >
                    <StopIcon className={baseIconClass} />
                  </Button>
                )}
              </div>
            </div>
            {isExecuting && (
              <div className="flex items-center gap-1 text-[11px] text-gray-400">
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></div>
                <span>执行中</span>
              </div>
            )}
          </div>
        )
      },
    },
  ]

  return (
    <>
      <PageHeader
        title="任务管理"
        description="创建和管理定时任务，支持复杂的Cron调度表达式"
        actions={
          <div className="flex items-center gap-3">
            {/* WebSocket任务更新状态 */}
            <div className="flex items-center text-sm text-gray-600">
              <div className={`w-2 h-2 rounded-full mr-2 ${taskUpdates.size > 0 ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
              实时更新 ({taskUpdates.size} 个任务)
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
          <div className="overflow-hidden">
            <Table
              columns={columns}
              dataSource={filteredTasks}
              rowKey="id"
              className="table-fixed"
              scroll={{ x: '100%' }}
              expandable={{
                expandedRowRender: (record: Task) => {
                  // 只在小屏幕上显示隐藏的信息，不展示执行抽屉
                  return (
                    <div className="py-2 bg-gray-50 space-y-2 md:hidden">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-500">数据源:</span>
                          <span className="ml-2 text-gray-900">{getDataSourceName(record.data_source_id)}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">调度:</span>
                          <span className="ml-2 text-gray-900">{record.schedule || '手动执行'}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">创建时间:</span>
                          <span className="ml-2 text-gray-900">{formatRelativeTime(record.created_at)}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">执行次数:</span>
                          <span className="ml-2 text-gray-900">{record.execution_count || 0}次</span>
                        </div>
                      </div>
                      {/* 移动端操作按钮 */}
                      <div className="flex gap-2 pt-2 border-t border-gray-200">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => router.push(`/tasks/${record.id}/edit`)}
                        >
                          <PencilIcon className="w-3 h-3 mr-1" />
                          编辑
                        </Button>
                        {!record.is_active && (
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => {
                              setSelectedTask(record)
                              setDeleteModalOpen(true)
                            }}
                          >
                            <TrashIcon className="w-3 h-3 mr-1" />
                            删除
                          </Button>
                        )}
                      </div>
                    </div>
                  )
                },
                rowExpandable: (_record: Task) => isMobile,
              }}
            />
          </div>
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
    </>
  )
}
