'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  ChevronDownIcon,
  UserIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline'
import { Avatar } from '@/components/ui/Avatar'
import { useAuthStore } from '@/features/auth/authStore'
import { NotificationCenter } from '@/components/ui/NotificationCenter'
import { cn } from '@/utils'

export function Header() {
  const router = useRouter()
  const { user, logout } = useAuthStore()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)

  // 点击外部关闭菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  const userMenuItems = [
    {
      name: '个人资料',
      icon: UserIcon,
      action: () => {
        setShowUserMenu(false)
        router.push('/profile')
      },
    },
    {
      name: '设置',
      icon: Cog6ToothIcon,
      action: () => {
        setShowUserMenu(false)
        router.push('/settings')
      },
    },
    {
      name: '退出登录',
      icon: ArrowRightOnRectangleIcon,
      action: handleLogout,
      className: 'text-red-600 hover:text-red-700',
    },
  ]

  return (
    <div className="sticky top-0 z-40 lg:mx-auto lg:max-w-7xl lg:px-8">
      <div className="flex h-16 items-center gap-x-4 border-b border-gray-200 bg-white px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-0 lg:shadow-none">
        <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
          {/* 左侧：应用标题或搜索 */}
          <div className="flex flex-1 items-center">
            <h1 className="text-xl font-semibold text-gray-900 lg:hidden">
              AutoReport AI
            </h1>
          </div>

          {/* 右侧：工具栏 */}
          <div className="flex items-center gap-x-4 lg:gap-x-6">
            {/* 实时通知中心 */}
            <NotificationCenter />

            {/* 分隔线 */}
            <div className="hidden lg:block lg:h-6 lg:w-px lg:bg-gray-900/10" />

            {/* 用户信息显示 */}
            <div className="hidden lg:flex lg:items-center lg:text-sm lg:text-gray-600">
              <span>欢迎回来, </span>
              <span className="ml-1 font-medium text-gray-900">
                {user?.username || user?.email?.split('@')[0] || '用户'}
              </span>
            </div>

            {/* 用户菜单 */}
            <div ref={userMenuRef} className="relative">
              <button
                type="button"
                className="-m-1.5 flex items-center p-1.5 hover:bg-gray-50 rounded-md transition-colors"
                onClick={() => setShowUserMenu(!showUserMenu)}
              >
                <Avatar
                  size="sm"
                  src={(user as any)?.avatar_url || undefined}
                  fallback={user?.username || user?.email}
                />
                <span className="hidden lg:flex lg:items-center">
                  <span className="ml-4 text-sm font-semibold leading-6 text-gray-900">
                    {user?.username || user?.email}
                  </span>
                  <ChevronDownIcon className="ml-2 h-5 w-5 text-gray-400" />
                </span>
              </button>

              {/* 用户下拉菜单 */}
              {showUserMenu && (
                <div className="absolute right-0 z-10 mt-2.5 w-48 origin-top-right rounded-md bg-white py-2 shadow-lg ring-1 ring-gray-900/5 focus:outline-none">
                  {/* 用户信息头部 */}
                  <div className="px-3 py-2 border-b border-gray-100">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {user?.username || user?.email}
                    </p>
                    <p className="text-xs text-gray-500 truncate">
                      {user?.email}
                    </p>
                    {user?.is_superuser && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 mt-1">
                        管理员
                      </span>
                    )}
                  </div>

                  {/* 菜单项 */}
                  <div className="py-1">
                    {userMenuItems.map((item) => (
                      <button
                        key={item.name}
                        className={cn(
                          'flex w-full items-center px-3 py-2 text-sm text-gray-900 hover:bg-gray-50 transition-colors',
                          item.className
                        )}
                        onClick={item.action}
                      >
                        <item.icon className="mr-3 h-5 w-5 text-gray-400" />
                        {item.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

    </div>
  )
}