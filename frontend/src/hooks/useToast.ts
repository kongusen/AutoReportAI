import { useState, useCallback } from 'react'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  message: string
  type: ToastType
  duration?: number
  title?: string
  details?: string
  actions?: Array<{
    label: string
    action: () => void
  }>
  dismissible?: boolean
  persistent?: boolean
}

let toastId = 0
const toasts: Toast[] = []
const listeners: Array<(toasts: Toast[]) => void> = []

const notify = (toasts: Toast[]) => {
  listeners.forEach(listener => listener([...toasts]))
}

const addToast = (
  message: string, 
  type: ToastType = 'info', 
  duration = 5000,
  options?: Partial<Toast>
) => {
  const id = String(toastId++)
  const toast: Toast = { 
    id, 
    message, 
    type, 
    duration: options?.persistent ? 0 : duration,
    dismissible: options?.dismissible ?? true,
    ...options 
  }
  
  toasts.push(toast)
  notify(toasts)
  
  if (toast.duration && toast.duration > 0) {
    setTimeout(() => {
      const index = toasts.findIndex(t => t.id === id)
      if (index > -1) {
        toasts.splice(index, 1)
        notify(toasts)
      }
    }, toast.duration)
  }
}

const removeToast = (id: string) => {
  const index = toasts.findIndex(t => t.id === id)
  if (index > -1) {
    toasts.splice(index, 1)
    notify(toasts)
  }
}

export const useToast = () => {
  const [toastList, setToastList] = useState<Toast[]>([...toasts])

  const subscribe = useCallback((listener: (toasts: Toast[]) => void) => {
    listeners.push(listener)
    return () => {
      const index = listeners.indexOf(listener)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }
  }, [])

  const showToast = useCallback((
    message: string, 
    type: ToastType = 'info', 
    duration = 5000,
    options?: Partial<Toast>
  ) => {
    addToast(message, type, duration, options)
  }, [])

  const showError = useCallback((message: string, details?: string, actions?: Toast['actions']) => {
    addToast(message, 'error', 10000, {
      title: 'Error',
      details,
      actions,
      persistent: true,
      dismissible: true
    })
  }, [])

  const showSuccess = useCallback((message: string, duration = 3000) => {
    addToast(message, 'success', duration)
  }, [])

  const showWarning = useCallback((message: string, duration = 5000) => {
    addToast(message, 'warning', duration)
  }, [])

  const showTaskError = useCallback((taskId: number, error: string, details?: string) => {
    const actions = [
      {
        label: 'View Details',
        action: () => console.log('Task error details:', { taskId, error, details })
      },
      {
        label: 'Retry Task',
        action: () => {
          // 这里可以添加重试任务的逻辑
          console.log('Retrying task:', taskId)
        }
      }
    ]
    
    addToast(
      `Task #${taskId} failed: ${error}`, 
      'error', 
      0, // persistent
      {
        title: 'Task Execution Failed',
        details,
        actions,
        persistent: true
      }
    )
  }, [])

  const clearAllToasts = useCallback(() => {
    toasts.splice(0, toasts.length)
    notify(toasts)
  }, [])

  return {
    toasts: toastList,
    showToast,
    showError,
    showSuccess,
    showWarning,
    showTaskError,
    removeToast,
    clearAllToasts,
    subscribe: (callback: (toasts: Toast[]) => void) => {
      setToastList([...toasts])
      listeners.push(callback)
      return () => {
        const index = listeners.indexOf(callback)
        if (index > -1) {
          listeners.splice(index, 1)
        }
      }
    }
  }
}