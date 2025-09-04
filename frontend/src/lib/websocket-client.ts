/**
 * AutoReportAI 增强WebSocket客户端
 * 基于WEBSOCKET_GUIDE.md实现
 * 支持自动重连、心跳检测、频道订阅、离线消息缓存
 */

import {
  WebSocketMessageType,
  type WebSocketMessage,
  type NotificationMessage,
  type TaskUpdateMessage,
  type ReportUpdateMessage
} from '@/types/api'

// ============================================================================
// WebSocket客户端配置
// ============================================================================

export interface WebSocketConfig {
  url: string
  token?: string
  clientType?: string
  clientVersion?: string
  maxReconnectAttempts?: number
  reconnectInterval?: number
  heartbeatInterval?: number
  debug?: boolean
}

export enum ConnectionStatus {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTING = 'disconnecting',
  DISCONNECTED = 'disconnected',
  ERROR = 'error'
}

// ============================================================================
// 增强WebSocket客户端
// ============================================================================

export class AutoReportWebSocketClient {
  private ws: WebSocket | null = null
  private config: Required<WebSocketConfig>
  private reconnectAttempts = 0
  private reconnectTimeout: NodeJS.Timeout | null = null
  private heartbeatInterval: NodeJS.Timeout | null = null
  private messageHandlers = new Map<string, Set<(message: any) => void>>()
  private connectionListeners = new Set<(status: ConnectionStatus, error?: Error) => void>()
  private subscriptions = new Set<string>()
  private offlineMessages: WebSocketMessage[] = []
  private connectionStats = {
    messagesReceived: 0,
    messagesSent: 0,
    reconnectCount: 0,
    connectedAt: null as Date | null,
    lastPingTime: null as Date | null,
    sessionId: null as string | null
  }
  private _status: ConnectionStatus = ConnectionStatus.DISCONNECTED

