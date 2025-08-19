'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { AppLayout } from '@/components/layout/AppLayout'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Select } from '@/components/ui/Select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Tabs, TabPanel, useTabsContext } from '@/components/ui/Tabs'
import { Switch } from '@/components/ui/Switch'
import { CronEditor } from '@/components/forms/CronEditor'
import { useTaskStore } from '@/features/tasks/taskStore'
import { useDataSourceStore } from '@/features/data-sources/dataSourceStore'
import { useTemplateStore } from '@/features/templates/templateStore'
import { TaskCreate, ProcessingMode, AgentWorkflowType, ReportPeriod } from '@/types'
import { isValidEmail, isValidCron } from '@/utils'
import { TaskConfigForm } from '@/components/tasks/TaskConfigForm'

const taskSchema = z.object({
  name: z.string().min(1, '任务名称不能为空').max(100, '任务名称不能超过100个字符'),
  description: z.string().max(500, '描述不能超过500个字符').optional(),
  template_id: z.string().min(1, '请选择模板'),
  data_source_id: z.string().min(1, '请选择数据源'),
  schedule: z.string().optional(),
  report_period: z.enum(['daily', 'weekly', 'monthly', 'yearly']).default('monthly'),
  recipients: z.array(z.string()).optional(),
  is_active: z.boolean().default(true),
  
  // 新增：Agent配置字段
  processing_mode: z.enum(['simple', 'intelligent', 'hybrid']).default('intelligent'),
  workflow_type: z.enum(['simple_report', 'statistical_analysis', 'chart_generation', 'comprehensive_analysis', 'custom_workflow']).default('simple_report'),
  max_context_tokens: z.number().min(1000).max(128000).default(32000),
  enable_compression: z.boolean().default(true),
}).refine((data) => {
  if (data.schedule && !isValidCron(data.schedule)) {
    return false
  }
  return true
}, {
  message: '无效的Cron表达式',
  path: ['schedule']
}).refine((data) => {
  if (data.recipients) {
    return data.recipients.every(email => isValidEmail(email))
  }
  return true
}, {
  message: '邮箱格式无效',
  path: ['recipients']
})

type FormData = z.infer<typeof taskSchema>

