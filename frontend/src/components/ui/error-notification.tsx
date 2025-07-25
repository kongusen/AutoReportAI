'use client'

import React, { useState, useEffect } from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  AlertCircle, 
  XCircle, 
  AlertTriangle, 
  Info, 
  X, 
  RefreshCw,
  Copy,
  CheckCircle
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ErrorNotification, ErrorSeverity } from '@/lib/error-handler'

interface ErrorNotificationProps {
  notification: ErrorNotification
  onClose?: () => void
  onRetry?: () => void
  className?: string
}

const severityConfig = {
  [ErrorSeverity.LOW]: {
    icon: Info,
    className: 'border-blue-200 bg-blue-50 text-blue-900 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-100',
    iconClassName: 'text-blue-600 dark:text-blue-400',
  },
  [ErrorSeverity.MEDIUM]: {
    icon: AlertTriangle,
    className: 'border-yellow-200 bg-yellow-50 text-yellow-900 dark:border-yellow-800 dark:bg-yellow-950 dark:text-yellow-100',
    iconClassName: 'text-yellow-600 dark:text-yellow-400',
  },
  [ErrorSeverity.HIGH]: {
    icon: AlertCircle,
    className: 'border-orange-200 bg-orange-50 text-orange-900 dark:border-orange-800 dark:bg-orange-950 dark:text-orange-100',
    iconClassName: 'text-orange-600 dark:text-orange-400',
  },
  [ErrorSeverity.CRITICAL]: {
    icon: XCircle,
    className: 'border-red-200 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100',
    iconClassName: 'text-red-600 dark:text-red-400',
  },
}

export function ErrorNotificationComponent({ 
  notification, 
  onClose, 
  onRetry,
  className 
}: ErrorNotificationProps) {
  const [isVisible, setIsVisible] = useState(true)
  const [copied, setCopied] = useState(false)
  const config = severityConfig[notification.severity]
  const Icon = config.icon

  useEffect(() => {
    if (notification.autoClose && notification.duration) {
      const timer = setTimeout(() => {
        handleClose()
      }, notification.duration)
      return () => clearTimeout(timer)
    }
  }, [notification.autoClose, notification.duration])

  const handleClose = () => {
    setIsVisible(false)
    setTimeout(() => onClose?.(), 300) // Allow animation to complete
  }

  const handleRetry = () => {
    onRetry?.()
    // Find retry action from notification actions
    const retryAction = notification.actions?.find(action => 
      action.label.toLowerCase().includes('retry')
    )
    retryAction?.action()
  }

  const copyErrorId = async () => {
    try {
      await navigator.clipboard.writeText(notification.id)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.warn('Failed to copy error ID:', error)
    }
  }

  if (!isVisible) return null

  return (
    <Alert 
      className={cn(
        'relative transition-all duration-300 ease-in-out',
        config.className,
        !isVisible && 'opacity-0 scale-95',
        className
      )}
    >
      <div className="flex items-start space-x-3">
        <Icon className={cn('h-5 w-5 mt-0.5 flex-shrink-0', config.iconClassName)} />
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <AlertTitle className="text-sm font-semibold">
              {notification.title}
            </AlertTitle>
            
            <div className="flex items-center space-x-2">
              <Badge 
                variant="outline" 
                className="text-xs px-2 py-0.5"
              >
                {notification.severity}
              </Badge>
              
              {onClose && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleClose}
                  className="h-6 w-6 p-0 hover:bg-transparent"
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
          
          <AlertDescription className="mt-1 text-sm">
            {notification.message}
          </AlertDescription>
          
          {/* Error ID for debugging */}
          <div className="mt-2 flex items-center space-x-2 text-xs opacity-70">
            <span>Error ID: {notification.id.slice(-8)}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={copyErrorId}
              className="h-4 w-4 p-0 hover:bg-transparent"
            >
              {copied ? (
                <CheckCircle className="h-3 w-3 text-green-600" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
            </Button>
          </div>
          
          {/* Action buttons */}
          {(notification.actions || onRetry) && (
            <div className="mt-3 flex items-center space-x-2">
              {onRetry && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRetry}
                  className="h-8 px-3 text-xs"
                >
                  <RefreshCw className="h-3 w-3 mr-1" />
                  Retry
                </Button>
              )}
              
              {notification.actions?.map((action, index) => (
                <Button
                  key={index}
                  variant="default"
                  size="sm"
                  onClick={action.action}
                  className="h-8 px-3 text-xs"
                >
                  {action.label}
                </Button>
              ))}
            </div>
          )}
        </div>
      </div>
    </Alert>
  )
}

// Toast notification variant
interface ErrorToastProps extends ErrorNotificationProps {
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center'
}

export function ErrorToast({ 
  notification, 
  onClose, 
  onRetry, 
  position = 'top-right',
  className 
}: ErrorToastProps) {
  const positionClasses = {
    'top-right': 'fixed top-4 right-4 z-50',
    'top-left': 'fixed top-4 left-4 z-50',
    'bottom-right': 'fixed bottom-4 right-4 z-50',
    'bottom-left': 'fixed bottom-4 left-4 z-50',
    'top-center': 'fixed top-4 left-1/2 transform -translate-x-1/2 z-50',
    'bottom-center': 'fixed bottom-4 left-1/2 transform -translate-x-1/2 z-50',
  }

  return (
    <div className={cn(positionClasses[position], 'max-w-md w-full')}>
      <ErrorNotificationComponent
        notification={notification}
        onClose={onClose}
        onRetry={onRetry}
        className={cn('shadow-lg border', className)}
      />
    </div>
  )
}

// Banner notification variant
export function ErrorBanner({ 
  notification, 
  onClose, 
  onRetry, 
  className 
}: ErrorNotificationProps) {
  return (
    <div className="fixed top-0 left-0 right-0 z-50">
      <ErrorNotificationComponent
        notification={notification}
        onClose={onClose}
        onRetry={onRetry}
        className={cn('rounded-none border-x-0 border-t-0', className)}
      />
    </div>
  )
}

// Modal notification variant
interface ErrorModalProps extends ErrorNotificationProps {
  isOpen: boolean
  onOpenChange?: (open: boolean) => void
}

export function ErrorModal({ 
  notification, 
  onClose, 
  onRetry, 
  isOpen,
  onOpenChange,
  className 
}: ErrorModalProps) {
  const handleClose = () => {
    onOpenChange?.(false)
    onClose?.()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 backdrop-blur-sm"
        onClick={handleClose}
      />
      
      {/* Modal content */}
      <div className="relative z-10 w-full max-w-md mx-4">
        <ErrorNotificationComponent
          notification={notification}
          onClose={handleClose}
          onRetry={onRetry}
          className={cn('shadow-2xl', className)}
        />
      </div>
    </div>
  )
}

// Inline notification variant (for forms, etc.)
export function ErrorInline({ 
  notification, 
  onClose, 
  onRetry, 
  className 
}: ErrorNotificationProps) {
  return (
    <ErrorNotificationComponent
      notification={notification}
      onClose={onClose}
      onRetry={onRetry}
      className={cn('border-0 bg-transparent p-0 shadow-none', className)}
    />
  )
}