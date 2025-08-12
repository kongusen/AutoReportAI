'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import toast from 'react-hot-toast'
import { AIProviderSettings as AIProviderSettingsComponent } from '@/components/settings/AIProviderSettings'
import { 
  UserIcon, 
  CpuChipIcon, 
  BellIcon, 
  ShieldCheckIcon,
  CogIcon,
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon
} from '@heroicons/react/24/outline'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('general')
  const [settings, setSettings] = useState({
    language: 'zh',
    theme: 'light',
    notifications: {
      email: true,
      reports: true,
      system: true
    },
    defaults: {
      reportFormat: 'pdf',
      storageDays: 30
    }
  })

  const settingsTabs = [
    { id: 'general', name: '通用设置', icon: CogIcon },
    { id: 'notifications', name: '通知设置', icon: BellIcon },
    { id: 'ai', name: 'AI提供商', icon: CpuChipIcon },
    { id: 'security', name: '安全设置', icon: ShieldCheckIcon },
  ]

  const handleSave = () => {
    // 模拟保存到本地存储
    localStorage.setItem('appSettings', JSON.stringify(settings))
    toast.success('设置已保存')
  }

  const handleSettingChange = (key: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }))
  }

  const handleNestedSettingChange = (section: string, key: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [section]: {
        ...(prev[section as keyof typeof prev] as Record<string, any> || {}),
        [key]: value
      }
    }))
  }

  const renderGeneralSettings = () => (
    <div className="space-y-6">
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">界面设置</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                语言
              </label>
              <select
                value={settings.language}
                onChange={(e) => handleSettingChange('language', e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="zh">中文</option>
                <option value="en">English</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                主题
              </label>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { value: 'light', label: '浅色', icon: SunIcon },
                  { value: 'dark', label: '深色', icon: MoonIcon },
                  { value: 'system', label: '跟随系统', icon: ComputerDesktopIcon }
                ].map((theme) => {
                  const IconComponent = theme.icon
                  return (
                    <button
                      key={theme.value}
                      onClick={() => handleSettingChange('theme', theme.value)}
                      className={`p-3 rounded-lg border-2 transition-colors ${
                        settings.theme === theme.value
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <IconComponent className="h-6 w-6 mx-auto mb-2" />
                      <div className="text-sm font-medium">{theme.label}</div>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      </Card>

      <Card>
        <div className="p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">默认设置</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                默认报告格式
              </label>
              <select
                value={settings.defaults.reportFormat}
                onChange={(e) => handleNestedSettingChange('defaults', 'reportFormat', e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="pdf">PDF</option>
                <option value="xlsx">Excel</option>
                <option value="html">HTML</option>
                <option value="csv">CSV</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                默认存储天数
              </label>
              <input
                type="number"
                min="1"
                max="365"
                value={settings.defaults.storageDays}
                onChange={(e) => handleNestedSettingChange('defaults', 'storageDays', parseInt(e.target.value))}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
      </Card>
    </div>
  )

  const renderNotificationSettings = () => (
    <Card>
      <div className="p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">通知偏好</h3>
        <div className="space-y-4">
          {[
            { key: 'email', label: '邮件通知', description: '接收重要邮件通知' },
            { key: 'reports', label: '报告通知', description: '报告生成完成时通知' },
            { key: 'system', label: '系统通知', description: '接收系统状态通知' }
          ].map((notification) => (
            <div key={notification.key} className="flex items-center justify-between py-3">
              <div>
                <div className="text-sm font-medium text-gray-700">
                  {notification.label}
                </div>
                <div className="text-sm text-gray-500">
                  {notification.description}
                </div>
              </div>
              <input
                type="checkbox"
                checked={settings.notifications[notification.key as keyof typeof settings.notifications]}
                onChange={(e) => handleNestedSettingChange('notifications', notification.key, e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>
          ))}
        </div>
      </div>
    </Card>
  )

  const renderAISettings = () => (
    <div className="space-y-6">
      <AIProviderSettingsComponent />
    </div>
  )

  const renderSecuritySettings = () => (
    <Card>
      <div className="p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">安全设置</h3>
        <div className="space-y-4">
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-700">密码管理</div>
                <div className="text-sm text-gray-500">更改登录密码</div>
              </div>
              <Button variant="outline" size="sm" disabled>
                更改密码
              </Button>
            </div>
          </div>

          <div className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-700">会话管理</div>
                <div className="text-sm text-gray-500">登出所有设备</div>
              </div>
              <Button variant="outline" size="sm" disabled>
                登出所有设备
              </Button>
            </div>
          </div>

          <div className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-700">数据导出</div>
                <div className="text-sm text-gray-500">导出账户数据</div>
              </div>
              <Button variant="outline" size="sm" disabled>
                导出数据
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Card>
  )

  const renderActiveTabContent = () => {
    switch (activeTab) {
      case 'general':
        return renderGeneralSettings()
      case 'notifications':
        return renderNotificationSettings()
      case 'ai':
        return renderAISettings()
      case 'security':
        return renderSecuritySettings()
      default:
        return renderGeneralSettings()
    }
  }

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
            {settingsTabs.map((tab) => {
              const isActive = activeTab === tab.id
              const IconComponent = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`group inline-flex items-center py-4 px-1 border-b-2 font-medium text-sm ${
                    isActive
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <IconComponent
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
          {renderActiveTabContent()}
          
          <div className="mt-6 flex justify-end">
            <Button onClick={handleSave}>
              保存设置
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}