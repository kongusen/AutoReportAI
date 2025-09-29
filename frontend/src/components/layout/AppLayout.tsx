'use client'

import React from 'react'
import { Sidebar } from './Sidebar'
import { useAuthStore } from '@/features/auth/authStore'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useWebSocket } from '@/hooks/useWebSocket'
import { ErrorBoundary } from '@/components/ErrorBoundary'

interface AppLayoutProps {
  children: React.ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const { isAuthenticated, isLoading } = useAuthStore()
  
  // 集成WebSocket实时通信
  const { isConnected } = useWebSocket({
    autoConnect: true,
    enableNotifications: true
  })

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <LoadingSpinner size="lg" text="正在加载..." />
      </div>
    )
  }

  if (!isAuthenticated) {
    return null // 这里应该由路由守卫处理重定向
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-50">
        {/* 侧边栏 */}
        <Sidebar />

        {/* 主内容区域 */}
        <div className="lg:pl-64">
          {/* 页面内容 - 添加顶部边距以避免被移动端导航栏遮挡 */}
          <main className="py-6 lg:pt-6 pt-6 lg:mt-0 mt-16">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
              <ErrorBoundary>
                {children}
              </ErrorBoundary>
            </div>
          </main>
        </div>

      </div>
    </ErrorBoundary>
  )
}

export default AppLayout