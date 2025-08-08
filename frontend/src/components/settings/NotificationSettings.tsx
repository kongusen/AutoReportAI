'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/hooks/useToast'
import { SettingsService, UserProfileUpdate } from '@/services/settingsService'

export function NotificationSettings() {
  const [settings, setSettings] = useState({
    email_notifications: true,
    report_notifications: true,
    system_notifications: true,
    task_completion_notifications: true,
    error_notifications: true,
    weekly_summary: true,
    marketing_emails: false
  })
  const [isSaving, setIsSaving] = useState(false)
  const { showToast } = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    
    try {
      const updateData: UserProfileUpdate = {
        email_notifications: settings.email_notifications,
        report_notifications: settings.report_notifications,
        system_notifications: settings.system_notifications
      }
      await SettingsService.updateUserProfile(updateData)
      showToast('通知设置已保存', 'success')
    } catch (error) {
      showToast('保存通知设置失败', 'error')
    } finally {
      setIsSaving(false)
    }
  }

  const handleChange = (field: string, value: boolean) => {
    setSettings(prev => ({
      ...prev,
      [field]: value
    }))
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900">通知设置</h3>
        <p className="mt-1 text-sm text-gray-600">
          控制您接收通知的类型和频率
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-medium text-gray-900 mb-4">邮件通知</h4>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  系统通知
                </label>
                <p className="text-sm text-gray-500">
                  接收系统维护、更新等重要通知
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.system_notifications}
                onChange={(e) => handleChange('system_notifications', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  报告完成通知
                </label>
                <p className="text-sm text-gray-500">
                  当报告生成完成时发送邮件通知
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.report_notifications}
                onChange={(e) => handleChange('report_notifications', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  任务完成通知
                </label>
                <p className="text-sm text-gray-500">
                  当任务执行完成时发送通知
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.task_completion_notifications}
                onChange={(e) => handleChange('task_completion_notifications', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  错误通知
                </label>
                <p className="text-sm text-gray-500">
                  当任务或报告生成出错时发送通知
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.error_notifications}
                onChange={(e) => handleChange('error_notifications', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  每周摘要
                </label>
                <p className="text-sm text-gray-500">
                  每周发送使用情况和活动摘要
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.weekly_summary}
                onChange={(e) => handleChange('weekly_summary', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-medium text-gray-900 mb-4">营销邮件</h4>
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                产品更新和营销邮件
              </label>
              <p className="text-sm text-gray-500">
                接收产品功能更新、最佳实践等邮件
              </p>
            </div>
            <input
              type="checkbox"
              checked={settings.marketing_emails}
              onChange={(e) => handleChange('marketing_emails', e.target.checked)}
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