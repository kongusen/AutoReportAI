/**
 * WebSocket适配器 - 处理新的流水线任务通知
 * 与后端的pipeline_notification_service集成
 */

import { webSocketManager, ConnectionStatus } from '@/lib/websocket-client'
import { APIAdapter } from './apiAdapter'
import toast from 'react-hot-toast'

// 任务状态枚举
export enum PipelineTaskStatus {
  PENDING = 'pending',
  SCANNING = 'scanning',
  ANALYZING = 'analyzing',
  ASSEMBLING = 'assembling',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

// 任务类型枚举
export enum PipelineTaskType {
  ETL_SCAN = 'etl_scan',
  REPORT_ASSEMBLY = 'report_assembly',
  HEALTH_CHECK = 'health_check',
  TEMPLATE_ANALYSIS = 'template_analysis'
}

// 任务更新数据接口
export interface PipelineTaskUpdate {
  task_id: string
  task_type: string
  status: PipelineTaskStatus
  progress: number // 0.0 - 1.0
  message: string
  timestamp: string
  details?: {
    template_id?: string
    data_source_id?: string
    user_id?: string
    result?: any
    error_details?: any
  }
  error?: string
}

// WebSocket消息类型
export interface TaskUpdateMessage {
  type: 'task_update'
  message: string
  data: PipelineTaskUpdate
}

// 任务状态监听器类型
export type TaskStatusListener = (update: PipelineTaskUpdate) => void
export type TaskCompleteListener = (taskId: string, result: any) => void
export type TaskErrorListener = (taskId: string, error: string) => void

/**
 * WebSocket流水线通知适配器
 */
export class WebSocketPipelineAdapter {
  private taskListeners = new Map<string, Set<TaskStatusListener>>()
  private globalListeners = new Set<TaskStatusListener>()
  private completeListeners = new Map<string, Set<TaskCompleteListener>>()
  private errorListeners = new Map<string, Set<TaskErrorListener>>()
  private subscribedTasks = new Set<string>()

  constructor() {
    this.setupWebSocketHandlers()
  }

  /**
   * 设置WebSocket消息处理器
   */
  private setupWebSocketHandlers(): void {
    const client = webSocketManager.getClient()
    if (!client) {
      console.warn('WebSocket client not initialized')
      return
    }

    // 监听任务更新消息
    client.on('task_update', this.handleTaskUpdate.bind(this))

    // 监听连接状态变化
    client.onConnectionChange((status: ConnectionStatus) => {
      if (status === ConnectionStatus.CONNECTED) {
        // 重新订阅所有任务
        this.resubscribeAllTasks()
      }
    })
  }

  /**
   * 处理任务更新消息
   */
  private handleTaskUpdate(message: TaskUpdateMessage): void {
    const update = message.data
    console.log('收到任务更新:', update)

    // 调用任务特定的监听器
    const taskListeners = this.taskListeners.get(update.task_id)
    if (taskListeners) {
      taskListeners.forEach(listener => {
        try {
          listener(update)
        } catch (error) {
          console.error('任务监听器错误:', error)
        }
      })
    }

    // 调用全局监听器
    this.globalListeners.forEach(listener => {
      try {
        listener(update)
      } catch (error) {
        console.error('全局任务监听器错误:', error)
      }
    })

    // 处理任务完成
    if (update.status === PipelineTaskStatus.COMPLETED) {
      this.handleTaskComplete(update)
    }

    // 处理任务错误
    if (update.status === PipelineTaskStatus.FAILED) {
      this.handleTaskError(update)
    }

    // 显示用户通知
    this.showTaskNotification(update)
  }

  /**
   * 处理任务完成
   */
  private handleTaskComplete(update: PipelineTaskUpdate): void {
    const completeListeners = this.completeListeners.get(update.task_id)
    if (completeListeners) {
      const result = update.details?.result || {}
      completeListeners.forEach(listener => {
        try {
          listener(update.task_id, result)
        } catch (error) {
          console.error('任务完成监听器错误:', error)
        }
      })
    }

    // 清理监听器
    this.cleanupTaskListeners(update.task_id)
  }

  /**
   * 处理任务错误
   */
  private handleTaskError(update: PipelineTaskUpdate): void {
    const errorListeners = this.errorListeners.get(update.task_id)
    if (errorListeners) {
      const error = update.error || '任务执行失败'
      errorListeners.forEach(listener => {
        try {
          listener(update.task_id, error)
        } catch (error) {
          console.error('任务错误监听器错误:', error)
        }
      })
    }

    // 清理监听器
    this.cleanupTaskListeners(update.task_id)
  }

