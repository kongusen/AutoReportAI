import { useState, useCallback } from 'react'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  message: string
  type: ToastType
  duration?: number
}

let toastId = 0
const toasts: Toast[] = []
const listeners: Array<(toasts: Toast[]) => void> = []

const notify = (toasts: Toast[]) => {
  listeners.forEach(listener => listener([...toasts]))
}

const addToast = (message: string, type: ToastType = 'info', duration = 5000) => {
  const id = String(toastId++)
  const toast: Toast = { id, message, type, duration }
  
  toasts.push(toast)
  notify(toasts)
  
  if (duration > 0) {
    setTimeout(() => {
      const index = toasts.findIndex(t => t.id === id)
      if (index > -1) {
        toasts.splice(index, 1)
        notify(toasts)
      }
    }, duration)
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

  const showToast = useCallback((message: string, type: ToastType = 'info', duration = 5000) => {
    addToast(message, type, duration)
  }, [])

  return {
    toasts: toastList,
    showToast,
    removeToast,
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