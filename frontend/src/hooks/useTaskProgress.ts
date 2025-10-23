import { useEffect, useRef, useState } from 'react'
import { apiClient as api } from '@/lib/api-client'
import { onTaskUpdate, PipelineTaskStatus, PipelineTaskUpdate } from '@/services/websocketAdapter'

export interface ProgressEvent {
  timestamp: string
  progress: number
  message: string
  stage?: string | null
  status?: string | null
  placeholder?: string | null
  details?: Record<string, any> | null
  error?: string | null
}

export interface ProgressData {
  task_id: number | string
  execution_id?: string
  progress_percentage: number
  current_step?: string
  execution_status: string
  started_at?: string | null
  completed_at?: string | null
  estimated_completion?: string | null
  celery_task_id?: string | null
  error_details?: string | null
  progress_details?: ProgressEvent[]
}

function mapWsStatusToExecutionStatus(status?: PipelineTaskStatus): string {
  switch (status) {
    case PipelineTaskStatus.COMPLETED:
      return 'completed'
    case PipelineTaskStatus.FAILED:
      return 'failed'
    case PipelineTaskStatus.CANCELLED:
      return 'cancelled'
    default:
      return 'processing'
  }
}

export function useTaskProgress(taskId: number | string, enabled: boolean = true, intervalMs: number = 2000) {
  const [data, setData] = useState<ProgressData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollingRef = useRef<NodeJS.Timer | null>(null)
  const taskIdStr = String(taskId)

  const normalizeApiData = (resp: ProgressData): ProgressData => {
    const progressDetails = Array.isArray(resp.progress_details) ? resp.progress_details : []
    return {
      task_id: resp.task_id ?? taskIdStr,
      execution_id: resp.execution_id,
      progress_percentage: resp.progress_percentage ?? 0,
      current_step: resp.current_step,
      execution_status: resp.execution_status ?? 'processing',
      started_at: resp.started_at ?? null,
      completed_at: resp.completed_at ?? null,
      estimated_completion: resp.estimated_completion ?? null,
      celery_task_id: resp.celery_task_id ?? null,
      error_details: resp.error_details ?? null,
      progress_details,
    }
  }

  useEffect(() => {
    if (!enabled) {
      stop()
      return
    }

    // Initial fetch
    fetchProgress()

    // Start polling
    pollingRef.current = setInterval(fetchProgress, intervalMs)

    // Subscribe to WS global updates
    const unsubscribe = onTaskUpdate((update: PipelineTaskUpdate) => {
      if (!update?.task_id) return
      if (String(update.task_id) !== taskIdStr) return

      const normalized = typeof update.progress === 'number'
        ? (update.progress <= 1 ? Math.round(update.progress * 100) : Math.round(update.progress))
        : (data?.progress_percentage ?? 0)
      const wsEvent: ProgressEvent | null = update.message
        ? {
            timestamp: new Date().toISOString(),
            progress: normalized,
            message: update.message,
            stage: update.details?.stage ?? null,
            status: update.details?.status ?? mapWsStatusToExecutionStatus(update.status),
            placeholder: update.details?.placeholder ?? null,
            details: update.details ?? null,
            error: update.error ?? null,
          }
        : null

      setData(prev => {
        const prevDetails = prev?.progress_details ?? []
        const mergedDetails = wsEvent ? [...prevDetails, wsEvent].slice(-60) : prevDetails

        return {
          task_id: taskIdStr,
          execution_id: prev?.execution_id,
          progress_percentage: normalized,
          current_step: update.message || prev?.current_step,
          execution_status: mapWsStatusToExecutionStatus(update.status),
          started_at: prev?.started_at ?? null,
          completed_at: prev?.completed_at ?? null,
          estimated_completion: prev?.estimated_completion ?? null,
          celery_task_id: prev?.celery_task_id ?? null,
          error_details: update.error || prev?.error_details || null,
          progress_details: mergedDetails,
        }
      })
    })

    return () => {
      if (unsubscribe) unsubscribe()
      stop()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskIdStr, enabled, intervalMs])

  async function fetchProgress() {
    try {
      const resp = await api.get<ProgressData>(`/tasks/${taskIdStr}/progress`)
      if (resp) setData(normalizeApiData(resp))
      setError(null)
    } catch (e: any) {
      // 404 表示尚未开始，不作为致命错误
      if (e?.response?.status === 404) return
      setError(e?.message || '获取任务进度失败')
    }
  }

  function stop() {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }

  return { data, error, stop }
}

export default useTaskProgress
