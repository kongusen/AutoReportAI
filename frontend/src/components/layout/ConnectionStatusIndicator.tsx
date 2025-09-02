'use client'

import { useWebSocket } from '@/hooks/useWebSocket'
import { 
  SignalIcon, 
  ExclamationCircleIcon, 
  ArrowsRightLeftIcon,
  XCircleIcon,
  WifiIcon,
  NoSymbolIcon
} from '@heroicons/react/24/outline'
import { useEffect, useState } from 'react'

export enum ConnectionStatus {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTING = 'disconnecting',
  DISCONNECTED = 'disconnected',
  ERROR = 'error'
}

export function ConnectionStatusIndicator() {
  const { status, isConnected, connectionInfo, connect: reconnect } = useWebSocket({
    autoConnect: true,
    debug: true
  })
  const [isVisible, setIsVisible] = useState(false)
  const [showDetails, setShowDetails] = useState(false)

  useEffect(() => {
    // 连接状态不正常时显示指示器
    if (status !== ConnectionStatus.CONNECTED) {
      setIsVisible(true)
    } else {
      // 连接成功后短暂显示成功状态
      setIsVisible(true)
      const timer = setTimeout(() => {
        setIsVisible(false)
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [status])

  if (!isVisible) return null

  const getStatusInfo = () => {
    switch (status) {
      case ConnectionStatus.CONNECTING:
        return {
          icon: <ArrowsRightLeftIcon className="w-4 h-4 animate-spin" />,
          text: '正在连接...',
          bgColor: 'bg-blue-50',
          textColor: 'text-blue-700',
          borderColor: 'border-blue-200',
          canRetry: false
        }
      case ConnectionStatus.CONNECTED:
        return {
          icon: <SignalIcon className="w-4 h-4 text-green-500" />,
          text: '实时连接已建立',
          bgColor: 'bg-green-50',
          textColor: 'text-green-700',
          borderColor: 'border-green-200',
          canRetry: false
        }
      case ConnectionStatus.DISCONNECTING:
        return {
          icon: <ArrowsRightLeftIcon className="w-4 h-4 animate-spin" />,
          text: '正在断开...',
          bgColor: 'bg-yellow-50',
          textColor: 'text-yellow-700',
          borderColor: 'border-yellow-200',
          canRetry: false
        }
      case ConnectionStatus.DISCONNECTED:
        return {
          icon: <XCircleIcon className="w-4 h-4 text-gray-500" />,
          text: '连接已断开',
          bgColor: 'bg-gray-50',
          textColor: 'text-gray-700',
          borderColor: 'border-gray-200',
          canRetry: true
        }
      case ConnectionStatus.ERROR:
        return {
          icon: <NoSymbolIcon className="w-4 h-4 text-red-500" />,
          text: '连接失败',
          bgColor: 'bg-red-50',
          textColor: 'text-red-700',
          borderColor: 'border-red-200',
          canRetry: true
        }
      default:
        return {
          icon: <ExclamationCircleIcon className="w-4 h-4" />,
          text: '未知状态',
          bgColor: 'bg-gray-50',
          textColor: 'text-gray-700',
          borderColor: 'border-gray-200',
          canRetry: false
        }
    }
  }

  const statusInfo = getStatusInfo()

  const handleReconnect = async () => {
    try {
      await reconnect()
    } catch (error) {
      console.error('手动重连失败:', error)
    }
  }

  const formatUptime = (uptime: number) => {
    if (uptime < 1000) return '刚刚连接'
    const seconds = Math.floor(uptime / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    
    if (hours > 0) {
      return `已连接 ${hours}小时${minutes % 60}分钟`
    } else if (minutes > 0) {
      return `已连接 ${minutes}分钟${seconds % 60}秒`
    } else {
      return `已连接 ${seconds}秒`
    }
  }

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* 主状态指示器 */}
      <div 
        className={`
          ${statusInfo.bgColor} ${statusInfo.borderColor} border rounded-lg 
          px-4 py-3 shadow-lg backdrop-blur-sm
          flex items-center space-x-3 cursor-pointer
          hover:shadow-xl transition-all duration-200
          ${showDetails ? 'rounded-b-none' : ''}
        `}
        onClick={() => setShowDetails(!showDetails)}
      >
        <div className="flex items-center space-x-2">
          {statusInfo.icon}
          <span className={`text-sm font-medium ${statusInfo.textColor}`}>
            {statusInfo.text}
          </span>
        </div>

        {/* 在线指示器 */}
        {isConnected && (
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-xs text-green-600">在线</span>
          </div>
        )}

        {/* 重连按钮 */}
        {statusInfo.canRetry && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              handleReconnect()
            }}
            className="px-2 py-1 text-xs bg-white bg-opacity-50 rounded border hover:bg-opacity-70 transition-colors"
          >
            重连
          </button>
        )}

        {/* 展开指示器 */}
        <div className={`transition-transform duration-200 ${showDetails ? 'rotate-180' : ''}`}>
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </div>
      </div>

      {/* 详细信息面板 */}
      {showDetails && connectionInfo && (
        <div className={`
          ${statusInfo.bgColor} ${statusInfo.borderColor} border border-t-0 
          rounded-b-lg px-4 py-3 shadow-lg backdrop-blur-sm
          max-w-xs
        `}>
          <div className="space-y-2 text-xs">
            {/* 连接信息 */}
            {connectionInfo.sessionId && (
              <div className="flex justify-between">
                <span className="text-gray-600">会话ID:</span>
                <span className="font-mono text-gray-800 truncate ml-2" title={connectionInfo.sessionId}>
                  {connectionInfo.sessionId.slice(-8)}
                </span>
              </div>
            )}
            
            {/* 运行时间 */}
            {connectionInfo.uptime > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-600">运行时间:</span>
                <span className="text-gray-800">
                  {formatUptime(connectionInfo.uptime)}
                </span>
              </div>
            )}

            {/* 消息统计 */}
            <div className="flex justify-between">
              <span className="text-gray-600">消息:</span>
              <span className="text-gray-800">
                ↑{connectionInfo.messagesSent} ↓{connectionInfo.messagesReceived}
              </span>
            </div>

            {/* 重连次数 */}
            {connectionInfo.reconnectCount > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-600">重连次数:</span>
                <span className="text-gray-800">{connectionInfo.reconnectCount}</span>
              </div>
            )}

            {/* 订阅频道 */}
            {connectionInfo.subscriptions && connectionInfo.subscriptions.length > 0 && (
              <div>
                <div className="text-gray-600 mb-1">订阅频道:</div>
                <div className="space-y-1 pl-2">
                  {connectionInfo.subscriptions.map((channel: string) => (
                    <div key={channel} className="flex items-center space-x-1">
                      <div className="w-1.5 h-1.5 bg-blue-400 rounded-full" />
                      <span className="text-gray-700 text-xs font-mono">{channel}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 离线消息数量 */}
            {connectionInfo.offlineMessageCount > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-600">离线消息:</span>
                <span className="text-orange-600 font-semibold">
                  {connectionInfo.offlineMessageCount}条待发送
                </span>
              </div>
            )}

            {/* 最后心跳时间 */}
            {connectionInfo.lastPingTime && (
              <div className="flex justify-between">
                <span className="text-gray-600">最后心跳:</span>
                <span className="text-gray-800">
                  {new Date(connectionInfo.lastPingTime).toLocaleTimeString()}
                </span>
              </div>
            )}
          </div>

          {/* 操作按钮 */}
          <div className="flex space-x-2 mt-3 pt-2 border-t border-opacity-20">
            <button
              onClick={handleReconnect}
              disabled={status === ConnectionStatus.CONNECTING}
              className="flex-1 px-2 py-1 text-xs bg-white bg-opacity-50 rounded border hover:bg-opacity-70 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {status === ConnectionStatus.CONNECTING ? '连接中...' : '重新连接'}
            </button>
            <button
              onClick={() => setShowDetails(false)}
              className="px-2 py-1 text-xs bg-white bg-opacity-50 rounded border hover:bg-opacity-70 transition-colors"
            >
              收起
            </button>
          </div>
        </div>
      )}
    </div>
  )
}