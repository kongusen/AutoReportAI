'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import toast from 'react-hot-toast'
import { LLMManagement } from '@/components/llm/LLMManagement'
import { 
  UserIcon, 
  BellIcon, 
  ShieldCheckIcon,
  CogIcon,
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
  ServerIcon
} from '@heroicons/react/24/outline'
import { useAuthStore } from '@/features/auth/authStore'
import { Avatar } from '@/components/ui/Avatar'

export default function SettingsPage() {
  const { user } = useAuthStore()
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
    { id: 'llm', name: 'LLM服务器', icon: ServerIcon },
    { id: 'security', name: '安全设置', icon: ShieldCheckIcon },
    { id: 'profile', name: '个人资料', icon: UserIcon },
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

  const renderLLMSettings = () => (
    <LLMManagement />
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

  const renderProfileSettings = () => (
    <div className="space-y-6">
      {/* 用户信息卡片 */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">个人信息</h3>
          <div className="flex items-center space-x-4">
            <Avatar
              size="lg"
              src={undefined}
              fallback={user?.username || user?.email}
            />
            <div className="flex-1">
              <h4 className="text-lg font-semibold text-gray-900">
                {user?.username || '未设置用户名'}
              </h4>
              <p className="text-gray-600">{user?.email}</p>
              <div className="mt-2">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  在线
                </span>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* 快捷操作 */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">快捷操作</h3>
          <div className="flex flex-wrap gap-4">
            <Button variant="outline" size="sm" disabled>
              编辑资料
            </Button>
            <Button variant="outline" size="sm" disabled>
              更改头像
            </Button>
            <Button variant="outline" size="sm" disabled>
              导出数据
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )

  const renderActiveTabContent = () => {
    switch (activeTab) {
      case 'general':
        return renderGeneralSettings()
      case 'notifications':
        return renderNotificationSettings()
      case 'llm':
        return renderLLMSettings()
      case 'security':
        return renderSecuritySettings()
      case 'profile':
        return renderProfileSettings()
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

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="flex flex-col md:flex-row">
          {/* 左侧导航栏 */}
          <div className="w-full md:w-64 border-b md:border-b-0 md:border-r border-gray-200 bg-gray-50">
            <nav className="p-4 space-y-1">
              {settingsTabs.map((tab) => {
                const isActive = activeTab === tab.id
                const IconComponent = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-white text-blue-700 shadow-sm border border-gray-200'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                  >
                    <IconComponent
                      className={`mr-3 h-5 w-5 ${
                        isActive 
                          ? 'text-blue-600' 
                          : 'text-gray-400'
                      }`}
                    />
                    {tab.name}
                  </button>
                )
              })}
            </nav>
          </div>

          {/* 右侧内容区域 */}
          <div className="flex-1 p-6">
            {renderActiveTabContent()}
            
            <div className="mt-6 flex justify-end">
              <Button onClick={handleSave}>
                保存设置
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}