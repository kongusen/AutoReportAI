'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
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
import { ExpandablePanel } from '@/components/ui/ExpandablePanel'
import { Switch } from '@/components/ui/Switch'
import { useDataSourceStore } from '@/features/data-sources/dataSourceStore'
import { DataSourceUpdate, DataSourceType } from '@/types'

import { dataSourceSchema } from '@/features/data-sources/validations'

type FormData = z.infer<typeof dataSourceSchema>

const dataSourceTypeOptions = [
  { label: 'SQL数据库', value: 'sql' },
  { label: 'Apache Doris', value: 'doris' },
  { label: 'API接口', value: 'api' },
  { label: 'CSV文件', value: 'csv' },
  { label: '推送数据', value: 'push' },
]

const sqlQueryTypeOptions = [
  { label: '单表查询', value: 'single_table' },
  { label: '多表关联', value: 'multi_table' },
  { label: '自定义视图', value: 'custom_view' },
]

const apiMethodOptions = [
  { label: 'GET', value: 'GET' },
  { label: 'POST', value: 'POST' },
  { label: 'PUT', value: 'PUT' },
  { label: 'DELETE', value: 'DELETE' },
]

export default function EditDataSourcePage() {
  const router = useRouter()
  const params = useParams()
  const dataSourceId = params.id as string
  const { getDataSource, updateDataSource, loading } = useDataSourceStore()
  const [selectedType, setSelectedType] = useState<DataSourceType>('sql')
  const [isLoading, setIsLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
    reset,
    getValues,
  } = useForm<FormData>({
    resolver: zodResolver(dataSourceSchema),
    defaultValues: {
      source_type: 'sql',
      sql_query_type: 'single_table',
      api_method: 'GET',
      doris_http_port: 8030,
      doris_query_port: 9030,
      is_active: true,
    },
  })

  const sourceType = watch('source_type')

  useEffect(() => {
    const loadDataSource = async () => {
      try {
        const dataSource = await getDataSource(dataSourceId)
        if (dataSource) {
          // 处理数据源数据以适配表单
          const formData = {
            ...dataSource,
            // 处理 JSON 字段转换为字符串
            api_headers: dataSource.api_headers ? JSON.stringify(dataSource.api_headers, null, 2) : '',
            api_body: dataSource.api_body ? JSON.stringify(dataSource.api_body, null, 2) : '',
            // 处理 Doris 主机列表
            doris_fe_hosts: Array.isArray(dataSource.doris_fe_hosts) 
              ? dataSource.doris_fe_hosts.join(', ') 
              : dataSource.doris_fe_hosts,
          }
          
          reset(formData)
          setSelectedType(dataSource.source_type)
        }
      } catch (error) {
        console.error('Failed to load data source:', error)
        // 可以添加错误提示
      } finally {
        setIsLoading(false)
      }
    }

    loadDataSource()
  }, [dataSourceId, getDataSource, reset])

  const onSubmit = async (data: FormData) => {
    setSaving(true)
    try {
      // 处理JSON字段和数据转换
      const processedData: DataSourceUpdate = {
        ...data,
        // 确保必填字段有默认值
        sql_query_type: data.sql_query_type || 'single_table',
        api_method: data.api_method || 'GET',
        is_active: data.is_active !== undefined ? data.is_active : true,
        // 处理JSON字段
        api_headers: data.api_headers ? (() => {
          try {
            return JSON.parse(data.api_headers)
          } catch {
            return {}
          }
        })() : undefined,
        api_body: data.api_body ? (() => {
          try {
            return JSON.parse(data.api_body)
          } catch {
            return {}
          }
        })() : undefined,
        // 处理Doris主机列表
        doris_fe_hosts: data.doris_fe_hosts ? 
          data.doris_fe_hosts.split(',').map(h => h.trim()).filter(h => h.length > 0) : 
          undefined,
      }

      await updateDataSource(dataSourceId, processedData)
      router.push('/data-sources')
    } catch (error) {
      // 错误处理在store中已处理
    } finally {
      setSaving(false)
    }
  }


  if (isLoading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-lg">加载中...</div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <PageHeader
        title="编辑数据源"
        description="修改数据源连接配置"
        breadcrumbs={[
          { label: '数据源', href: '/data-sources' },
          { label: '编辑数据源' },
        ]}
      />

      <form onSubmit={handleSubmit(onSubmit)} className="max-w-4xl mx-auto">
        <div className="space-y-6">
          <BasicInfoCard 
            sourceType={sourceType}
            register={register}
            errors={errors}
            setValue={setValue}
            setSelectedType={setSelectedType}
            getValues={getValues}
          />
          
          <ExpandablePanel title="连接配置" defaultExpanded={false}>
            <ConfigurationContent
              sourceType={sourceType}
              register={register}
              errors={errors}
            />
          </ExpandablePanel>
          
          <ExpandablePanel title="状态管理" defaultExpanded={false}>
            <StatusManagement
              getValues={getValues}
              setValue={setValue}
            />
          </ExpandablePanel>
        </div>

        <div className="mt-8 flex justify-end space-x-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.back()}
          >
            取消
          </Button>
          <Button type="submit" loading={saving}>
            保存更改
          </Button>
        </div>
      </form>
    </AppLayout>
  )
}

