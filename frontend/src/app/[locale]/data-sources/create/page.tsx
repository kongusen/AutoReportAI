'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Loader2, ArrowLeft, Save } from 'lucide-react'
import { useI18n } from '@/components/providers/I18nProvider'
import { httpClient } from '@/lib/api/client';

const dataSourceFormSchema = z.object({
  name: z.string().min(1, '数据源名称必填'),
  type: z.enum(['database', 'api', 'file']),
  url: z.string().optional(),
  username: z.string().optional(),
  password: z.string().optional(),
  api_key: z.string().optional(),
  api_secret: z.string().optional(),
  file_path: z.string().optional(),
  description: z.string().optional(),
  is_active: z.boolean(),
})

type DataSourceFormValues = z.infer<typeof dataSourceFormSchema>

export default function DataSourceFormPage() {
  const { t } = useI18n()
  const router = useRouter()
  const searchParams = useSearchParams()
  const editId = searchParams.get('id')
  const isEdit = !!editId
  const [saving, setSaving] = useState(false)
  const [initialValues, setInitialValues] = useState<DataSourceFormValues | null>(null)

  useEffect(() => {
    if (isEdit) {
      httpClient.get(`/v1/data-sources/${editId}`)
        .then(res => {
          const found = res.data
          setInitialValues({
            name: found.name,
            type: found.type,
            url: found.url || '',
            username: found.username || '',
            password: found.password || '',
            api_key: found.api_key || '',
            api_secret: found.api_secret || '',
            file_path: found.file_path || '',
            description: found.description || '',
            is_active: found.is_active,
          })
        })
        .catch(() => setInitialValues(null))
    } else {
      setInitialValues({
        name: '',
        type: 'database',
        url: '',
        username: '',
        password: '',
        api_key: '',
        api_secret: '',
        file_path: '',
        description: '',
        is_active: true,
      })
    }
  }, [isEdit, editId])

  const form = useForm<DataSourceFormValues>({
    resolver: zodResolver(dataSourceFormSchema),
    defaultValues: initialValues || {
      name: '',
      type: 'database',
      url: '',
      username: '',
      password: '',
      api_key: '',
      api_secret: '',
      file_path: '',
      description: '',
      is_active: true,
    },
    values: initialValues || undefined,
  })

  const type = form.watch('type')

  const onSubmit = async (values: DataSourceFormValues) => {
    setSaving(true)
    try {
      if (isEdit) {
        await httpClient.put(`/v1/data-sources/${editId}`, values)
        alert('数据源已更新！')
      } else {
        await httpClient.post('/v1/data-sources', values)
        alert('数据源创建成功！')
      }
      router.push('/data-sources')
    } catch {
      alert('操作失败')
    } finally {
      setSaving(false)
    }
  }

  if (!initialValues) {
    return <div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin" /></div>
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center py-4">
      <div className="w-full max-w-[95vw] px-2">
        <Card className="w-full shadow-lg">
          <CardHeader>
            <CardTitle>{isEdit ? t('editDataSource', 'dataSources') : t('addDataSource', 'dataSources')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className="overflow-x-auto overflow-y-auto border rounded-lg bg-white p-6"
              style={{ maxHeight: 'calc(100vh - 220px)' }}
            >
              <Form {...form}>
                <form className="space-y-6 min-w-[400px] w-full max-w-3xl mx-auto" onSubmit={form.handleSubmit(onSubmit)}>
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('dataSourceName', 'dataSources')}</FormLabel>
                        <FormControl>
                          <Input placeholder={t('dataSourceNamePlaceholder', 'dataSources')} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('dataSourceType', 'dataSources')}</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="database">{t('database', 'dataSources')}</SelectItem>
                            <SelectItem value="api">{t('api', 'dataSources')}</SelectItem>
                            <SelectItem value="file">{t('file', 'dataSources')}</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  {type === 'database' && (
                    <>
                      <FormField
                        control={form.control}
                        name="url"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>数据库URL</FormLabel>
                            <FormControl>
                              <Input placeholder="如 mysql://host:port/db" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="username"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>账户</FormLabel>
                            <FormControl>
                              <Input placeholder="数据库账户" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="password"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>密码</FormLabel>
                            <FormControl>
                              <Input type="password" placeholder="数据库密码" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </>
                  )}
                  {type === 'api' && (
                    <>
                      <FormField
                        control={form.control}
                        name="url"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>API地址</FormLabel>
                            <FormControl>
                              <Input placeholder="https://api.example.com" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="api_key"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>API Key</FormLabel>
                            <FormControl>
                              <Input placeholder="API Key" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </>
                  )}
                  {type === 'file' && (
                    <FormField
                      control={form.control}
                      name="file_path"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>文件上传</FormLabel>
                          <FormControl>
                            <div className="flex items-center space-x-2">
                              <Input
                                type="file"
                                onChange={e => {
                                  const file = e.target.files?.[0]
                                  if (file) {
                                    field.onChange(file.name)
                                  }
                                }}
                              />
                              {field.value && <span className="text-xs text-gray-500">{field.value}</span>}
                            </div>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  )}
                  <FormField
                    control={form.control}
                    name="description"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('description', 'dataSources')}</FormLabel>
                        <FormControl>
                          <Textarea placeholder={t('descriptionPlaceholder', 'dataSources')} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="is_active"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3">
                        <FormLabel className="text-base">{t('active', 'dataSources')}</FormLabel>
                        <FormControl>
                          <Switch checked={field.value} onCheckedChange={field.onChange} />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <div className="flex justify-end space-x-2 mt-6">
                    <Button type="submit" disabled={saving}>
                      {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                      {isEdit ? t('save', 'dataSources') : t('createDataSource', 'dataSources')}
                    </Button>
                    <Button type="button" variant="outline" onClick={() => router.back()}>
                      <ArrowLeft className="h-4 w-4 mr-2" />
                      {t('cancel')}
                    </Button>
                  </div>
                </form>
              </Form>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
} 