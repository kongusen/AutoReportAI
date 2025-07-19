'use client'

import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import api from '@/lib/api'
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
import { Separator } from '@/components/ui/separator'
import { User, Bell, Shield, Database, Mail, Bot, TestTube } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

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
  smtp_port: z.number().min(1, 'Port must be a positive number'),
  smtp_username: z.string().min(1, 'Username is required'),
  smtp_password: z.string().min(1, 'Password is required'),
  smtp_use_tls: z.boolean(),
  sender_email: z.string().email('Invalid email address'),
  sender_name: z.string().optional(),
})

const aiProviderFormSchema = z.object({
  provider_name: z.enum(['openai', 'local', 'custom'], {
    required_error: 'Please select an AI provider',
  }),
  api_key: z.string().optional(),
  api_url: z.string().url().optional().or(z.literal('')),
  model_name: z.string().optional(),
  max_tokens: z.number().min(1).max(4000).optional(),
  temperature: z.number().min(0).max(2).optional(),
  is_active: z.boolean(),
})

type ProfileFormValues = z.infer<typeof profileFormSchema>
type NotificationFormValues = z.infer<typeof notificationFormSchema>
type SecurityFormValues = z.infer<typeof securityFormSchema>
type EmailFormValues = z.infer<typeof emailFormSchema>
type AIProviderFormValues = z.infer<typeof aiProviderFormSchema>

