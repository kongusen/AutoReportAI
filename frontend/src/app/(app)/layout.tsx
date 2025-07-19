'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LanguageSwitcher, UserProfile } from '@/components/layout'
import { AuthGuard } from '@/components/providers'
import { BarChart3, Database, FileText, Settings, Users } from 'lucide-react'

const menuItems = [
  { id: 'overview', label: '总览', icon: BarChart3, href: '/' },
  { id: 'data-sources', label: '数据源', icon: Database, href: '/data-sources' },
  { id: 'templates', label: '模板', icon: FileText, href: '/templates' },
  { id: 'tasks', label: '任务', icon: Users, href: '/tasks' },
  { id: 'settings', label: '设置', icon: Settings, href: '/settings' },
]

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="flex">
          {/* 侧边栏 */}
          <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
            <div className="p-6 flex justify-between items-center">
              <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">AutoReportAI</h1>
              <LanguageSwitcher />
            </div>
            <nav className="px-4 pb-6 flex-1">
              {menuItems.map((item) => {
                const Icon = item.icon
                const isActive =
                  (item.href === '/' && pathname === '/') ||
                  (item.href !== '/' && pathname.startsWith(item.href))
                return (
                  <Link
                    key={item.id}
                    href={item.href}
                    className={`
                      w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors
                      ${isActive
                        ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                        : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
                      }
                    `}
                  >
                    <Icon className="h-5 w-5" />
                    <span>{item.label}</span>
                  </Link>
                )
              })}
            </nav>
            <div className="mt-auto">
              <UserProfile />
            </div>
          </div>
          {/* 主内容区 */}
          <div className="flex-1 p-8">
            <div className="max-w-7xl mx-auto">{children}</div>
          </div>
        </div>
      </div>
    </AuthGuard>
  )
}
