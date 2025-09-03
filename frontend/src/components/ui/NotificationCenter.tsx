'use client'

/**
 * 通知中心组件 - 集成WebSocket实时通知和状态提示
 */

import React, { useEffect, useState, useCallback, useRef } from 'react'
import { cn } from '@/utils'
import { useWebSocket } from '@/hooks/useWebSocket'
import {
  BellIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline'

export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error' | 'task_update' | 'report_ready'
  title?: string
  message: string
  details?: string
  timestamp: Date
  read: boolean
  persistent?: boolean
  duration?: number
  actions?: Array<{
    label: string
    action: () => void
    variant?: 'default' | 'primary' | 'danger'
  }>
  metadata?: {
    taskId?: string
    reportId?: string
    userId?: string
    [key: string]: any
  }
}

export interface NotificationCenterProps {
  className?: string
  maxVisible?: number
  showHeader?: boolean
  enableSound?: boolean
}

export function NotificationCenter({
  className,
  maxVisible = 5,
  showHeader = false,
  enableSound = true
}: NotificationCenterProps) {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const notificationRef = useRef<HTMLDivElement>(null)

  // 处理WebSocket消息
  const handleWebSocketMessage = useCallback((message: any) => {
    if (message.type === 'notification') {
      addNotification({
        id: message.data.id || generateId(),
        type: message.data.type || 'info',
        title: message.data.title,
        message: message.data.message,
        details: message.data.details,
        timestamp: new Date(message.timestamp || Date.now()),
        read: false,
        persistent: message.data.persistent,
        duration: message.data.duration,
        metadata: message.data.metadata
      })
    }
  }, [])

  // WebSocket连接
  const { isConnected, connectionInfo } = useWebSocket({
    onMessage: handleWebSocketMessage,
    enableNotifications: true,
    autoConnect: true
  })

  // 生成唯一ID
  const generateId = () => `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

  // 添加通知
  const addNotification = useCallback((notification: Omit<Notification, 'id'> & { id?: string }) => {
    const newNotification: Notification = {
      id: notification.id || generateId(),
      ...notification,
      timestamp: notification.timestamp || new Date()
    }

    setNotifications(prev => {
      const exists = prev.some(n => n.id === newNotification.id)
      if (exists) return prev
      
      const updated = [newNotification, ...prev].slice(0, 100) // 最多保留100条
      return updated
    })

    // 播放提示音
    if (enableSound && audioRef.current) {
      audioRef.current.play().catch(() => {
        // 静默处理音频播放失败
      })
    }
  }, [enableSound])

  // 移除通知
  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }, [])

  // 标记为已读
  const markAsRead = useCallback((id: string) => {
    setNotifications(prev => 
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    )
  }, [])

  // 标记所有为已读
  const markAllAsRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })))
  }, [])

  // 清空所有通知
  const clearAll = useCallback(() => {
    setNotifications([])
  }, [])

  // 计算未读数量
  useEffect(() => {
    setUnreadCount(notifications.filter(n => !n.read).length)
  }, [notifications])

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  // 自动隐藏非持久化通知
  useEffect(() => {
    const timers: NodeJS.Timeout[] = []

    notifications.forEach(notification => {
      if (!notification.persistent && notification.duration && notification.duration > 0) {
        const timer = setTimeout(() => {
          removeNotification(notification.id)
        }, notification.duration)
        timers.push(timer)
      }
    })

    return () => timers.forEach(timer => clearTimeout(timer))
  }, [notifications, removeNotification])

  const visibleNotifications = notifications.slice(0, maxVisible)

  return (
    <>
      {/* 提示音 */}
      {enableSound && (
        <audio ref={audioRef} preload="auto">
          <source src="data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+nousIzCjmH0fHTeCUEJHXJ8N+QQQ" type="audio/wav" />
        </audio>
      )}

      <div ref={notificationRef} className={cn('relative', className)}>
        {/* 通知触发按钮 */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={cn(
            'relative inline-flex items-center justify-center p-2 rounded-md',
            'text-gray-400 hover:text-gray-500 hover:bg-gray-100',
            'focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500',
            'transition-colors duration-200'
          )}
        >
          <BellIcon className="h-6 w-6" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-red-500 flex items-center justify-center">
              <span className="text-xs font-medium text-white">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            </span>
          )}
          
          {/* WebSocket连接状态指示器 */}
          <div className={cn(
            'absolute -bottom-1 -right-1 h-3 w-3 rounded-full border-2 border-white',
            isConnected ? 'bg-green-400' : 'bg-red-400'
          )} />
        </button>

        {/* 通知面板 */}
        {isOpen && (
          <div className="absolute right-0 top-full mt-2 w-96 bg-white rounded-lg shadow-lg ring-1 ring-black ring-opacity-5 z-50">
            {/* 头部 */}
            {showHeader && (
              <div className="px-4 py-3 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900">通知中心</h3>
                  <div className="flex items-center space-x-2">
                    {notifications.length > 0 && (
                      <button
                        onClick={markAllAsRead}
                        className="text-sm text-blue-600 hover:text-blue-700"
                      >
                        全部已读
                      </button>
                    )}
                    <button
                      onClick={() => setIsOpen(false)}
                      className="text-gray-400 hover:text-gray-500"
                    >
                      <XMarkIcon className="h-5 w-5" />
                    </button>
                  </div>
                </div>
                
                {/* 连接状态 */}
                <div className="flex items-center mt-2 text-xs text-gray-500">
                  <div className={cn(
                    'h-2 w-2 rounded-full mr-2',
                    isConnected ? 'bg-green-400' : 'bg-red-400'
                  )} />
                  {isConnected ? '实时通知已连接' : '连接已断开'}
                  {connectionInfo?.subscriptions?.length && (
                    <span className="ml-2">
                      ({connectionInfo.subscriptions.length} 个频道)
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* 通知列表 */}
            <div className="max-h-96 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="px-4 py-8 text-center text-gray-500">
                  <BellIcon className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                  <p className="text-sm">暂无通知</p>
                </div>
              ) : (
                <div className="py-2">
                  {visibleNotifications.map((notification) => (
                    <NotificationItem
                      key={notification.id}
                      notification={notification}
                      onRead={markAsRead}
                      onDismiss={removeNotification}
                    />
                  ))}
                  
                  {notifications.length > maxVisible && (
                    <div className="px-4 py-2 text-center border-t border-gray-100">
                      <button
                        onClick={clearAll}
                        className="text-sm text-gray-600 hover:text-gray-700"
                      >
                        查看全部 ({notifications.length - maxVisible} 条更多)
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  )
}

// 单个通知项组件
interface NotificationItemProps {
  notification: Notification
  onRead: (id: string) => void
  onDismiss: (id: string) => void
}

function NotificationItem({ notification, onRead, onDismiss }: NotificationItemProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // 格式化时间
  const formatTime = (timestamp: Date) => {
    const now = new Date()
    const diff = now.getTime() - timestamp.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (days > 0) return `${days}天前`
    if (hours > 0) return `${hours}小时前`
    if (minutes > 0) return `${minutes}分钟前`
    return '刚刚'
  }

  const handleClick = () => {
    if (!notification.read) {
      onRead(notification.id)
    }
    if (notification.details) {
      setIsExpanded(!isExpanded)
    }
  }

  const getIcon = () => {
    switch (notification.type) {
      case 'success':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'error':
        return <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
      case 'warning':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
      case 'task_update':
        return <InformationCircleIcon className="h-5 w-5 text-blue-500" />
      case 'report_ready':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      default:
        return <InformationCircleIcon className="h-5 w-5 text-gray-500" />
    }
  }

  const getTypeLabel = () => {
    switch (notification.type) {
      case 'task_update':
        return '任务更新'
      case 'report_ready':
        return '报告完成'
      case 'success':
        return '成功'
      case 'error':
        return '错误'
      case 'warning':
        return '警告'
      default:
        return '信息'
    }
  }

  return (
    <div
      className={cn(
        'px-4 py-3 border-b border-gray-100 last:border-b-0',
        'hover:bg-gray-50 cursor-pointer transition-colors',
        !notification.read && 'bg-blue-50 border-l-4 border-l-blue-500'
      )}
      onClick={handleClick}
    >
      <div className="flex items-start space-x-3">
        {/* 图标 */}
        <div className="flex-shrink-0">
          {getIcon()}
        </div>

        {/* 内容 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              {notification.title && (
                <p className="text-sm font-medium text-gray-900 truncate">
                  {notification.title}
                </p>
              )}
              <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full">
                {getTypeLabel()}
              </span>
            </div>
            
            <div className="flex items-center space-x-2">
              <span className="text-xs text-gray-500">
                {formatTime(notification.timestamp)}
              </span>
              {!notification.read && (
                <div className="h-2 w-2 bg-blue-500 rounded-full" />
              )}
            </div>
          </div>

          <p className="text-sm text-gray-600 mt-1">
            {notification.message}
          </p>

          {/* 详细信息（可展开） */}
          {notification.details && isExpanded && (
            <div className="mt-2 p-2 bg-gray-50 rounded text-xs text-gray-600">
              {notification.details}
            </div>
          )}

          {/* 元数据显示 */}
          {notification.metadata && (
            <div className="mt-2 flex items-center space-x-4 text-xs text-gray-500">
              {notification.metadata.taskId && (
                <span>任务: {notification.metadata.taskId.slice(-8)}</span>
              )}
              {notification.metadata.reportId && (
                <span>报告: {notification.metadata.reportId.slice(-8)}</span>
              )}
            </div>
          )}

          {/* 操作按钮 */}
          {notification.actions && notification.actions.length > 0 && (
            <div className="mt-3 flex space-x-2">
              {notification.actions.map((action, index) => (
                <button
                  key={index}
                  onClick={(e) => {
                    e.stopPropagation()
                    action.action()
                  }}
                  className={cn(
                    'text-xs px-3 py-1 rounded border transition-colors',
                    action.variant === 'primary' && 'bg-blue-100 text-blue-700 border-blue-200 hover:bg-blue-200',
                    action.variant === 'danger' && 'bg-red-100 text-red-700 border-red-200 hover:bg-red-200',
                    !action.variant && 'bg-gray-100 text-gray-700 border-gray-200 hover:bg-gray-200'
                  )}
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 关闭按钮 */}
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDismiss(notification.id)
          }}
          className="flex-shrink-0 text-gray-400 hover:text-gray-500 transition-colors"
        >
          <XMarkIcon className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}