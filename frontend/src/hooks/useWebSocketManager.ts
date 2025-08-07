'use client'

import { useEffect, useRef } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { getWebSocketManager } from '@/lib/websocket'

export function useWebSocketManager() {
  const { token, isAuthenticated } = useAuthStore()
  const wsManagerRef = useRef<ReturnType<typeof getWebSocketManager> | null>(null)

  useEffect(() => {
    if (isAuthenticated && token) {
      // 创建WebSocket连接
      if (!wsManagerRef.current) {
        wsManagerRef.current = getWebSocketManager()
      }

      const wsManager = wsManagerRef.current

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
        if (wsManager) {
          wsManager.disconnect()
        }
      }
    } else {
      // 用户未认证，断开WebSocket连接
      if (wsManagerRef.current) {
        wsManagerRef.current.disconnect()
      }
    }
  }, [isAuthenticated, token])

  return wsManagerRef.current
}