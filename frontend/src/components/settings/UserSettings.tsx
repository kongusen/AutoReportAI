'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import toast from 'react-hot-toast'
import { SettingsService, UserProfile, UserProfileUpdate } from '@/services/settingsService'

export function UserSettings() {
  const [profile, setProfile] = useState<Partial<UserProfile>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    loadProfile()
  }, [])

  const loadProfile = async () => {
    try {
      setIsLoading(true)
      const data = await SettingsService.getUserProfile()
      setProfile(data)
    } catch (error) {
      toast.error('加载用户设置失败')
      // 设置默认值
      setProfile({
        language: 'zh',
        theme: 'light',
        email_notifications: true,
        report_notifications: true,
        system_notifications: true,
        default_storage_days: 30,
        auto_cleanup_enabled: false,
        default_report_format: 'pdf',
        timezone: 'Asia/Shanghai',
        date_format: '%Y-%m-%d'
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    
    try {
      const updateData: UserProfileUpdate = {
        language: profile.language,
        theme: profile.theme,
        email_notifications: profile.email_notifications,
        report_notifications: profile.report_notifications,
        system_notifications: profile.system_notifications,
        default_storage_days: profile.default_storage_days,
        auto_cleanup_enabled: profile.auto_cleanup_enabled,
        default_report_format: profile.default_report_format,
        timezone: profile.timezone,
        date_format: profile.date_format,
      }
      await SettingsService.updateUserProfile(updateData)
      toast.success('设置已保存')
    } catch (error) {
      toast.error('保存设置失败')
    } finally {
      setIsSaving(false)
    }
  }

  const handleChange = (field: keyof UserProfile, value: any) => {
    setProfile(prev => ({
      ...prev,
      [field]: value
    }))
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900">个人设置</h3>
        <p className="mt-1 text-sm text-gray-600">
          管理您的个人偏好和应用设置
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 界面设置 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-medium text-gray-900 mb-4">界面设置</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                语言
              </label>
              <select
                value={profile.language}
                onChange={(e) => handleChange('language', e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="zh">中文</option>
                <option value="en">English</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                主题
              </label>
              <select
                value={profile.theme}
                onChange={(e) => handleChange('theme', e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="light">浅色主题</option>
                <option value="dark">深色主题</option>
                <option value="system">跟随系统</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                时区
              </label>
              <select
                value={profile.timezone}
                onChange={(e) => handleChange('timezone', e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="Asia/Shanghai">中国标准时间</option>
                <option value="UTC">UTC</option>
                <option value="America/New_York">Eastern Time</option>
                <option value="America/Los_Angeles">Pacific Time</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                日期格式
              </label>
              <select
                value={profile.date_format}
                onChange={(e) => handleChange('date_format', e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="%Y-%m-%d">2024-01-01</option>
                <option value="%m/%d/%Y">01/01/2024</option>
                <option value="%d/%m/%Y">01/01/2024</option>
                <option value="%Y年%m月%d日">2024年01月01日</option>
              </select>
            </div>
          </div>
        </div>

        {/* 通知设置 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-medium text-gray-900 mb-4">通知设置</h4>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  邮件通知
                </label>
                <p className="text-sm text-gray-500">
                  接收重要邮件通知
                </p>
              </div>
              <input
                type="checkbox"
                checked={profile.email_notifications}
                onChange={(e) => handleChange('email_notifications', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  报告通知
                </label>
                <p className="text-sm text-gray-500">
                  报告生成完成时通知
                </p>
              </div>
              <input
                type="checkbox"
                checked={profile.report_notifications}
                onChange={(e) => handleChange('report_notifications', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  系统通知
                </label>
                <p className="text-sm text-gray-500">
                  接收系统状态通知
                </p>
              </div>
              <input
                type="checkbox"
                checked={profile.system_notifications}
                onChange={(e) => handleChange('system_notifications', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>
          </div>
        </div>

        {/* 数据管理设置 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-medium text-gray-900 mb-4">数据管理</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                默认存储天数
              </label>
              <input
                type="number"
                min="1"
                max="365"
                value={profile.default_storage_days}
                onChange={(e) => handleChange('default_storage_days', parseInt(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                默认报告格式
              </label>
              <select
                value={profile.default_report_format}
                onChange={(e) => handleChange('default_report_format', e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="pdf">PDF</option>
                <option value="xlsx">Excel</option>
                <option value="html">HTML</option>
                <option value="csv">CSV</option>
              </select>
            </div>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                自动清理过期数据
              </label>
              <p className="text-sm text-gray-500">
                自动删除超过存储期限的数据
              </p>
            </div>
            <input
              type="checkbox"
              checked={profile.auto_cleanup_enabled}
              onChange={(e) => handleChange('auto_cleanup_enabled', e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button 
            type="submit" 
            disabled={isSaving}
            className="inline-flex items-center"
          >
            {isSaving && <LoadingSpinner className="w-4 h-4 mr-2" />}
            保存设置
          </Button>
        </div>
      </form>
    </div>
  )
}