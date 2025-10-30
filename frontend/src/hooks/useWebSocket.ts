/**
 * AutoReportAI 增强WebSocket React Hook
 * 基于新的WebSocket客户端实现
 */

import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { toast } from 'react-hot-toast'
import { AutoReportWebSocketClient, ConnectionStatus, webSocketManager } from '@/lib/websocket-client'
import {
  WebSocketMessageType,
  type WebSocketMessage,
  type NotificationMessage,
  type TaskUpdateMessage,
  type ReportUpdateMessage
} from '@/types/api'

// ============================================================================
// Hook配置接口
// ============================================================================

export interface UseWebSocketConfig {
  autoConnect?: boolean
  enableNotifications?: boolean
  enableTaskUpdates?: boolean
  enableReportUpdates?: boolean
  subscribeToUserChannel?: boolean
  subscribeToSystemAlerts?: boolean
  onConnectionChange?: (status: ConnectionStatus, error?: Error) => void
  onMessage?: (message: WebSocketMessage) => void
  debug?: boolean
}

// ============================================================================
// Hook返回类型
// ============================================================================

export interface UseWebSocketResult {
  // 连接状态
  status: ConnectionStatus
  isConnected: boolean
  isConnecting: boolean
  
  // 连接控制
  connect: () => Promise<void>
  disconnect: () => void
  reconnect: () => Promise<void>
  
  // 消息发送
  send: (message: WebSocketMessage) => void
  
  // 频道订阅
  subscribe: (channel: string) => void
  unsubscribe: (channel: string) => void
  subscriptions: string[]
  
  // 统计信息
  connectionInfo: any
  
  // 消息历史
  messages: WebSocketMessage[]
  clearMessages: () => void
  
  // 通知管理
  notifications: NotificationMessage[]
  clearNotifications: () => void
  markNotificationAsRead: (id: string) => void
  
  // 任务更新
  taskUpdates: Map<string, TaskUpdateMessage>
  clearTaskUpdates: () => void
  
  // 报告更新
  reportUpdates: Map<string, ReportUpdateMessage>
  clearReportUpdates: () => void
}

// ============================================================================
// 主Hook实现
// ============================================================================

