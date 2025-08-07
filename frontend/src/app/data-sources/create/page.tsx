'use client'

import { useState } from 'react'
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
import { useDataSourceStore } from '@/features/data-sources/dataSourceStore'
import { DataSourceCreate, DataSourceType } from '@/types'

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

export default function CreateDataSourcePage() {
  const router = useRouter()
  const { createDataSource, loading } = useDataSourceStore()
  const [selectedType, setSelectedType] = useState<DataSourceType>('sql')

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
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

  const onSubmit = async (data: FormData) => {
    try {
      // 处理JSON字段
      const processedData: DataSourceCreate = {
        ...data,
        api_headers: data.api_headers ? JSON.parse(data.api_headers) : undefined,
        api_body: data.api_body ? JSON.parse(data.api_body) : undefined,
        doris_fe_hosts: data.doris_fe_hosts ? data.doris_fe_hosts.split(',').map(h => h.trim()) : undefined,
      }

      await createDataSource(processedData)
      router.push('/data-sources')
    } catch (error) {
      // 错误处理在store中已处理
    }
  }

  const tabItems = [
    { key: 'basic', label: '基本信息' },
    { key: 'config', label: '连接配置' },
  ]

  return (
    <AppLayout>
      <PageHeader
        title="添加数据源"
        description="配置新的数据源连接"
        breadcrumbs={[
          { label: '数据源', href: '/data-sources' },
          { label: '添加数据源' },
        ]}
      />

      <form onSubmit={handleSubmit(onSubmit)} className="max-w-4xl mx-auto">
        <Tabs items={tabItems} defaultActiveKey="basic">
          <DataSourceTabs 
            sourceType={sourceType}
            register={register}
            errors={errors}
            setValue={setValue}
            setSelectedType={setSelectedType}
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
            创建数据源
          </Button>
        </div>
      </form>
    </AppLayout>
  )
}

interface DataSourceTabsProps {
  sourceType: DataSourceType
  register: any
  errors: any
  setValue: any
  setSelectedType: (type: DataSourceType) => void
}

function DataSourceTabs({ sourceType, register, errors, setValue, setSelectedType }: DataSourceTabsProps) {
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
          </CardContent>
        </Card>
      </TabPanel>

      <TabPanel value="config" activeValue={activeKey}>
        <Card>
          <CardHeader>
            <CardTitle>连接配置</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
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
          </CardContent>
        </Card>
      </TabPanel>
    </>
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