  /**
   * 显示任务通知
   */
  private showTaskNotification(update: PipelineTaskUpdate): void {
    const taskTypeNames = {
      [PipelineTaskType.ETL_SCAN]: 'ETL扫描',
      [PipelineTaskType.REPORT_ASSEMBLY]: '报告组装',
      [PipelineTaskType.HEALTH_CHECK]: '健康检查',
      [PipelineTaskType.TEMPLATE_ANALYSIS]: '模板分析'
    }

    const taskTypeName = taskTypeNames[update.task_type as PipelineTaskType] || update.task_type

    switch (update.status) {
      case PipelineTaskStatus.COMPLETED:
        toast.success(`${taskTypeName}完成: ${update.message}`)
        break
      case PipelineTaskStatus.FAILED:
        toast.error(`${taskTypeName}失败: ${update.message}`)
        break
      case PipelineTaskStatus.SCANNING:
      case PipelineTaskStatus.ANALYZING:
      case PipelineTaskStatus.ASSEMBLING:
        // 对于进行中的任务，只在特定进度节点显示通知
        if (update.progress > 0 && update.progress % 0.25 === 0) {
          toast(`${taskTypeName}: ${update.message}`, {
            icon: '⚡',
            duration: 2000
          })
        }
        break
    }
  }

  /**
   * 订阅任务更新
   */
  async subscribeToTask(
    taskId: string,
    onUpdate?: TaskStatusListener,
    onComplete?: TaskCompleteListener,
    onError?: TaskErrorListener
  ): Promise<boolean> {
    try {
      // 添加监听器
      if (onUpdate) {
        if (!this.taskListeners.has(taskId)) {
          this.taskListeners.set(taskId, new Set())
        }
        this.taskListeners.get(taskId)!.add(onUpdate)
      }

      if (onComplete) {
        if (!this.completeListeners.has(taskId)) {
          this.completeListeners.set(taskId, new Set())
        }
        this.completeListeners.get(taskId)!.add(onComplete)
      }

      if (onError) {
        if (!this.errorListeners.has(taskId)) {
          this.errorListeners.set(taskId, new Set())
        }
        this.errorListeners.get(taskId)!.add(onError)
      }

      // 调用后端API订阅任务
      const result = await APIAdapter.subscribeToTask(taskId)
      if (result.success) {
        this.subscribedTasks.add(taskId)
        console.log(`成功订阅任务: ${taskId}`)
        return true
      } else {
        if (result.error) {
          APIAdapter.handleError(result.error)
        }
        return false
      }
    } catch (error) {
      console.error('订阅任务失败:', error)
      toast.error('订阅任务更新失败')
      return false
    }
  }

  /**
   * 取消订阅任务
   */
  unsubscribeFromTask(taskId: string): void {
    this.cleanupTaskListeners(taskId)
    this.subscribedTasks.delete(taskId)
  }

  /**
   * 添加全局任务监听器
   */
  onTaskUpdate(listener: TaskStatusListener): () => void {
    this.globalListeners.add(listener)
    return () => this.globalListeners.delete(listener)
  }

  /**
   * 获取任务状态
   */
  async getTaskStatus(taskId: string): Promise<PipelineTaskUpdate | null> {
    try {
      const result = await APIAdapter.getTaskStatus(taskId)
      if (result.success && result.data) {
        return {
          task_id: result.data.task_id,
          task_type: result.data.task_type,
          status: result.data.status as PipelineTaskStatus,
          progress: result.data.progress,
          message: result.data.message,
          timestamp: new Date().toISOString(),
          details: result.data
        }
      }
      return null
    } catch (error) {
      console.error('获取任务状态失败:', error)
      return null
    }
  }

  /**
   * 重新订阅所有任务
   */
  private async resubscribeAllTasks(): Promise<void> {
    const tasks = Array.from(this.subscribedTasks)
    console.log(`重新订阅 ${tasks.length} 个任务`)

    for (const taskId of tasks) {
      try {
        const result = await APIAdapter.subscribeToTask(taskId)
        if (!result.success) {
          console.warn(`重新订阅任务失败: ${taskId}`)
        }
      } catch (error) {
        console.error(`重新订阅任务 ${taskId} 失败:`, error)
      }
    }
  }

  /**
   * 清理任务监听器
   */
  private cleanupTaskListeners(taskId: string): void {
    this.taskListeners.delete(taskId)
    this.completeListeners.delete(taskId)
    this.errorListeners.delete(taskId)
  }

  /**
   * 获取订阅的任务列表
   */
  getSubscribedTasks(): string[] {
    return Array.from(this.subscribedTasks)
  }

  /**
   * 清理所有监听器
   */
  cleanup(): void {
    this.taskListeners.clear()
    this.globalListeners.clear()
    this.completeListeners.clear()
    this.errorListeners.clear()
    this.subscribedTasks.clear()
  }
}

// 全局实例
export const pipelineWebSocketAdapter = new WebSocketPipelineAdapter()

// 便捷函数
export const subscribeToTask = pipelineWebSocketAdapter.subscribeToTask.bind(pipelineWebSocketAdapter)
export const unsubscribeFromTask = pipelineWebSocketAdapter.unsubscribeFromTask.bind(pipelineWebSocketAdapter)
export const onTaskUpdate = pipelineWebSocketAdapter.onTaskUpdate.bind(pipelineWebSocketAdapter)
export const getTaskStatus = pipelineWebSocketAdapter.getTaskStatus.bind(pipelineWebSocketAdapter)

export default pipelineWebSocketAdapter