export function useWebSocket(config: UseWebSocketConfig = {}): UseWebSocketResult {
  const {
    autoConnect = true,
    enableNotifications = true,
    enableTaskUpdates = true,
    enableReportUpdates = true,
    subscribeToUserChannel = true,
    subscribeToSystemAlerts = true,
    onConnectionChange,
    onMessage,
    debug = false
  } = config

  // 状态管理
  const [status, setStatus] = useState<ConnectionStatus>(ConnectionStatus.DISCONNECTED)
  const [messages, setMessages] = useState<WebSocketMessage[]>([])
  const [notifications, setNotifications] = useState<NotificationMessage[]>([])
  const [taskUpdates, setTaskUpdates] = useState<Map<string, TaskUpdateMessage>>(new Map())
  const [reportUpdates, setReportUpdates] = useState<Map<string, ReportUpdateMessage>>(new Map())

  // 引用
  const clientRef = useRef<AutoReportWebSocketClient | null>(null)
  const configRef = useRef(config)
  const userIdRef = useRef<string | null>(null)

  // 更新配置引用
  useEffect(() => {
    configRef.current = config
  }, [config])

  // ============================================================================
  // 消息处理器
  // ============================================================================

  const handleMessage = useCallback((message: WebSocketMessage) => {
    setMessages(prev => {
      const newMessages = [...prev, message]
      // 限制消息历史数量
      if (newMessages.length > 100) {
        newMessages.splice(0, newMessages.length - 100)
      }
      return newMessages
    })

    onMessage?.(message)
  }, [onMessage])

  const handleNotification = useCallback((message: NotificationMessage) => {
    setNotifications(prev => {
      const newNotifications = [...prev, { ...message, id: message.id || Date.now().toString() }]
      // 限制通知数量
      if (newNotifications.length > 50) {
        newNotifications.splice(0, newNotifications.length - 50)
      }
      return newNotifications
    })

    // 显示toast通知
    if (message.notification_type && message.title && message.message) {
      switch (message.notification_type) {
        case 'success':
          toast.success(`${message.title}: ${message.message}`)
          break
        case 'error':
          toast.error(`${message.title}: ${message.message}`)
          break
        case 'warning':
          toast(`${message.title}: ${message.message}`, { icon: '⚠️' })
          break
        default:
          toast(`${message.title}: ${message.message}`)
          break
      }
    }
  }, [])

  const handleTaskUpdate = useCallback((message: TaskUpdateMessage) => {
    // 统一从 data 读取任务更新负载
    const data: any = (message as any).data ?? message
    const wsTaskId: string | undefined = data?.task_id
    const internalTaskId: string | number | undefined = data?.details?.task_internal_id

    setTaskUpdates(prev => {
      const newMap = new Map(prev)
      if (wsTaskId) {
        newMap.set(String(wsTaskId), data)
      }
      // 同时用内部任务ID（数值型任务ID）进行键控，便于页面以任务ID直接读取
      if (internalTaskId !== undefined && internalTaskId !== null) {
        newMap.set(String(internalTaskId), data)
      }
      return newMap
    })

    // 显示任务进度更新
    if (data?.status === 'completed') {
      toast.success(`任务完成: ${wsTaskId || internalTaskId}`)
    } else if (data?.status === 'failed') {
      toast.error(`任务失败: ${wsTaskId || internalTaskId}`)
    }
  }, [])

  const handleReportUpdate = useCallback((message: ReportUpdateMessage) => {
    setReportUpdates(prev => {
      const newMap = new Map(prev)
      newMap.set(message.report_id, message)
      return newMap
    })

    // 显示报告生成进度
    if (message.status === 'completed') {
      toast.success(message.file_url ? 
        '报告生成完成！点击下载' : 
        '报告生成完成！', {
        duration: 5000
      })
      
      // 如果有下载链接，自动打开
      if (message.file_url) {
        setTimeout(() => window.open(message.file_url, '_blank'), 1000)
      }
    } else if (message.status === 'failed') {
      toast.error('报告生成失败')
    }
  }, [])

  // ============================================================================
  // WebSocket客户端初始化
  // ============================================================================

  const initializeClient = useCallback(() => {
    if (typeof window === 'undefined') return

    const token = localStorage.getItem('authToken')
    const user = localStorage.getItem('user')
    
    if (debug) {
      console.log('WebSocket初始化:', {
        hasToken: !!token,
        tokenPreview: token ? `${token.substring(0, 10)}...` : 'None',
        hasUser: !!user
      })
    }
    
    if (user) {
      try {
        const userData = JSON.parse(user)
        userIdRef.current = userData.id
      } catch (error) {
        console.warn('解析用户信息失败:', error)
      }
    }

    if (!token) {
      console.warn('未找到认证token，无法连接WebSocket')
      return
    }

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/'
    
    const client = webSocketManager.init({
      url: wsUrl,
      token,
      clientType: 'web',
      clientVersion: process.env.NEXT_PUBLIC_APP_VERSION || '2.0.0',
      debug
    })

    clientRef.current = client

    // 注册连接状态监听器
    const unsubscribeConnection = client.onConnectionChange((newStatus: ConnectionStatus, error?: Error) => {
      setStatus(newStatus)
      onConnectionChange?.(newStatus, error)
      
      if (debug) {
        console.log('WebSocket状态变更:', newStatus, error?.message)
      }
    })

    // 注册消息处理器
    client.on('*', handleMessage)
    
    if (enableNotifications) {
      client.on(WebSocketMessageType.NOTIFICATION, handleNotification)
    }
    
    if (enableTaskUpdates) {
      client.on(WebSocketMessageType.TASK_UPDATE, handleTaskUpdate)
    }
    
    if (enableReportUpdates) {
      client.on(WebSocketMessageType.REPORT_UPDATE, handleReportUpdate)
    }

    return () => {
      unsubscribeConnection()
      client.disconnect()
    }
  }, [debug, enableNotifications, enableTaskUpdates, enableReportUpdates, onConnectionChange, handleMessage, handleNotification, handleTaskUpdate, handleReportUpdate])


  // ============================================================================
  // 自动连接和订阅
  // ============================================================================

  useEffect(() => {
    if (!autoConnect) return

    const cleanup = initializeClient()

    return cleanup
  }, [initializeClient, autoConnect])

  useEffect(() => {
    const client = clientRef.current
    if (!client || !client.isConnected) return

    // 自动订阅用户频道
    if (subscribeToUserChannel && userIdRef.current) {
      client.subscribe(`user:${userIdRef.current}`)
    }

    // 自动订阅系统警报频道
    if (subscribeToSystemAlerts) {
      client.subscribe('system:alerts')
      client.subscribe('system:updates')
    }

    // 订阅通知频道
    if (enableNotifications) {
      client.subscribe('notifications:user')
    }
  }, [status, subscribeToUserChannel, subscribeToSystemAlerts, enableNotifications])

  // ============================================================================
  // 导出的方法
  // ============================================================================

  const connect = useCallback(async () => {
    if (!clientRef.current) {
      initializeClient()
    }
    
    if (clientRef.current) {
      await clientRef.current.connect()
    }
  }, [initializeClient])

  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect()
    }
  }, [])

  const reconnect = useCallback(async () => {
    if (clientRef.current) {
      await clientRef.current.connect()
    }
  }, [])

  const send = useCallback((message: WebSocketMessage) => {
    if (clientRef.current) {
      clientRef.current.send(message)
    }
  }, [])

  const subscribe = useCallback((channel: string) => {
    if (clientRef.current) {
      clientRef.current.subscribe(channel)
    }
  }, [])

  const unsubscribe = useCallback((channel: string) => {
    if (clientRef.current) {
      clientRef.current.unsubscribe(channel)
    }
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  const clearNotifications = useCallback(() => {
    setNotifications([])
  }, [])

  const markNotificationAsRead = useCallback((id: string) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id))
  }, [])

  const clearTaskUpdates = useCallback(() => {
    setTaskUpdates(new Map())
  }, [])

  const clearReportUpdates = useCallback(() => {
    setReportUpdates(new Map())
  }, [])

  // ============================================================================
  // 计算属性
  // ============================================================================

  const isConnected = status === ConnectionStatus.CONNECTED
  const isConnecting = status === ConnectionStatus.CONNECTING

  const subscriptions = useMemo(() => {
    return clientRef.current?.subscriptionList || []
  }, [status])

  const connectionInfo = useMemo(() => {
    return clientRef.current?.connectionInfo || null
  }, [status])

  // ============================================================================
  // 清理
  // ============================================================================

  useEffect(() => {
    return () => {
      if (clientRef.current) {
        clientRef.current.disconnect()
      }
    }
  }, [])

  // ============================================================================
  // 返回结果
  // ============================================================================

  return {
    // 连接状态
    status,
    isConnected,
    isConnecting,
    
    // 连接控制
    connect,
    disconnect,
    reconnect,
    
    // 消息发送
    send,
    
    // 频道订阅
    subscribe,
    unsubscribe,
    subscriptions,
    
    // 统计信息
    connectionInfo,
    
    // 消息历史
    messages,
    clearMessages,
    
    // 通知管理
    notifications,
    clearNotifications,
    markNotificationAsRead,
    
    // 任务更新
    taskUpdates,
    clearTaskUpdates,
    
    // 报告更新
    reportUpdates,
    clearReportUpdates
  }
}