  constructor(config: WebSocketConfig) {
    this.config = {
      url: config.url,
      token: config.token || '',
      clientType: config.clientType || 'web',
      clientVersion: config.clientVersion || '2.0.0',
      maxReconnectAttempts: config.maxReconnectAttempts || 5,
      reconnectInterval: config.reconnectInterval || 3000,
      heartbeatInterval: config.heartbeatInterval || 30000,
      debug: config.debug ?? (process.env.NODE_ENV === 'development')
    }

    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', () => this.disconnect())
      window.addEventListener('online', () => this.handleOnline())
      window.addEventListener('offline', () => this.handleOffline())
    }
  }

  // ============================================================================
  // 连接管理
  // ============================================================================

  /**
   * 建立WebSocket连接
   */
  async connect(token?: string): Promise<void> {
    if (token) {
      this.config.token = token
    }

    if (this._status === ConnectionStatus.CONNECTING) {
      this.log('已经在连接中，忽略重复连接请求')
      return
    }

    if (this._status === ConnectionStatus.CONNECTED) {
      this.log('已经连接，忽略重复连接请求')
      return
    }

    return new Promise((resolve, reject) => {
      try {
        this.setStatus(ConnectionStatus.CONNECTING)

        // 构建连接URL
        const params = new URLSearchParams({
          client_type: this.config.clientType,
          client_version: this.config.clientVersion
        })

        if (this.config.token) {
          params.set('token', this.config.token)
        }

        const wsUrl = `${this.config.url}?${params.toString()}`
        this.log('连接WebSocket:', wsUrl)
        this.log('WebSocket配置:', {
          url: this.config.url,
          token: this.config.token ? `${this.config.token.substring(0, 10)}...` : 'None',
          clientType: this.config.clientType,
          clientVersion: this.config.clientVersion
        })

        this.ws = new WebSocket(wsUrl)

        this.ws.onopen = () => {
          this.log('WebSocket连接成功')
          this.connectionStats.connectedAt = new Date()
          this.connectionStats.reconnectCount = this.reconnectAttempts
          this.reconnectAttempts = 0

          // 如果没有通过URL参数传递token，发送认证消息
          if (!this.config.token) {
            this.sendAuth()
          }

          this.setStatus(ConnectionStatus.CONNECTED)
          this.startHeartbeat()
          this.resubscribeChannels()
          this.processOfflineMessages()
          resolve()
        }

        this.ws.onmessage = (event) => {
          this.connectionStats.messagesReceived++
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            this.log('消息解析失败:', error, event.data)
          }
        }

        this.ws.onclose = (event) => {
          this.log(`WebSocket连接关闭: ${event.code} - ${event.reason}`)
          this.log('WebSocket关闭详情:', {
            code: event.code,
            reason: event.reason || 'No reason provided',
            wasClean: event.wasClean,
            status: this._status
          })
          this.stopHeartbeat()
          this.connectionStats.connectedAt = null

          if (event.code === 4001) {
            this.setStatus(ConnectionStatus.ERROR, new Error('认证失败'))
            reject(new Error('认证失败'))
          } else if (event.code !== 1000 && this._status !== ConnectionStatus.DISCONNECTING) {
            this.setStatus(ConnectionStatus.DISCONNECTED)
            this.scheduleReconnect()
          } else {
            this.setStatus(ConnectionStatus.DISCONNECTED)
          }
        }

        this.ws.onerror = (error) => {
          this.log('WebSocket错误:', error)
          // WebSocket error event 是一个 Event 对象，没有 type 属性
          let errorMessage = 'Unknown error'
          
          if (error instanceof ErrorEvent) {
            errorMessage = error.message || error.error?.message || 'Network error'
          } else if (error instanceof Event) {
            // 对于普通的 Event 对象，我们可以根据 WebSocket 的状态来判断错误类型
            if (this.ws) {
              switch (this.ws.readyState) {
                case WebSocket.CONNECTING:
                  errorMessage = 'Connection failed'
                  break
                case WebSocket.CLOSING:
                  errorMessage = 'Connection closing error'
                  break
                case WebSocket.CLOSED:
                  errorMessage = 'Connection closed unexpectedly'
                  break
                default:
                  errorMessage = 'WebSocket error occurred'
              }
            }
          }
          
          const wsError = new Error(`WebSocket连接错误: ${errorMessage}`)
          this.setStatus(ConnectionStatus.ERROR, wsError)
          reject(wsError)
        }
      } catch (error) {
        const createError = error instanceof Error ? error : new Error('创建WebSocket失败')
        this.setStatus(ConnectionStatus.ERROR, createError)
        reject(createError)
      }
    })
  }

  /**
   * 断开WebSocket连接
   */
  disconnect(): void {
    this.log('主动断开WebSocket连接')
    this.setStatus(ConnectionStatus.DISCONNECTING)
    this.stopHeartbeat()
    this.clearReconnectTimeout()

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }

    this.setStatus(ConnectionStatus.DISCONNECTED)
    this.reconnectAttempts = 0
  }

  // ============================================================================
  // 重连机制
  // ============================================================================

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.log('达到最大重连次数')
      this.setStatus(ConnectionStatus.ERROR, new Error('达到最大重连次数'))
      return
    }

    this.reconnectAttempts++
    const delay = this.config.reconnectInterval * Math.pow(2, Math.min(this.reconnectAttempts - 1, 5))
    const jitter = Math.random() * 1000

    this.log(`安排重连: ${delay + jitter}ms后 (第${this.reconnectAttempts}/${this.config.maxReconnectAttempts}次)`)

    this.reconnectTimeout = setTimeout(() => {
      this.reconnect()
    }, delay + jitter)
  }

  private async reconnect(): Promise<void> {
    try {
      await this.connect()
      this.log('重连成功')
    } catch (error) {
      this.log('重连失败:', error)
      this.scheduleReconnect()
    }
  }

  private clearReconnectTimeout(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
  }

  // ============================================================================
  // 心跳机制
  // ============================================================================

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected) {
        this.connectionStats.lastPingTime = new Date()
        this.send({
          type: WebSocketMessageType.PING,
          timestamp: new Date().toISOString()
        })
      }
    }, this.config.heartbeatInterval)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  // ============================================================================
  // 消息处理
  // ============================================================================

  private handleMessage(message: WebSocketMessage): void {
    this.log('收到消息:', message)

    // 处理系统消息
    switch (message.type) {
      case WebSocketMessageType.PONG:
        this.log('收到心跳响应')
        return

      case WebSocketMessageType.NOTIFICATION:
        const notification = message as NotificationMessage
        if (notification.data?.session_id) {
          this.connectionStats.sessionId = notification.data.session_id
          this.log('收到会话ID:', notification.data.session_id)
        }
        break

      case WebSocketMessageType.ERROR:
        this.log('服务器错误:', message.data)
        break
    }

    // 分发到具体的处理器
    const handlers = this.messageHandlers.get(message.type)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(message)
        } catch (error) {
          this.log('消息处理器错误:', error)
        }
      })
    }

    // 分发到通用处理器
    const generalHandlers = this.messageHandlers.get('*')
    if (generalHandlers) {
      generalHandlers.forEach(handler => {
        try {
          handler(message)
        } catch (error) {
          this.log('通用消息处理器错误:', error)
        }
      })
    }
  }

  /**
   * 发送消息
   */
  send(message: WebSocketMessage): void {
    if (this.isConnected && this.ws) {
      try {
        const messageStr = JSON.stringify(message)
        this.ws.send(messageStr)
        this.connectionStats.messagesSent++
        this.log('发送消息:', message)
      } catch (error) {
        this.log('发送消息失败:', error)
      }
    } else {
      // 离线时缓存消息
      if (message.type !== WebSocketMessageType.PING) {
        this.offlineMessages.push(message)
        this.log('连接断开，消息已缓存:', message)
      }
    }
  }

  /**
   * 发送认证消息
   */
  private sendAuth(): void {
    if (this.config.token) {
      this.send({
        type: WebSocketMessageType.AUTH,
        token: this.config.token
      })
    }
  }

  // ============================================================================
  // 频道订阅
  // ============================================================================

  /**
   * 订阅频道
   */
  subscribe(channel: string): void {
    this.subscriptions.add(channel)
    this.send({
      type: WebSocketMessageType.SUBSCRIBE,
      data: { channel }
    })
    this.log('订阅频道:', channel)
  }

  /**
   * 取消订阅频道
   */
  unsubscribe(channel: string): void {
    this.subscriptions.delete(channel)
    this.send({
      type: WebSocketMessageType.UNSUBSCRIBE,
      data: { channel }
    })
    this.log('取消订阅频道:', channel)
  }

  /**
   * 重新订阅所有频道
   */
  private resubscribeChannels(): void {
    this.subscriptions.forEach(channel => {
      this.send({
        type: WebSocketMessageType.SUBSCRIBE,
        data: { channel }
      })
    })
    this.log('重新订阅频道:', Array.from(this.subscriptions))
  }

  // ============================================================================
  // 事件监听
  // ============================================================================

  /**
   * 注册消息处理器
   */
  on(messageType: string, handler: (message: any) => void): void {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, new Set())
    }
    this.messageHandlers.get(messageType)!.add(handler)
  }

  /**
   * 取消消息处理器
   */
  off(messageType: string, handler?: (message: any) => void): void {
    const handlers = this.messageHandlers.get(messageType)
    if (handlers) {
      if (handler) {
        handlers.delete(handler)
      } else {
        handlers.clear()
      }
    }
  }

  /**
   * 注册连接状态监听器
   */
  onConnectionChange(listener: (status: ConnectionStatus, error?: Error) => void): () => void {
    this.connectionListeners.add(listener)
    return () => this.connectionListeners.delete(listener)
  }

  // ============================================================================
  // 离线消息处理
  // ============================================================================

  private processOfflineMessages(): void {
    if (this.offlineMessages.length > 0) {
      this.log('处理离线消息:', this.offlineMessages.length)
      const messages = [...this.offlineMessages]
      this.offlineMessages = []

      messages.forEach(message => this.send(message))
    }
  }

  // ============================================================================
  // 网络状态处理
  // ============================================================================

  private handleOnline(): void {
    this.log('网络恢复在线')
    if (this._status === ConnectionStatus.DISCONNECTED || this._status === ConnectionStatus.ERROR) {
      this.connect()
    }
  }

  private handleOffline(): void {
    this.log('网络离线')
    // 不主动断开连接，让WebSocket自然超时
  }

  // ============================================================================
  // 状态管理
  // ============================================================================

  private setStatus(status: ConnectionStatus, error?: Error): void {
    if (this._status !== status) {
      this._status = status
      this.log('连接状态变更:', status, error?.message)

      this.connectionListeners.forEach(listener => {
        try {
          listener(status, error)
        } catch (err) {
          this.log('连接状态监听器错误:', err)
        }
      })
    }
  }

  // ============================================================================
  // 公共属性
  // ============================================================================

  get status(): ConnectionStatus {
    return this._status
  }

  get isConnected(): boolean {
    return this._status === ConnectionStatus.CONNECTED && this.ws?.readyState === WebSocket.OPEN
  }

  get isConnecting(): boolean {
    return this._status === ConnectionStatus.CONNECTING
  }

  get subscriptionList(): string[] {
    return Array.from(this.subscriptions)
  }

  get connectionInfo() {
    return {
      ...this.connectionStats,
      status: this._status,
      subscriptions: Array.from(this.subscriptions),
      offlineMessageCount: this.offlineMessages.length,
      uptime: this.connectionStats.connectedAt 
        ? Date.now() - this.connectionStats.connectedAt.getTime() 
        : 0
    }
  }

  // ============================================================================
  // 工具方法
  // ============================================================================

  private log(...args: any[]): void {
    if (this.config.debug) {
      console.log('[WebSocket]', ...args)
    }
  }

  /**
   * 更新认证token
   */
  updateToken(token: string): void {
    this.config.token = token
    if (this.isConnected) {
      this.sendAuth()
    }
  }

  /**
   * 清除离线消息
   */
  clearOfflineMessages(): void {
    this.offlineMessages = []
  }

  /**
   * 获取连接统计信息
   */
  getStats() {
    return { ...this.connectionInfo }
  }
}

// ============================================================================
// 全局WebSocket管理器
// ============================================================================

class WebSocketManager {
  private client: AutoReportWebSocketClient | null = null
  private config: WebSocketConfig | null = null

  /**
   * 初始化WebSocket客户端
   */
  init(config: WebSocketConfig): AutoReportWebSocketClient {
    if (this.client) {
      this.client.disconnect()
    }

    this.config = config
    this.client = new AutoReportWebSocketClient(config)
    return this.client
  }

  /**
   * 获取当前客户端
   */
  getClient(): AutoReportWebSocketClient | null {
    return this.client
  }

  /**
   * 重新连接
   */
  reconnect(): Promise<void> {
    if (!this.client || !this.config) {
      throw new Error('WebSocket未初始化')
    }

    return this.client.connect()
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    if (this.client) {
      this.client.disconnect()
    }
  }
}

// 导出全局实例
export const webSocketManager = new WebSocketManager()
export default AutoReportWebSocketClient