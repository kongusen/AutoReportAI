import React, { useState, useEffect } from 'react'
import { StopIcon } from '@heroicons/react/24/outline'
import { apiClient as api } from '@/lib/api-client'
import useTaskProgress from '@/hooks/useTaskProgress'

interface TaskExecutionProgressProps {
  taskId: number
  isExecuting: boolean
  onExecutionComplete?: (result: any) => void
  onExecutionError?: (error: string) => void
  onCancel?: () => void
}

interface ProgressData {
  task_id: number
  execution_id: string
  progress_percentage: number
  current_step: string
  execution_status: string
  started_at: string | null
  completed_at: string | null
  estimated_completion: string | null
  celery_task_id: string | null
  error_details: string | null
}

const progressStages = [
  { threshold: 5, message: '任务初始化完成', description: '正在准备任务执行环境...' },
  { threshold: 10, message: '正在生成时间上下文', description: '正在分析报告周期和时间范围...' },
  { threshold: 15, message: '正在初始化Agent系统', description: '正在启动智能分析引擎...' },
  { threshold: 20, message: '正在分析占位符', description: '正在解析模板占位符...' },
  { threshold: 30, message: '正在执行ETL流水线', description: '正在提取和处理数据...' },
  { threshold: 45, message: 'SQL生成完成，正在执行查询', description: '正在从数据库获取数据...' },
  { threshold: 60, message: '数据提取完成，正在处理', description: '正在清洗和转换数据...' },
  { threshold: 70, message: 'ETL流水线执行完成', description: '数据处理完成，正在生成内容...' },
  { threshold: 75, message: '正在生成报告文档', description: '正在创建图表和文档...' },
  { threshold: 85, message: '正在上传文档到存储', description: '正在保存和上传文件...' },
  { threshold: 90, message: '文档生成完成', description: '正在完成最后步骤...' },
  { threshold: 95, message: '正在发送通知', description: '正在发送完成通知...' },
  { threshold: 100, message: '任务执行完成', description: '所有步骤已完成' }
]

export const TaskExecutionProgress: React.FC<TaskExecutionProgressProps> = ({
  taskId,
  isExecuting,
  onExecutionComplete,
  onExecutionError,
  onCancel
}) => {
  const { data: progressData, error } = useTaskProgress(taskId, isExecuting, 2000)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [cancelling, setCancelling] = useState(false)

  useEffect(() => {
    if (!isExecuting) {
      setElapsedTime(0)
      return
    }
    const startTime = Date.now()
    const timeInterval = setInterval(() => {
      setElapsedTime(Date.now() - startTime)
    }, 1000)
    return () => clearInterval(timeInterval)
  }, [isExecuting, taskId])

  useEffect(() => {
    if (error) {
      onExecutionError?.(error)
    }
  }, [error, onExecutionError])

  useEffect(() => {
    if (!progressData) return
    if (progressData.execution_status === 'completed') {
      onExecutionComplete?.(progressData)
    } else if (progressData.execution_status === 'failed') {
      onExecutionError?.(progressData.error_details || '任务执行失败')
    }
  }, [progressData, onExecutionComplete, onExecutionError])

  if (!isExecuting && !progressData) return null

  const progress = progressData?.progress_percentage || 0
  const currentStage = progressStages.find((stage, index) => {
    const nextStage = progressStages[index + 1]
    return progress >= stage.threshold && (!nextStage || progress < nextStage.threshold)
  }) || progressStages[0]

  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000)
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
  }

  const getEstimatedRemaining = () => {
    if (!progressData?.estimated_completion) return null
    const estimated = new Date(progressData.estimated_completion)
    const now = new Date()
    const remaining = estimated.getTime() - now.getTime()
    if (remaining <= 0) return null
    return Math.ceil(remaining / 1000)
  }

  const estimatedRemaining = getEstimatedRemaining()

  const handleCancel = async () => {
    if (cancelling) return

    setCancelling(true)
    try {
      const response = await api.post(`/tasks/${taskId}/cancel`) as any
      if (response.data?.success) {
        onCancel?.()
      }
    } catch (error: any) {
      console.error('Failed to cancel task:', error)
      onExecutionError?.('取消任务失败')
    } finally {
      setCancelling(false)
    }
  }

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
      <div className="space-y-3">
        {/* 头部信息 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
            <span className="text-sm font-medium text-gray-800">
              正在执行任务
            </span>
          </div>
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-3 text-xs text-gray-500">
              <span>已耗时: {formatTime(elapsedTime)}</span>
              {estimatedRemaining && (
                <span>预计剩余: {Math.floor(estimatedRemaining / 60)}:{(estimatedRemaining % 60).toString().padStart(2, '0')}</span>
              )}
            </div>
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="flex items-center gap-1 px-2 py-1 text-xs text-red-600 hover:text-red-700 hover:bg-red-50 rounded border border-red-200 disabled:opacity-50 disabled:cursor-not-allowed"
              title="停止执行"
            >
              <StopIcon className="w-3 h-3" />
              {cancelling ? '停止中...' : '停止'}
            </button>
          </div>
        </div>

        {/* 当前步骤 */}
        <div className="text-sm text-gray-700">
          <div className="font-medium">{progressData?.current_step || currentStage.message}</div>
          <div className="text-xs text-gray-500 mt-1">{currentStage.description}</div>
        </div>

        {/* 进度条 */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-gray-500">
            <span>进度</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-1000 ease-out"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>

        {/* 阶段指示器 */}
        <div className="flex justify-between items-center">
          {progressStages.filter((_, index) => index % 3 === 0 || index === progressStages.length - 1).map((stage, index) => {
            const stageProgress = progress >= stage.threshold
            return (
              <div key={stage.threshold} className="flex flex-col items-center">
                <div
                  className={`w-2 h-2 rounded-full ${
                    stageProgress
                      ? 'bg-blue-500'
                      : 'bg-gray-300'
                  }`}
                ></div>
                <div className="text-xs text-gray-500 mt-1 text-center max-w-16">
                  {stage.threshold}%
                </div>
              </div>
            )
          })}
        </div>

        {/* 错误信息 */}
        {progressData?.error_details && (
          <div className="bg-red-50 border border-red-200 rounded p-2">
            <div className="text-sm text-red-800 font-medium">执行失败</div>
            <div className="text-xs text-red-600 mt-1">{progressData.error_details}</div>
          </div>
        )}

        {/* 执行ID */}
        {progressData?.execution_id && (
          <div className="text-xs text-gray-400 text-center">
            执行ID: {progressData.execution_id.substring(0, 8)}...
          </div>
        )}
      </div>
    </div>
  )
}
