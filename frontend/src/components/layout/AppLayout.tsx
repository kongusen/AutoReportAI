'use client'

import React from 'react'
import { Sidebar } from './Sidebar'
import { useAuthStore } from '@/features/auth/authStore'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useWebSocketIntegration } from '@/hooks/useWebSocketIntegration'
import { ConnectionStatusIndicator } from './ConnectionStatusIndicator'
import { ErrorBoundary } from '@/components/ErrorBoundary'

interface AppLayoutProps {
  children: React.ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const { isAuthenticated, isLoading } = useAuthStore()
  
  // 集成WebSocket实时通信
  useWebSocketIntegration()

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
          {/* 页面内容 */}
          <main className="py-6">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
              <ErrorBoundary>
                {children}
              </ErrorBoundary>
            </div>
          </main>
        </div>
        
        {/* 连接状态指示器 */}
        <ConnectionStatusIndicator />
      </div>
    </ErrorBoundary>
  )
}