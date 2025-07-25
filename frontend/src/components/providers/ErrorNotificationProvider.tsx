'use client'

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { ErrorNotification, errorHandler, onErrorNotification } from '@/lib/error-handler'
import { 
  ErrorToast, 
  ErrorBanner, 
  ErrorModal, 
  ErrorInline 
} from '@/components/ui/error-notification'

interface ErrorNotificationContextValue {
  // Show notifications manually
  showError: (notification: Omit<ErrorNotification, 'id'>) => string
  showToast: (notification: Omit<ErrorNotification, 'id' | 'type'>) => string
  showBanner: (notification: Omit<ErrorNotification, 'id' | 'type'>) => string
  showModal: (notification: Omit<ErrorNotification, 'id' | 'type'>) => string
  
  // Hide notifications
  hideNotification: (id: string) => void
  hideAllNotifications: () => void
  
  // Retry functionality
  setRetryHandler: (id: string, handler: () => void) => void
  removeRetryHandler: (id: string) => void
  
  // Current notifications
  notifications: ErrorNotification[]
}

const ErrorNotificationContext = createContext<ErrorNotificationContextValue | undefined>(undefined)

interface ErrorNotificationProviderProps {
  children: React.ReactNode
  maxNotifications?: number
  defaultPosition?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center'
}

