import React, { useState, useEffect } from 'react'
import useTaskProgress from '@/hooks/useTaskProgress'

interface CompactTaskProgressProps {
  taskId: number
  isExecuting: boolean
  onExecutionComplete?: (result: any) => void
  onExecutionError?: (error: string) => void
}

export const CompactTaskProgress: React.FC<CompactTaskProgressProps> = ({
  taskId,
  isExecuting,
  onExecutionComplete,
  onExecutionError
}) => {
  const { data: progressData, error } = useTaskProgress(taskId, isExecuting, 3000)
  const [elapsedTime, setElapsedTime] = useState(0)

  useEffect(() => {
    if (!isExecuting) {
      setElapsedTime(0)
      return
    }
    const startTime = Date.now()
    const timeInterval = setInterval(() => setElapsedTime(Date.now() - startTime), 1000)
    return () => clearInterval(timeInterval)
  }, [isExecuting, taskId])

  useEffect(() => {
    if (!progressData) return
    if (progressData.execution_status === 'completed') {
      onExecutionComplete?.(progressData)
    } else if (progressData.execution_status === 'failed') {
      onExecutionError?.(progressData.error_details || '任务执行失败')
    }
  }, [progressData, onExecutionComplete, onExecutionError])

  useEffect(() => {
    if (error) {
      onExecutionError?.(error)
    }
  }, [error, onExecutionError])

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
