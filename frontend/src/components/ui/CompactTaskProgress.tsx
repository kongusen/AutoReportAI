import React, { useState, useEffect } from 'react'
import { apiClient as api } from '@/lib/api-client'

interface CompactTaskProgressProps {
  taskId: number
  isExecuting: boolean
  onExecutionComplete?: (result: any) => void
  onExecutionError?: (error: string) => void
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

export const CompactTaskProgress: React.FC<CompactTaskProgressProps> = ({
  taskId,
  isExecuting,
  onExecutionComplete,
  onExecutionError
}) => {
  const [progressData, setProgressData] = useState<ProgressData | null>(null)
  const [elapsedTime, setElapsedTime] = useState(0)

  useEffect(() => {
    if (!isExecuting) {
      setProgressData(null)
      setElapsedTime(0)
      return
    }

    const startTime = Date.now()

    // 立即获取一次进度
    fetchProgress()

    // 设置轮询
    const progressInterval = setInterval(fetchProgress, 3000) // 每3秒轮询一次

    // 设置计时器
    const timeInterval = setInterval(() => {
      setElapsedTime(Date.now() - startTime)
    }, 1000)

    return () => {
      clearInterval(progressInterval)
      clearInterval(timeInterval)
    }
  }, [isExecuting, taskId])

  const fetchProgress = async () => {
    try {
      const response = await api.get(`/tasks/${taskId}/progress`) as any
      if (response.data?.success) {
        const data = response.data.data as ProgressData
        setProgressData(data)

        // 检查是否完成或失败
        if (data.execution_status === 'completed') {
          onExecutionComplete?.(data)
        } else if (data.execution_status === 'failed') {
          onExecutionError?.(data.error_details || '任务执行失败')
        }
      }
    } catch (error: any) {
      console.error('Failed to fetch task progress:', error)
      if (error.response?.status !== 404) {
        onExecutionError?.('获取任务进度失败')
      }
    }
  }

  if (!isExecuting && !progressData) return null

  const progress = progressData?.progress_percentage || 0
  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000)
    return `${Math.floor(seconds / 60)}:${(seconds % 60).toString().padStart(2, '0')}`
  }

  return (
    <div className="space-y-1">
      {/* 进度条 */}
      <div className="w-24">
        <div className="w-full bg-gray-200 rounded-full h-1.5">
          <div
            className="bg-blue-500 h-1.5 rounded-full transition-all duration-1000 ease-out"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      </div>

      {/* 进度信息 */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{progress}%</span>
        <span>{formatTime(elapsedTime)}</span>
      </div>

      {/* 当前步骤 */}
      <div className="text-xs text-gray-600 truncate max-w-32" title={progressData?.current_step}>
        {progressData?.current_step || '执行中...'}
      </div>

      {/* 错误信息 */}
      {progressData?.error_details && (
        <div className="text-xs text-red-600 truncate max-w-32" title={progressData.error_details}>
          执行失败
        </div>
      )}
    </div>
  )
}