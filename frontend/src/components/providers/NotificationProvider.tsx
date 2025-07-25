'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { Toaster } from 'sonner'
import { wsManager, NotificationMessage } from '@/lib/websocket'
import { httpClient } from '@/lib/api/client';

interface NotificationContextType {
  notifications: NotificationMessage[]
  isConnected: boolean
  clearNotifications: () => void
  markAsRead: (id: string) => void
  sendTestNotification: () => void
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined)

export function useNotificationContext() {
  const context = useContext(NotificationContext)
  if (!context) {
    throw new Error('useNotificationContext must be used within a NotificationProvider')
  }
  return context
}

interface NotificationProviderProps {
  children: React.ReactNode
}

export function NotificationProvider({ children }: NotificationProviderProps) {
  const [notifications, setNotifications] = useState<NotificationMessage[]>([])
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    // 添加通知监听器
    const removeListener = wsManager.addListener((message) => {
      setNotifications(prev => [message, ...prev.slice(0, 49)]) // 保留最近50条通知
    })

    // 定期检查连接状态
    const checkConnection = setInterval(() => {
      setIsConnected(wsManager.isConnected())
    }, 2000)

    // 初始连接状态检查
    setIsConnected(wsManager.isConnected())

    return () => {
      removeListener()
      clearInterval(checkConnection)
    }
  }, [])

  const clearNotifications = () => {
    setNotifications([])
  }

  const markAsRead = (id: string) => {
    setNotifications(prev => 
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    )
  }

  const sendTestNotification = async () => {
    try {
      await httpClient.post('/v1/notifications/send', {
        type: 'info',
        title: 'Test Notification',
        message: 'This is a test notification to verify the system is working.',
        data: { test: true }
      });
    } catch (error) {
      console.error('Error sending test notification:', error)
    }
  }

  const value: NotificationContextType = {
    notifications,
    isConnected,
    clearNotifications,
    markAsRead,
    sendTestNotification
  }

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <Toaster 
        position="top-right"
        expand={true}
        richColors
        closeButton
        toastOptions={{
          duration: 5000,
          style: {
            background: 'white',
            border: '1px solid #e5e7eb',
            color: '#374151'
          }
        }}
      />
    </NotificationContext.Provider>
  )
}

export default NotificationProvider