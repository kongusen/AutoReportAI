'use client'

import { useEffect, useRef, useState } from 'react'
import { useAuthStore } from '@/features/auth/authStore'
import { getWebSocketManager, WebSocketManager, ConnectionState } from '@/lib/websocket'

export function useWebSocketManager(): { wsManager: WebSocketManager | null; connectionState: ConnectionState | null } {
  const { token, isAuthenticated } = useAuthStore()
  const wsManagerRef = useRef<WebSocketManager | null>(null)
  const [connectionState, setConnectionState] = useState<ConnectionState | null>(null)

  useEffect(() => {
    if (isAuthenticated && token) {
      if (!wsManagerRef.current) {
        wsManagerRef.current = getWebSocketManager()
      }
      const wsManager = wsManagerRef.current

      const handleStateChange = (state: ConnectionState) => {
        setConnectionState(state)
      }
      wsManager.onConnectionStateChange(handleStateChange)

      if (wsManager.connectionState !== ConnectionState.OPEN && 
          wsManager.connectionState !== ConnectionState.CONNECTING) {
        wsManager.connect(token).catch(err => {
          console.error('WebSocket connection failed on hook mount', err)
        })
      }

      return () => {
        wsManager.offConnectionStateChange(handleStateChange)
      }
    } else {
      if (wsManagerRef.current && wsManagerRef.current.connectionState === ConnectionState.OPEN) {
        wsManagerRef.current.disconnect()
        setConnectionState(ConnectionState.CLOSED)
      }
    }
  }, [isAuthenticated, token])

  return { wsManager: wsManagerRef.current, connectionState }
}