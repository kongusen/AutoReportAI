'use client'

import { usePathname } from 'next/navigation'
import { Sidebar } from '@/components/layout/Sidebar'
import { AuthGuard } from '@/components/providers/AuthGuard'
import { AppProviders } from '@/components/providers/AppProviders'

const AUTH_PAGES = ['/login', '/register', '/forgot-password', '/reset-password', '/verify-email']

export default function LocaleLayout({ 
  children,
  params
}: { 
  children: React.ReactNode
  params: Promise<{ locale: string }>
}) {
  const pathname = usePathname()
  const isAuthPage = AUTH_PAGES.some(p => pathname.includes(p))

  if (isAuthPage) {
    return (
      <AppProviders>
        <div className="min-h-screen bg-gray-50">
          {children}
        </div>
      </AppProviders>
    )
  }

  return (
    <AppProviders>
      <AuthGuard>
        <div className="min-h-screen bg-gray-50 flex">
          <Sidebar />
          <main className="flex-1 overflow-auto">
            <header className="h-16 border-b border-gray-200 bg-white px-6 flex items-center justify-between shadow-sm">
              <div className="flex items-center space-x-4">
                <h2 className="text-lg font-semibold text-gray-900">控制面板</h2>
              </div>
              <div className="flex items-center space-x-4">
                {/* 用户信息、通知等 */}
              </div>
            </header>
            <div className="p-6">
              {children}
            </div>
          </main>
        </div>
      </AuthGuard>
    </AppProviders>
  )
}