interface BasicInfoCardProps {
  sourceType: DataSourceType
  register: any
  errors: any
  setValue: any
  setSelectedType: (type: DataSourceType) => void
  getValues: any
}

function BasicInfoCard({ sourceType, register, errors, setValue, setSelectedType, getValues }: BasicInfoCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>基本信息</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              数据源名称 *
            </label>
            <Input
              placeholder="输入数据源名称"
              error={!!errors.name}
              {...register('name')}
            />
            {errors.name && (
              <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              显示名称
            </label>
            <Input
              placeholder="输入显示名称（可选）"
              {...register('display_name')}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            数据源类型 *
          </label>
          <Select
            options={dataSourceTypeOptions}
            value={sourceType}
            onChange={(value) => {
              const newType = value as DataSourceType
              setValue('source_type', newType)
              setSelectedType(newType)
            }}
          />
          {errors.source_type && (
            <p className="mt-1 text-sm text-red-600">{errors.source_type.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            描述
          </label>
          <Textarea
            placeholder="输入数据源描述（可选）"
            {...register('description')}
          />
        </div>

        <div className="pt-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700">数据源状态</label>
            <Switch
              checked={getValues('is_active')}
              onChange={(checked) => setValue('is_active', checked)}
              label="启用"
              description=""
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

interface ConfigurationContentProps {
  sourceType: DataSourceType
  register: any
  errors: any
}

function ConfigurationContent({ sourceType, register, errors }: ConfigurationContentProps) {
  return (
    <div className="space-y-6">
      {sourceType === 'sql' && (
        <SqlConfiguration register={register} errors={errors} />
      )}
      {sourceType === 'doris' && (
        <DorisConfiguration register={register} errors={errors} />
      )}
      {sourceType === 'api' && (
        <ApiConfiguration register={register} errors={errors} />
      )}
      {sourceType === 'push' && (
        <PushConfiguration register={register} errors={errors} />
      )}
      {sourceType === 'csv' && (
        <CsvConfiguration register={register} errors={errors} />
      )}
    </div>
  )
}

interface StatusManagementProps {
  getValues: any
  setValue: any
}

function StatusManagement({ getValues, setValue }: StatusManagementProps) {
  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          数据源状态
        </label>
        <Switch
          checked={getValues('is_active')}
          onChange={(checked) => setValue('is_active', checked)}
          label="启用数据源"
          description="启用后可以在任务中使用此数据源"
        />
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="text-sm font-medium text-blue-900 mb-2">状态说明</h4>
        <div className="text-sm text-blue-800 space-y-1">
          <p>• 启用状态：数据源可以正常使用，任务可以访问该数据源</p>
          <p>• 禁用状态：数据源暂停使用，相关任务将无法执行</p>
          <p>• 修改状态后，正在运行的任务可能需要重新启动才能生效</p>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          连接测试
        </label>
        <div className="flex items-center space-x-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              console.log('Testing connection...')
            }}
          >
            测试连接
          </Button>
          <span className="text-sm text-gray-500">
            点击测试当前配置的连接是否正常
          </span>
        </div>
      </div>
    </div>
  )
}

function SqlConfiguration({ register, errors }: { register: any; errors: any }) {
  return (
    <>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          连接字符串 *
        </label>
        <Input
          placeholder="postgresql://user:password@localhost:5432/database"
          error={!!errors.connection_string}
          {...register('connection_string')}
        />
        {errors.connection_string && (
          <p className="mt-1 text-sm text-red-600">{errors.connection_string.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          查询类型
        </label>
        <Select
          options={sqlQueryTypeOptions}
          placeholder="选择查询类型"
          {...register('sql_query_type')}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          基础查询
        </label>
        <Textarea
          placeholder="SELECT * FROM table_name"
          {...register('base_query')}
        />
      </div>
    </>
  )
}

function DorisConfiguration({ register, errors }: { register: any; errors: any }) {
  return (
    <>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          FE节点地址 *
        </label>
        <Input
          placeholder="192.168.1.100,192.168.1.101"
          error={!!errors.doris_fe_hosts}
          {...register('doris_fe_hosts')}
        />
        <p className="mt-1 text-xs text-gray-500">多个地址用逗号分隔</p>
        {errors.doris_fe_hosts && (
          <p className="mt-1 text-sm text-red-600">{errors.doris_fe_hosts.message}</p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            HTTP端口
          </label>
          <Input
            type="number"
            placeholder="8030"
            {...register('doris_http_port', { valueAsNumber: true })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            查询端口
          </label>
          <Input
            type="number"
            placeholder="9030"
            {...register('doris_query_port', { valueAsNumber: true })}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            数据库名
          </label>
          <Input
            placeholder="database_name"
            {...register('doris_database')}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            用户名 *
          </label>
          <Input
            placeholder="username"
            error={!!errors.doris_username}
            {...register('doris_username')}
          />
          {errors.doris_username && (
            <p className="mt-1 text-sm text-red-600">{errors.doris_username.message}</p>
          )}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          密码
        </label>
        <Input
          type="password"
          placeholder="输入密码"
          {...register('doris_password')}
        />
      </div>
    </>
  )
}

function ApiConfiguration({ register, errors }: { register: any; errors: any }) {
  return (
    <>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          API地址 *
        </label>
        <Input
          placeholder="https://api.example.com/data"
          error={!!errors.api_url}
          {...register('api_url')}
        />
        {errors.api_url && (
          <p className="mt-1 text-sm text-red-600">{errors.api_url.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          请求方法
        </label>
        <Select
          options={apiMethodOptions}
          placeholder="选择请求方法"
          {...register('api_method')}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          请求头
        </label>
        <Textarea
          placeholder='{"Authorization": "Bearer token"}'
          {...register('api_headers')}
        />
        <p className="mt-1 text-xs text-gray-500">JSON格式</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          请求体
        </label>
        <Textarea
          placeholder='{"query": "SELECT * FROM table"}'
          {...register('api_body')}
        />
        <p className="mt-1 text-xs text-gray-500">JSON格式</p>
      </div>
    </>
  )
}

function PushConfiguration({ register, errors }: { register: any; errors: any }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        推送端点
      </label>
      <Input
        placeholder="/webhook/data-push"
        {...register('push_endpoint')}
      />
      <p className="mt-1 text-xs text-gray-500">数据推送的接收端点</p>
    </div>
  )
}

function CsvConfiguration({ register, errors }: { register: any; errors: any }) {
  return (
    <div className="text-center py-8 text-gray-500">
      <p>CSV文件数据源将通过文件上传配置</p>
      <p className="text-sm mt-2">支持本地上传和远程URL导入</p>
    </div>
  )
}