export default function SettingsPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [user, setUser] = useState<any>(null)

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
      smtp_port: 587,
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
      max_tokens: 1000,
      temperature: 0.7,
      is_active: true,
    },
  })

  const [testingEmail, setTestingEmail] = useState(false)
  const [testingAI, setTestingAI] = useState(false)

  useEffect(() => {
    fetchUserData()
    fetchEmailSettings()
    fetchAIProviderSettings()
  }, [])

  const fetchUserData = async () => {
    try {
      const response = await api.get('/users/me')
      const userData = response.data
      setUser(userData)
      
      // 更新表单默认值
      profileForm.reset({
        username: userData.username || '',
        email: userData.email || '',
        full_name: userData.full_name || '',
        bio: userData.bio || '',
      })
    } catch (error) {
      console.error('Failed to fetch user data:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchEmailSettings = async () => {
    try {
      // 假设有一个获取邮箱设置的接口
      const response = await api.get('/user-profile/email-settings')
      const emailData = response.data
      emailForm.reset({
        smtp_server: emailData.smtp_server || '',
        smtp_port: emailData.smtp_port || 587,
        smtp_username: emailData.smtp_username || '',
        smtp_password: emailData.smtp_password || '',
        smtp_use_tls: emailData.smtp_use_tls ?? true,
        sender_email: emailData.sender_email || '',
        sender_name: emailData.sender_name || '',
      })
    } catch (error) {
      console.error('Failed to fetch email settings:', error)
    }
  }

  const fetchAIProviderSettings = async () => {
    try {
      // 获取当前用户的AI供应商设置
      const response = await api.get('/ai-providers')
      const providers = Array.isArray(response.data) ? response.data : (response.data.items || [])
      const activeProvider = providers.find((p: any) => p.is_active)
      
      if (activeProvider) {
        aiProviderForm.reset({
          provider_name: activeProvider.provider_name || 'openai',
          api_key: activeProvider.api_key || '',
          api_url: activeProvider.api_url || '',
          model_name: activeProvider.model_name || 'gpt-3.5-turbo',
          max_tokens: activeProvider.max_tokens || 1000,
          temperature: activeProvider.temperature || 0.7,
          is_active: activeProvider.is_active ?? true,
        })
      }
    } catch (error) {
      console.error('Failed to fetch AI provider settings:', error)
    }
  }

  const onProfileSubmit = async (values: ProfileFormValues) => {
    setSaving(true)
    try {
      await api.put('/users/me', values)
      alert('Profile updated successfully!')
      fetchUserData()
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to update profile')
    } finally {
      setSaving(false)
    }
  }

  const onNotificationSubmit = async (values: NotificationFormValues) => {
    setSaving(true)
    try {
      await api.put('/user-profile/me', { preferences: values })
      alert('Notification settings updated successfully!')
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to update notification settings')
    } finally {
      setSaving(false)
    }
  }

  const onSecuritySubmit = async (values: SecurityFormValues) => {
    setSaving(true)
    try {
      await api.put('/users/me/password', {
        current_password: values.current_password,
        new_password: values.new_password,
      })
      alert('Password updated successfully!')
      securityForm.reset()
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to update password')
    } finally {
      setSaving(false)
    }
  }

  const onEmailSubmit = async (values: EmailFormValues) => {
    setSaving(true)
    try {
      await api.put('/user-profile/email-settings', values)
      alert('Email settings updated successfully!')
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to update email settings')
    } finally {
      setSaving(false)
    }
  }

  const onAIProviderSubmit = async (values: AIProviderFormValues) => {
    setSaving(true)
    try {
      // 先获取现有的AI供应商列表
      const response = await api.get('/ai-providers')
      const providers = Array.isArray(response.data) ? response.data : (response.data.items || [])
      const existingProvider = providers.find((p: any) => p.provider_name === values.provider_name)

      if (existingProvider) {
        // 更新现有供应商
        await api.put(`/ai-providers/${existingProvider.id}`, values)
      } else {
        // 创建新供应商
        await api.post('/ai-providers', values)
      }
      
      alert('AI provider settings updated successfully!')
      fetchAIProviderSettings()
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to update AI provider settings')
    } finally {
      setSaving(false)
    }
  }

  const testEmailConnection = async () => {
    setTestingEmail(true)
    try {
      const values = emailForm.getValues()
      await api.post('/user-profile/test-email', values)
      alert('Email connection test successful!')
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Email connection test failed')
    } finally {
      setTestingEmail(false)
    }
  }

  const testAIProvider = async () => {
    setTestingAI(true)
    try {
      const values = aiProviderForm.getValues()
      await api.post('/ai-providers/test', values)
      alert('AI provider test successful!')
    } catch (error: any) {
      alert(error.response?.data?.detail || 'AI provider test failed')
    } finally {
      setTestingAI(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Loading settings...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-gray-600">Manage your account settings and preferences</p>
      </div>

      <Tabs defaultValue="profile" className="space-y-4">
        <TabsList>
          <TabsTrigger value="profile">
            <User className="w-4 h-4 mr-2" />
            Profile
          </TabsTrigger>
          <TabsTrigger value="notifications">
            <Bell className="w-4 h-4 mr-2" />
            Notifications
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
            Security
          </TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>
                Update your personal information and profile details.
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
                        <FormLabel>Username</FormLabel>
                        <FormControl>
                          <Input placeholder="Enter your username" {...field} />
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
                        <FormLabel>Email</FormLabel>
                        <FormControl>
                          <Input placeholder="Enter your email" type="email" {...field} />
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
                        <FormLabel>Full Name</FormLabel>
                        <FormControl>
                          <Input placeholder="Enter your full name" {...field} />
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
                        <FormLabel>Bio</FormLabel>
                        <FormControl>
                          <Textarea 
                            placeholder="Tell us about yourself" 
                            className="resize-none" 
                            {...field} 
                          />
                        </FormControl>
                        <FormDescription>
                          Brief description for your profile. Max 160 characters.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button type="submit" disabled={saving}>
                    {saving ? 'Saving...' : 'Save Changes'}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>
                Choose what notifications you want to receive.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...notificationForm}>
                <form onSubmit={notificationForm.handleSubmit(onNotificationSubmit)} className="space-y-6">
                  <FormField
                    control={notificationForm.control}
                    name="email_notifications"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel className="text-base">Email Notifications</FormLabel>
                          <FormDescription>
                            Receive notifications via email
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
                          <FormLabel className="text-base">Report Completion</FormLabel>
                          <FormDescription>
                            Get notified when reports are generated
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
                          <FormLabel className="text-base">Error Alerts</FormLabel>
                          <FormDescription>
                            Get notified when errors occur
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
                          <FormLabel className="text-base">Weekly Summary</FormLabel>
                          <FormDescription>
                            Receive weekly activity summaries
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
                    {saving ? 'Saving...' : 'Save Preferences'}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="email">
          <Card>
            <CardHeader>
              <CardTitle>Email Settings</CardTitle>
              <CardDescription>
                Configure SMTP settings for sending email notifications and reports.
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
                          <FormLabel>SMTP Server</FormLabel>
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
                          <FormLabel>SMTP Port</FormLabel>
                          <FormControl>
                            <Input 
                              type="number" 
                              placeholder="587" 
                              {...field}
                              onChange={(e) => field.onChange(parseInt(e.target.value) || 587)}
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
                          <FormLabel>SMTP Username</FormLabel>
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
                          <FormLabel>SMTP Password</FormLabel>
                          <FormControl>
                            <Input type="password" placeholder="••••••••" {...field} />
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
                          <FormLabel className="text-base">Use TLS/SSL</FormLabel>
                          <FormDescription>
                            Enable secure connection to SMTP server
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
                          <FormLabel>Sender Email</FormLabel>
                          <FormControl>
                            <Input placeholder="noreply@yourcompany.com" type="email" {...field} />
                          </FormControl>
                          <FormDescription>
                            Email address that will appear as sender
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={emailForm.control}
                      name="sender_name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Sender Name</FormLabel>
                          <FormControl>
                            <Input placeholder="AutoReportAI" {...field} />
                          </FormControl>
                          <FormDescription>
                            Name that will appear as sender
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                  <div className="flex space-x-2">
                    <Button type="submit" disabled={saving}>
                      {saving ? 'Saving...' : 'Save Email Settings'}
                    </Button>
                    <Button 
                      type="button" 
                      variant="outline" 
                      onClick={testEmailConnection}
                      disabled={testingEmail}
                    >
                      <TestTube className="w-4 h-4 mr-2" />
                      {testingEmail ? 'Testing...' : 'Test Connection'}
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
              <CardTitle>AI Provider Settings</CardTitle>
              <CardDescription>
                Configure AI provider for intelligent report generation and data analysis.
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
                        <FormLabel>AI Provider</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select an AI provider" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="openai">OpenAI</SelectItem>
                            <SelectItem value="local">Local Model</SelectItem>
                            <SelectItem value="custom">Custom Provider</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormDescription>
                          Choose your preferred AI provider for content generation
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  {aiProviderForm.watch('provider_name') === 'openai' && (
                    <>
                      <FormField
                        control={aiProviderForm.control}
                        name="api_key"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>OpenAI API Key</FormLabel>
                            <FormControl>
                              <Input type="password" placeholder="sk-..." {...field} />
                            </FormControl>
                            <FormDescription>
                              Your OpenAI API key for accessing GPT models
                            </FormDescription>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={aiProviderForm.control}
                        name="model_name"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Model</FormLabel>
                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                              <FormControl>
                                <SelectTrigger>
                                  <SelectValue placeholder="Select a model" />
                                </SelectTrigger>
                              </FormControl>
                              <SelectContent>
                                <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                                <SelectItem value="gpt-4">GPT-4</SelectItem>
                                <SelectItem value="gpt-4-turbo">GPT-4 Turbo</SelectItem>
                              </SelectContent>
                            </Select>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </>
                  )}

                  {aiProviderForm.watch('provider_name') === 'custom' && (
                    <FormField
                      control={aiProviderForm.control}
                      name="api_url"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>API URL</FormLabel>
                          <FormControl>
                            <Input placeholder="https://api.example.com/v1" {...field} />
                          </FormControl>
                          <FormDescription>
                            Custom API endpoint for your AI provider
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField
                      control={aiProviderForm.control}
                      name="max_tokens"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Max Tokens</FormLabel>
                          <FormControl>
                            <Input 
                              type="number" 
                              placeholder="1000" 
                              {...field}
                              onChange={(e) => field.onChange(parseInt(e.target.value) || 1000)}
                            />
                          </FormControl>
                          <FormDescription>
                            Maximum tokens for AI responses (1-4000)
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={aiProviderForm.control}
                      name="temperature"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Temperature</FormLabel>
                          <FormControl>
                            <Input 
                              type="number" 
                              step="0.1"
                              min="0"
                              max="2"
                              placeholder="0.7" 
                              {...field}
                              onChange={(e) => field.onChange(parseFloat(e.target.value) || 0.7)}
                            />
                          </FormControl>
                          <FormDescription>
                            Creativity level (0.0-2.0, lower = more focused)
                          </FormDescription>
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
                          <FormLabel className="text-base">Enable AI Provider</FormLabel>
                          <FormDescription>
                            Activate this AI provider for report generation
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
                      {saving ? 'Saving...' : 'Save AI Settings'}
                    </Button>
                    <Button 
                      type="button" 
                      variant="outline" 
                      onClick={testAIProvider}
                      disabled={testingAI}
                    >
                      <TestTube className="w-4 h-4 mr-2" />
                      {testingAI ? 'Testing...' : 'Test AI Provider'}
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
              <CardTitle>Security Settings</CardTitle>
              <CardDescription>
                Update your password and security preferences.
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
                        <FormLabel>Current Password</FormLabel>
                        <FormControl>
                          <Input type="password" placeholder="Enter current password" {...field} />
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
                        <FormLabel>New Password</FormLabel>
                        <FormControl>
                          <Input type="password" placeholder="Enter new password" {...field} />
                        </FormControl>
                        <FormDescription>
                          Password must be at least 8 characters long.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={securityForm.control}
                    name="confirm_password"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Confirm New Password</FormLabel>
                        <FormControl>
                          <Input type="password" placeholder="Confirm new password" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button type="submit" disabled={saving}>
                    {saving ? 'Updating...' : 'Update Password'}
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