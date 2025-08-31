/**
 * 通知中心组件 - 统一的消息通知和状态提示
 */

import React, { useEffect, useState, useCallback } from 'react'
import { cn } from '@/utils'
import { useToast, Toast } from '@/hooks/useToast'

export interface NotificationCenterProps {
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center'
  maxNotifications?: number
  className?: string
}

export const NotificationCenter: React.FC<NotificationCenterProps> = ({
  position = 'top-right',
  maxNotifications = 5,
  className
}) => {
  const { toasts, removeToast } = useToast()
  const [visibleToasts, setVisibleToasts] = useState<Toast[]>([])

  // 限制显示的通知数量
  useEffect(() => {
    setVisibleToasts(toasts.slice(0, maxNotifications))
  }, [toasts, maxNotifications])

  const positionClasses = {
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4', 
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'top-center': 'top-4 left-1/2 transform -translate-x-1/2',
    'bottom-center': 'bottom-4 left-1/2 transform -translate-x-1/2'
  }

  if (visibleToasts.length === 0) return null

  return (
    <div className={cn(
      'fixed z-50 space-y-2',
      positionClasses[position],
      className
    )}>
      {visibleToasts.map((toast) => (
        <NotificationItem
          key={toast.id}
          toast={toast}
          onDismiss={() => removeToast(toast.id)}
        />
      ))}
    </div>
  )
}

// 单个通知项组件
interface NotificationItemProps {
  toast: Toast
  onDismiss: () => void
}

const NotificationItem: React.FC<NotificationItemProps> = ({ toast, onDismiss }) => {
  const [isVisible, setIsVisible] = useState(false)
  const [isExiting, setIsExiting] = useState(false)

  // 入场动画
  useEffect(() => {
    setIsVisible(true)
  }, [])

  // 自动消失
  useEffect(() => {
    if (toast.duration && toast.duration > 0) {
      const timer = setTimeout(() => {
        handleDismiss()
      }, toast.duration)
      
      return () => clearTimeout(timer)
    }
  }, [toast.duration])

  const handleDismiss = useCallback(() => {
    if (!toast.dismissible) return
    
    setIsExiting(true)
    setTimeout(() => {
      onDismiss()
    }, 200) // 等待退出动画完成
  }, [onDismiss, toast.dismissible])

  const typeStyles = {
    success: {
      bg: 'bg-green-50 border-green-200',
      icon: 'text-green-400',
      title: 'text-green-800',
      message: 'text-green-700'
    },
    error: {
      bg: 'bg-red-50 border-red-200',
      icon: 'text-red-400',
      title: 'text-red-800',
      message: 'text-red-700'
    },
    warning: {
      bg: 'bg-yellow-50 border-yellow-200',
      icon: 'text-yellow-400',
      title: 'text-yellow-800',
      message: 'text-yellow-700'
    },
    info: {
      bg: 'bg-blue-50 border-blue-200',
      icon: 'text-blue-400',
      title: 'text-blue-800',
      message: 'text-blue-700'
    }
  }

  const styles = typeStyles[toast.type]

  const typeIcons = {
    success: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
      </svg>
    ),
    error: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
      </svg>
    ),
    warning: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
      </svg>
    ),
    info: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
      </svg>
    )
  }

  return (
    <div
      className={cn(
        'max-w-md w-full border rounded-lg shadow-lg pointer-events-auto overflow-hidden transition-all duration-200',
        styles.bg,
        isVisible && !isExiting ? 'transform translate-x-0 opacity-100' : 'transform translate-x-full opacity-0'
      )}
    >
      <div className="p-4">
        <div className="flex items-start">
          {/* 图标 */}
          <div className={cn('flex-shrink-0', styles.icon)}>
            {typeIcons[toast.type]}
          </div>
          
          <div className="ml-3 w-0 flex-1">
            {/* 标题 */}
            {toast.title && (
              <p className={cn('text-sm font-medium', styles.title)}>
                {toast.title}
              </p>
            )}
            
            {/* 消息 */}
            <p className={cn(
              'text-sm',
              styles.message,
              toast.title ? 'mt-1' : ''
            )}>
              {toast.message}
            </p>
            
            {/* 详细信息 */}
            {toast.details && (
              <p className="text-xs text-gray-500 mt-2">
                {toast.details}
              </p>
            )}
            
            {/* 操作按钮 */}
            {toast.actions && toast.actions.length > 0 && (
              <div className="mt-3 flex space-x-2">
                {toast.actions.map((action, index) => (
                  <button
                    key={index}
                    onClick={action.action}
                    className={cn(
                      'text-xs font-medium px-2 py-1 rounded border',
                      'hover:bg-opacity-80 transition-colors',
                      styles.title
                    )}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </div>
          
          {/* 关闭按钮 */}
          {toast.dismissible && (
            <div className="ml-4 flex-shrink-0 flex">
              <button
                onClick={handleDismiss}
                className={cn(
                  'inline-flex text-gray-400 hover:text-gray-500 focus:outline-none',
                  'focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500'
                )}
              >
                <span className="sr-only">关闭</span>
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          )}
        </div>
      </div>
      
      {/* 进度条 */}
      {!toast.persistent && toast.duration && toast.duration > 0 && (
        <div className="h-1 bg-gray-200">
          <div 
            className={cn('h-full bg-current opacity-50 transition-all linear')}
            style={{ 
              animation: `progress-shrink ${toast.duration}ms linear forwards`,
              backgroundColor: styles.icon.replace('text-', 'bg-').replace('-400', '-500')
            }}
          />
        </div>
      )}
    </div>
  )
}

// CSS动画（需要添加到全局样式中）
const styles = `
@keyframes progress-shrink {
  from { width: 100%; }
  to { width: 0%; }
}
`