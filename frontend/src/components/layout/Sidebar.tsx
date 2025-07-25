'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname, useParams } from 'next/navigation'
import { useAuth } from '@/lib/auth/AuthContext'
import { Button } from '@/components/ui/button'
import {
  BarChart3,
  Database,
  FileText,
  Settings,
  History,
  PlayCircle,
  Bot,
  User,
  LogOut,
  ChevronLeft,
  ChevronRight
} from 'lucide-react'

const navigation = [
  {
    name: '仪表板',
    href: '/dashboard',
    icon: BarChart3,
    description: '系统概览和统计'
  },
  {
    name: '数据源',
    href: '/data-sources',
    icon: Database,
    description: '管理数据源连接'
  },
  {
    name: '模板',
    href: '/templates',
    icon: FileText,
    description: '报告模板管理'
  },
  {
    name: '任务',
    href: '/tasks',
    icon: PlayCircle,
    description: '定时任务管理'
  },
  {
    name: '历史记录',
    href: '/history',
    icon: History,
    description: '查看报告历史'
  },
  {
    name: 'AI 提供商',
    href: '/settings/ai-providers',
    icon: Bot,
    description: 'AI服务配置'
  },
  {
    name: '设置',
    href: '/settings',
    icon: Settings,
    description: '系统设置'
  }
]

export function Sidebar() {
  const pathname = usePathname()
  const params = useParams()
  const locale = params.locale as string
  const { user, logout } = useAuth()
  const [collapsed, setCollapsed] = useState(false)

  const handleLogout = async () => {
    await logout()
  }

  return (
    <div className={`bg-white border-r border-gray-200 flex flex-col transition-all duration-300 ${
      collapsed ? 'w-16' : 'w-64'
    }`}>
      {/* Header */}
      <div className="h-16 border-b border-gray-200 flex items-center justify-between px-4">
        {!collapsed && (
          <h1 className="text-lg font-semibold text-gray-900">AutoReportAI</h1>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setCollapsed(!collapsed)}
          className="h-8 w-8 p-0"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname.includes(item.href)
          const Icon = item.icon
          
          return (
            <Link
              key={item.name}
              href={`/${locale}${item.href}`}
              className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-gray-100 text-gray-900'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`}
              title={collapsed ? item.name : undefined}
            >
              <Icon className={`${collapsed ? 'h-5 w-5' : 'h-4 w-4 mr-3'} flex-shrink-0`} />
              {!collapsed && (
                <div>
                  <div className="text-sm">{item.name}</div>
                  {!isActive && (
                    <div className="text-xs text-gray-500">{item.description}</div>
                  )}
                </div>
              )}
            </Link>
          )
        })}
      </nav>

      {/* User Profile */}
      <div className="border-t border-gray-200 p-4">
        {!collapsed && user ? (
          <div className="space-y-3">
            <div className="flex items-center space-x-3">
              <div className="h-8 w-8 bg-gray-200 rounded-full flex items-center justify-center">
                <User className="h-4 w-4 text-gray-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {user.full_name || user.username}
                </p>
                <p className="text-xs text-gray-500 truncate">{user.email}</p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleLogout}
              className="w-full justify-start text-gray-600 hover:text-gray-900"
            >
              <LogOut className="h-4 w-4 mr-2" />
              退出登录
            </Button>
          </div>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="w-full justify-center"
            title="退出登录"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}