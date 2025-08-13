import { WebSocketMessage, TaskProgressMessage, SystemNotificationMessage, ReportCompletedMessage } from '@/types'

export enum ConnectionState {
  CONNECTING = 0,
  OPEN = 1,
  CLOSING = 2,
  CLOSED = 3
}

export interface WebSocketConfig {
  url: string
  maxReconnectAttempts?: number
  heartbeatInterval?: number
  reconnectBackoffFactor?: number
  maxReconnectDelay?: number
  debug?: boolean
}

export class WebSocketManager {
  private ws: WebSocket | null = null
  private config: Required<WebSocketConfig>
  private reconnectAttempts = 0
  private reconnectTimeout: NodeJS.Timeout | null = null
  private heartbeatInterval: NodeJS.Timeout | null = null
  private heartbeatTimeout: NodeJS.Timeout | null = null
  private messageHandlers: Map<string, (data: any) => void> = new Map()
  private connectionStateListeners: Set<(state: ConnectionState, error?: Error) => void> = new Set()
  private lastToken: string | undefined
  private connectionStartTime: number = 0
  private messagesReceived = 0
  private messagesSent = 0
  private _connectionState: ConnectionState = ConnectionState.CLOSED

  constructor(config: WebSocketConfig | string) {
    if (typeof config === 'string') {
      this.config = {
        url: config,
        maxReconnectAttempts: 5,
        heartbeatInterval: 30000,
        reconnectBackoffFactor: 2,
        maxReconnectDelay: 30000,
        debug: false
      }
    } else {
      this.config = {
        maxReconnectAttempts: 5,
        heartbeatInterval: 30000,
        reconnectBackoffFactor: 2,
        maxReconnectDelay: 30000,
        debug: false,
        ...config
      }
    }
  }

  connect(token?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.connectionState === ConnectionState.CONNECTING || (this.ws && this.ws.readyState === WebSocket.CONNECTING)) {
        this.log('Already connecting, ignoring duplicate connect call')
        return
      }

      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.log('Already connected')
        resolve()
        return
      }

      this.lastToken = token
      this.connectionStartTime = Date.now()
      this.notifyStateChange(ConnectionState.CONNECTING)
      
      try {
        const wsUrl = token ? `${this.config.url}?token=${token}` : this.config.url
        this.ws = new WebSocket(wsUrl)
        
        this.ws.onopen = () => {
          this.log('WebSocket connected successfully')
          this.reconnectAttempts = 0
          this.startHeartbeat()
          this.notifyStateChange(ConnectionState.OPEN)
          resolve()
        }

        this.ws.onmessage = (event) => {
          this.messagesReceived++
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            this.log('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onclose = (event) => {
          this.log(`WebSocket disconnected: ${event.code} - ${event.reason}`)
          this.stopHeartbeat()
          this.notifyStateChange(ConnectionState.CLOSED)
          
          // 如果不是主动关闭（1000）或认证失败（4001），尝试重连
          if (event.code !== 1000 && event.code !== 4001) {
            this.scheduleReconnect()
          } else if (event.code === 4001) {
            this.log('Authentication failed, not attempting to reconnect')
          }
        }

        this.ws.onerror = (error) => {
          this.log('WebSocket error:', error)
          const wsError = new Error('WebSocket connection error')
          this.notifyStateChange(ConnectionState.CLOSED, wsError)
          reject(wsError)
        }
      } catch (error) {
        this.log('Failed to create WebSocket connection:', error)
        const createError = error instanceof Error ? error : new Error('Failed to create WebSocket')
        this.notifyStateChange(ConnectionState.CLOSED, createError)
        reject(createError)
      }
    })
  }

  disconnect(): void {
    this.log('Disconnecting WebSocket')
    this.stopHeartbeat()
    this.clearReconnectTimeout()
    
    if (this.ws) {
      this.notifyStateChange(ConnectionState.CLOSING)
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
    
    this.reconnectAttempts = 0
    this.notifyStateChange(ConnectionState.CLOSED)
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.log('Max reconnection attempts reached')
      const maxAttemptsError = new Error('Max reconnection attempts reached')
      this.notifyStateChange(ConnectionState.CLOSED, maxAttemptsError)
      return
    }

    this.reconnectAttempts++
    const baseDelay = 1000 * Math.pow(this.config.reconnectBackoffFactor, this.reconnectAttempts - 1)
    const delay = Math.min(baseDelay, this.config.maxReconnectDelay)
    
    this.log(`Scheduling reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.config.maxReconnectAttempts})`)
    
    this.reconnectTimeout = setTimeout(() => {
      this.attemptReconnect()
    }, delay)
  }

  private async attemptReconnect(): Promise<void> {
    try {
      await this.connect(this.lastToken)
      this.log('Reconnection successful')
    } catch (error) {
      this.log('Reconnection failed:', error)
      this.scheduleReconnect()
    }
  }

  private clearReconnectTimeout(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
  }

  // 日志记录
  private log(...args: any[]): void {
    if (this.config.debug) {
      console.log('[WebSocket]', ...args)
    }
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        // 发送心跳前设置超时检测
        if (this.heartbeatTimeout) {
          clearTimeout(this.heartbeatTimeout)
        }
        
        // 设置5秒超时
        this.heartbeatTimeout = setTimeout(() => {
          this.log('Heartbeat timeout, closing connection')
          if (this.ws) {
            this.ws.close(4000, 'Heartbeat timeout')
          }
        }, 5000)
        
        this.ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, this.config.heartbeatInterval) // 使用配置的心跳间隔
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
    
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout)
      this.heartbeatTimeout = null
    }
  }

  private handleMessage(message: WebSocketMessage): void {
    // 处理心跳响应
    if (message.type === 'pong') {
      // 清除心跳超时定时器
      if (this.heartbeatTimeout) {
        clearTimeout(this.heartbeatTimeout)
        this.heartbeatTimeout = null
      }
      this.log('Heartbeat pong received')
      return
    }

    // 分发消息到对应的处理器
    const handler = this.messageHandlers.get(message.type)
    if (handler) {
      handler(message.payload)
    } else {
      console.warn('No handler registered for message type:', message.type)
    }
  }

  // 注册消息处理器
  on(messageType: string, handler: (data: any) => void): void {
    this.messageHandlers.set(messageType, handler)
  }

  // 取消消息处理器
  off(messageType: string): void {
    this.messageHandlers.delete(messageType)
  }

  // 注册连接状态监听器
  onConnectionStateChange(listener: (state: ConnectionState, error?: Error) => void): void {
    this.connectionStateListeners.add(listener)
  }

  // 取消连接状态监听器
  offConnectionStateChange(listener: (state: ConnectionState, error?: Error) => void): void {
    this.connectionStateListeners.delete(listener)
  }

  // 通知连接状态变化
  private notifyStateChange(state: ConnectionState, error?: Error): void {
    this._connectionState = state
    this.connectionStateListeners.forEach(listener => {
      try {
        listener(state, error)
      } catch (err) {
        console.error('Error in connection state listener:', err)
      }
    })
  }

  // 发送消息
  send(message: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  get isConnecting(): boolean {
    return this.connectionState === ConnectionState.CONNECTING
  }

  // 获取连接状态
  get isConnected(): boolean {
    return this.connectionState === ConnectionState.OPEN
  }

  get connectionState(): ConnectionState {
    return this._connectionState
  }
}

// 创建全局WebSocket管理器实例
let wsManager: WebSocketManager | null = null

export const getWebSocketManager = (): WebSocketManager => {
  if (!wsManager) {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws'
    wsManager = new WebSocketManager(wsUrl)
  }
  return wsManager
}