export default function CreateTaskPage() {
  const router = useRouter()
  const { createTask, loading } = useTaskStore()
  const { dataSources, fetchDataSources } = useDataSourceStore()
  const { templates, fetchTemplates } = useTemplateStore()
  const [recipientInput, setRecipientInput] = useState('')
  const [isDirty, setIsDirty] = useState(false)
  const [lastAutoSave, setLastAutoSave] = useState<Date | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
    getValues,
  } = useForm<FormData>({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      is_active: true,
      recipients: [],
      schedule: '',
      report_period: 'monthly' as ReportPeriod,
      processing_mode: 'intelligent' as ProcessingMode,
      workflow_type: 'simple_report' as AgentWorkflowType,
      max_context_tokens: 32000,
      enable_compression: true,
    },
  })

  const watchedRecipients = watch('recipients') || []
  const watchedSchedule = watch('schedule') || ''

  useEffect(() => {
    fetchDataSources()
    fetchTemplates()
    
    // 监听cron自动保存事件
    const handleCronAutoSave = (event: CustomEvent) => {
      const { cron } = event.detail
      setValue('schedule', cron)
      setIsDirty(true)
      setLastAutoSave(new Date())
      
      // 显示保存提示
      console.log('Cron 配置已自动保存:', cron)
    }
    
    window.addEventListener('cronAutoSave', handleCronAutoSave as EventListener)
    
    return () => {
      window.removeEventListener('cronAutoSave', handleCronAutoSave as EventListener)
    }
  }, [fetchDataSources, fetchTemplates, setValue])

  const onSubmit = async (data: FormData) => {
    try {
      const result = await createTask({
        ...data,
        template_id: data.template_id as any, // UUID类型转换
        data_source_id: data.data_source_id as any, // UUID类型转换
        schedule: data.schedule || undefined,
        recipients: data.recipients || [],
      })
      
      // 确保创建成功后才跳转
      if (result) {
        console.log('任务创建成功，准备跳转到任务列表页:', result)
        router.push('/tasks')
      } else {
        console.error('任务创建返回空结果')
        throw new Error('任务创建失败：返回结果为空')
      }
    } catch (error) {
      console.error('创建任务时发生错误:', error)
      // 错误处理在store中已处理，这里不需要额外处理
    }
  }

  const addRecipient = () => {
    if (recipientInput.trim() && isValidEmail(recipientInput.trim())) {
      const currentRecipients = getValues('recipients') || []
      if (!currentRecipients.includes(recipientInput.trim())) {
        setValue('recipients', [...currentRecipients, recipientInput.trim()])
        setRecipientInput('')
      }
    }
  }

  const removeRecipient = (email: string) => {
    const currentRecipients = getValues('recipients') || []
    setValue('recipients', currentRecipients.filter(r => r !== email))
  }

  const handleRecipientKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addRecipient()
    }
  }


  const dataSourceOptions = dataSources.map(ds => ({
    label: ds.display_name || ds.name,
    value: ds.id,
  }))

  const templateOptions = templates.map(template => ({
    label: template.name,
    value: template.id,
  }))

  const tabItems = [
    { key: 'basic', label: '基本信息' },
    { key: 'ai_config', label: 'AI配置' },
    { key: 'schedule', label: '调度设置' },
    { key: 'notification', label: '通知配置' },
  ]

  return (
    <AppLayout>
      <PageHeader
        title="创建任务"
        description="创建新的定时任务"
        breadcrumbs={[
          { label: '任务管理', href: '/tasks' },
          { label: '创建任务' },
        ]}
      />

      <form onSubmit={handleSubmit(onSubmit)} className="max-w-4xl mx-auto">
        <Tabs items={tabItems} defaultActiveKey="basic">
          <TaskTabs
            register={register}
            errors={errors}
            setValue={setValue}
            getValues={getValues}
            dataSourceOptions={dataSourceOptions}
            templateOptions={templateOptions}
            watchedRecipients={watchedRecipients}
            watchedSchedule={watchedSchedule}
            recipientInput={recipientInput}
            setRecipientInput={setRecipientInput}
            addRecipient={addRecipient}
            removeRecipient={removeRecipient}
            handleRecipientKeyDown={handleRecipientKeyDown}
            isDirty={isDirty}
            lastAutoSave={lastAutoSave}
            setIsDirty={setIsDirty}
          />
        </Tabs>

        <div className="mt-8 flex justify-end space-x-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.back()}
          >
            取消
          </Button>
          <Button type="submit" loading={loading}>
            创建任务
          </Button>
        </div>
      </form>
    </AppLayout>
  )
}

interface TaskTabsProps {
  register: any
  errors: any
  setValue: any
  getValues: any
  dataSourceOptions: Array<{ label: string; value: string }>
  templateOptions: Array<{ label: string; value: string }>
  watchedRecipients: string[]
  watchedSchedule: string
  recipientInput: string
  setRecipientInput: (value: string) => void
  addRecipient: () => void
  removeRecipient: (email: string) => void
  handleRecipientKeyDown: (e: React.KeyboardEvent) => void
  isDirty: boolean
  lastAutoSave: Date | null
  setIsDirty: (dirty: boolean) => void
}

