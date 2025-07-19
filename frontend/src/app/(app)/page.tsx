'use client'

import { useEffect, useMemo } from 'react'
import { 
  Database, 
  FileText, 
  Users, 
  Activity, 
  TrendingUp, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  Plus,
  ArrowRight
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { ExportProgressTracker } from '@/components/forms/ExportProgressTracker'
import { useAppState } from '@/lib/context/hooks'
import api from '@/lib/api'
import { useI18n } from '@/lib/i18n'
import Link from 'next/link'

export default function HomePage() {
  const { t } = useI18n()
  const { 
    templates, 
    dataSources, 
    tasks, 
    reportHistory, 
    ui 
  } = useAppState()

  // Computed dashboard stats using state management
  const stats = useMemo(() => {
    const activeTasks = tasks.activeTasks.length
    const successfulReports = reportHistory.reportHistory.filter(report => report.status === 'success').length
    const successRate = reportHistory.reportHistory.length > 0 
      ? Math.round((successfulReports / reportHistory.reportHistory.length) * 100) 
      : 0

    return {
      totalReports: reportHistory.reportHistory.length,
      totalDataSources: dataSources.dataSources.length,
      totalTemplates: templates.templates.length,
      totalTasks: tasks.tasks.length,
      activeTasks,
      successRate,
      recentReports: reportHistory.recentReports.slice(0, 5),
      taskStats: {
        total: tasks.tasks.length,
        active: activeTasks,
        inactive: tasks.tasks.length - activeTasks
      }
    }
  }, [
    templates.templates,
    dataSources.dataSources,
    tasks.tasks,
    tasks.activeTasks,
    reportHistory.reportHistory,
    reportHistory.recentReports
  ])

  const recentTasks = useMemo(() => {
    return tasks.tasks.slice(0, 3)
  }, [tasks.tasks])

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      ui.setLoading(true)
      ui.clearError()

      // 尝试获取各种数据，如果失败则使用默认值
      const results = await Promise.allSettled([
        api.get('/data-sources').catch(() => ({ data: [] })),
        api.get('/templates').catch(() => ({ data: [] })),
        api.get('/tasks').catch(() => ({ data: [] })),
        api.get('/history').catch(() => ({ data: [] }))
      ])

      const [dataSourcesRes, templatesRes, tasksRes, historyRes] = results.map(result => 
        result.status === 'fulfilled' ? result.value : { data: [] }
      )

      const dataSourcesData = Array.isArray(dataSourcesRes.data) ? dataSourcesRes.data : (dataSourcesRes.data?.items || [])
      const templatesData = Array.isArray(templatesRes.data) ? templatesRes.data : (templatesRes.data?.items || [])
      const tasksData = Array.isArray(tasksRes.data) ? tasksRes.data : (tasksRes.data?.items || [])
      const historyData = Array.isArray(historyRes.data) ? historyRes.data : (historyRes.data?.items || [])

      // Update state management
      dataSources.setDataSources(dataSourcesData)
      templates.setTemplates(templatesData)
      tasks.setTasks(tasksData)
      reportHistory.setReportHistory(historyData)
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
      // 设置默认空数据而不是错误
      dataSources.setDataSources([])
      templates.setTemplates([])
      tasks.setTasks([])
      reportHistory.setReportHistory([])
    } finally {
      ui.setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failure':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      case 'in_progress':
        return <Clock className="h-4 w-4 text-blue-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 text-green-800'
      case 'failure':
        return 'bg-red-100 text-red-800'
      case 'in_progress':
        return 'bg-blue-100 text-blue-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (ui.loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Loading dashboard...</div>
      </div>
    )
  }

  if (ui.error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-red-500">{ui.error}</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-gray-600">Welcome back! Here's what's happening with your reports.</p>
        </div>
        <div className="flex space-x-2">
          <Link href="/tasks">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Task
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Reports</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalReports}</div>
            <p className="text-xs text-muted-foreground">
              Generated reports
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Tasks</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.activeTasks}</div>
            <p className="text-xs text-muted-foreground">
              of {stats.totalTasks} total tasks
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.successRate}%</div>
            <Progress value={stats.successRate} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Data Sources</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalDataSources}</div>
            <p className="text-xs text-muted-foreground">
              Connected sources
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Activity */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Recent Activity</CardTitle>
              <Link href="/history">
                <Button variant="outline" size="sm">
                  View All
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats.recentReports.length > 0 ? (
                stats.recentReports.map((report) => (
                  <div key={report.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(report.status)}
                      <div>
                        <p className="text-sm font-medium">Task #{report.task_id}</p>
                        <p className="text-xs text-gray-500">
                          {new Date(report.generated_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <Badge className={getStatusColor(report.status)}>
                      {report.status}
                    </Badge>
                  </div>
                ))
              ) : (
                <div className="text-center py-8">
                  <Activity className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">No recent activity</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Link href="/data-sources">
              <Button className="w-full justify-start" variant="outline">
                <Database className="mr-2 h-4 w-4" />
                Add Data Source
              </Button>
            </Link>
            <Link href="/templates">
              <Button className="w-full justify-start" variant="outline">
                <FileText className="mr-2 h-4 w-4" />
                Upload Template
              </Button>
            </Link>
            <Link href="/tasks">
              <Button className="w-full justify-start" variant="outline">
                <Plus className="mr-2 h-4 w-4" />
                Create Task
              </Button>
            </Link>
            <Link href="/data-export">
              <Button className="w-full justify-start" variant="outline">
                <ArrowRight className="mr-2 h-4 w-4" />
                Data Export
              </Button>
            </Link>
            <Link href="/settings">
              <Button className="w-full justify-start" variant="outline">
                <Users className="mr-2 h-4 w-4" />
                Settings
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Export Progress Tracker */}
      <ExportProgressTracker className="lg:col-span-1" />

      {/* Recent Tasks */}
      {recentTasks.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Recent Tasks</CardTitle>
              <Link href="/tasks">
                <Button variant="outline" size="sm">
                  Manage Tasks
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {recentTasks.map((task) => (
                <div key={task.id} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium truncate">{task.name}</h3>
                    <Badge variant={task.is_active ? 'default' : 'secondary'}>
                      {task.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                  {task.last_execution && (
                    <p className="text-xs text-gray-500">
                      Last run: {new Date(task.last_execution).toLocaleString()}
                    </p>
                  )}
                  {task.next_execution && (
                    <p className="text-xs text-gray-500">
                      Next run: {new Date(task.next_execution).toLocaleString()}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}