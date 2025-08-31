/**
 * 系统状态监控Hook - 实时监控API、WebSocket和任务状态
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { ApiClient } from '@/lib/api-client'
import { useWebSocketIntegration } from '@/hooks/useWebSocketIntegration'
import { ConnectionState } from '@/lib/websocket'

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'checking'
  version: string
  environment: string
  timestamp: string
  checks: {
    database: {
      status: 'healthy' | 'unhealthy'
      message: string
    }
    services: {
      status: 'healthy' | 'degraded' | 'unhealthy'
      details?: any
    }
    system: {
      status: 'healthy' | 'unhealthy'
      memory_usage_percent: number
      available_memory_mb: number
    }
  }
  response_time_ms: number
}

export interface TaskStatus {
  id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  message?: string
  startTime?: Date
  endTime?: Date
  duration?: number
}

export interface SystemStatusState {
  health: SystemHealth | null
  tasks: TaskStatus[]
  notifications: Array<{
    id: string
    type: 'info' | 'warning' | 'error' | 'success'
    title: string
    message: string
    timestamp: Date
    persistent?: boolean
  }>
  connectionQuality: 'excellent' | 'good' | 'poor' | 'offline'
  lastUpdate: Date | null
}

export function useSystemStatus(options: {
  enableAutoRefresh?: boolean
  refreshInterval?: number
  enableTaskMonitoring?: boolean
  enableNotifications?: boolean
} = {}) {
  const {
    enableAutoRefresh = true,
    refreshInterval = 30000, // 30秒
    enableTaskMonitoring = true,
    enableNotifications = true
  } = options

  const { connectionState, sendMessage, lastMessage } = useWebSocketIntegration()
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  
  const [state, setState] = useState<SystemStatusState>({
    health: null,
    tasks: [],
    notifications: [],
    connectionQuality: 'good',
    lastUpdate: null
  })

  // 检查系统健康状态
  const checkSystemHealth = useCallback(async () => {
    try {
      const startTime = Date.now()
      const healthData = await ApiClient.get<SystemHealth>('/health/detailed', {
        showToast: false,
        cache: false
      })
      const responseTime = Date.now() - startTime

      // 更新连接质量评估
      let quality: SystemStatusState['connectionQuality']
      if (responseTime < 100 && healthData.status === 'healthy') {
        quality = 'excellent'
      } else if (responseTime < 500 && healthData.status !== 'unhealthy') {
        quality = 'good'
      } else if (responseTime < 1000) {
        quality = 'poor'
      } else {
        quality = 'offline'
      }

      setState(prev => ({
        ...prev,
        health: { ...healthData, response_time_ms: responseTime },
        connectionQuality: quality,
        lastUpdate: new Date()
      }))

    } catch (error: any) {
      console.error('Health check failed:', error)
      setState(prev => ({
        ...prev,
        health: null,
        connectionQuality: 'offline',
        lastUpdate: new Date()
      }))
    }
  }, [])

  // 获取任务状态
  const fetchTaskStatus = useCallback(async () => {
    if (!enableTaskMonitoring) return

    try {
      const tasks = await ApiClient.get<TaskStatus[]>('/task-scheduler/status', {
        showToast: false,
        cache: true,
        cacheTTL: 10000 // 10秒缓存
      })

      setState(prev => ({
        ...prev,
        tasks
      }))

    } catch (error: any) {
      console.error('Failed to fetch task status:', error)
    }
  }, [enableTaskMonitoring])

  // 处理WebSocket消息
  useEffect(() => {
    if (!lastMessage || !enableNotifications) return

    try {
      const message = JSON.parse(lastMessage.data)
      
      // 处理任务状态更新
      if (message.type === 'task_update' && enableTaskMonitoring) {
        setState(prev => ({
          ...prev,
          tasks: prev.tasks.map(task => 
            task.id === message.data.id 
              ? { ...task, ...message.data }
              : task
          )
        }))
      }
      
      // 处理系统通知
      if (message.type === 'system_notification' && enableNotifications) {
        const notification = {
          id: `notif_${Date.now()}`,
          type: message.data.type || 'info',
          title: message.data.title || '系统通知',
          message: message.data.message,
          timestamp: new Date(),
          persistent: message.data.persistent || false
        }
        
        setState(prev => ({
          ...prev,
          notifications: [notification, ...prev.notifications.slice(0, 19)] // 保持最新20条
        }))
      }
      
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error)
    }
  }, [lastMessage, enableTaskMonitoring, enableNotifications])

  // 定时刷新
  useEffect(() => {
    if (enableAutoRefresh) {
      checkSystemHealth() // 立即检查
      
      intervalRef.current = setInterval(() => {
        checkSystemHealth()
        fetchTaskStatus()
      }, refreshInterval)
      
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
        }
      }
    }
  }, [enableAutoRefresh, refreshInterval, checkSystemHealth, fetchTaskStatus])

  // 手动刷新
  const refresh = useCallback(async () => {
    await Promise.all([
      checkSystemHealth(),
      fetchTaskStatus()
    ])
  }, [checkSystemHealth, fetchTaskStatus])

  // 清除通知
  const clearNotification = useCallback((id: string) => {
    setState(prev => ({
      ...prev,
      notifications: prev.notifications.filter(n => n.id !== id)
    }))
  }, [])

  // 清除所有通知
  const clearAllNotifications = useCallback(() => {
    setState(prev => ({
      ...prev,
      notifications: []
    }))
  }, [])

  // 获取运行中的任务
  const getRunningTasks = useCallback(() => {
    return state.tasks.filter(task => 
      task.status === 'running' || task.status === 'pending'
    )
  }, [state.tasks])

  // 获取系统状态摘要
  const getStatusSummary = useCallback(() => {
    const runningTasks = getRunningTasks()
    const hasErrors = state.health?.status === 'unhealthy' || 
                     connectionState === ConnectionState.CLOSED ||
                     state.connectionQuality === 'offline'
    
    return {
      isHealthy: !hasErrors,
      hasRunningTasks: runningTasks.length > 0,
      taskCount: runningTasks.length,
      notificationCount: state.notifications.length,
      connectionQuality: state.connectionQuality,
      lastUpdate: state.lastUpdate
    }
  }, [state, connectionState, getRunningTasks])

  return {
    ...state,
    
    // 方法
    refresh,
    checkSystemHealth,
    fetchTaskStatus,
    clearNotification,
    clearAllNotifications,
    getRunningTasks,
    getStatusSummary,
    
    // 计算属性
    isConnected: connectionState === ConnectionState.OPEN,
    isHealthy: state.health?.status === 'healthy',
    hasRunningTasks: getRunningTasks().length > 0,
    
    // WebSocket相关
    connectionState,
    sendMessage
  }
}

// 简化版的状态监控Hook
export function useSimpleSystemStatus() {
  const { health, connectionQuality, isHealthy, lastUpdate } = useSystemStatus({
    enableAutoRefresh: true,
    refreshInterval: 60000, // 1分钟
    enableTaskMonitoring: false,
    enableNotifications: false
  })

  return {
    status: health?.status || 'checking',
    connectionQuality,
    isHealthy,
    lastUpdate,
    responseTime: health?.response_time_ms || 0
  }
}