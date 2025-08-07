'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  BellIcon,
  ChevronDownIcon,
  UserIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline'
import { Avatar } from '@/components/ui/Avatar'
import { Badge } from '@/components/ui/Badge'
import { useAuthStore } from '@/features/auth/authStore'
import { cn } from '@/utils'

export function Header() {
  const router = useRouter()
  const { user, logout } = useAuthStore()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)
  const notificationRef = useRef<HTMLDivElement>(null)

  // 点击外部关闭菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false)
      }
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
        setShowNotifications(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLogout = async () => {
    await logout()
    router.push('/auth/login')
  }

  const userMenuItems = [
    {
      name: '个人资料',
      icon: UserIcon,
      action: () => router.push('/profile'),
    },
    {
      name: '设置',
      icon: Cog6ToothIcon,
      action: () => router.push('/settings'),
    },
    {
      name: '退出登录',
      icon: ArrowRightOnRectangleIcon,
      action: handleLogout,
      className: 'text-red-600 hover:text-red-700',
    },
  ]

  // 模拟通知数据
  const notifications = [
    { id: 1, title: '报告生成完成', message: '月度销售报告已生成', time: '2分钟前', read: false },
    { id: 2, title: '数据源连接异常', message: 'MySQL数据源连接失败', time: '10分钟前', read: false },
    { id: 3, title: '任务执行成功', message: '定时任务已成功执行', time: '1小时前', read: true },
  ]

  const unreadCount = notifications.filter(n => !n.read).length

  return (
    <div className="sticky top-0 z-40 lg:mx-auto lg:max-w-7xl lg:px-8">
      <div className="flex h-16 items-center gap-x-4 border-b border-gray-200 bg-white px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-0 lg:shadow-none">
        <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
          <div className="flex flex-1"></div>
          <div className="flex items-center gap-x-4 lg:gap-x-6">
            {/* 通知按钮 */}
            <div ref={notificationRef} className="relative">
              <button
                type="button"
                className="-m-2.5 p-2.5 text-gray-400 hover:text-gray-500 relative"
                onClick={() => setShowNotifications(!showNotifications)}
              >
                <BellIcon className="h-6 w-6" />
                {unreadCount > 0 && (
                  <Badge
                    variant="destructive"
                    size="sm"
                    className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 text-xs flex items-center justify-center min-w-0"
                  >
                    {unreadCount}
                  </Badge>
                )}
              </button>

              {/* 通知下拉菜单 */}
              {showNotifications && (
                <div className="absolute right-0 z-10 mt-2 w-80 origin-top-right rounded-md bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                  <div className="px-4 py-2 border-b border-gray-100">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium text-gray-900">通知</h3>
                      {unreadCount > 0 && (
                        <span className="text-xs text-gray-500">{unreadCount} 条未读</span>
                      )}
                    </div>
                  </div>
                  <div className="max-h-96 overflow-y-auto">
                    {notifications.length === 0 ? (
                      <div className="px-4 py-6 text-center text-sm text-gray-500">
                        暂无通知
                      </div>
                    ) : (
                      notifications.map((notification) => (
                        <div
                          key={notification.id}
                          className={cn(
                            'px-4 py-3 hover:bg-gray-50 cursor-pointer border-b border-gray-50 last:border-b-0',
                            !notification.read && 'bg-blue-50'
                          )}
                        >
                          <div className="flex items-start">
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-gray-900 truncate">
                                {notification.title}
                              </p>
                              <p className="text-sm text-gray-500 mt-1">
                                {notification.message}
                              </p>
                              <p className="text-xs text-gray-400 mt-1">
                                {notification.time}
                              </p>
                            </div>
                            {!notification.read && (
                              <div className="ml-2 w-2 h-2 bg-blue-600 rounded-full flex-shrink-0 mt-1"></div>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                  <div className="px-4 py-2 border-t border-gray-100">
                    <button className="text-sm text-blue-600 hover:text-blue-700">
                      查看全部通知
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="hidden lg:block lg:h-6 lg:w-px lg:bg-gray-900/10" />

            {/* 用户菜单 */}
            <div ref={userMenuRef} className="relative">
              <button
                type="button"
                className="-m-1.5 flex items-center p-1.5 hover:bg-gray-50 rounded-md"
                onClick={() => setShowUserMenu(!showUserMenu)}
              >
                <Avatar
                  size="sm"
                  src={user?.avatar_url}
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
                  {userMenuItems.map((item) => (
                    <button
                      key={item.name}
                      className={cn(
                        'flex w-full items-center px-3 py-2 text-sm text-gray-900 hover:bg-gray-50',
                        item.className
                      )}
                      onClick={item.action}
                    >
                      <item.icon className="mr-3 h-5 w-5 text-gray-400" />
                      {item.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}