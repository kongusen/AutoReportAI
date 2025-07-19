'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const enhancedDataSourceSchema = z.object({
  name: z.string().min(1, '数据源名称不能为空'),
  source_type: z.enum(['sql', 'csv', 'api', 'push']),
  sql_query_type: z.enum(['single_table', 'multi_table', 'custom_view']).optional(),
  connection_string: z.string().optional(),
  base_query: z.string().optional(),
  wide_table_name: z.string().optional(),
  api_url: z.string().url().optional().or(z.literal('')),
  api_method: z.enum(['GET', 'POST', 'PUT', 'DELETE']).optional(),
  api_headers: z.string().optional(),
  api_body: z.string().optional(),
  push_endpoint: z.string().url().optional().or(z.literal('')),
  push_auth_config: z.string().optional(),
  is_active: z.boolean().default(true),
})

type EnhancedDataSourceFormValues = z.infer<typeof enhancedDataSourceSchema>

interface EnhancedDataSourceFormProps {
  onSubmit: (values: EnhancedDataSourceFormValues) => void
  defaultValues?: Partial<EnhancedDataSourceFormValues>
}

export function EnhancedDataSourceForm({
  onSubmit,
  defaultValues,
}: EnhancedDataSourceFormProps) {
  const [activeTab, setActiveTab] = useState('basic')

  const form = useForm<EnhancedDataSourceFormValues>({
    resolver: zodResolver(enhancedDataSourceSchema),
    defaultValues: defaultValues || {
      name: '',
      source_type: 'sql',
      sql_query_type: 'single_table',
      api_method: 'GET',
      is_active: true,
    },
  })

  const sourceType = form.watch('source_type')

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <div className="w-full">
          <div className="border-b">
            <div className="flex space-x-4">
              <button
                type="button"
                className={`px-4 py-2 text-sm font-medium ${activeTab === 'basic' ? 'border-b-2 border-blue-500' : ''}`}
                onClick={() => setActiveTab('basic')}
              >
                基本信息
              </button>
              <button
                type="button"
                className={`px-4 py-2 text-sm font-medium ${activeTab === 'sql' ? 'border-b-2 border-blue-500' : ''}`}
                onClick={() => setActiveTab('sql')}
              >
                SQL配置
              </button>
              <button
                type="button"
                className={`px-4 py-2 text-sm font-medium ${activeTab === 'api' ? 'border-b-2 border-blue-500' : ''}`}
                onClick={() => setActiveTab('api')}
              >
                API配置
              </button>
              <button
                type="button"
                className={`px-4 py-2 text-sm font-medium ${activeTab === 'push' ? 'border-b-2 border-blue-500' : ''}`}
                onClick={() => setActiveTab('push')}
              >
                推送配置
              </button>
            </div>
          </div>

          <div className="mt-4">
            {activeTab === 'basic' && (
              <Card>
                <CardHeader>
                  <CardTitle>基本信息</CardTitle>
                  <CardDescription>配置数据源的基本信息</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>数据源名称</FormLabel>
                        <FormControl>
                          <Input placeholder="例如：销售数据库" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="source_type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>数据源类型</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="选择数据源类型" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="sql">SQL数据库</SelectItem>
                            <SelectItem value="csv">CSV文件</SelectItem>
                            <SelectItem value="api">API接口</SelectItem>
                            <SelectItem value="push">数据推送</SelectItem>
                          </SelectContent>
                        </Select>
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
                          <FormLabel>启用数据源</FormLabel>
                          <FormDescription>
                            启用后该数据源将可用于ETL任务
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
                </CardContent>
              </Card>
            )}

            {activeTab === 'sql' && sourceType === 'sql' && (
              <Card>
                <CardHeader>
                  <CardTitle>SQL配置</CardTitle>
                  <CardDescription>配置SQL数据库连接和查询</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="sql_query_type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>查询类型</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="选择查询类型" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="single_table">单表查询</SelectItem>
                            <SelectItem value="multi_table">多表联查</SelectItem>
                            <SelectItem value="custom_view">自定义视图</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="connection_string"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>连接字符串</FormLabel>
                        <FormControl>
                          <Input 
                            placeholder="例如：postgresql://user:pass@localhost/dbname" 
                            {...field} 
                          />
                        </FormControl>
                        <FormDescription>
                          数据库连接字符串
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="base_query"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>基础查询</FormLabel>
                        <FormControl>
                          <Textarea 
                            placeholder="SELECT * FROM your_table" 
                            className="font-mono"
                            rows={6}
                            {...field} 
                          />
                        </FormControl>
                        <FormDescription>
                          基础SQL查询，支持多表联查
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="wide_table_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>宽表名称</FormLabel>
                        <FormControl>
                          <Input 
                            placeholder="例如：fact_sales_wide" 
                            {...field} 
                          />
                        </FormControl>
                        <FormDescription>
                          生成的宽表名称
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>
            )}

            {activeTab === 'api' && sourceType === 'api' && (
              <Card>
                <CardHeader>
                  <CardTitle>API配置</CardTitle>
                  <CardDescription>配置API接口参数</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="api_url"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>API URL</FormLabel>
                        <FormControl>
                          <Input 
                            placeholder="https://api.example.com/data" 
                            {...field} 
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="api_method"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>请求方法</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="选择请求方法" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="GET">GET</SelectItem>
                            <SelectItem value="POST">POST</SelectItem>
                            <SelectItem value="PUT">PUT</SelectItem>
                            <SelectItem value="DELETE">DELETE</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="api_headers"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>请求头 (JSON格式)</FormLabel>
                        <FormControl>
                          <Textarea 
                            placeholder='{"Authorization": "Bearer token"}' 
                            className="font-mono"
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
                    name="api_body"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>请求体 (JSON格式)</FormLabel>
                        <FormControl>
                          <Textarea 
                            placeholder='{"param": "value"}' 
                            className="font-mono"
                            rows={3}
                            {...field} 
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>
            )}

            {activeTab === 'push' && sourceType === 'push' && (
              <Card>
                <CardHeader>
                  <CardTitle>推送配置</CardTitle>
                  <CardDescription>配置数据推送接收端点</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="push_endpoint"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>推送端点</FormLabel>
                        <FormControl>
                          <Input 
                            placeholder="https://your-app.com/webhook" 
                            {...field} 
                          />
                        </FormControl>
                        <FormDescription>
                          接收推送数据的端点URL
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="push_auth_config"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>认证配置 (JSON格式)</FormLabel>
                        <FormControl>
                          <Textarea 
                            placeholder='{"secret": "your-secret-key"}' 
                            className="font-mono"
                            rows={3}
                            {...field} 
                          />
                        </FormControl>
                        <FormDescription>
                          推送数据的认证配置
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        <div className="flex justify-end">
          <Button type="submit">保存数据源</Button>
        </div>
      </form>
    </Form>
  )
}
