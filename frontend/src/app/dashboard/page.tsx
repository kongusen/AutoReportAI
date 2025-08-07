'use client'

import { useEffect, useState } from 'react'
import { 
  CircleStackIcon,
  DocumentTextIcon, 
  ClockIcon,
  DocumentArrowDownIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Progress } from '@/components/ui/Progress'
import { AppLayout } from '@/components/layout/AppLayout'
import { PageHeader } from '@/components/layout/PageHeader'
import { api } from '@/lib/api'
import { formatRelativeTime, formatNumber } from '@/utils'
import { DashboardStats, Task, Report } from '@/types'

interface StatsCardProps {
  title: string
  value: string | number
  description?: string
  icon: React.ComponentType<{ className?: string }>
  trend?: {
    value: number
    label: string
    type: 'increase' | 'decrease'
  }
}

function StatsCard({ title, value, description, icon: Icon, trend }: StatsCardProps) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center">
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-600">{title}</p>
            <p className="text-2xl font-bold text-gray-900">
              {typeof value === 'number' ? formatNumber(value) : value}
            </p>
            {description && (
              <p className="text-xs text-gray-500 mt-1">{description}</p>
            )}
            {trend && (
              <div className="flex items-center mt-1">
                <span className={`text-xs font-medium ${
                  trend.type === 'increase' ? 'text-green-600' : 'text-red-600'
                }`}>
                  {trend.type === 'increase' ? '+' : '-'}{trend.value}%
                </span>
                <span className="text-xs text-gray-500 ml-1">{trend.label}</span>
              </div>
            )}
          </div>
          <div className="ml-4">
            <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center">
              <Icon className="w-6 h-6 text-gray-600" />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [recentTasks, setRecentTasks] = useState<Task[]>([])
  const [recentReports, setRecentReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true)
        
        // 并行获取仪表板数据
        const promises = [
          api.get('/dashboard').catch(err => {
            console.error('Dashboard API failed:', err)
            return { data: null }
          }),
          api.get('/tasks?limit=5').catch(err => {
            console.error('Tasks API failed:', err) 
            return { data: { items: [] } }
          }),
          api.get('/reports?limit=5').catch(err => {
            console.error('Reports API failed:', err)
            return { data: { items: [] } }
          })
        ]
        const [statsResponse, tasksResponse, reportsResponse] = await Promise.all(promises)

        // 处理后端返回的ApiResponse格式
        setStats(statsResponse.data || statsResponse)
        
        // 处理任务数据（可能是分页响应）
        let tasks = []
        if (tasksResponse.data?.items) {
          tasks = tasksResponse.data.items
        } else if (tasksResponse.data && Array.isArray(tasksResponse.data)) {
          tasks = tasksResponse.data
        } else if (Array.isArray(tasksResponse)) {
          tasks = tasksResponse
        }
        setRecentTasks(tasks)
        
        // 处理报告数据（可能是分页响应）
        let reports = []
        if (reportsResponse.data?.items) {
          reports = reportsResponse.data.items
        } else if (reportsResponse.data && Array.isArray(reportsResponse.data)) {
          reports = reportsResponse.data
        } else if (Array.isArray(reportsResponse)) {
          reports = reportsResponse
        }
        setRecentReports(reports)
      } catch (err: any) {
        console.error('Failed to fetch dashboard data:', err)
        setError('加载仪表板数据失败')
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()
  }, [])

  if (loading) {
    return (
      <AppLayout>
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-48"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-white p-6 rounded-lg shadow">
                <div className="animate-pulse space-y-3">
                  <div className="h-4 bg-gray-200 rounded w-20"></div>
                  <div className="h-8 bg-gray-200 rounded w-16"></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </AppLayout>
    )
  }

  if (error) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-red-500" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">加载失败</h3>
            <p className="mt-1 text-sm text-gray-500">{error}</p>
            <div className="mt-6">
              <Button onClick={() => window.location.reload()}>
                重新加载
              </Button>
            </div>
          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <PageHeader
        title="仪表板"
        description="查看系统概览和最新动态"
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatsCard
          title="数据源"
          value={stats?.system_stats?.total_data_sources || 0}
          description="已配置的数据源"
          icon={CircleStackIcon}
          trend={{ value: 12, label: '较上月', type: 'increase' }}
        />
        <StatsCard
          title="模板"
          value={stats?.system_stats?.total_templates || 0}
          description="可用的报告模板"
          icon={DocumentTextIcon}
          trend={{ value: 8, label: '较上月', type: 'increase' }}
        />
        <StatsCard
          title="活跃任务"
          value={stats?.system_stats?.total_tasks || 0}
          description="正在运行的任务"
          icon={ClockIcon}
        />
        <StatsCard
          title="本月报告"
          value="156"
          description="已生成的报告数"
          icon={DocumentArrowDownIcon}
          trend={{ value: 23, label: '较上月', type: 'increase' }}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* 最近任务 */}
        <Card>
          <CardHeader>
            <CardTitle>最近任务</CardTitle>
            <CardDescription>查看最新的任务执行情况</CardDescription>
          </CardHeader>
          <CardContent>
            {recentTasks.length === 0 ? (
              <div className="text-center py-6 text-gray-500">
                暂无任务
              </div>
            ) : (
              <div className="space-y-4">
                {recentTasks.slice(0, 5).map((task) => (
                  <div key={task.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {task.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatRelativeTime(task.created_at)}
                      </p>
                    </div>
                    <Badge variant={task.is_active ? 'success' : 'secondary'}>
                      {task.is_active ? '运行中' : '已停止'}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-4 pt-4 border-t border-gray-200">
              <Button variant="outline" size="sm" className="w-full">
                查看全部任务
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* 最近报告 */}
        <Card>
          <CardHeader>
            <CardTitle>最近报告</CardTitle>
            <CardDescription>查看最新生成的报告</CardDescription>
          </CardHeader>
          <CardContent>
            {recentReports.length === 0 ? (
              <div className="text-center py-6 text-gray-500">
                暂无报告
              </div>
            ) : (
              <div className="space-y-4">
                {recentReports.slice(0, 5).map((report) => (
                  <div key={report.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {report.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatRelativeTime(report.created_at)}
                      </p>
                    </div>
                    <Badge 
                      variant={
                        report.status === 'completed' ? 'success' :
                        report.status === 'failed' ? 'destructive' : 'secondary'
                      }
                    >
                      {report.status === 'completed' ? '已完成' :
                       report.status === 'failed' ? '失败' : '生成中'}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-4 pt-4 border-t border-gray-200">
              <Button variant="outline" size="sm" className="w-full">
                查看全部报告
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 系统状态 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>系统概览</CardTitle>
            <CardDescription>查看系统运行状态和资源使用情况</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">CPU使用率</span>
                  <span className="text-sm text-gray-500">45%</span>
                </div>
                <Progress value={45} variant="info" />
              </div>
              
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">内存使用率</span>
                  <span className="text-sm text-gray-500">67%</span>
                </div>
                <Progress value={67} variant="warning" />
              </div>
              
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">存储使用率</span>
                  <span className="text-sm text-gray-500">34%</span>
                </div>
                <Progress value={34} variant="success" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>快速操作</CardTitle>
            <CardDescription>常用功能快速入口</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Button className="w-full justify-start" variant="outline">
                <CircleStackIcon className="mr-2 h-4 w-4" />
                添加数据源
              </Button>
              <Button className="w-full justify-start" variant="outline">
                <DocumentTextIcon className="mr-2 h-4 w-4" />
                创建模板
              </Button>
              <Button className="w-full justify-start" variant="outline">
                <ClockIcon className="mr-2 h-4 w-4" />
                新建任务
              </Button>
              <Button className="w-full justify-start" variant="outline">
                <ChartBarIcon className="mr-2 h-4 w-4" />
                查看分析
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}