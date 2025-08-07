'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  HomeIcon,
  CircleStackIcon,
  DocumentTextIcon,
  ClockIcon,
  DocumentArrowDownIcon,
  CogIcon,
  ChartBarIcon,
  XMarkIcon,
  Bars3Icon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils'

const navigation = [
  { name: '仪表板', href: '/dashboard', icon: HomeIcon },
  { name: '数据源', href: '/data-sources', icon: CircleStackIcon },
  { name: '模板', href: '/templates', icon: DocumentTextIcon },
  { name: '任务', href: '/tasks', icon: ClockIcon },
  { name: '报告', href: '/reports', icon: DocumentArrowDownIcon },
  { name: '分析', href: '/analytics', icon: ChartBarIcon },
]

const settingsNavigation = [
  { name: '设置', href: '/settings', icon: CogIcon },
]

export function Sidebar() {
  const pathname = usePathname()
  const [sidebarOpen, setSidebarOpen] = useState(false)

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
                <div className="mt-auto">
                  <SidebarNavigation navigation={settingsNavigation} pathname={pathname} />
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
            <div className="mt-auto pb-4">
              <SidebarNavigation navigation={settingsNavigation} pathname={pathname} />
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