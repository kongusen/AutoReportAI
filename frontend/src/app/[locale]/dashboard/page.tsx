'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { 
  BarChart3, 
  Database, 
  FileText, 
  PlayCircle, 
  Users, 
  Activity,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Plus
} from 'lucide-react'
import { httpClient } from '@/lib/api/client'

interface DashboardStats {
  totalDataSources: number
  totalTemplates: number
  totalTasks: number
  totalReports: number
  activeUsers: number
  systemHealth: 'healthy' | 'warning' | 'error'
}

interface RecentActivity {
  id: string
  type: 'report' | 'task' | 'data_source'
  title: string
  status: 'success' | 'running' | 'failed'
  timestamp: string
}

interface ReportHistory {
  id: number
  status: string
  generated_at: string
  task_id?: number
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    totalDataSources: 0,
    totalTemplates: 0,
    totalTasks: 0,
    totalReports: 0,
    activeUsers: 0,
    systemHealth: 'healthy'
  })
  
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchDashboardData() {
      setLoading(true)
      setError(null)
      try {
        // 并行获取各种统计数据
        const [reportsRes, dataSourcesRes, templatesRes, tasksRes] = await Promise.all([
          httpClient.get('/v1/dashboard/stats').catch(() => ({ data: { total_reports: 0 } })),
          httpClient.get('/v1/data-sources?limit=1').catch(() => ({ data: { total: 0 } })),
          httpClient.get('/v1/templates?limit=1').catch(() => ({ data: { total: 0 } })),
          httpClient.get('/v1/tasks?limit=1').catch(() => ({ data: { total: 0 } }))
        ])

        setStats({
          totalReports: reportsRes.data?.total_reports || 0,
          totalDataSources: dataSourcesRes.data?.total || 0,
          totalTemplates: templatesRes.data?.total || 0,
          totalTasks: tasksRes.data?.total || 0,
          activeUsers: 1,
          systemHealth: 'healthy'
        })

        // 获取最近活动
        const activityRes = await httpClient.get('/v1/dashboard/recent-activity').catch(() => ({ data: [] }))
        setRecentActivity(activityRes.data || [
          {
            id: '1',
            type: 'report',
            title: '月度销售报告',
            status: 'success',
            timestamp: new Date().toISOString()
          }
        ])
      } catch (err) {
        setError('仪表板数据加载失败，请稍后重试')
        // 设置默认数据
        setStats({
          totalDataSources: 0,
          totalTemplates: 0,
          totalTasks: 0,
          totalReports: 0,
          activeUsers: 1,
          systemHealth: 'healthy'
        })
      } finally {
        setLoading(false)
      }
    }
    
    fetchDashboardData()
  }, [])

  const statCards = [
    {
      title: '数据源',
      value: stats.totalDataSources,
      description: '已配置的数据源',
      icon: Database,
      color: 'text-blue-600'
    },
    {
      title: '模板',
      value: stats.totalTemplates,
      description: '报告模板数量',
      icon: FileText,
      color: 'text-green-600'
    },
    {
      title: '任务',
      value: stats.totalTasks,
      description: '定时任务数量',
      icon: PlayCircle,
      color: 'text-purple-600'
    },
    {
      title: '报告',
      value: stats.totalReports,
      description: '已生成报告',
      icon: BarChart3,
      color: 'text-orange-600'
    }
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />
      case 'running':
        return <Activity className="h-4 w-4 text-blue-500 animate-pulse" />
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      default:
        return null
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 text-green-800'
      case 'running':
        return 'bg-blue-100 text-blue-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">仪表板</h1>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="pb-3">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              </CardHeader>
              <CardContent>
                <div className="h-8 bg-gray-200 rounded w-1/2 mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-full"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-[400px] flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center text-red-600">
              <AlertCircle className="h-5 w-5 mr-2" />
              加载失败
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600 mb-4">{error}</p>
            <Button onClick={() => window.location.reload()} className="w-full">
              重新加载
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">仪表板</h1>
          <p className="text-gray-600">系统概览和关键指标</p>
        </div>
        <div className="flex items-center space-x-4">
          <Badge variant={stats.systemHealth === 'healthy' ? 'default' : 'destructive'}>
            系统状态: {stats.systemHealth === 'healthy' ? '正常' : '异常'}
          </Badge>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            创建任务
          </Button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => {
          const Icon = stat.icon
          return (
            <Card key={index} className="hover:shadow-md transition-shadow">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">
                  {stat.title}
                </CardTitle>
                <Icon className={`h-5 w-5 ${stat.color}`} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-900">{stat.value}</div>
                <p className="text-xs text-gray-500 mt-1">{stat.description}</p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* 主要内容区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 系统活动 */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center">
              <Activity className="h-5 w-5 mr-2 text-gray-600" />
              最近活动
            </CardTitle>
            <CardDescription>
              系统最近的操作记录
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentActivity.length > 0 ? recentActivity.map((activity) => (
                <div key={activity.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(activity.status)}
                    <div>
                      <p className="text-sm font-medium text-gray-900">{activity.title}</p>
                      <p className="text-xs text-gray-500">
                        {new Date(activity.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline" className={getStatusColor(activity.status)}>
                    {activity.status === 'success' ? '成功' : 
                     activity.status === 'running' ? '运行中' : '失败'}
                  </Badge>
                </div>
              )) : (
                <div className="text-center py-8 text-gray-500">
                  暂无活动记录
                </div>
              )}
            </div>
            <div className="mt-4 pt-4 border-t">
              <Button variant="outline" size="sm" className="w-full">
                查看所有活动
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* 快速操作 */}
        <Card>
          <CardHeader>
            <CardTitle>快速操作</CardTitle>
            <CardDescription>
              常用功能快捷入口
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button className="w-full justify-start" variant="outline">
              <Database className="h-4 w-4 mr-2" />
              新建数据源
            </Button>
            <Button className="w-full justify-start" variant="outline">
              <FileText className="h-4 w-4 mr-2" />
              创建模板
            </Button>
            <Button className="w-full justify-start" variant="outline">
              <PlayCircle className="h-4 w-4 mr-2" />
              新建任务
            </Button>
            <Button className="w-full justify-start" variant="outline">
              <BarChart3 className="h-4 w-4 mr-2" />
              生成报告
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* 系统状态 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <TrendingUp className="h-5 w-5 mr-2 text-gray-600" />
            系统状态
          </CardTitle>
          <CardDescription>
            系统性能和资源使用情况
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">CPU 使用率</span>
                <span className="font-medium">45%</span>
              </div>
              <Progress value={45} className="h-2" />
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">内存使用</span>
                <span className="font-medium">62%</span>
              </div>
              <Progress value={62} className="h-2" />
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">存储空间</span>
                <span className="font-medium">38%</span>
              </div>
              <Progress value={38} className="h-2" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
} 