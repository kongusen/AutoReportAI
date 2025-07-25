'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, Save, Loader2, FileText, Database, Clock, Info } from 'lucide-react'
import { useI18n } from '@/components/providers/I18nProvider'
import { httpClient } from '@/lib/api/client';

interface Template {
  id: number
  name: string
  description: string
  category: string
}

interface DataSource {
  id: number
  name: string
  type: string
  status: string
}

const taskFormSchema = z.object({
  name: z.string().min(1, 'Task name is required'),
  description: z.string().optional(),
  template_id: z.string().min(1, 'Template is required'),
  data_source_id: z.string().min(1, 'Data source is required'),
  is_active: z.boolean(),
  schedule_type: z.enum(['manual', 'daily', 'weekly', 'monthly', 'custom']),
  schedule_config: z.string().optional(),
  priority: z.enum(['low', 'medium', 'high']),
  notification_enabled: z.boolean(),
  // 新增
  daily_time: z.string().optional(),
  weekly_day: z.string().optional(),
  weekly_time: z.string().optional(),
  monthly_day: z.string().optional(),
  monthly_time: z.string().optional(),
})

type TaskFormValues = z.infer<typeof taskFormSchema>

export default function CreateTaskPage() {
  const { t } = useI18n()
  const router = useRouter()
  const [templates, setTemplates] = useState<Template[]>([])
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [selectedDataSource, setSelectedDataSource] = useState<DataSource | null>(null)

  const form = useForm<TaskFormValues>({
    resolver: zodResolver(taskFormSchema),
    defaultValues: {
      name: '',
      description: '',
      template_id: '',
      data_source_id: '',
      is_active: true,
      schedule_type: 'manual',
      schedule_config: '',
      priority: 'medium',
      notification_enabled: true,
      daily_time: '',
      weekly_day: '',
      weekly_time: '',
      monthly_day: '',
      monthly_time: '',
    },
  })

  useEffect(() => {
    fetchTemplates()
    fetchDataSources()
  }, [])

  const fetchTemplates = async () => {
    setLoading(true)
    try {
      const response = await httpClient.get('/v1/templates?limit=100')
      setTemplates(response.data.items || [])
    } catch (error) {
      console.error('Error fetching templates:', error)
      setTemplates([])
    } finally {
      setLoading(false)
    }
  }

  const fetchDataSources = async () => {
    try {
      const response = await httpClient.get('/v1/data-sources?limit=100')
      setDataSources(response.data.items || [])
    } catch (error) {
      console.error('Error fetching data sources:', error)
      setDataSources([])
    }
  }

  const onSubmit = async (values: TaskFormValues) => {
    setSaving(true)
    try {
      const payload = {
        ...values,
        template_id: parseInt(values.template_id, 10),
        data_source_id: parseInt(values.data_source_id, 10),
      }
      await httpClient.post('/v1/tasks', payload)
      router.push('/tasks')
    } catch {
      alert('任务创建失败')
    } finally {
      setSaving(false)
    }
  }

  const handleTemplateChange = (templateId: string) => {
    const template = templates.find(t => t.id === parseInt(templateId))
    setSelectedTemplate(template || null)
  }

  const handleDataSourceChange = (dataSourceId: string) => {
    const dataSource = dataSources.find(d => d.id === parseInt(dataSourceId))
    setSelectedDataSource(dataSource || null)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">{t('loading')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.back()}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                {t('back')}
              </Button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">{t('createTask', 'tasks')}</h1>
                <p className="text-sm text-gray-500">{t('createTaskDescription', 'tasks')}</p>
              </div>
            </div>
            <div className="flex space-x-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => router.back()}
              >
                {t('cancel')}
              </Button>
              <Button
                type="submit"
                form="task-form"
                disabled={saving}
              >
                {saving ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('creating', 'tasks')}
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    {t('createTask', 'tasks')}
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Form {...form}>
          <form id="task-form" onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
            {/* Basic Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Info className="mr-2 h-5 w-5" />
                  {t('basicInformation', 'tasks')}
                </CardTitle>
                <CardDescription>
                  {t('basicInformationDescription', 'tasks')}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('taskName', 'tasks')}</FormLabel>
                        <FormControl>
                          <Input placeholder={t('taskNamePlaceholder', 'tasks')} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="priority"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('priority', 'tasks')}</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="low">
                              <div className="flex items-center">
                                <Badge variant="secondary" className="mr-2">低</Badge>
                                {t('lowPriority', 'tasks')}
                              </div>
                            </SelectItem>
                            <SelectItem value="medium">
                              <div className="flex items-center">
                                <Badge variant="default" className="mr-2">中</Badge>
                                {t('mediumPriority', 'tasks')}
                              </div>
                            </SelectItem>
                            <SelectItem value="high">
                              <div className="flex items-center">
                                <Badge variant="destructive" className="mr-2">高</Badge>
                                {t('highPriority', 'tasks')}
                              </div>
                            </SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <FormField
                  control={form.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('description', 'tasks')}</FormLabel>
                      <FormControl>
                        <Textarea 
                          placeholder={t('taskDescriptionPlaceholder', 'tasks')} 
                          rows={3}
                          {...field} 
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="is_active"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base">{t('active', 'tasks')}</FormLabel>
                        <p className="text-sm text-gray-500">{t('activeDescription', 'tasks')}</p>
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
              </CardContent>
            </Card>

            {/* Template and Data Source */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <FileText className="mr-2 h-5 w-5" />
                    {t('template', 'tasks')}
                  </CardTitle>
                  <CardDescription>
                    {t('templateDescription', 'tasks')}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <FormField
                    control={form.control}
                    name="template_id"
                    render={({ field }) => (
                      <FormItem>
                        <Select onValueChange={(value) => {
                          field.onChange(value)
                          handleTemplateChange(value)
                        }} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder={t('selectTemplate', 'tasks')} />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {templates.map(template => (
                              <SelectItem key={template.id} value={template.id.toString()}>
                                <div className="flex flex-col">
                                  <div className="font-medium">{template.name}</div>
                                  <div className="text-sm text-gray-500">{template.description}</div>
                                  <Badge variant="outline" className="w-fit mt-1">{template.category}</Badge>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  {selectedTemplate && (
                    <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                      <h4 className="font-medium text-blue-900">{selectedTemplate.name}</h4>
                      <p className="text-sm text-blue-700 mt-1">{selectedTemplate.description}</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Database className="mr-2 h-5 w-5" />
                    {t('dataSource', 'tasks')}
                  </CardTitle>
                  <CardDescription>
                    {t('dataSourceDescription', 'tasks')}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <FormField
                    control={form.control}
                    name="data_source_id"
                    render={({ field }) => (
                      <FormItem>
                        <Select onValueChange={(value) => {
                          field.onChange(value)
                          handleDataSourceChange(value)
                        }} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder={t('selectDataSource', 'tasks')} />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {dataSources.map(dataSource => (
                              <SelectItem key={dataSource.id} value={dataSource.id.toString()}>
                                <div className="flex flex-col">
                                  <div className="font-medium">{dataSource.name}</div>
                                  <div className="text-sm text-gray-500">{dataSource.type}</div>
                                  <Badge variant="outline" className="w-fit mt-1">{dataSource.status}</Badge>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  {selectedDataSource && (
                    <div className="mt-4 p-4 bg-green-50 rounded-lg">
                      <h4 className="font-medium text-green-900">{selectedDataSource.name}</h4>
                      <p className="text-sm text-green-700 mt-1">{t('dataSourceType', 'tasks')}: {selectedDataSource.type}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Schedule Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Clock className="mr-2 h-5 w-5" />
                  {t('scheduleSettings', 'tasks')}
                </CardTitle>
                <CardDescription>
                  {t('scheduleSettingsDescription', 'tasks')}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <FormField
                  control={form.control}
                  name="schedule_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('scheduleType', 'tasks')}</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger className="w-40">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="manual">{t('manual', 'tasks')}</SelectItem>
                          <SelectItem value="daily">{t('dailyReport', 'tasks')}</SelectItem>
                          <SelectItem value="weekly">{t('weeklyReport', 'tasks')}</SelectItem>
                          <SelectItem value="monthly">{t('monthlyReport', 'tasks')}</SelectItem>
                          <SelectItem value="custom">{t('custom', 'tasks')}</SelectItem>
                        </SelectContent>
                      </Select>
                    </FormItem>
                  )}
                />
                {/* 日报 */}
                {form.watch('schedule_type') === 'daily' && (
                  <div className="flex items-center space-x-2">
                    <span className="text-gray-500 text-sm">{t('nextDay', 'tasks')}</span>
                    <FormField
                      control={form.control}
                      name="daily_time"
                      rules={{ required: true }}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="sr-only">{t('selectTime', 'tasks')}</FormLabel>
                          <FormControl>
                            <Input type="time" min="00:00" max="12:00" step="1800" className="w-28" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <span className="text-xs text-gray-400">{t('dailyTimeTip', 'tasks')}</span>
                  </div>
                )}
                {/* 周报 */}
                {form.watch('schedule_type') === 'weekly' && (
                  <div className="flex items-center space-x-2">
                    <FormField
                      control={form.control}
                      name="weekly_day"
                      rules={{ required: true }}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="sr-only">{t('selectWeekday', 'tasks')}</FormLabel>
                          <Select onValueChange={field.onChange} defaultValue={field.value}>
                            <FormControl>
                              <SelectTrigger className="w-24">
                                <SelectValue />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="1">{t('weekday1', 'tasks')}</SelectItem>
                              <SelectItem value="2">{t('weekday2', 'tasks')}</SelectItem>
                              <SelectItem value="3">{t('weekday3', 'tasks')}</SelectItem>
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="weekly_time"
                      rules={{ required: true }}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="sr-only">{t('selectTime', 'tasks')}</FormLabel>
                          <FormControl>
                            <Input type="time" min="00:00" max="12:00" step="1800" className="w-28" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <span className="text-xs text-gray-400">{t('weeklyTimeTip', 'tasks')}</span>
                  </div>
                )}
                {/* 月报 */}
                {form.watch('schedule_type') === 'monthly' && (
                  <div className="flex items-center space-x-2">
                    <FormField
                      control={form.control}
                      name="monthly_day"
                      rules={{ required: true }}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="sr-only">{t('selectDay', 'tasks')}</FormLabel>
                          <Select onValueChange={field.onChange} defaultValue={field.value}>
                            <FormControl>
                              <SelectTrigger className="w-20">
                                <SelectValue />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {Array.from({length: 15}, (_,i) => i+1).map(d => (
                                <SelectItem key={d} value={d.toString()}>{d}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="monthly_time"
                      rules={{ required: true }}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="sr-only">{t('selectTime', 'tasks')}</FormLabel>
                          <FormControl>
                            <Input type="time" min="00:00" max="12:00" step="1800" className="w-28" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <span className="text-xs text-gray-400">{t('monthlyTimeTip', 'tasks')}</span>
                  </div>
                )}
                {/* 自定义 */}
                {form.watch('schedule_type') === 'custom' && (
                  <FormField
                    control={form.control}
                    name="schedule_config"
                    rules={{ required: true }}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('customConfig', 'tasks')}</FormLabel>
                        <FormControl>
                          <Input placeholder={t('customConfigPlaceholder', 'tasks')} {...field} />
                        </FormControl>
                        <div className="text-xs text-gray-500 mt-1">{t('customLimitTip', 'tasks')}</div>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}
                {/* 手动类型下不显示任何配置项 */}
                {form.watch('schedule_type') === 'manual' && (
                  <div className="text-xs text-gray-400">{t('manualTip', 'tasks')}</div>
                )}
              </CardContent>
            </Card>
          </form>
        </Form>
      </div>
    </div>
  )
} 