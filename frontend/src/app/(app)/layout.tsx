'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import AuthProvider from '@/components/AuthProvider'

const navItems = [
  { name: 'Tasks', href: '/tasks' },
  { name: 'ETL Jobs', href: '/etl-jobs' },
  { name: 'Data Sources', href: '/data-sources' },
  { name: 'AI Providers', href: '/ai-providers' },
  // Future pages can be added here
  // { name: 'Templates', href: '/templates' },
  // { name: 'History', href: '/history' },
]

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <AuthProvider>
      <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
        {/* Sidebar */}
        <aside className="w-64 flex-shrink-0 bg-gray-800 dark:bg-black text-white">
          <div className="flex items-center justify-center h-16 border-b border-gray-700 dark:border-gray-800">
            <h1 className="text-2xl font-bold">AutoReportAI</h1>
          </div>
          <nav className="mt-6">
            {navItems.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center px-6 py-3 text-base transition-colors duration-200 ${
                  pathname.startsWith(item.href)
                    ? 'bg-gray-700 dark:bg-gray-900 text-white'
                    : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                }`}
              >
                {item.name}
              </Link>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-8">{children}</div>
        </main>
      </div>
    </AuthProvider>
  )
}
