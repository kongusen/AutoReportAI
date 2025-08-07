'use client'

import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { getWebSocketManager, WebSocketManager, ConnectionState } from '@/lib/websocket'
import { useAuthStore } from '@/stores/authStore'

interface WebSocketContextValue {
  wsManager: WebSocketManager | null
  isConnected: boolean
  connectionState: ConnectionState | null
}

const WebSocketContext = createContext<WebSocketContextValue>({
  wsManager: null,
  isConnected: false,
  connectionState: null,
})

export const useWebSocket = () => {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}

interface WebSocketProviderProps {
  children: React.ReactNode
}

export function WebSocketProvider({ children }: WebSocketProviderProps) {
  const { token, isAuthenticated } = useAuthStore()
  const wsManagerRef = useRef<WebSocketManager | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [connectionState, setConnectionState] = useState<ConnectionState | null>(null)

  useEffect(() => {
    if (isAuthenticated && token) {
      // 创建WebSocket连接
      if (!wsManagerRef.current) {
        wsManagerRef.current = getWebSocketManager()
      }

      const wsManager = wsManagerRef.current

      // 注册连接状态监听器
      const handleConnectionStateChange = (state: ConnectionState, error?: Error) => {
        setConnectionState(state)
        setIsConnected(state === ConnectionState.OPEN)
        
        if (error) {
          console.error('WebSocket connection error:', error)
        }
      }

      wsManager.onConnectionStateChange(handleConnectionStateChange)

      // 连接WebSocket
      wsManager.connect(token)
        .then(() => {
          console.log('WebSocket connected successfully')
        })
        .catch((error) => {
          console.error('Failed to connect WebSocket:', error)
        })

      // 清理函数
      return () => {
        wsManager.offConnectionStateChange(handleConnectionStateChange)
        if (wsManager) {
          wsManager.disconnect()
        }
      }
    } else {
      // 用户未认证，断开WebSocket连接
      if (wsManagerRef.current) {
        wsManagerRef.current.disconnect()
        setIsConnected(false)
        setConnectionState(ConnectionState.CLOSED)
      }
    }
  }, [isAuthenticated, token])

  const contextValue: WebSocketContextValue = {
    wsManager: wsManagerRef.current,
    isConnected,
    connectionState,
  }

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  )
}