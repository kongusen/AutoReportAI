'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { WebSocketManager, ConnectionState } from '@/lib/websocket'
import { useWebSocketManager } from '@/hooks/useWebSocketManager'

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
  const { wsManager, connectionState } = useWebSocketManager()
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    setIsConnected(connectionState === ConnectionState.OPEN)
  }, [connectionState])

  const contextValue: WebSocketContextValue = {
    wsManager,
    isConnected,
    connectionState,
  }

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  )
}