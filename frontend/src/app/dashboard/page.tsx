'use client'

import { useEffect, useState, useCallback } from 'react'
import { 
  CircleStackIcon,
  DocumentTextIcon, 
  ClockIcon,
  DocumentArrowDownIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  CpuChipIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { PageHeader } from '@/components/layout/PageHeader'
import { useWebSocket } from '@/hooks/useWebSocket'
import { SystemService, TaskService, ReportService } from '@/services/apiService'
import { formatRelativeTime, formatNumber } from '@/utils'
import { DashboardStats, Task, Report } from '@/types'
import { apiClient } from '@/lib/api-client'

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
  const [systemHealth, setSystemHealth] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [refreshing, setRefreshing] = useState(false)

  // WebSocket集成用于实时更新
  const { isConnected, subscribe, messages } = useWebSocket({
    autoConnect: true,
    channels: ['dashboard', 'tasks', 'reports'],
    onMessage: handleRealtimeUpdate
  })

  // 处理WebSocket实时消息
  function handleRealtimeUpdate(message: any) {
    if (message.type === 'task_status_changed' || message.type === 'task_completed') {
      // 实时更新任务状态
      setRecentTasks(prev => 
        prev.map(task => 
          task.id === message.data.task_id 
            ? { ...task, ...message.data }
            : task
        )
      )
    } else if (message.type === 'report_generated' || message.type === 'report_completed') {
      // 实时更新报告状态
      setRecentReports(prev => 
        prev.map(report => 
          report.id === message.data.report_id 
            ? { ...report, ...message.data }
            : report
        )
      )
    } else if (message.type === 'dashboard_stats_updated') {
      // 实时更新仪表板统计
      setStats(prev => prev ? { ...prev, ...message.data } : null)
    }
  }

  // 使用新的API服务获取数据
  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true)
      setError('')
      
      // 使用新的API服务并行获取数据，包含React Agent系统健康状态
      const [statsData, tasksData, reportsData, healthData] = await Promise.allSettled([
        SystemService.getDashboardStats(),
        TaskService.list({ page: 1, size: 5 }),
        ReportService.list({ page: 1, size: 5 }),
        apiClient.getSystemHealth()
      ])

      // 处理仪表板统计
      if (statsData.status === 'fulfilled') {
        setStats(statsData.value)
      } else {
        console.error('Failed to fetch dashboard stats:', statsData.reason)
      }
        
      // 处理任务数据
      if (tasksData.status === 'fulfilled') {
        setRecentTasks(tasksData.value.items || [])
      } else {
        console.error('Failed to fetch tasks:', tasksData.reason)
        setRecentTasks([])
      }
        
      // 处理报告数据
      if (reportsData.status === 'fulfilled') {
        setRecentReports(reportsData.value.items || [])
      } else {
        console.error('Failed to fetch reports:', reportsData.reason)
        setRecentReports([])
      }

      // 处理React Agent系统健康数据
      if (healthData.status === 'fulfilled') {
        setSystemHealth(healthData.value)
      } else {
        console.error('Failed to fetch system health:', healthData.reason)
        // 设置默认值以防止页面崩溃
        setSystemHealth({
          overall_status: 'unknown',
          components: {},
          checks: []
        })
      }

    } catch (err: any) {
      console.error('Failed to fetch dashboard data:', err)
      setError('加载仪表板数据失败')
    } finally {
      setLoading(false)
    }
  }, [])

  // 手动刷新功能
  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    await fetchDashboardData()
    setRefreshing(false)
  }, [fetchDashboardData])

  useEffect(() => {
    fetchDashboardData()
  }, [fetchDashboardData])

  if (loading) {
    return (
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
    )
  }

  if (error) {
    return (
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
    )
  }

  return (
    <>
      <PageHeader
        title="仪表板"
        description={
          <div className="flex items-center space-x-4">
            <span>查看系统概览和最新动态</span>
            <div className="flex items-center space-x-2 text-sm">
              <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-gray-400'}`} />
              <span className="text-gray-500">
                {isConnected ? '实时数据已连接' : '离线模式'}
              </span>
            </div>
          </div>
        }
        actions={
          <Button 
            onClick={handleRefresh} 
            variant="outline" 
            size="sm"
            disabled={loading || refreshing}
          >
            <ArrowPathIcon className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? '刷新中...' : '刷新'}
          </Button>
        }
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

      {/* React Agent 系统状态 */}
      {systemHealth && (
        <Card className="mb-8">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center">
                  <CpuChipIcon className="mr-2 h-5 w-5" />
                  React Agent 系统状态
                </CardTitle>
                <CardDescription>智能代理系统运行状态</CardDescription>
              </div>
              <Badge 
                variant={
                  systemHealth.overall_status === 'healthy' ? 'default' :
                  systemHealth.overall_status === 'degraded' ? 'warning' : 'destructive'
                }
              >
                {systemHealth.overall_status?.toUpperCase()}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {Object.entries(systemHealth.components).map(([mode, component]: [string, any]) => (
                <div key={mode} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex-1">
                    <p className="text-sm font-medium">{mode} 模式</p>
                    <p className="text-xs text-gray-500">
                      {component?.status || 'unknown'}
                    </p>
                  </div>
                  <Badge 
                    size="sm"
                    variant={component?.status === 'healthy' ? 'default' : 'secondary'}
                  >
                    {component?.status === 'healthy' ? '正常' : '待机'}
                  </Badge>
                </div>
              ))}
            </div>
            <div className="mt-4 flex justify-between items-center">
              <div className="text-sm text-gray-500">
                最后更新: {systemHealth.timestamp ? new Date(systemHealth.timestamp).toLocaleString() : '未知'}
              </div>
              <Button variant="outline" size="sm">
                <ChartBarIcon className="mr-2 h-4 w-4" />
                查看详细洞察
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

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

      {/* 快速操作 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
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
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  )
}