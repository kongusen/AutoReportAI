'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthenticated } from '@/lib/auth'
import Link from 'next/link'
import { LanguageSwitcher, UserProfile } from '@/components/layout'
import { AuthGuard } from '@/components/providers'
import { BarChart3, Database, FileText, Settings, Users } from 'lucide-react'
import HomePage from './(app)/page'

const menuItems = [
  { id: 'overview', label: '总览', icon: BarChart3, href: '/' },
  { id: 'data-sources', label: '数据源', icon: Database, href: '/data-sources' },
  { id: 'templates', label: '模板', icon: FileText, href: '/templates' },
  { id: 'tasks', label: '任务', icon: Users, href: '/tasks' },
  { id: 'settings', label: '设置', icon: Settings, href: '/settings' },
]

export default function RootPage() {
  const router = useRouter()
  const [isClient, setIsClient] = useState(false)
  const [authChecked, setAuthChecked] = useState(false)

  useEffect(() => {
    // 标记为客户端渲染
    setIsClient(true)
    
    // 检查认证状态
    const checkAuth = () => {
      if (!isAuthenticated()) {
        console.log('用户未登录，重定向到登录页')
        router.replace('/login')
      } else {
        console.log('用户已登录，显示主页')
        setAuthChecked(true)
      }
    }

    // 延迟检查以避免 hydration 问题
    const timer = setTimeout(checkAuth, 100)
    return () => clearTimeout(timer)
  }, [router])

  // 服务端渲染时显示加载状态
  if (!isClient) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    )
  }

  // 客户端渲染但认证未检查完成
  if (!authChecked) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-gray-900"></div>
      </div>
    )
  }

  // 已认证，显示主页内容
  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="flex flex-col lg:flex-row">
          {/* 侧边栏 - 响应式设计 */}
          <div className="w-full lg:w-64 bg-white dark:bg-gray-800 border-b lg:border-r lg:border-b-0 border-gray-200 dark:border-gray-700 flex flex-col">
            <div className="p-4 lg:p-6 flex justify-between items-center">
              <h1 className="text-lg lg:text-xl font-bold text-gray-900 dark:text-gray-100">AutoReportAI</h1>
              <LanguageSwitcher />
            </div>
            <nav className="px-4 pb-4 lg:pb-6 flex-1">
              <div className="flex lg:flex-col space-x-2 lg:space-x-0 lg:space-y-1 overflow-x-auto lg:overflow-x-visible">
                {menuItems.map((item) => {
                  const Icon = item.icon
                  const isActive = item.href === '/'
                  return (
                    <Link
                      key={item.id}
                      href={item.href}
                      className={`
                        flex items-center space-x-3 px-3 lg:px-4 py-2 lg:py-3 rounded-lg text-sm font-medium transition-colors whitespace-nowrap
                        ${isActive
                          ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                          : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
                        }
                      `}
                    >
                      <Icon className="h-4 w-4 lg:h-5 lg:w-5 flex-shrink-0" />
                      <span className="hidden sm:inline">{item.label}</span>
                    </Link>
                  )
                })}
              </div>
            </nav>
            <div className="mt-auto p-4 lg:p-0">
              <UserProfile />
            </div>
          </div>
          {/* 主内容区 - 响应式设计 */}
          <div className="flex-1 p-4 lg:p-8 overflow-x-hidden">
            <div className="max-w-7xl mx-auto">
              <HomePage />
            </div>
          </div>
        </div>
      </div>
    </AuthGuard>
  )
}