function TaskTabs({
  register,
  errors,
  setValue,
  getValues,
  dataSourceOptions,
  templateOptions,
  watchedRecipients,
  watchedSchedule,
  recipientInput,
  setRecipientInput,
  addRecipient,
  removeRecipient,
  handleRecipientKeyDown,
  isDirty,
  lastAutoSave,
  setIsDirty,
}: TaskTabsProps) {
  const { activeKey } = useTabsContext()

  return (
    <>
      <TabPanel value="basic" activeValue={activeKey}>
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  任务名称 *
                </label>
                <Input
                  placeholder="输入任务名称"
                  error={!!errors.name}
                  {...register('name')}
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  状态
                </label>
                <Switch
                  checked={getValues('is_active')}
                  onChange={(checked: boolean) => setValue('is_active', checked)}
                  label="启用任务"
                  description="启用后任务将按调度自动执行"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                任务描述
              </label>
              <Textarea
                placeholder="输入任务描述（可选）"
                {...register('description')}
              />
              {errors.description && (
                <p className="mt-1 text-sm text-red-600">{errors.description.message}</p>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  模板 *
                </label>
                <Select
                  options={templateOptions}
                  placeholder="选择报告模板"
                  onChange={(value) => setValue('template_id', value)}
                />
                {errors.template_id && (
                  <p className="mt-1 text-sm text-red-600">{errors.template_id.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  数据源 *
                </label>
                <Select
                  options={dataSourceOptions}
                  placeholder="选择数据源"
                  onChange={(value) => setValue('data_source_id', value)}
                />
                {errors.data_source_id && (
                  <p className="mt-1 text-sm text-red-600">{errors.data_source_id.message}</p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                报告周期 *
              </label>
              <Select
                options={[
                  { value: 'daily', label: '每日' },
                  { value: 'weekly', label: '每周' },
                  { value: 'monthly', label: '每月' },
                  { value: 'yearly', label: '每年' }
                ]}
                onChange={(value) => setValue('report_period', value as ReportPeriod)}
              />
              {errors.report_period && (
                <p className="mt-1 text-sm text-red-600">{errors.report_period.message}</p>
              )}
              <p className="mt-1 text-sm text-gray-500">
                设置报告数据的时间范围，用于动态生成SQL时间参数
              </p>
            </div>
          </CardContent>
        </Card>
      </TabPanel>

      <TabPanel value="ai_config" activeValue={activeKey}>
        <TaskConfigForm
          task={getValues()}
          onChange={(config) => {
            Object.entries(config).forEach(([key, value]) => {
              setValue(key as keyof FormData, value)
            })
          }}
          showAdvanced={true}
        />
      </TabPanel>

      <TabPanel value="schedule" activeValue={activeKey}>
        <Card>
          <CardHeader>
            <CardTitle>调度设置</CardTitle>
          </CardHeader>
          <CardContent>
            <CronEditor
              value={watchedSchedule}
              onChange={(cron) => {
                setValue('schedule', cron)
                setIsDirty(true)
              }}
              error={errors.schedule?.message}
              autoSave={true}
            />
            {isDirty && (
              <div className="mt-4 text-xs text-green-600 bg-green-50 p-2 rounded flex items-center">
                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                周期配置已自动保存{lastAutoSave ? ` (于 ${lastAutoSave.toLocaleTimeString()})` : ''}
              </div>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      <TabPanel value="notification" activeValue={activeKey}>
        <Card>
          <CardHeader>
            <CardTitle>通知配置</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                邮件通知
              </label>
              <div className="flex gap-2">
                <Input
                  placeholder="输入邮箱地址"
                  value={recipientInput}
                  onChange={(e) => setRecipientInput(e.target.value)}
                  onKeyDown={handleRecipientKeyDown}
                />
                <Button type="button" variant="outline" onClick={addRecipient}>
                  添加
                </Button>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                按Enter键或点击添加按钮来添加邮箱地址
              </p>
              {errors.recipients && (
                <p className="mt-1 text-sm text-red-600">{errors.recipients.message}</p>
              )}
            </div>

            {watchedRecipients.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  通知列表
                </label>
                <div className="space-y-2">
                  {watchedRecipients.map((email, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-2 bg-gray-50 rounded-md"
                    >
                      <span className="text-sm text-gray-900">{email}</span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeRecipient(email)}
                      >
                        删除
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
              <h4 className="text-sm font-medium text-blue-900 mb-2">通知说明</h4>
              <div className="text-sm text-blue-800 space-y-1">
                <p>• 任务执行完成后会自动发送邮件通知</p>
                <p>• 任务执行失败时也会发送错误通知</p>
                <p>• 通知邮件包含任务执行结果和生成的报告下载链接</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </TabPanel>
    </>
  )
}

