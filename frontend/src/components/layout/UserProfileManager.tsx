'use client'

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { 
  User, 
  Settings, 
  Bell, 
  Palette, 
  Globe, 
  Download, 
  Upload,
  RotateCcw,
  Save
} from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useApiCall } from '@/lib/hooks/useApiCall'
import { useErrorNotification } from '@/components/providers/ErrorNotificationProvider'
import { userProfileApiService, UserProfileUpdate } from '@/lib/api/services/user-profile-service'
import type { UserProfile } from '@/types/api'
import { LoadingSpinner } from '@/components/ui/loading'
import { ErrorSeverity } from '@/lib/error-handler'

// User profile form schema
const userProfileSchema = z.object({
  language: z.string().min(1, 'Language is required'),
  theme: z.string().min(1, 'Theme is required'),
  email_notifications: z.boolean(),
  report_notifications: z.boolean(),
  system_notifications: z.boolean(),
  default_storage_days: z.number().min(1).max(365),
  auto_cleanup_enabled: z.boolean(),
  default_report_format: z.string().min(1, 'Default report format is required'),
  default_ai_provider: z.string().optional(),
  custom_css: z.string().optional(),
  dashboard_layout: z.string().optional(),
  timezone: z.string().min(1, 'Timezone is required'),
  date_format: z.string().min(1, 'Date format is required'),
})

type UserProfileFormData = z.infer<typeof userProfileSchema>