export function ErrorNotificationProvider({ 
  children, 
  maxNotifications = 5,
  defaultPosition = 'top-right'
}: ErrorNotificationProviderProps) {
  const [notifications, setNotifications] = useState<ErrorNotification[]>([])
  const [retryHandlers, setRetryHandlers] = useState<Map<string, () => void>>(new Map())

  // Generate unique ID for notifications
  const generateId = useCallback(() => {
    return `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }, [])

  // Add notification
  const addNotification = useCallback((notification: ErrorNotification) => {
    setNotifications(prev => {
      const newNotifications = [notification, ...prev].slice(0, maxNotifications)
      return newNotifications
    })
    return notification.id
  }, [maxNotifications])

  // Remove notification
  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
    setRetryHandlers(prev => {
      const newMap = new Map(prev)
      newMap.delete(id)
      return newMap
    })
  }, [])

  // Show error notification
  const showError = useCallback((notification: Omit<ErrorNotification, 'id'>) => {
    const id = generateId()
    const fullNotification: ErrorNotification = {
      ...notification,
      id,
    }
    return addNotification(fullNotification)
  }, [generateId, addNotification])

  // Convenience methods for different types
  const showToast = useCallback((notification: Omit<ErrorNotification, 'id' | 'type'>) => {
    return showError({ ...notification, type: 'toast' })
  }, [showError])

  const showBanner = useCallback((notification: Omit<ErrorNotification, 'id' | 'type'>) => {
    return showError({ ...notification, type: 'banner' })
  }, [showError])

  const showModal = useCallback((notification: Omit<ErrorNotification, 'id' | 'type'>) => {
    return showError({ ...notification, type: 'modal' })
  }, [showError])

  // Hide notifications
  const hideNotification = useCallback((id: string) => {
    removeNotification(id)
  }, [removeNotification])

  const hideAllNotifications = useCallback(() => {
    setNotifications([])
    setRetryHandlers(new Map())
  }, [])

  // Retry handlers
  const setRetryHandler = useCallback((id: string, handler: () => void) => {
    setRetryHandlers(prev => new Map(prev).set(id, handler))
  }, [])

  const removeRetryHandler = useCallback((id: string) => {
    setRetryHandlers(prev => {
      const newMap = new Map(prev)
      newMap.delete(id)
      return newMap
    })
  }, [])

  // Listen to global error handler
  useEffect(() => {
    const handleGlobalError = (notification: ErrorNotification) => {
      addNotification(notification)
    }

    onErrorNotification(handleGlobalError)

    return () => {
      // Note: The error handler doesn't provide a way to remove listeners
      // This is a limitation that could be improved
    }
  }, [addNotification])

  // Auto-remove notifications after their duration
  useEffect(() => {
    const timers: NodeJS.Timeout[] = []

    notifications.forEach(notification => {
      if (notification.autoClose && notification.duration) {
        const timer = setTimeout(() => {
          removeNotification(notification.id)
        }, notification.duration)
        timers.push(timer)
      }
    })

    return () => {
      timers.forEach(timer => clearTimeout(timer))
    }
  }, [notifications, removeNotification])

  const contextValue: ErrorNotificationContextValue = {
    showError,
    showToast,
    showBanner,
    showModal,
    hideNotification,
    hideAllNotifications,
    setRetryHandler,
    removeRetryHandler,
    notifications,
  }

  // Separate notifications by type
  const toastNotifications = notifications.filter(n => n.type === 'toast')
  const bannerNotifications = notifications.filter(n => n.type === 'banner')
  const modalNotifications = notifications.filter(n => n.type === 'modal')
  const inlineNotifications = notifications.filter(n => n.type === 'inline')

  return (
    <ErrorNotificationContext.Provider value={contextValue}>
      {children}
      
      {/* Render toast notifications */}
      <div className="fixed inset-0 pointer-events-none z-50">
        <div className={`absolute ${getPositionClasses(defaultPosition)} space-y-2 pointer-events-auto`}>
          {toastNotifications.map(notification => (
            <ErrorToast
              key={notification.id}
              notification={notification}
              position={defaultPosition}
              onClose={() => removeNotification(notification.id)}
              onRetry={retryHandlers.get(notification.id)}
            />
          ))}
        </div>
      </div>
      
      {/* Render banner notifications */}
      {bannerNotifications.map(notification => (
        <ErrorBanner
          key={notification.id}
          notification={notification}
          onClose={() => removeNotification(notification.id)}
          onRetry={retryHandlers.get(notification.id)}
        />
      ))}
      
      {/* Render modal notifications */}
      {modalNotifications.map(notification => (
        <ErrorModal
          key={notification.id}
          notification={notification}
          isOpen={true}
          onOpenChange={(open) => {
            if (!open) removeNotification(notification.id)
          }}
          onClose={() => removeNotification(notification.id)}
          onRetry={retryHandlers.get(notification.id)}
        />
      ))}
    </ErrorNotificationContext.Provider>
  )
}

function getPositionClasses(position: string): string {
  switch (position) {
    case 'top-right':
      return 'top-4 right-4'
    case 'top-left':
      return 'top-4 left-4'
    case 'bottom-right':
      return 'bottom-4 right-4'
    case 'bottom-left':
      return 'bottom-4 left-4'
    case 'top-center':
      return 'top-4 left-1/2 transform -translate-x-1/2'
    case 'bottom-center':
      return 'bottom-4 left-1/2 transform -translate-x-1/2'
    default:
      return 'top-4 right-4'
  }
}

export function useErrorNotification() {
  const context = useContext(ErrorNotificationContext)
  if (context === undefined) {
    throw new Error('useErrorNotification must be used within an ErrorNotificationProvider')
  }
  return context
}

// Hook for handling API errors with automatic retry
export function useApiErrorHandler() {
  const { showToast, setRetryHandler } = useErrorNotification()

  const handleApiError = useCallback((
    error: Error, 
    options: {
      retryFn?: () => void | Promise<void>
      context?: string
      showNotification?: boolean
    } = {}
  ) => {
    const { retryFn, context = 'API call', showNotification = true } = options

    if (showNotification) {
      const notificationId = showToast({
        severity: 'medium' as any,
        title: 'Request Failed',
        message: error.message || 'An unexpected error occurred',
        autoClose: !retryFn, // Don't auto-close if retry is available
        duration: retryFn ? undefined : 5000,
      })

      if (retryFn) {
        setRetryHandler(notificationId, async () => {
          try {
            await retryFn()
          } catch (retryError) {
            console.error('Retry failed:', retryError)
            // Could show another notification for retry failure
          }
        })
      }
    }

    // Also send to global error handler for logging/reporting
    errorHandler.handleError(error, { 
      component: 'api-error-handler',
      action: context 
    })
  }, [showToast, setRetryHandler])

  return { handleApiError }
}

// Hook for form error handling
export function useFormErrorHandler() {
  const { showToast } = useErrorNotification()

  const handleFormError = useCallback((
    error: Error | string,
    field?: string
  ) => {
    const message = typeof error === 'string' ? error : error.message
    
    showToast({
      severity: 'medium' as any,
      title: field ? `${field} Error` : 'Form Error',
      message,
      autoClose: true,
      duration: 4000,
    })
  }, [showToast])

  const handleValidationErrors = useCallback((
    errors: Record<string, string[]>
  ) => {
    Object.entries(errors).forEach(([field, messages]) => {
      messages.forEach(message => {
        handleFormError(message, field)
      })
    })
  }, [handleFormError])

  return { 
    handleFormError, 
    handleValidationErrors 
  }
}