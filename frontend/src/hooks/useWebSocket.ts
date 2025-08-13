'use client'

import { useEffect, useRef, useState } from 'react'
import { useTaskStore } from '@/features/tasks/taskStore'
import { TaskProgress, WebSocketMessage, TaskProgressMessage, SystemNotificationMessage } from '@/types'
import toast from 'react-hot-toast'

interface UseWebSocketOptions {
  url?: string
  enabled?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const {
    url = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',
    enabled = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10
  } = options

  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const ws = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null)

  const { updateTaskProgress } = useTaskStore()

  const connect = () => {
    if (!enabled || connecting || (ws.current && ws.current.readyState === WebSocket.OPEN)) {
      return
    }

    setConnecting(true)

    try {
      // 获取认证token
      const token = localStorage.getItem('authToken')
      const wsUrl = token ? `${url}?token=${token}` : url

      ws.current = new WebSocket(wsUrl)

      ws.current.onopen = () => {
        console.log('WebSocket connected')
        setConnected(true)
        setConnecting(false)
        reconnectAttempts.current = 0
        
        // 发送心跳包
        if (ws.current) {
          ws.current.send(JSON.stringify({ type: 'ping' }))
        }
      }

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          handleMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        setConnected(false)
        setConnecting(false)
        ws.current = null

        // 如果不是手动关闭且还有重连次数，则重连
        if (enabled && event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++
          console.log(`Reconnecting in ${reconnectInterval}ms... (${reconnectAttempts.current}/${maxReconnectAttempts})`)
          
          reconnectTimeout.current = setTimeout(() => {
            connect()
          }, reconnectInterval)
        }
      }

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnecting(false)
      }
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      setConnecting(false)
    }
  }

  const disconnect = () => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current)
      reconnectTimeout.current = null
    }

    if (ws.current) {
      ws.current.close(1000, 'User initiated disconnect')
      ws.current = null
    }

    setConnected(false)
    setConnecting(false)
    reconnectAttempts.current = 0
  }

  const handleMessage = (message: WebSocketMessage) => {
    switch (message.type) {
      case 'task_progress':
        handleTaskProgressMessage(message as TaskProgressMessage)
        break
      case 'system_notification':
        handleSystemNotificationMessage(message as SystemNotificationMessage)
        break
      case 'report_completed':
        handleReportCompletedMessage(message)
        break
      case 'pong':
        // 心跳响应，不需要处理
        break
      default:
        console.log('Unknown WebSocket message type:', message.type)
    }
  }

  const handleTaskProgressMessage = (message: TaskProgressMessage) => {
    const progress: TaskProgress = {
      task_id: message.payload.task_id,
      progress: message.payload.progress,
      status: message.payload.status,
      message: message.payload.message,
      current_step: message.payload.current_step,
      updated_at: message.timestamp
    }

    updateTaskProgress(progress)

    // 显示重要状态变更的通知
    if (progress.status === 'completed') {
      toast.success(`任务 #${progress.task_id} 执行完成`)
    } else if (progress.status === 'failed') {
      toast.error(`任务 #${progress.task_id} 执行失败`)
    }
  }

  const handleSystemNotificationMessage = (message: SystemNotificationMessage) => {
    const { title, message: content, level } = message.payload

    switch (level) {
      case 'success':
        toast.success(`${title}: ${content}`)
        break
      case 'error':
        toast.error(`${title}: ${content}`)
        break
      case 'warning':
        toast(`${title}: ${content}`, { icon: '⚠️' })
        break
      default:
        toast(`${title}: ${content}`)
    }
  }

  const handleReportCompletedMessage = (message: WebSocketMessage) => {
    const report = message.payload
    toast.success(`报告 "${report.name}" 生成完成，可以下载了`)
  }

  const sendMessage = (message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket not connected, cannot send message')
    }
  }

  // 设置定期心跳
  useEffect(() => {
    if (!connected) return

    const heartbeat = setInterval(() => {
      sendMessage({ type: 'ping' })
    }, 30000) // 每30秒发送一次心跳

    return () => clearInterval(heartbeat)
  }, [connected])

  // 初始连接和清理
  useEffect(() => {
    if (enabled) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [enabled])

  return {
    connected,
    connecting,
    connect,
    disconnect,
    sendMessage
  }
}