export function UserProfileManager() {
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null)
  const [isImportOpen, setIsImportOpen] = useState(false)
  const { showToast, showError } = useErrorNotification()

  const form = useForm<UserProfileFormData>({
    resolver: zodResolver(userProfileSchema),
    defaultValues: {
      language: 'zh-CN',
      theme: 'system',
      email_notifications: true,
      report_notifications: true,
      system_notifications: true,
      default_storage_days: 30,
      auto_cleanup_enabled: false,
      default_report_format: 'pdf',
      default_ai_provider: '',
      custom_css: '',
      dashboard_layout: 'default',
      timezone: 'Asia/Shanghai',
      date_format: 'YYYY-MM-DD',
    },
  })

  // Load user profile
  const loadProfileApi = useApiCall(
    () => userProfileApiService.getUserProfile(),
    {
      loadingMessage: 'Loading user profile...',
      errorContext: 'fetch user profile',
      onSuccess: (data) => {
        setUserProfile(data)
        form.reset(data)
      }
    }
  )

  // Update user profile
  const updateProfileApi = useApiCall(
    (data: UserProfileUpdate) => userProfileApiService.updateUserProfile(data),
    {
      loadingMessage: 'Updating profile...',
      errorContext: 'update user profile',
      onSuccess: (data) => {
        setUserProfile(data)
        showToast({ severity: ErrorSeverity.LOW, title: 'Success', message: 'Profile updated successfully' })
      }
    }
  )

  // Reset user profile
  const resetProfileApi = useApiCall(
    () => userProfileApiService.resetUserProfile(),
    {
      loadingMessage: 'Resetting profile...',
      errorContext: 'reset user profile',
      onSuccess: (data) => {
        setUserProfile(data)
        form.reset(data)
        showToast({ severity: ErrorSeverity.LOW, title: 'Success', message: 'Profile reset to defaults' })
      }
    }
  )

  // Export user profile
  const exportProfileApi = useApiCall(
    () => userProfileApiService.exportUserProfile(),
    {
      loadingMessage: 'Exporting profile...',
      errorContext: 'export user profile',
      onSuccess: (blob) => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `user-profile-${new Date().toISOString().split('T')[0]}.json`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        showToast({ severity: ErrorSeverity.LOW, title: 'Success', message: 'Profile exported successfully' })
      }
    }
  )

  // Import user profile
  const importProfileApi = useApiCall(
    (file: File) => userProfileApiService.importUserProfile(file),
    {
      loadingMessage: 'Importing profile...',
      errorContext: 'import user profile',
      onSuccess: (data) => {
        setUserProfile(data)
        form.reset(data)
        showToast({ severity: ErrorSeverity.LOW, title: 'Success', message: 'Profile imported successfully' })
        setIsImportOpen(false)
      }
    }
  )

  useEffect(() => {
    loadProfileApi.execute()
  }, [])

  const handleSubmit = async (data: UserProfileFormData) => {
    await updateProfileApi.execute(data)
  }

  const handleReset = async () => {
    if (confirm('Are you sure you want to reset your profile to default settings?')) {
      await resetProfileApi.execute()
    }
  }

  const handleExport = async () => {
    await exportProfileApi.execute()
  }

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      await importProfileApi.execute(file)
    }
  }

  // Show loading state
  if (loadProfileApi.isLoading && !loadProfileApi.data) {
    return <LoadingSpinner />
  }

  // Show error state
  if (loadProfileApi.isError && !loadProfileApi.data) {
    return (
      <div className="text-destructive p-4 text-center">
        Failed to load user profile
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">User Profile</h2>
          <p className="text-gray-600">Manage your account settings and preferences</p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" onClick={handleExport} disabled={exportProfileApi.isLoading}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <Button variant="outline" onClick={() => setIsImportOpen(true)}>
            <Upload className="mr-2 h-4 w-4" />
            Import
          </Button>
          <Button variant="outline" onClick={handleReset} disabled={resetProfileApi.isLoading}>
            <RotateCcw className="mr-2 h-4 w-4" />
            Reset
          </Button>
        </div>
      </div>

      <form onSubmit={form.handleSubmit(handleSubmit)}>
        <Tabs defaultValue="general" className="space-y-4">
          <TabsList>
            <TabsTrigger value="general">
              <User className="w-4 h-4 mr-2" />
              General
            </TabsTrigger>
            <TabsTrigger value="appearance">
              <Palette className="w-4 h-4 mr-2" />
              Appearance
            </TabsTrigger>
            <TabsTrigger value="notifications">
              <Bell className="w-4 h-4 mr-2" />
              Notifications
            </TabsTrigger>
            <TabsTrigger value="advanced">
              <Settings className="w-4 h-4 mr-2" />
              Advanced
            </TabsTrigger>
          </TabsList>

          <TabsContent value="general">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Language & Region</CardTitle>
                  <CardDescription>
                    Configure your language and regional preferences
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="language">Language</Label>
                    <Select
                      value={form.watch('language')}
                      onValueChange={(value) => form.setValue('language', value)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="zh-CN">中文 (简体)</SelectItem>
                        <SelectItem value="en-US">English (US)</SelectItem>
                        <SelectItem value="ja-JP">日本語</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="timezone">Timezone</Label>
                    <Select
                      value={form.watch('timezone')}
                      onValueChange={(value) => form.setValue('timezone', value)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Asia/Shanghai">Asia/Shanghai</SelectItem>
                        <SelectItem value="America/New_York">America/New_York</SelectItem>
                        <SelectItem value="Europe/London">Europe/London</SelectItem>
                        <SelectItem value="Asia/Tokyo">Asia/Tokyo</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="date_format">Date Format</Label>
                    <Select
                      value={form.watch('date_format')}
                      onValueChange={(value) => form.setValue('date_format', value)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="YYYY-MM-DD">YYYY-MM-DD</SelectItem>
                        <SelectItem value="MM/DD/YYYY">MM/DD/YYYY</SelectItem>
                        <SelectItem value="DD/MM/YYYY">DD/MM/YYYY</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Default Settings</CardTitle>
                  <CardDescription>
                    Configure default values for reports and data
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="default_report_format">Default Report Format</Label>
                    <Select
                      value={form.watch('default_report_format')}
                      onValueChange={(value) => form.setValue('default_report_format', value)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pdf">PDF</SelectItem>
                        <SelectItem value="docx">Word Document</SelectItem>
                        <SelectItem value="xlsx">Excel Spreadsheet</SelectItem>
                        <SelectItem value="html">HTML</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="default_storage_days">Default Storage Days</Label>
                    <Input
                      type="number"
                      min="1"
                      max="365"
                      {...form.register('default_storage_days', { valueAsNumber: true })}
                    />
                    <p className="text-sm text-gray-500">
                      How long to keep generated reports (1-365 days)
                    </p>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Switch
                      checked={form.watch('auto_cleanup_enabled')}
                      onCheckedChange={(checked) => form.setValue('auto_cleanup_enabled', checked)}
                    />
                    <Label htmlFor="auto_cleanup_enabled">Enable Auto Cleanup</Label>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="appearance">
            <Card>
              <CardHeader>
                <CardTitle>Appearance Settings</CardTitle>
                <CardDescription>
                  Customize the look and feel of your interface
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="theme">Theme</Label>
                  <Select
                    value={form.watch('theme')}
                    onValueChange={(value) => form.setValue('theme', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="light">Light</SelectItem>
                      <SelectItem value="dark">Dark</SelectItem>
                      <SelectItem value="system">System</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="dashboard_layout">Dashboard Layout</Label>
                  <Select
                    value={form.watch('dashboard_layout')}
                    onValueChange={(value) => form.setValue('dashboard_layout', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="default">Default</SelectItem>
                      <SelectItem value="compact">Compact</SelectItem>
                      <SelectItem value="expanded">Expanded</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="custom_css">Custom CSS</Label>
                  <Textarea
                    placeholder="Enter custom CSS rules..."
                    rows={6}
                    {...form.register('custom_css')}
                  />
                  <p className="text-sm text-gray-500">
                    Add custom CSS to personalize your interface
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="notifications">
            <Card>
              <CardHeader>
                <CardTitle>Notification Preferences</CardTitle>
                <CardDescription>
                  Choose which notifications you want to receive
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="email_notifications">Email Notifications</Label>
                    <p className="text-sm text-gray-500">
                      Receive notifications via email
                    </p>
                  </div>
                  <Switch
                    checked={form.watch('email_notifications')}
                    onCheckedChange={(checked) => form.setValue('email_notifications', checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="report_notifications">Report Notifications</Label>
                    <p className="text-sm text-gray-500">
                      Get notified when reports are generated
                    </p>
                  </div>
                  <Switch
                    checked={form.watch('report_notifications')}
                    onCheckedChange={(checked) => form.setValue('report_notifications', checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="system_notifications">System Notifications</Label>
                    <p className="text-sm text-gray-500">
                      Receive system updates and maintenance notifications
                    </p>
                  </div>
                  <Switch
                    checked={form.watch('system_notifications')}
                    onCheckedChange={(checked) => form.setValue('system_notifications', checked)}
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="advanced">
            <Card>
              <CardHeader>
                <CardTitle>Advanced Settings</CardTitle>
                <CardDescription>
                  Advanced configuration options
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="default_ai_provider">Default AI Provider</Label>
                  <Select
                    value={form.watch('default_ai_provider')}
                    onValueChange={(value) => form.setValue('default_ai_provider', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select AI provider" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">None</SelectItem>
                      <SelectItem value="openai">OpenAI</SelectItem>
                      <SelectItem value="azure">Azure OpenAI</SelectItem>
                      <SelectItem value="anthropic">Anthropic</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <div className="flex justify-end space-x-2 mt-6">
          <Button
            type="submit"
            disabled={updateProfileApi.isLoading}
          >
            {updateProfileApi.isLoading ? (
              <>
                <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-gray-600" />
                Saving...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                Save Changes
              </>
            )}
          </Button>
        </div>
      </form>

      {/* Import Dialog */}
      {isImportOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <h3 className="text-lg font-medium mb-4">Import Profile</h3>
            <p className="text-sm text-gray-600 mb-4">
              Select a profile configuration file to import your settings.
            </p>
            <input
              type="file"
              accept=".json"
              onChange={handleImport}
              className="w-full p-2 border border-gray-300 rounded-md"
            />
            <div className="flex justify-end space-x-2 mt-4">
              <Button variant="outline" onClick={() => setIsImportOpen(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}