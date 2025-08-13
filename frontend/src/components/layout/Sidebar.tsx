'use client'

import { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  HomeIcon,
  CircleStackIcon,
  DocumentTextIcon,
  ClockIcon,
  DocumentArrowDownIcon,
  CogIcon,
  XMarkIcon,
  Bars3Icon,
  BellIcon,
  ChevronDownIcon,
  UserIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils'
import { Avatar } from '@/components/ui/Avatar'
import { Badge } from '@/components/ui/Badge'
import { useAuthStore } from '@/features/auth/authStore'

const navigation = [
  { name: '仪表板', href: '/dashboard', icon: HomeIcon },
  { name: '数据源', href: '/data-sources', icon: CircleStackIcon },
  { name: '模板', href: '/templates', icon: DocumentTextIcon },
  { name: '任务', href: '/tasks', icon: ClockIcon },
  { name: '报告', href: '/reports', icon: DocumentArrowDownIcon },
]


export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuthStore()
  const [sidebarOpen, setSidebarOpen] = useState(false)
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
    router.push('/login')
  }

  const userMenuItems = [
    {
      name: '个人资料',
      icon: UserIcon,
      action: () => router.push('/profile'),
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
    <>
      {/* Mobile sidebar */}
      <div className={cn(
        'relative z-50 lg:hidden',
        sidebarOpen ? 'block' : 'hidden'
      )}>
        <div className="fixed inset-0 bg-gray-900/80" onClick={() => setSidebarOpen(false)} />
        
        <div className="fixed inset-0 flex">
          <div className="relative mr-16 flex w-full max-w-xs flex-1">
            <div className="absolute left-full top-0 flex w-16 justify-center pt-5">
              <button
                type="button"
                className="-m-2.5 p-2.5"
                onClick={() => setSidebarOpen(false)}
              >
                <XMarkIcon className="h-6 w-6 text-white" />
              </button>
            </div>

            <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-white px-6 pb-2">
              <div className="flex h-16 shrink-0 items-center">
                <h1 className="text-xl font-bold text-gray-900">AutoReportAI</h1>
              </div>
              <nav className="flex flex-1 flex-col">
                <SidebarNavigation navigation={navigation} pathname={pathname} />
                <div className="mt-auto space-y-4">
                  
                  {/* 通知中心 */}
                  <div ref={notificationRef} className="relative">
                    <button
                      type="button"
                      className="-m-2.5 p-2.5 text-gray-400 hover:text-gray-500 relative w-full flex items-center justify-between rounded-md hover:bg-gray-50"
                      onClick={() => setShowNotifications(!showNotifications)}
                    >
                      <div className="flex items-center gap-x-3">
                        <BellIcon className="h-6 w-6" />
                        <span className="text-sm font-medium text-gray-600 hover:text-gray-900">通知中心</span>
                      </div>
                      {unreadCount > 0 && (
                        <Badge
                          variant="destructive"
                          size="sm"
                          className="h-5 w-5 rounded-full p-0 text-xs flex items-center justify-center min-w-0"
                        >
                          {unreadCount}
                        </Badge>
                      )}
                    </button>

                    {/* 通知下拉菜单 */}
                    {showNotifications && (
                      <div className="absolute left-0 bottom-full z-10 mb-2 w-80 origin-bottom-left rounded-md bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
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

                  {/* 用户菜单 */}
                  <div ref={userMenuRef} className="relative border-t border-gray-200 pt-4">
                    <button
                      type="button"
                      className="-m-1.5 flex items-center p-1.5 hover:bg-gray-50 rounded-md w-full"
                      onClick={() => setShowUserMenu(!showUserMenu)}
                    >
                      <Avatar
                        size="sm"
                        src={undefined}
                        fallback={user?.username || user?.email}
                      />
                      <div className="flex flex-1 items-center justify-between ml-3">
                        <div className="text-left">
                          <p className="text-sm font-semibold text-gray-900 truncate">
                            {user?.username || user?.email}
                          </p>
                          <p className="text-xs text-gray-500">在线</p>
                        </div>
                        <ChevronDownIcon className="h-5 w-5 text-gray-400" />
                      </div>
                    </button>

                    {/* 用户下拉菜单 */}
                    {showUserMenu && (
                      <div className="absolute left-0 bottom-full z-10 mb-2 w-full origin-bottom-left rounded-md bg-white py-2 shadow-lg ring-1 ring-gray-900/5 focus:outline-none">
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
              </nav>
            </div>
          </div>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-64 lg:flex-col">
        <div className="flex grow flex-col gap-y-5 overflow-y-auto border-r border-gray-200 bg-white px-6">
          <div className="flex h-16 shrink-0 items-center">
            <h1 className="text-xl font-bold text-gray-900">AutoReportAI</h1>
          </div>
          <nav className="flex flex-1 flex-col">
            <SidebarNavigation navigation={navigation} pathname={pathname} />
            <div className="mt-auto pb-4 space-y-4">
              
              {/* 通知中心 */}
              <div ref={notificationRef} className="relative">
                <button
                  type="button"
                  className="-m-2.5 p-2.5 text-gray-400 hover:text-gray-500 relative w-full flex items-center justify-between rounded-md hover:bg-gray-50"
                  onClick={() => setShowNotifications(!showNotifications)}
                >
                  <div className="flex items-center gap-x-3">
                    <BellIcon className="h-6 w-6" />
                    <span className="text-sm font-medium text-gray-600 hover:text-gray-900">通知中心</span>
                  </div>
                  {unreadCount > 0 && (
                    <Badge
                      variant="destructive"
                      size="sm"
                      className="h-5 w-5 rounded-full p-0 text-xs flex items-center justify-center min-w-0"
                    >
                      {unreadCount}
                    </Badge>
                  )}
                </button>

                {/* 通知下拉菜单 */}
                {showNotifications && (
                  <div className="absolute left-0 bottom-full z-10 mb-2 w-80 origin-bottom-left rounded-md bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
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

              {/* 用户菜单 */}
              <div ref={userMenuRef} className="relative border-t border-gray-200 pt-4">
                <button
                  type="button"
                  className="-m-1.5 flex items-center p-1.5 hover:bg-gray-50 rounded-md w-full"
                  onClick={() => setShowUserMenu(!showUserMenu)}
                >
                  <Avatar
                    size="sm"
                    src={undefined}
                    fallback={user?.username || user?.email}
                  />
                  <div className="flex flex-1 items-center justify-between ml-3">
                    <div className="text-left">
                      <p className="text-sm font-semibold text-gray-900 truncate">
                        {user?.username || user?.email}
                      </p>
                      <p className="text-xs text-gray-500">在线</p>
                    </div>
                    <ChevronDownIcon className="h-5 w-5 text-gray-400" />
                  </div>
                </button>

                {/* 用户下拉菜单 */}
                {showUserMenu && (
                  <div className="absolute left-0 bottom-full z-10 mb-2 w-full origin-bottom-left rounded-md bg-white py-2 shadow-lg ring-1 ring-gray-900/5 focus:outline-none">
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
          </nav>
        </div>
      </div>

      {/* Mobile sidebar toggle button */}
      <div className="sticky top-0 z-40 flex items-center gap-x-6 bg-white px-4 py-4 shadow-sm sm:px-6 lg:hidden">
        <button
          type="button"
          className="-m-2.5 p-2.5 text-gray-700 lg:hidden"
          onClick={() => setSidebarOpen(true)}
        >
          <Bars3Icon className="h-6 w-6" />
        </button>
        <div className="flex-1 text-sm font-semibold leading-6 text-gray-900">
          AutoReportAI
        </div>
      </div>
    </>
  )
}

interface SidebarNavigationProps {
  navigation: Array<{
    name: string
    href: string
    icon: React.ComponentType<{ className?: string }>
  }>
  pathname: string
}

function SidebarNavigation({ navigation, pathname }: SidebarNavigationProps) {
  return (
    <ul role="list" className="flex flex-1 flex-col gap-y-7">
      <li>
        <ul role="list" className="-mx-2 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
            
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  className={cn(
                    'group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-medium transition-colors',
                    isActive
                      ? 'bg-gray-100 text-gray-900'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  )}
                >
                  <item.icon
                    className={cn(
                      'h-6 w-6 shrink-0',
                      isActive ? 'text-gray-900' : 'text-gray-400 group-hover:text-gray-600'
                    )}
                  />
                  {item.name}
                </Link>
              </li>
            )
          })}
        </ul>
      </li>
    </ul>
  )
}