'use client'

import { useState } from 'react'
import { UserSettings } from '@/components/settings/UserSettings'
import { AIProviderSettings } from '@/components/settings/AIProviderSettings'
import { NotificationSettings } from '@/components/settings/NotificationSettings'
import { SecuritySettings } from '@/components/settings/SecuritySettings'
import { 
  UserIcon, 
  CpuChipIcon, 
  BellIcon, 
  ShieldCheckIcon 
} from '@heroicons/react/24/outline'

const settingsTabs = [
  { name: '个人信息', icon: UserIcon, component: UserSettings },
  { name: 'AI提供商', icon: CpuChipIcon, component: AIProviderSettings },
  { name: '通知设置', icon: BellIcon, component: NotificationSettings },
  { name: '安全设置', icon: ShieldCheckIcon, component: SecuritySettings },
]

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState(0)
  const ActiveComponent = settingsTabs[activeTab].component

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">设置</h1>
        <p className="mt-1 text-sm text-gray-600">
          管理您的账户设置和应用偏好
        </p>
      </div>

      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6" aria-label="Tabs">
            {settingsTabs.map((tab, index) => {
              const isActive = activeTab === index
              return (
                <button
                  key={tab.name}
                  onClick={() => setActiveTab(index)}
                  className={`group inline-flex items-center py-4 px-1 border-b-2 font-medium text-sm ${
                    isActive
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <tab.icon
                    className={`mr-2 h-5 w-5 ${
                      isActive 
                        ? 'text-blue-500' 
                        : 'text-gray-400 group-hover:text-gray-500'
                    }`}
                  />
                  {tab.name}
                </button>
              )
            })}
          </nav>
        </div>

        <div className="p-6">
          <ActiveComponent />
        </div>
      </div>
    </div>
  )
}