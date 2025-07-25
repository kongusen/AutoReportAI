'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, Edit, Play, Trash2, Clock, Calendar, FileText, Database, Pause, RefreshCw, XCircle, Repeat, Loader2 } from 'lucide-react'
import { useI18n } from '@/components/providers/I18nProvider'
import { toast } from 'sonner'
import { httpClient } from '@/lib/api/client';

interface Task {
  id: number
  name: string
  description: string
  is_active: boolean
  template: { id: number; name: string; description: string }
  data_source: { id: number; name: string; type: string }
  schedule_type: string
  schedule_config: string
  created_at: string
  updated_at: string
  last_run?: string
  next_run?: string
  userId: string;
}

export default function TaskDetailPage() {
  const { t } = useI18n()
  const router = useRouter()
  const params = useParams()
  const taskId = params.id as string
  
  const [task, setTask] = useState<Task | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)

  // 轮询任务状态
  useEffect(() => {
    if (!taskId) return
    const timer = setInterval(() => {
      fetchTask()
    }, 5000)
    return () => clearInterval(timer)
  }, [taskId])

  const fetchTask = async () => {
    setLoading(true)
    try {
      const response = await httpClient.get(`/v1/tasks/${taskId}`)
      setTask(response.data)
    } catch {
      setTask(null)
    } finally {
      setLoading(false)
    }
  }

  const handleRunTask = async () => {
    setRunning(true)
    try {
      const response = await httpClient.post(`/v1/tasks/${taskId}/run`)
      toast.success(response.data?.message || '任务已开始执行！')
      await fetchTask()
    } catch {
      toast.error('执行任务失败，请稍后重试')
    } finally {
      setRunning(false)
    }
  }

  const handleEnableTask = async () => {
    setActionLoading(true)
    try {
      await httpClient.post(`/v1/tasks/${taskId}/enable`)
      await fetchTask()
      toast.success('任务已启用')
    } catch {
      toast.error('启用任务失败')
    } finally {
      setActionLoading(false)
    }
  }

  const handleDisableTask = async () => {
    setActionLoading(true)
    try {
      const res = await httpClient.post(`/v1/tasks/${taskId}/disable`)
      await fetchTask()
      toast.success('任务已禁用')
    } catch {
      toast.error('禁用任务失败')
    } finally {
      setActionLoading(false)
    }
  }

  const handleRetryTask = async () => {
    setActionLoading(true)
    try {
      const res = await httpClient.post(`/v1/tasks/${taskId}/retry`)
      toast.success('任务已重试')
      await fetchTask()
    } catch {
      toast.error('重试任务失败')
    } finally {
      setActionLoading(false)
    }
  }

  const handleCancelTask = async () => {
    setActionLoading(true)
    try {
      const res = await httpClient.post(`/v1/tasks/${taskId}/cancel`)
      toast.success('任务已取消')
      await fetchTask()
    } catch {
      toast.error('取消任务失败')
    } finally {
      setActionLoading(false)
    }
  }

  const handleDeleteTask = async () => {
    if (!confirm(t('confirmDelete', 'tasks'))) return
    router.push('/tasks')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-2 text-gray-600">{t('loading')}</p>
        </div>
      </div>
    )
  }

  if (!task) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-gray-600">{t('taskNotFound', 'tasks')}</p>
          <Button onClick={() => router.push('/tasks')} className="mt-4">
            {t('backToTasks', 'tasks')}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push('/tasks')}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('back')}
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{task.name}</h1>
            <p className="text-gray-600">{task.description}</p>
          </div>
        </div>
        <div className="flex space-x-2">
          <Button
            onClick={handleRunTask}
            disabled={running || !task.is_active || actionLoading}
          >
            {running ? <span className="mr-2"><Loader2 className="h-4 w-4 animate-spin inline" /></span> : <Play className="mr-2 h-4 w-4" />}
            {running ? t('running', 'tasks') : t('run', 'tasks')}
          </Button>
          {task.is_active ? (
            <Button variant="outline" onClick={handleDisableTask} disabled={actionLoading}>
              {actionLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Pause className="mr-2 h-4 w-4" />}{t('pause', 'tasks')}
            </Button>
          ) : (
            <Button variant="outline" onClick={handleEnableTask} disabled={actionLoading}>
              {actionLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}{t('resume', 'tasks')}
            </Button>
          )}
          <Button variant="outline" onClick={handleRetryTask} disabled={actionLoading}>
            {actionLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Repeat className="mr-2 h-4 w-4" />}{t('retry', 'tasks')}
          </Button>
          <Button variant="outline" onClick={handleCancelTask} disabled={actionLoading}>
            {actionLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <XCircle className="mr-2 h-4 w-4" />}{t('cancel', 'tasks')}
          </Button>
          <Button
            variant="outline"
            onClick={() => router.push(`/tasks/${task.id}/edit`)}
          >
            <Edit className="mr-2 h-4 w-4" />
            {t('edit', 'tasks')}
          </Button>
          <Button
            variant="outline"
            onClick={handleDeleteTask}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            {t('delete', 'tasks')}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <FileText className="mr-2 h-5 w-5" />
              {t('template', 'tasks')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div>
                <span className="font-medium">{task.template.name}</span>
              </div>
              <p className="text-sm text-gray-600">{task.template.description}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Database className="mr-2 h-5 w-5" />
              {t('dataSource', 'tasks')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div>
                <span className="font-medium">{task.data_source.name}</span>
              </div>
              <Badge variant="outline">{task.data_source.type}</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Clock className="mr-2 h-5 w-5" />
            {t('schedule', 'tasks')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-500">{t('scheduleType', 'tasks')}</label>
              <p className="mt-1">{t(task.schedule_type, 'tasks')}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">{t('scheduleConfig', 'tasks')}</label>
              <p className="mt-1">{task.schedule_config}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">{t('status', 'tasks')}</label>
              <div className="mt-1">
                <Badge variant={task.is_active ? 'default' : 'secondary'}>
                  {task.is_active ? t('active', 'tasks') : t('inactive', 'tasks')}
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Calendar className="mr-2 h-5 w-5" />
            {t('executionHistory', 'tasks')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-500">{t('lastRun', 'tasks')}</label>
              <p className="mt-1">
                {task.last_run ? new Date(task.last_run).toLocaleString() : t('never', 'tasks')}
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">{t('nextRun', 'tasks')}</label>
              <p className="mt-1">
                {task.next_run ? new Date(task.next_run).toLocaleString() : t('notScheduled', 'tasks')}
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">{t('created', 'tasks')}</label>
              <p className="mt-1">{new Date(task.created_at).toLocaleString()}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
} 