// ============================================================================
// 专用Hooks
// ============================================================================

/**
 * 专用于任务更新的Hook
 */
export function useTaskUpdates() {
  const { taskUpdates, clearTaskUpdates } = useWebSocket({
    autoConnect: true,
    enableTaskUpdates: true,
    enableNotifications: false,
    enableReportUpdates: false
  })

  return {
    taskUpdates,
    clearTaskUpdates,
    getTaskUpdate: (taskId: string) => taskUpdates.get(taskId),
    hasTaskUpdate: (taskId: string) => taskUpdates.has(taskId)
  }
}

/**
 * 专用于通知的Hook
 */
export function useNotifications() {
  const { 
    notifications, 
    clearNotifications, 
    markNotificationAsRead,
    isConnected 
  } = useWebSocket({
    autoConnect: true,
    enableNotifications: true,
    enableTaskUpdates: false,
    enableReportUpdates: false
  })

  return {
    notifications,
    clearNotifications,
    markNotificationAsRead,
    isConnected,
    unreadCount: notifications.length
  }
}

/**
 * 专用于报告更新的Hook
 */
export function useReportUpdates() {
  const { reportUpdates, clearReportUpdates } = useWebSocket({
    autoConnect: true,
    enableReportUpdates: true,
    enableNotifications: false,
    enableTaskUpdates: false
  })

  return {
    reportUpdates,
    clearReportUpdates,
    getReportUpdate: (reportId: string) => reportUpdates.get(reportId),
    hasReportUpdate: (reportId: string) => reportUpdates.has(reportId)
  }
}

export default useWebSocket