'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/lib/i18n'
import { AIProviderForm } from '../forms/AIProviderForm'

export function SettingsPanel() {
  const { t } = useI18n()
  const [activeTab, setActiveTab] = useState('profile')

  const tabs = [
    { id: 'profile', label: '个人资料', icon: '👤' },
    { id: 'ai', label: 'AI模型', icon: '🤖' },
    { id: 'email', label: '邮箱配置', icon: '📧' }
  ]

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">{t('common.settings')}</h1>
      
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                py-2 px-1 border-b-2 font-medium text-sm
                ${activeTab === tab.id
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }
              `}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="mt-6">
        {activeTab === 'profile' && (
          <Card>
            <CardHeader>
              <CardTitle>个人资料</CardTitle>
              <CardDescription>管理您的个人信息和账户设置</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium">用户名</label>
                  <input 
                    type="text" 
                    className="w-full mt-1 px-3 py-2 border rounded-md"
                    placeholder="用户名"
                    disabled
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">邮箱</label>
                  <input 
                    type="email" 
                    className="w-full mt-1 px-3 py-2 border rounded-md"
                    placeholder="邮箱地址"
                    disabled
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">全名</label>
                  <input 
                    type="text" 
                    className="w-full mt-1 px-3 py-2 border rounded-md"
                    placeholder="全名"
                  />
                </div>
                <Button>保存更改</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {activeTab === 'ai' && (
          <Card>
            <CardHeader>
              <CardTitle>AI模型配置</CardTitle>
              <CardDescription>配置和管理AI模型提供商</CardDescription>
            </CardHeader>
            <CardContent>
              <AIProviderForm onSubmit={() => {}} />
            </CardContent>
          </Card>
        )}

        {activeTab === 'email' && (
          <Card>
            <CardHeader>
              <CardTitle>邮箱配置</CardTitle>
              <CardDescription>配置邮件发送设置</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium">SMTP服务器</label>
                  <input 
                    type="text" 
                    className="w-full mt-1 px-3 py-2 border rounded-md"
                    placeholder="smtp.example.com"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">端口</label>
                  <input 
                    type="number" 
                    className="w-full mt-1 px-3 py-2 border rounded-md"
                    placeholder="587"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">用户名</label>
                  <input 
                    type="text" 
                    className="w-full mt-1 px-3 py-2 border rounded-md"
                    placeholder="用户名"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">密码</label>
                  <input 
                    type="password" 
                    className="w-full mt-1 px-3 py-2 border rounded-md"
                    placeholder="密码"
                  />
                </div>
                <Button>保存配置</Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
