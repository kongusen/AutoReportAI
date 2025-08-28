'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { 
  ArrowLeftIcon,
  PlayIcon,
  PauseIcon,
  PencilIcon,
  TrashIcon,
  ClockIcon,
  CalendarIcon,
  DocumentTextIcon,
  CircleStackIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Modal } from '@/components/ui/Modal'
import { useTaskStore } from '@/features/tasks/taskStore'
import { useDataSourceStore } from '@/features/data-sources/dataSourceStore'
import { formatRelativeTime } from '@/utils'
import { Task } from '@/types'

export default function TaskDetailPage() {
  const params = useParams()
  const router = useRouter()
  const taskId = params.id as string

  const { 
    tasks, 
    loading, 
    fetchTasks, 
    deleteTask, 
    toggleTaskStatus, 
    executeTask,
    getTaskProgress
  } = useTaskStore()
  
  const { dataSources, fetchDataSources } = useDataSourceStore()
  
  const [task, setTask] = useState<Task | null>(null)
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [taskLoading, setTaskLoading] = useState(true)

  useEffect(() => {
    const loadData = async () => {
      setTaskLoading(true)
      try {
        await Promise.all([
          fetchTasks(),
          fetchDataSources()
        ])
      } finally {
        setTaskLoading(false)
      }
    }
    loadData()
  }, [fetchTasks, fetchDataSources])

  useEffect(() => {
    if (tasks.length > 0 && taskId) {
      const foundTask = tasks.find(t => t.id.toString() === taskId)
      setTask(foundTask || null)
    }
  }, [tasks, taskId])

  const handleDeleteConfirm = async () => {
    if (!task) return
    
    try {
      await deleteTask(task.id.toString())
      setDeleteModalOpen(false)
      router.push('/tasks')
    } catch (error) {
      // 错误处理已在store中处理
    }
  }

  const getDataSourceName = (dataSourceId: string) => {
    const dataSource = dataSources.find(ds => ds.id === dataSourceId)
    return dataSource?.display_name || dataSource?.name || '未知数据源'
  }

  if (loading || taskLoading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!task) {
    return (
      <div className="text-center py-12">
        <ExclamationTriangleIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">任务不存在</h2>
        <p className="text-gray-600 mb-6">找不到指定的任务，可能已被删除</p>
        <Button onClick={() => router.push('/tasks')}>
          <ArrowLeftIcon className="w-4 h-4 mr-2" />
          返回任务列表
        </Button>
      </div>
    )
  }

  const progress = getTaskProgress(task.id.toString())

  return (
    <>
      <PageHeader
        title={task.name}
        description={task.description || '任务详情'}
        breadcrumbs={[
          { label: '任务管理', href: '/tasks' },
          { label: task.name },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => executeTask(task.id.toString())}
              disabled={!task.is_active || !!progress}
            >
              <PlayIcon className="w-4 h-4 mr-2" />
              {progress ? '执行中...' : '立即执行'}
            </Button>
            <Button
              variant="outline"
              onClick={() => toggleTaskStatus(task.id.toString(), !task.is_active)}
            >
              {task.is_active ? (
                <>
                  <PauseIcon className="w-4 h-4 mr-2" />
                  暂停
                </>
              ) : (
                <>
                  <PlayIcon className="w-4 h-4 mr-2" />
                  启动
                </>
              )}
            </Button>
            <Button
              variant="outline"
              onClick={() => router.push(`/tasks/${task.id}/edit`)}
            >
              <PencilIcon className="w-4 h-4 mr-2" />
              编辑
            </Button>
            <Button
              variant="destructive"
              onClick={() => setDeleteModalOpen(true)}
            >
              <TrashIcon className="w-4 h-4 mr-2" />
              删除
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 基本信息 */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>基本信息</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <dt className="text-sm font-medium text-gray-500">任务名称</dt>
                  <dd className="mt-1 text-sm text-gray-900">{task.name}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">状态</dt>
                  <dd className="mt-1">
                    <Badge variant={task.is_active ? 'success' : 'secondary'}>
                      {task.is_active ? '运行中' : '已停止'}
                    </Badge>
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">数据源</dt>
                  <dd className="mt-1 flex items-center text-sm text-gray-900">
                    <CircleStackIcon className="w-4 h-4 text-gray-400 mr-2" />
                    {getDataSourceName(task.data_source_id)}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">调度表达式</dt>
                  <dd className="mt-1 flex items-center text-sm text-gray-900">
                    <ClockIcon className="w-4 h-4 text-gray-400 mr-2" />
                    <code className="bg-gray-100 px-2 py-1 rounded text-xs">
                      {task.schedule || '手动执行'}
                    </code>
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">创建时间</dt>
                  <dd className="mt-1 flex items-center text-sm text-gray-900">
                    <CalendarIcon className="w-4 h-4 text-gray-400 mr-2" />
                    {formatRelativeTime(task.created_at)}
                  </dd>
                </div>
                {task.updated_at && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">最后更新</dt>
                    <dd className="mt-1 flex items-center text-sm text-gray-900">
                      <CalendarIcon className="w-4 h-4 text-gray-400 mr-2" />
                      {formatRelativeTime(task.updated_at)}
                    </dd>
                  </div>
                )}
              </div>
              
              {task.description && (
                <div className="mt-6">
                  <dt className="text-sm font-medium text-gray-500 mb-2">描述</dt>
                  <dd className="text-sm text-gray-900 bg-gray-50 p-3 rounded-md">
                    {task.description}
                  </dd>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 任务配置 */}
          {false && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <DocumentTextIcon className="w-5 h-5 mr-2" />
                  任务配置
                </CardTitle>
              </CardHeader>
              <CardContent>
                {false && (
                  <div className="mb-4">
                    <dt className="text-sm font-medium text-gray-500 mb-2">SQL查询</dt>
                    <dd>
                      <pre className="bg-gray-900 text-gray-100 p-3 rounded-md text-xs overflow-x-auto">
                        <code>{}</code>
                      </pre>
                    </dd>
                  </div>
                )}
                
                {false && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500 mb-2">参数配置</dt>
                    <dd>
                      <pre className="bg-gray-50 p-3 rounded-md text-xs overflow-x-auto">
                        <code>{}</code>
                      </pre>
                    </dd>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* 执行状态 */}
        <div className="space-y-6">
          {/* 当前执行进度 */}
          {progress && (
            <Card>
              <CardHeader>
                <CardTitle>执行进度</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <Progress 
                    value={progress.progress} 
                    status={progress.status as any}
                    message={progress.message}
                    showPercent={true}
                    showMessage={true}
                    size="default"
                    onRetry={progress.status === 'failed' ? async () => {
                      try {
                        await executeTask(task.id.toString())
                      } catch (error) {
                        // 错误处理已在store中处理
                      }
                    } : undefined}
                  />
                </div>
              </CardContent>
            </Card>
          )}

          {/* 快捷操作 */}
          <Card>
            <CardHeader>
              <CardTitle>快捷操作</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button 
                className="w-full justify-start"
                variant="ghost"
                onClick={() => executeTask(task.id.toString())}
                disabled={!task.is_active || !!progress}
              >
                <PlayIcon className="w-4 h-4 mr-2" />
                {progress ? '执行中...' : '立即执行'}
              </Button>
              <Button 
                className="w-full justify-start"
                variant="ghost"
                onClick={() => toggleTaskStatus(task.id.toString(), !task.is_active)}
              >
                {task.is_active ? (
                  <>
                    <PauseIcon className="w-4 h-4 mr-2" />
                    暂停任务
                  </>
                ) : (
                  <>
                    <PlayIcon className="w-4 h-4 mr-2" />
                    启动任务
                  </>
                )}
              </Button>
              <Button 
                className="w-full justify-start"
                variant="ghost"
                onClick={() => router.push(`/tasks/${task.id}/edit`)}
              >
                <PencilIcon className="w-4 h-4 mr-2" />
                编辑任务
              </Button>
              <hr className="my-2" />
              <Button 
                className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50"
                variant="ghost"
                onClick={() => setDeleteModalOpen(true)}
              >
                <TrashIcon className="w-4 h-4 mr-2" />
                删除任务
              </Button>
            </CardContent>
          </Card>

          {/* 执行统计 */}
          <Card>
            <CardHeader>
              <CardTitle>执行统计</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">总执行次数</span>
                <span className="text-sm font-medium">{task.execution_count || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">成功次数</span>
                <span className="text-sm font-medium text-green-600">{task.success_count || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">失败次数</span>
                <span className="text-sm font-medium text-red-600">{task.failure_count || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">成功率</span>
                <span className={`text-sm font-medium ${
                  (task.success_rate || 0) >= 0.8 ? 'text-green-600' : 
                  (task.success_rate || 0) >= 0.5 ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {((task.success_rate || 0) * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">平均执行时间</span>
                <span className="text-sm font-medium text-blue-600">
                  {task.average_execution_time ? `${task.average_execution_time.toFixed(1)}s` : '-'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">上次执行</span>
                <span className="text-sm font-medium">
                  {task.last_execution_at ? formatRelativeTime(task.last_execution_at) : '从未执行'}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 删除确认对话框 */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        title="删除任务"
        description={`确定要删除任务"${task.name}"吗？此操作无法撤销。`}
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
    </>
  )
}