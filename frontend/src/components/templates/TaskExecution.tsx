'use client'

import React, { useState, useEffect } from 'react'
import { 
  PlayIcon, 
  PauseIcon, 
  StopIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  DocumentDuplicateIcon,
  ChartBarIcon,
  DocumentTextIcon,
  EnvelopeIcon,
  CloudArrowUpIcon
} from '@heroicons/react/24/outline'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { Switch } from '@/components/ui/Switch'
import { Select } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

interface TaskExecutionProps {
  templateId: string
  dataSources: Array<{
    id: string
    name: string
    source_type: string
  }>
  onTaskStart?: (taskId: string) => void
  onTaskComplete?: (result: any) => void
}

interface TaskStatus {
  task_id: string
  status: string
  current_step: string
  progress: number
  start_time: string
  updated_at?: string
  error?: string
}

interface TaskConfig {
  output_format: string
  send_email: boolean
  email_recipients: string[]
  attach_files: boolean
  cron_expression?: string
  execution_time?: string
  force_repair: boolean
}

export function TaskExecution({ templateId, dataSources, onTaskStart, onTaskComplete }: TaskExecutionProps) {
  const [isExecuting, setIsExecuting] = useState(false)
  const [currentTask, setCurrentTask] = useState<TaskStatus | null>(null)
  const [taskConfig, setTaskConfig] = useState<TaskConfig>({
    output_format: 'docx',
    send_email: false,
    email_recipients: [],
    attach_files: true,
    force_repair: true
  })
  const [selectedDataSources, setSelectedDataSources] = useState<string[]>([])
  const [emailInput, setEmailInput] = useState('')

  // 轮询任务状态
  useEffect(() => {
    let interval: NodeJS.Timeout

    if (currentTask && ['validating', 'processing', 'generating', 'exporting', 'delivering'].includes(currentTask.status)) {
      interval = setInterval(async () => {
        try {
          const response = await api.get(`/placeholders/task-status/${currentTask.task_id}`)
          if (response.data.success) {
            const newStatus = response.data.data
            setCurrentTask(newStatus)
            
            if (['completed', 'failed', 'cancelled'].includes(newStatus.status)) {
              setIsExecuting(false)
              if (newStatus.status === 'completed' && onTaskComplete) {
                onTaskComplete(newStatus)
              }
            }
          }
        } catch (error) {
          console.error('获取任务状态失败:', error)
        }
      }, 2000) // 每2秒轮询一次
    }

    return () => {
      if (interval) {
        clearInterval(interval)
      }
    }
  }, [currentTask, onTaskComplete])

  const handleStartTask = async () => {
    if (selectedDataSources.length === 0) {
      toast.error('请选择至少一个数据源')
      return
    }

    try {
      setIsExecuting(true)
      
      // 构建请求参数
      const requestData = {
        template_id: templateId,
        data_source_ids: selectedDataSources,
        execution_context: {
          force_repair: taskConfig.force_repair,
          optimization_level: 'enhanced'
        },
        output_format: taskConfig.output_format,
        delivery_config: {
          send_email: taskConfig.send_email,
          email_recipients: taskConfig.email_recipients,
          attach_files: taskConfig.attach_files
        }
      }

      // 添加时间上下文（如果配置了）
      if (taskConfig.cron_expression) {
        requestData.time_context = {
          cron_expression: taskConfig.cron_expression,
          execution_time: taskConfig.execution_time || new Date().toISOString(),
          task_type: 'scheduled'
        }
      }

      toast.loading('启动报告生成任务...', { duration: 1000 })

      const response = await api.post('/placeholders/generate-report', requestData)
      
      if (response.data.success) {
        const taskData = response.data.data
        setCurrentTask({
          task_id: taskData.task_id,
          status: taskData.status,
          current_step: '初始化任务',
          progress: 0,
          start_time: taskData.started_at
        })
        
        if (onTaskStart) {
          onTaskStart(taskData.task_id)
        }
        
        toast.success('报告生成任务已启动')
      } else {
        throw new Error(response.data.message || '启动任务失败')
      }
    } catch (error: any) {
      console.error('启动任务失败:', error)
      toast.error(error.response?.data?.detail || error.message || '启动任务失败')
      setIsExecuting(false)
    }
  }

  const handleCancelTask = async () => {
    if (!currentTask) return

    try {
      const response = await api.post(`/placeholders/cancel-task/${currentTask.task_id}`)
      
      if (response.data.success) {
        setCurrentTask(prev => prev ? { ...prev, status: 'cancelled' } : null)
        setIsExecuting(false)
        toast.success('任务已取消')
      }
    } catch (error: any) {
      console.error('取消任务失败:', error)
      toast.error('取消任务失败')
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'validating':
        return <ClockIcon className="w-5 h-5 text-blue-500 animate-spin" />
      case 'processing':
        return <ChartBarIcon className="w-5 h-5 text-yellow-500" />
      case 'generating':
        return <DocumentTextIcon className="w-5 h-5 text-purple-500" />
      case 'exporting':
        return <DocumentDuplicateIcon className="w-5 h-5 text-indigo-500" />
      case 'delivering':
        return <EnvelopeIcon className="w-5 h-5 text-blue-500" />
      case 'completed':
        return <CheckCircleIcon className="w-5 h-5 text-green-500" />
      case 'failed':
        return <ExclamationTriangleIcon className="w-5 h-5 text-red-500" />
      default:
        return <PlayIcon className="w-5 h-5 text-gray-500" />
    }
  }

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'failed':
        return 'destructive'
      case 'cancelled':
        return 'secondary'
      default:
        return 'default'
    }
  }

  const addEmailRecipient = () => {
    if (emailInput && !taskConfig.email_recipients.includes(emailInput)) {
      setTaskConfig(prev => ({
        ...prev,
        email_recipients: [...prev.email_recipients, emailInput]
      }))
      setEmailInput('')
    }
  }

  const removeEmailRecipient = (email: string) => {
    setTaskConfig(prev => ({
      ...prev,
      email_recipients: prev.email_recipients.filter(e => e !== email)
    }))
  }

  return (
    <div className="space-y-6">
      {/* 任务配置 */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold">报告生成配置</h3>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 数据源选择 */}
          <div>
            <label className="block text-sm font-medium mb-2">选择数据源</label>
            <Select
              multiple
              value={selectedDataSources}
              onValueChange={setSelectedDataSources}
              placeholder="选择数据源"
              disabled={isExecuting}
            >
              {dataSources.map((ds) => (
                <option key={ds.id} value={ds.id}>
                  {ds.name} ({ds.source_type})
                </option>
              ))}
            </Select>
          </div>

          {/* 输出格式 */}
          <div>
            <label className="block text-sm font-medium mb-2">输出格式</label>
            <Select
              value={taskConfig.output_format}
              onValueChange={(value) => setTaskConfig(prev => ({ ...prev, output_format: value }))}
              disabled={isExecuting}
            >
              <option value="docx">Word文档 (.docx)</option>
              <option value="pdf">PDF文档 (.pdf)</option>
              <option value="html">HTML文档 (.html)</option>
            </Select>
          </div>

          {/* 强制修复占位符 */}
          <div className="flex items-center space-x-2">
            <Switch
              checked={taskConfig.force_repair}
              onCheckedChange={(checked) => setTaskConfig(prev => ({ ...prev, force_repair: checked }))}
              disabled={isExecuting}
            />
            <label className="text-sm">强制验证和修复占位符SQL</label>
          </div>

          {/* 邮件配置 */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <Switch
                checked={taskConfig.send_email}
                onCheckedChange={(checked) => setTaskConfig(prev => ({ ...prev, send_email: checked }))}
                disabled={isExecuting}
              />
              <label className="text-sm">发送邮件通知</label>
            </div>

            {taskConfig.send_email && (
              <div className="space-y-2">
                <div className="flex space-x-2">
                  <Input
                    type="email"
                    placeholder="输入邮箱地址"
                    value={emailInput}
                    onChange={(e) => setEmailInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && addEmailRecipient()}
                    disabled={isExecuting}
                  />
                  <Button onClick={addEmailRecipient} disabled={isExecuting}>
                    添加
                  </Button>
                </div>

                {taskConfig.email_recipients.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {taskConfig.email_recipients.map((email) => (
                      <Badge key={email} variant="secondary" className="flex items-center gap-1">
                        {email}
                        <button
                          onClick={() => removeEmailRecipient(email)}
                          className="ml-1 hover:bg-gray-200 rounded-full p-1"
                          disabled={isExecuting}
                        >
                          ×
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}

                <div className="flex items-center space-x-2">
                  <Switch
                    checked={taskConfig.attach_files}
                    onCheckedChange={(checked) => setTaskConfig(prev => ({ ...prev, attach_files: checked }))}
                    disabled={isExecuting}
                  />
                  <label className="text-sm">附加报告文件</label>
                </div>
              </div>
            )}
          </div>

          {/* 定时任务配置 */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium">定时任务配置（可选）</h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Cron表达式</label>
                <Input
                  placeholder="0 6 * * * (每天6点)"
                  value={taskConfig.cron_expression || ''}
                  onChange={(e) => setTaskConfig(prev => ({ ...prev, cron_expression: e.target.value }))}
                  disabled={isExecuting}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">执行时间</label>
                <Input
                  type="datetime-local"
                  value={taskConfig.execution_time || ''}
                  onChange={(e) => setTaskConfig(prev => ({ ...prev, execution_time: e.target.value }))}
                  disabled={isExecuting}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 任务执行控制 */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold">任务执行</h3>
        </CardHeader>
        <CardContent>
          <div className="flex space-x-3">
            <Button
              onClick={handleStartTask}
              disabled={isExecuting || selectedDataSources.length === 0}
              className="flex items-center space-x-2"
            >
              <PlayIcon className="w-4 h-4" />
              <span>开始生成报告</span>
            </Button>

            {isExecuting && currentTask && (
              <Button
                onClick={handleCancelTask}
                variant="destructive"
                className="flex items-center space-x-2"
              >
                <StopIcon className="w-4 h-4" />
                <span>取消任务</span>
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 任务状态 */}
      {currentTask && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">任务状态</h3>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center space-x-3">
              {getStatusIcon(currentTask.status)}
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{currentTask.current_step}</span>
                  <Badge variant={getStatusBadgeVariant(currentTask.status)}>
                    {currentTask.status}
                  </Badge>
                </div>
                <Progress value={currentTask.progress} className="w-full" />
                <div className="text-xs text-gray-500 mt-1">
                  {currentTask.progress.toFixed(1)}% 完成
                </div>
              </div>
            </div>

            <div className="text-sm space-y-1">
              <div>任务ID: <code className="bg-gray-100 px-1 rounded">{currentTask.task_id}</code></div>
              <div>开始时间: {new Date(currentTask.start_time).toLocaleString()}</div>
              {currentTask.updated_at && (
                <div>更新时间: {new Date(currentTask.updated_at).toLocaleString()}</div>
              )}
            </div>

            {currentTask.error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                <div className="flex">
                  <ExclamationTriangleIcon className="w-5 h-5 text-red-500 mr-2" />
                  <div className="text-sm text-red-700">{currentTask.error}</div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}