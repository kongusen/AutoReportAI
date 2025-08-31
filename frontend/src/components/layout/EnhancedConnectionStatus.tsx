/**
 * 增强的连接状态指示器 - 包含API健康检查、WebSocket状态和网络质量
 */

import React, { useEffect, useState, useCallback } from 'react'
import { cn } from '@/utils'
import { useWebSocketIntegration } from '@/hooks/useWebSocketIntegration'
import { ConnectionState } from '@/lib/websocket'
import { ApiClient } from '@/lib/api-client'

interface ConnectionStatus {
  api: 'healthy' | 'degraded' | 'unhealthy' | 'checking'
  websocket: ConnectionState
  network: 'excellent' | 'good' | 'poor' | 'offline'
  lastCheck: Date | null
}

interface NetworkStats {
  latency: number
  successRate: number
  errorCount: number
}

export const EnhancedConnectionStatus: React.FC = () => {
  const { connectionState } = useWebSocketIntegration()
  const [status, setStatus] = useState<ConnectionStatus>({
    api: 'checking',
    websocket: connectionState || ConnectionState.CLOSED,
    network: 'good',
    lastCheck: null
  })
  const [networkStats, setNetworkStats] = useState<NetworkStats>({
    latency: 0,
    successRate: 100,
    errorCount: 0
  })
  const [isExpanded, setIsExpanded] = useState(false)
  const [autoCollapse, setAutoCollapse] = useState<NodeJS.Timeout | null>(null)

  // 检查API健康状态
  const checkApiHealth = useCallback(async () => {
    const startTime = Date.now()
    
    try {
      const healthData = await ApiClient.checkHealth()
      const latency = Date.now() - startTime
      
      setStatus(prev => ({
        ...prev,
        api: healthData.status === 'healthy' ? 'healthy' : 'degraded',
        lastCheck: new Date()
      }))
      
      setNetworkStats(prev => ({
        latency,
        successRate: Math.min(100, prev.successRate + 1),
        errorCount: Math.max(0, prev.errorCount - 1)
      }))
      
    } catch (error) {
      setStatus(prev => ({
        ...prev,
        api: 'unhealthy',
        lastCheck: new Date()
      }))
      
      setNetworkStats(prev => ({
        latency: 0,
        successRate: Math.max(0, prev.successRate - 5),
        errorCount: prev.errorCount + 1
      }))
    }
  }, [])

  // 定期检查健康状态
  useEffect(() => {
    checkApiHealth() // 立即检查一次
    
    const interval = setInterval(checkApiHealth, 30000) // 每30秒检查一次
    return () => clearInterval(interval)
  }, [checkApiHealth])

  // 更新WebSocket状态
  useEffect(() => {
    setStatus(prev => ({
      ...prev,
      websocket: connectionState || ConnectionState.CLOSED
    }))
  }, [connectionState])

  // 根据网络统计计算网络质量
  useEffect(() => {
    const { latency, successRate } = networkStats
    
    let networkQuality: NetworkStats['latency'] extends number ? 'excellent' | 'good' | 'poor' | 'offline' : never
    
    if (successRate < 50 || latency === 0) {
      networkQuality = 'offline'
    } else if (latency < 100 && successRate > 90) {
      networkQuality = 'excellent' 
    } else if (latency < 300 && successRate > 75) {
      networkQuality = 'good'
    } else {
      networkQuality = 'poor'
    }
    
    setStatus(prev => ({
      ...prev,
      network: networkQuality
    }))
  }, [networkStats])

  // 点击展开/收起
  const handleClick = useCallback(() => {
    setIsExpanded(!isExpanded)
    
    // 自动收起
    if (autoCollapse) {
      clearTimeout(autoCollapse)
    }
    
    if (!isExpanded) {
      const timer = setTimeout(() => {
        setIsExpanded(false)
      }, 5000)
      setAutoCollapse(timer)
    }
  }, [isExpanded, autoCollapse])

  // 获取整体状态
  const getOverallStatus = () => {
    if (status.api === 'unhealthy' || status.network === 'offline') {
      return 'error'
    }
    if (status.api === 'degraded' || status.network === 'poor' || status.websocket === ConnectionState.CLOSED) {
      return 'warning'
    }
    if (status.api === 'checking') {
      return 'loading'
    }
    return 'success'
  }

  const overallStatus = getOverallStatus()

  const statusStyles = {
    success: {
      bg: 'bg-green-100 hover:bg-green-200',
      border: 'border-green-200',
      text: 'text-green-800',
      dot: 'bg-green-500'
    },
    warning: {
      bg: 'bg-yellow-100 hover:bg-yellow-200',
      border: 'border-yellow-200', 
      text: 'text-yellow-800',
      dot: 'bg-yellow-500'
    },
    error: {
      bg: 'bg-red-100 hover:bg-red-200',
      border: 'border-red-200',
      text: 'text-red-800', 
      dot: 'bg-red-500'
    },
    loading: {
      bg: 'bg-blue-100 hover:bg-blue-200',
      border: 'border-blue-200',
      text: 'text-blue-800',
      dot: 'bg-blue-500 animate-pulse'
    }
  }

  const currentStyles = statusStyles[overallStatus]

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div
        className={cn(
          'transition-all duration-300 cursor-pointer',
          'border rounded-lg shadow-lg backdrop-blur-sm',
          currentStyles.bg,
          currentStyles.border,
          isExpanded ? 'w-80' : 'w-auto'
        )}
        onClick={handleClick}
      >
        {/* 简化视图 */}
        <div className="flex items-center space-x-2 p-3">
          <div className={cn(
            'w-2 h-2 rounded-full',
            currentStyles.dot
          )} />
          
          <span className={cn('text-sm font-medium', currentStyles.text)}>
            {overallStatus === 'success' && '系统正常'}
            {overallStatus === 'warning' && '部分异常'}
            {overallStatus === 'error' && '连接异常'}
            {overallStatus === 'loading' && '检查中...'}
          </span>
          
          {!isExpanded && (
            <svg className={cn('w-4 h-4', currentStyles.text)} fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          )}
        </div>

        {/* 详细视图 */}
        {isExpanded && (
          <div className="border-t border-gray-200 p-3 space-y-3">
            {/* API状态 */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">API服务</span>
              <div className="flex items-center space-x-2">
                <div className={cn(
                  'w-2 h-2 rounded-full',
                  status.api === 'healthy' ? 'bg-green-500' :
                  status.api === 'degraded' ? 'bg-yellow-500' :
                  status.api === 'checking' ? 'bg-blue-500 animate-pulse' : 'bg-red-500'
                )} />
                <span className="text-sm font-medium">
                  {status.api === 'healthy' && '健康'}
                  {status.api === 'degraded' && '降级'}
                  {status.api === 'unhealthy' && '异常'}
                  {status.api === 'checking' && '检查中'}
                </span>
              </div>
            </div>

            {/* WebSocket状态 */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">实时连接</span>
              <div className="flex items-center space-x-2">
                <div className={cn(
                  'w-2 h-2 rounded-full',
                  status.websocket === ConnectionState.OPEN ? 'bg-green-500' :
                  status.websocket === ConnectionState.CONNECTING ? 'bg-blue-500 animate-pulse' :
                  'bg-red-500'
                )} />
                <span className="text-sm font-medium">
                  {status.websocket === ConnectionState.OPEN && '已连接'}
                  {status.websocket === ConnectionState.CONNECTING && '连接中'}
                  {status.websocket === ConnectionState.CLOSING && '断开中'}
                  {status.websocket === ConnectionState.CLOSED && '已断开'}
                </span>
              </div>
            </div>

            {/* 网络质量 */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">网络质量</span>
              <div className="flex items-center space-x-2">
                <div className={cn(
                  'w-2 h-2 rounded-full',
                  status.network === 'excellent' ? 'bg-green-500' :
                  status.network === 'good' ? 'bg-blue-500' :
                  status.network === 'poor' ? 'bg-yellow-500' : 'bg-red-500'
                )} />
                <span className="text-sm font-medium">
                  {status.network === 'excellent' && '优秀'}
                  {status.network === 'good' && '良好'}
                  {status.network === 'poor' && '较差'}
                  {status.network === 'offline' && '离线'}
                </span>
              </div>
            </div>

            {/* 网络统计 */}
            {networkStats.latency > 0 && (
              <div className="text-xs text-gray-500 space-y-1">
                <div className="flex justify-between">
                  <span>延迟:</span>
                  <span>{networkStats.latency}ms</span>
                </div>
                <div className="flex justify-between">
                  <span>成功率:</span>
                  <span>{Math.round(networkStats.successRate)}%</span>
                </div>
                {status.lastCheck && (
                  <div className="flex justify-between">
                    <span>最后检查:</span>
                    <span>{status.lastCheck.toLocaleTimeString()}</span>
                  </div>
                )}
              </div>
            )}

            {/* 操作按钮 */}
            <div className="flex space-x-2 text-xs">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  checkApiHealth()
                }}
                className="px-2 py-1 bg-white border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
              >
                重新检查
              </button>
              
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setIsExpanded(false)
                }}
                className="px-2 py-1 bg-white border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
              >
                收起
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}