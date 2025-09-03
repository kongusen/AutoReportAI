/**
 * 优化的WebSocket Hook
 * 统一管理多页面的WebSocket连接，避免重复连接
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { useWebSocket } from './useWebSocket'
import type { WebSocketMessage, TaskUpdateMessage, NotificationMessage } from '@/types/api'

// 全局WebSocket连接管理器
class WebSocketConnectionManager {
  private static instance: WebSocketConnectionManager
  private connections: Map<string, any> = new Map()
  private subscribers: Map<string, Set<Function>> = new Map()

  static getInstance(): WebSocketConnectionManager {
    if (!WebSocketConnectionManager.instance) {
      WebSocketConnectionManager.instance = new WebSocketConnectionManager()
    }
    return WebSocketConnectionManager.instance
  }

  subscribe(pageId: string, callback: Function) {
    if (!this.subscribers.has(pageId)) {
      this.subscribers.set(pageId, new Set())
    }
    this.subscribers.get(pageId)!.add(callback)
  }

  unsubscribe(pageId: string, callback: Function) {
    const subs = this.subscribers.get(pageId)
    if (subs) {
      subs.delete(callback)
      if (subs.size === 0) {
        this.subscribers.delete(pageId)
      }
    }
  }

  broadcast(pageId: string, data: any) {
    const subs = this.subscribers.get(pageId)
    if (subs) {
      subs.forEach(callback => callback(data))
    }
  }
}

interface UseOptimizedWebSocketOptions {
  pageId: string
  enableTaskUpdates?: boolean
  enableNotifications?: boolean
  enableReportUpdates?: boolean
  onTaskUpdate?: (update: TaskUpdateMessage) => void
  onNotification?: (notification: NotificationMessage) => void
  onReportUpdate?: (update: any) => void
}

/**
 * 页面级优化的WebSocket Hook
 */
export function useOptimizedWebSocket(options: UseOptimizedWebSocketOptions) {
  const {
    pageId,
    enableTaskUpdates = false,
    enableNotifications = false,
    enableReportUpdates = false,
    onTaskUpdate,
    onNotification,
    onReportUpdate
  } = options

  const manager = WebSocketConnectionManager.getInstance()
  const [connectionState, setConnectionState] = useState({
    isConnected: false,
    activeUpdates: 0
  })

  // 基础WebSocket连接
  const { 
    isConnected, 
    taskUpdates, 
    notifications, 
    reportUpdates,
    subscribe,
    unsubscribe
  } = useWebSocket({
    autoConnect: true,
    enableTaskUpdates,
    enableNotifications,
    enableReportUpdates,
    onConnectionChange: (status) => {
      setConnectionState(prev => ({
        ...prev,
        isConnected: status === 'connected'
      }))
    }
  })

  // 页面特定的消息处理
  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (pageId) {
      case 'tasks':
        if (message.type === 'task_update' && onTaskUpdate) {
          onTaskUpdate(message as TaskUpdateMessage)
        }
        break
      case 'templates':
        if ((message.type === 'template_created' || 
             message.type === 'template_updated' ||
             message.type === 'template_deleted' ||
             message.type === 'placeholder_analysis_completed') && onNotification) {
          onNotification(message as NotificationMessage)
        }
        break
      case 'data-sources':
        if ((message.type === 'data_source_created' ||
             message.type === 'data_source_updated' ||
             message.type === 'data_source_deleted' ||
             message.type === 'data_source_test_completed') && onNotification) {
          onNotification(message as NotificationMessage)
        }
        break
    }
  }, [pageId, onTaskUpdate, onNotification])

  // 订阅页面特定的频道
  useEffect(() => {
    if (!isConnected) return

    const channels: string[] = []
    
    switch (pageId) {
      case 'tasks':
        channels.push('tasks', 'task-updates', 'user:notifications')
        break
      case 'templates':
        channels.push('templates', 'placeholders', 'user:notifications')
        break
      case 'data-sources':
        channels.push('data-sources', 'system:alerts', 'user:notifications')
        break
    }

    // 订阅频道
    channels.forEach(channel => subscribe(channel))

    // 注册消息处理器
    manager.subscribe(pageId, handleMessage)

    return () => {
      channels.forEach(channel => unsubscribe(channel))
      manager.unsubscribe(pageId, handleMessage)
    }
  }, [isConnected, pageId, subscribe, unsubscribe, handleMessage, manager])

  // 计算活跃更新数量
  useEffect(() => {
    let activeCount = 0
    if (enableTaskUpdates) activeCount += taskUpdates.size
    if (enableNotifications) activeCount += notifications.length
    if (enableReportUpdates) activeCount += reportUpdates.size

    setConnectionState(prev => ({
      ...prev,
      activeUpdates: activeCount
    }))
  }, [taskUpdates.size, notifications.length, reportUpdates.size, enableTaskUpdates, enableNotifications, enableReportUpdates])

  return {
    isConnected: connectionState.isConnected,
    activeUpdates: connectionState.activeUpdates,
    taskUpdates: enableTaskUpdates ? taskUpdates : new Map(),
    notifications: enableNotifications ? notifications : [],
    reportUpdates: enableReportUpdates ? reportUpdates : new Map(),
    
    // 便捷方法
    hasTaskUpdate: (taskId: string) => taskUpdates.has(taskId),
    getTaskUpdate: (taskId: string) => taskUpdates.get(taskId),
    hasActiveNotifications: () => notifications.length > 0,
    hasActiveReports: () => reportUpdates.size > 0
  }
}

/**
 * 任务页面专用Hook
 */
export function useTaskPageWebSocket() {
  return useOptimizedWebSocket({
    pageId: 'tasks',
    enableTaskUpdates: true,
    enableNotifications: true
  })
}

/**
 * 模板页面专用Hook  
 */
export function useTemplatePageWebSocket() {
  return useOptimizedWebSocket({
    pageId: 'templates',
    enableNotifications: true
  })
}

/**
 * 数据源页面专用Hook
 */
export function useDataSourcePageWebSocket() {
  return useOptimizedWebSocket({
    pageId: 'data-sources',
    enableNotifications: true
  })
}

export default useOptimizedWebSocket