/**
 * WebSocket集成钩子
 * 提供WebSocket连接和消息处理的集成功能
 */

import { useEffect } from 'react'
import { useWebSocket } from './useWebSocket'

export function useWebSocketIntegration() {
  const { isConnected, connect, disconnect } = useWebSocket()

  useEffect(() => {
    // 自动连接WebSocket
    connect()
    
    // 组件卸载时断开连接
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    isConnected
  }
}