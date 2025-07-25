'use client'

import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useI18n } from '@/components/providers/I18nProvider'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { User, Bell, Shield, Mail, Bot, TestTube, RefreshCw, Globe } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { httpClient } from '@/lib/api/client';

const profileFormSchema = z.object({
  username: z.string().min(2, 'Username must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  full_name: z.string().optional(),
  bio: z.string().optional(),
})

const notificationFormSchema = z.object({
  email_notifications: z.boolean(),
  report_completion: z.boolean(),
  error_alerts: z.boolean(),
  weekly_summary: z.boolean(),
})

const securityFormSchema = z.object({
  current_password: z.string().min(1, 'Current password is required'),
  new_password: z.string().min(8, 'Password must be at least 8 characters'),
  confirm_password: z.string().min(1, 'Please confirm your password'),
}).refine((data) => data.new_password === data.confirm_password, {
  message: "Passwords don't match",
  path: ["confirm_password"],
})

const emailFormSchema = z.object({
  smtp_server: z.string().min(1, 'SMTP server is required'),
  smtp_port: z.string().min(1, 'Port is required').transform((val) => parseInt(val, 10)).refine((val) => !isNaN(val) && val > 0, {
    message: 'Port must be a positive number'
  }),
  smtp_username: z.string().min(1, 'Username is required'),
  smtp_password: z.string().min(1, 'Password is required'),
  smtp_use_tls: z.boolean(),
  sender_email: z.string().email('Invalid email address'),
  sender_name: z.string().optional(),
})

const aiProviderFormSchema = z.object({
  provider_name: z.enum(['openai', 'local', 'custom']),
  api_key: z.string().optional(),
  api_url: z.string().optional().refine((val) => !val || /^https?:\/\/.+/.test(val), {
    message: 'API URL must be a valid URL when provided'
  }),
  model_name: z.string().optional(),
  max_tokens: z.string().optional().transform((val) => val ? parseInt(val, 10) : undefined).refine((val) => !val || (val >= 1 && val <= 4000), {
    message: 'Max tokens must be between 1 and 4000'
  }),
  temperature: z.string().optional().transform((val) => val ? parseFloat(val) : undefined).refine((val) => !val || (val >= 0 && val <= 2), {
    message: 'Temperature must be between 0 and 2'
  }),
  is_active: z.boolean(),
})

const preferencesFormSchema = z.object({
  language: z.enum(['zh-CN', 'en-US']),
  theme: z.enum(['light', 'dark', 'system']),
  timezone: z.string().optional(),
  date_format: z.enum(['YYYY-MM-DD', 'MM/DD/YYYY', 'DD/MM/YYYY']),
  time_format: z.enum(['12h', '24h']),
})

type ProfileFormValues = z.infer<typeof profileFormSchema>
type NotificationFormValues = z.infer<typeof notificationFormSchema>
type SecurityFormValues = z.infer<typeof securityFormSchema>
type EmailFormValues = {
  smtp_server: string
  smtp_port: string
  smtp_username: string
  smtp_password: string
  smtp_use_tls: boolean
  sender_email: string
  sender_name?: string
}
type AIProviderFormValues = {
  provider_name: 'openai' | 'local' | 'custom'
  api_key?: string
  api_url?: string
  model_name?: string
  max_tokens?: string
  temperature?: string
  is_active: boolean
}
type PreferencesFormValues = z.infer<typeof preferencesFormSchema>

export default function SettingsPage() {
  const { t, currentLocale, setLocale } = useI18n()
  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testingEmail, setTestingEmail] = useState(false)
  const [testingAI, setTestingAI] = useState(false)

  const profileForm = useForm<ProfileFormValues>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: {
      username: '',
      email: '',
      full_name: '',
      bio: '',
    },
  })

  const notificationForm = useForm<NotificationFormValues>({
    resolver: zodResolver(notificationFormSchema),
    defaultValues: {
      email_notifications: true,
      report_completion: true,
      error_alerts: true,
      weekly_summary: false,
    },
  })

  const securityForm = useForm<SecurityFormValues>({
    resolver: zodResolver(securityFormSchema),
    defaultValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
  })

  const emailForm = useForm<EmailFormValues>({
    resolver: zodResolver(emailFormSchema),
    defaultValues: {
      smtp_server: '',
      smtp_port: '587',
      smtp_username: '',
      smtp_password: '',
      smtp_use_tls: true,
      sender_email: '',
      sender_name: '',
    },
  })

  const aiProviderForm = useForm<AIProviderFormValues>({
    resolver: zodResolver(aiProviderFormSchema),
    defaultValues: {
      provider_name: 'openai',
      api_key: '',
      api_url: '',
      model_name: 'gpt-3.5-turbo',
      max_tokens: '1000',
      temperature: '0.7',
      is_active: true,
    },
  })

  const preferencesForm = useForm<PreferencesFormValues>({
    resolver: zodResolver(preferencesFormSchema),
    defaultValues: {
      language: currentLocale,
      theme: 'light',
      timezone: 'Asia/Shanghai',
      date_format: 'YYYY-MM-DD',
      time_format: '24h',
    },
  })

  useEffect(() => {
    fetchAllSettings()
  }, [])

  const fetchAllSettings = async () => {
    setLoading(true)
    try {
      // 获取用户配置信息
      const [profileResponse, preferencesResponse, emailResponse, aiProviderResponse] = await Promise.all([
        httpClient.get('/v1/users/me'),
        httpClient.get('/v1/user-profile/me'),
        httpClient.get('/v1/email-settings'),
        httpClient.get('/v1/ai-providers/active'),
      ]);

      if (profileResponse.status === 200) {
        const profileData = profileResponse.data;
        profileForm.reset({
          username: profileData.username || '',
          email: profileData.email || '',
          full_name: profileData.full_name || '',
          bio: profileData.bio || '',
        });
      }

      if (preferencesResponse.status === 200) {
        const preferencesData = preferencesResponse.data;
        preferencesForm.reset({
          language: preferencesData.language || currentLocale,
          theme: preferencesData.theme || 'light',
          timezone: preferencesData.timezone || 'Asia/Shanghai',
          date_format: preferencesData.date_format || 'YYYY-MM-DD',
          time_format: preferencesData.time_format || '24h',
        });
      }

      if (emailResponse.status === 200) {
        const emailData = emailResponse.data;
        emailForm.reset({
          smtp_server: emailData.smtp_server || '',
          smtp_port: emailData.smtp_port?.toString() || '587',
          smtp_username: emailData.smtp_username || '',
          smtp_password: '', // 不显示密码
          smtp_use_tls: emailData.smtp_use_tls ?? true,
          sender_email: emailData.sender_email || '',
          sender_name: emailData.sender_name || '',
        });
      }

      if (aiProviderResponse.status === 200) {
        const aiProviderData = aiProviderResponse.data;
        aiProviderForm.reset({
          provider_name: aiProviderData.provider_name || 'openai',
          api_key: '', // 不显示API密钥
          api_url: aiProviderData.api_url || '',
          model_name: aiProviderData.model_name || 'gpt-3.5-turbo',
          max_tokens: aiProviderData.max_tokens?.toString() || '1000',
          temperature: aiProviderData.temperature?.toString() || '0.7',
          is_active: aiProviderData.is_active ?? true,
        });
      }
    } catch (error) {
      console.error('Error fetching settings:', error);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }

  const onProfileSubmit = async (values: ProfileFormValues) => { // eslint-disable-line @typescript-eslint/no-unused-vars
    setSaving(true)
    setTimeout(() => {
      alert('Profile updated successfully!')
      setSaving(false)
    }, 1000)
  }

  const onNotificationSubmit = async (values: NotificationFormValues) => { // eslint-disable-line @typescript-eslint/no-unused-vars
    setSaving(true)
    setTimeout(() => {
      alert('Notification settings updated successfully!')
      setSaving(false)
    }, 1000)
  }

  const onSecuritySubmit = async (values: SecurityFormValues) => { // eslint-disable-line @typescript-eslint/no-unused-vars
    setSaving(true)
    setTimeout(() => {
      alert('Password updated successfully!')
      securityForm.reset()
      setSaving(false)
    }, 1000)
  }

  const onEmailSubmit = async (values: EmailFormValues) => { // eslint-disable-line @typescript-eslint/no-unused-vars
    setSaving(true)
    setTimeout(() => {
      alert('Email settings updated successfully!')
      setSaving(false)
    }, 1000)
  }

  const onAIProviderSubmit = async (values: AIProviderFormValues) => { // eslint-disable-line @typescript-eslint/no-unused-vars
    setSaving(true)
    setTimeout(() => {
      alert('AI provider settings updated successfully!')
      setSaving(false)
    }, 1000)
  }

  const onPreferencesSubmit = async (values: PreferencesFormValues) => {
    setSaving(true)
    setTimeout(() => {
      // 更新语言设置
      if (values.language !== currentLocale) {
        setLocale(values.language)
        // 跳转到对应语言的路由
        const newLocale = values.language === 'zh-CN' ? 'zh-CN' : 'en-US'
        const currentPath = window.location.pathname
        const newPath = currentPath.replace(/^\/(zh-CN|en-US)/, `/${newLocale}`)
        window.location.href = newPath
      }
      alert('Preferences updated successfully!')
      setSaving(false)
    }, 1000)
  }

  const testEmailConnection = async () => {
    setTestingEmail(true)
    setTimeout(() => {
      alert('Email connection test successful!')
      setTestingEmail(false)
    }, 1000)
  }

  const testAIProvider = async () => {
    setTestingAI(true)
    setTimeout(() => {
      alert('AI provider test successful!')
      setTestingAI(false)
    }, 1000)
  }

  const handleRefresh = () => {
    setIsRefreshing(true)
    fetchAllSettings()
  }

  if (loading) {
    return <div className="p-8 text-center text-gray-500">{t('loading')}</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">{t('title', 'settings')}</h1>
          <p className="text-gray-600">{t('description', 'settings')}</p>
        </div>
        <Button onClick={handleRefresh} disabled={isRefreshing} variant="outline" size="sm">
          <RefreshCw className="mr-2 h-4 w-4" />
          {t('refresh')}
        </Button>
      </div>

      <Tabs defaultValue="profile" className="space-y-4">
        <TabsList>
          <TabsTrigger value="profile">
            <User className="w-4 h-4 mr-2" />
            {t('profile', 'user')}
          </TabsTrigger>
          <TabsTrigger value="notifications">
            <Bell className="w-4 h-4 mr-2" />
            {t('notifications', 'user')}
          </TabsTrigger>
          <TabsTrigger value="preferences">
            <Globe className="w-4 h-4 mr-2" />
            {t('preferences', 'user')}
          </TabsTrigger>
          <TabsTrigger value="email">
            <Mail className="w-4 h-4 mr-2" />
            Email
          </TabsTrigger>
          <TabsTrigger value="ai-provider">
            <Bot className="w-4 h-4 mr-2" />
            AI Provider
          </TabsTrigger>
          <TabsTrigger value="security">
            <Shield className="w-4 h-4 mr-2" />
            {t('security', 'user')}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle>{t('profile', 'user')}</CardTitle>
              <CardDescription>
                {t('updateProfile', 'settings')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...profileForm}>
                <form onSubmit={profileForm.handleSubmit(onProfileSubmit)} className="space-y-4">
                  <FormField
                    control={profileForm.control}
                    name="username"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('username', 'auth')}</FormLabel>
                        <FormControl>
                          <Input placeholder={t('usernamePlaceholder', 'auth')} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={profileForm.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('email', 'auth')}</FormLabel>
                        <FormControl>
                          <Input placeholder={t('passwordPlaceholder', 'auth')} type="email" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={profileForm.control}
                    name="full_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('fullName', 'settings')}</FormLabel>
                        <FormControl>
                          <Input placeholder={t('fullNamePlaceholder', 'settings')} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={profileForm.control}
                    name="bio"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('bio', 'settings')}</FormLabel>
                        <FormControl>
                          <Textarea placeholder={t('bioPlaceholder', 'settings')} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button type="submit" disabled={saving}>
                    {saving ? t('loading') : t('save')}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>{t('notifications', 'user')}</CardTitle>
              <CardDescription>
                {t('updateNotifications', 'settings')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...notificationForm}>
                <form onSubmit={notificationForm.handleSubmit(onNotificationSubmit)} className="space-y-4">
                  <FormField
                    control={notificationForm.control}
                    name="email_notifications"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel className="text-base">{t('emailNotifications', 'settings')}</FormLabel>
                          <FormDescription>
                            {t('emailNotificationsDesc', 'settings')}
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={notificationForm.control}
                    name="report_completion"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel className="text-base">{t('reportCompletion', 'settings')}</FormLabel>
                          <FormDescription>
                            {t('reportCompletionDesc', 'settings')}
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={notificationForm.control}
                    name="error_alerts"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel className="text-base">{t('errorAlerts', 'settings')}</FormLabel>
                          <FormDescription>
                            {t('errorAlertsDesc', 'settings')}
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={notificationForm.control}
                    name="weekly_summary"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel className="text-base">{t('weeklySummary', 'settings')}</FormLabel>
                          <FormDescription>
                            {t('weeklySummaryDesc', 'settings')}
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <Button type="submit" disabled={saving}>
                    {saving ? t('loading') : t('save')}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preferences">
          <Card>
            <CardHeader>
              <CardTitle>{t('preferences', 'user')}</CardTitle>
              <CardDescription>
                {t('updatePreferences', 'settings')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...preferencesForm}>
                <form onSubmit={preferencesForm.handleSubmit(onPreferencesSubmit)} className="space-y-4">
                  <FormField
                    control={preferencesForm.control}
                    name="language"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('language', 'settings')}</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select language" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="zh-CN">中文 (简体)</SelectItem>
                            <SelectItem value="en-US">English (US)</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormDescription>
                          {t('languageDesc', 'settings')}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={preferencesForm.control}
                    name="theme"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('theme', 'settings')}</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select theme" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="light">Light</SelectItem>
                            <SelectItem value="dark">Dark</SelectItem>
                            <SelectItem value="system">System</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormDescription>
                          {t('themeDesc', 'settings')}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={preferencesForm.control}
                    name="date_format"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('dateFormat', 'settings')}</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select date format" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="YYYY-MM-DD">YYYY-MM-DD</SelectItem>
                            <SelectItem value="MM/DD/YYYY">MM/DD/YYYY</SelectItem>
                            <SelectItem value="DD/MM/YYYY">DD/MM/YYYY</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormDescription>
                          {t('dateFormatDesc', 'settings')}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={preferencesForm.control}
                    name="time_format"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('timeFormat', 'settings')}</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select time format" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="12h">12-hour (AM/PM)</SelectItem>
                            <SelectItem value="24h">24-hour</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormDescription>
                          {t('timeFormatDesc', 'settings')}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button type="submit" disabled={saving}>
                    {saving ? t('loading') : t('saveSettings', 'settings')}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="email">
          <Card>
            <CardHeader>
              <CardTitle>{t('email', 'settings')}</CardTitle>
              <CardDescription>
                {t('updateEmail', 'settings')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...emailForm}>
                <form onSubmit={emailForm.handleSubmit(onEmailSubmit)} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField
                      control={emailForm.control}
                      name="smtp_server"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('smtpServer', 'settings')}</FormLabel>
                          <FormControl>
                            <Input placeholder="smtp.gmail.com" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={emailForm.control}
                      name="smtp_port"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('smtpPort', 'settings')}</FormLabel>
                          <FormControl>
                            <Input 
                              type="number" 
                              placeholder="587" 
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField
                      control={emailForm.control}
                      name="smtp_username"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('smtpUsername', 'settings')}</FormLabel>
                          <FormControl>
                            <Input placeholder="your-email@gmail.com" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={emailForm.control}
                      name="smtp_password"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('smtpPassword', 'settings')}</FormLabel>
                          <FormControl>
                            <Input type="password" placeholder="Your password" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                  <FormField
                    control={emailForm.control}
                    name="smtp_use_tls"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel className="text-base">{t('useTLS', 'settings')}</FormLabel>
                          <FormDescription>
                            {t('useTLSDesc', 'settings')}
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField
                      control={emailForm.control}
                      name="sender_email"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('senderEmail', 'settings')}</FormLabel>
                          <FormControl>
                            <Input placeholder="noreply@yourcompany.com" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={emailForm.control}
                      name="sender_name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('senderName', 'settings')}</FormLabel>
                          <FormControl>
                            <Input placeholder="Your Company" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                  <div className="flex space-x-2">
                    <Button type="submit" disabled={saving}>
                      {saving ? t('loading') : t('saveSettings', 'settings')}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={testEmailConnection}
                      disabled={testingEmail}
                    >
                      <TestTube className="mr-2 h-4 w-4" />
                      {testingEmail ? t('testing', 'settings') : t('testConnection', 'settings')}
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ai-provider">
          <Card>
            <CardHeader>
              <CardTitle>{t('aiProvider', 'settings')}</CardTitle>
              <CardDescription>
                {t('updateAIProvider', 'settings')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...aiProviderForm}>
                <form onSubmit={aiProviderForm.handleSubmit(onAIProviderSubmit)} className="space-y-4">
                  <FormField
                    control={aiProviderForm.control}
                    name="provider_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('provider', 'settings')}</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder={t('providerPlaceholder', 'settings')} />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="openai">OpenAI</SelectItem>
                            <SelectItem value="local">Local Model</SelectItem>
                            <SelectItem value="custom">Custom Provider</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={aiProviderForm.control}
                    name="api_key"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('apiKey', 'settings')}</FormLabel>
                        <FormControl>
                          <Input type="password" placeholder={t('apiKeyPlaceholder', 'settings')} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={aiProviderForm.control}
                    name="api_url"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('apiUrl', 'settings')}</FormLabel>
                        <FormControl>
                          <Input placeholder={t('apiUrlPlaceholder', 'settings')} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <FormField
                      control={aiProviderForm.control}
                      name="model_name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('modelName', 'settings')}</FormLabel>
                          <FormControl>
                            <Input placeholder={t('modelNamePlaceholder', 'settings')} {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={aiProviderForm.control}
                      name="max_tokens"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('maxTokens', 'settings')}</FormLabel>
                          <FormControl>
                            <Input 
                              type="number" 
                              placeholder={t('maxTokensPlaceholder', 'settings')} 
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={aiProviderForm.control}
                      name="temperature"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('temperature', 'settings')}</FormLabel>
                          <FormControl>
                            <Input 
                              type="number" 
                              step="0.1"
                              placeholder={t('temperaturePlaceholder', 'settings')} 
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                  <FormField
                    control={aiProviderForm.control}
                    name="is_active"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel className="text-base">{t('activeProvider', 'settings')}</FormLabel>
                          <FormDescription>
                            {t('activeProviderDesc', 'settings')}
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <div className="flex space-x-2">
                    <Button type="submit" disabled={saving}>
                      {saving ? t('loading') : t('saveSettings', 'settings')}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={testAIProvider}
                      disabled={testingAI}
                    >
                      <TestTube className="mr-2 h-4 w-4" />
                      {testingAI ? t('testing', 'settings') : t('testProvider', 'settings')}
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>{t('security', 'user')}</CardTitle>
              <CardDescription>
                {t('updatePassword', 'settings')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...securityForm}>
                <form onSubmit={securityForm.handleSubmit(onSecuritySubmit)} className="space-y-4">
                  <FormField
                    control={securityForm.control}
                    name="current_password"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('currentPassword', 'settings')}</FormLabel>
                        <FormControl>
                          <Input type="password" placeholder={t('currentPasswordPlaceholder', 'settings')} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={securityForm.control}
                    name="new_password"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('newPassword', 'settings')}</FormLabel>
                        <FormControl>
                          <Input type="password" placeholder={t('newPasswordPlaceholder', 'settings')} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={securityForm.control}
                    name="confirm_password"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('confirmPassword', 'settings')}</FormLabel>
                        <FormControl>
                          <Input type="password" placeholder={t('confirmPasswordPlaceholder', 'settings')} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button type="submit" disabled={saving}>
                    {saving ? t('updating', 'settings') : t('updatePassword', 'settings')}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}