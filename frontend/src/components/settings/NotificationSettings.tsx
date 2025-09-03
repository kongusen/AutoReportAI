'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import toast from 'react-hot-toast'
import { NotificationService, NotificationPreference } from '@/services/apiService'
import { useEffect } from 'react'

export function NotificationSettings() {
  const [settings, setSettings] = useState<Partial<NotificationPreference>>({
    enable_email: true,
    enable_websocket: true,
    enable_browser: true,
    enable_sound: true,
    enable_report_notifications: true,
    enable_system_notifications: true,
    enable_task_notifications: true,
    enable_error_notifications: true,
    max_notifications_per_day: 50,
    quiet_hours_start: '',
    quiet_hours_end: ''
  })
  const [isSaving, setIsSaving] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  // 加载现有设置
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const preferences = await NotificationService.getPreferences()
        setSettings(preferences)
      } catch (error) {
        console.error('加载通知设置失败:', error)
      } finally {
        setIsLoading(false)
      }
    }

    loadSettings()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    
    try {
      await NotificationService.updatePreferences(settings)
      toast.success('通知设置已保存')
    } catch (error) {
      toast.error('保存通知设置失败')
      console.error('保存设置错误:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleChange = (field: string, value: boolean | string | number) => {
    setSettings(prev => ({
      ...prev,
      [field]: value
    }))
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-medium text-gray-900">通知设置</h3>
          <p className="mt-1 text-sm text-gray-600">加载中...</p>
        </div>
        <LoadingSpinner className="w-6 h-6" />
      </div>
    )
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
          <h4 className="text-md font-medium text-gray-900 mb-4">通知渠道</h4>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  实时通知
                </label>
                <p className="text-sm text-gray-500">
                  启用WebSocket实时通知
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.enable_websocket}
                onChange={(e) => handleChange('enable_websocket', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  邮件通知
                </label>
                <p className="text-sm text-gray-500">
                  接收邮件通知，包括报告附件推送
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.enable_email}
                onChange={(e) => handleChange('enable_email', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  浏览器通知
                </label>
                <p className="text-sm text-gray-500">
                  启用浏览器桌面通知
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.enable_browser}
                onChange={(e) => handleChange('enable_browser', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  声音提示
                </label>
                <p className="text-sm text-gray-500">
                  播放通知提示音
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.enable_sound}
                onChange={(e) => handleChange('enable_sound', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-medium text-gray-900 mb-4">通知类型</h4>
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
                checked={settings.enable_system_notifications}
                onChange={(e) => handleChange('enable_system_notifications', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  报告通知
                </label>
                <p className="text-sm text-gray-500">
                  报告生成完成时发送通知，邮件将包含报告文件附件
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.enable_report_notifications}
                onChange={(e) => handleChange('enable_report_notifications', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  任务通知
                </label>
                <p className="text-sm text-gray-500">
                  当任务执行完成时发送通知
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.enable_task_notifications}
                onChange={(e) => handleChange('enable_task_notifications', e.target.checked)}
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
                checked={settings.enable_error_notifications}
                onChange={(e) => handleChange('enable_error_notifications', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-medium text-gray-900 mb-4">邮件通知专项设置</h4>
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <span className="text-blue-600">📧</span>
                </div>
                <div className="ml-3">
                  <h5 className="text-sm font-medium text-blue-900">邮件推送说明</h5>
                  <p className="mt-1 text-sm text-blue-700">
                    启用邮件通知后，系统将通过邮件发送以下内容：
                  </p>
                  <ul className="mt-2 text-sm text-blue-700 list-disc list-inside space-y-1">
                    <li>任务完成/失败状态通知</li>
                    <li>报告生成完成通知 + 报告文件附件</li>
                    <li>系统维护和重要更新通知</li>
                    <li>错误和异常情况警告</li>
                  </ul>
                </div>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  报告文件邮件推送
                </label>
                <p className="text-sm text-gray-500">
                  自动将生成的报告文件作为邮件附件发送
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.enable_email && settings.enable_report_notifications}
                disabled={!settings.enable_email}
                onChange={(e) => {
                  if (e.target.checked) {
                    handleChange('enable_report_notifications', true)
                  } else {
                    handleChange('enable_report_notifications', false)
                  }
                }}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-medium text-gray-900 mb-4">高级设置</h4>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  每日通知上限
                </label>
                <p className="text-sm text-gray-500">
                  每天最多接收的通知数量
                </p>
              </div>
              <input
                type="number"
                min="1"
                max="100"
                value={settings.max_notifications_per_day}
                onChange={(e) => handleChange('max_notifications_per_day', parseInt(e.target.value))}
                className="w-20 px-3 py-1 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  免打扰开始时间
                </label>
                <input
                  type="time"
                  value={settings.quiet_hours_start || ''}
                  onChange={(e) => handleChange('quiet_hours_start', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  免打扰结束时间
                </label>
                <input
                  type="time"
                  value={settings.quiet_hours_end || ''}
                  onChange={(e) => handleChange('quiet_hours_end', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-end space-x-3">
          <Button 
            type="button"
            variant="outline"
            onClick={async () => {
              try {
                await NotificationService.sendTestNotification('这是一条测试通知')
                toast.success('测试通知已发送')
              } catch (error) {
                toast.error('发送测试通知失败')
              }
            }}
          >
            发送测试通知
          </Button>
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