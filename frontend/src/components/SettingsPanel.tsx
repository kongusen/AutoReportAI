"use client"

import { useState } from 'react'
import { useTheme } from '@/components/ui/ThemeProvider'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'

export function SettingsPanel() {
  const { theme, language, setTheme, setLanguage, t } = useTheme()
  const [notifications, setNotifications] = useState({
    email: true,
    report: true,
    system: true
  })

  return (
    <div className="space-y-6">
      <Card className="border-gray-200 dark:border-gray-700">
        <CardHeader>
          <CardTitle className="text-gray-900 dark:text-gray-100">{t('settings')}</CardTitle>
          <CardDescription className="text-gray-600 dark:text-gray-400">
            个性化您的使用体验
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* 主题设置 */}
          <div className="space-y-2">
            <Label className="text-gray-700 dark:text-gray-300">{t('theme')}</Label>
            <Select value={theme} onValueChange={setTheme}>
              <SelectTrigger className="w-full bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">{t('light')}</SelectItem>
                <SelectItem value="dark">{t('dark')}</SelectItem>
                <SelectItem value="auto">{t('auto')}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* 语言设置 */}
          <div className="space-y-2">
            <Label className="text-gray-700 dark:text-gray-300">{t('language')}</Label>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger className="w-full bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="zh-CN">简体中文</SelectItem>
                <SelectItem value="en-US">English</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* 通知设置 */}
          <div className="space-y-4">
            <Label className="text-gray-700 dark:text-gray-300">{t('notifications')}</Label>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="email-notifications" className="text-gray-600 dark:text-gray-400">
                  邮件通知
                </Label>
                <Switch
                  id="email-notifications"
                  checked={notifications.email}
                  onCheckedChange={(checked) => 
                    setNotifications(prev => ({ ...prev, email: checked }))
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="report-notifications" className="text-gray-600 dark:text-gray-400">
                  报告通知
                </Label>
                <Switch
                  id="report-notifications"
                  checked={notifications.report}
                  onCheckedChange={(checked) => 
                    setNotifications(prev => ({ ...prev, report: checked }))
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="system-notifications" className="text-gray-600 dark:text-gray-400">
                  系统通知
                </Label>
                <Switch
                  id="system-notifications"
                  checked={notifications.system}
                  onCheckedChange={(checked) => 
                    setNotifications(prev => ({ ...prev, system: checked }))
                  }
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
