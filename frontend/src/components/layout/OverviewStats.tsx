'use client'

import { useEffect, useState } from 'react'
import { Database, FileText, Users } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import api from '@/lib/api'
import { useI18n } from '@/lib/i18n'

interface DashboardStats {
  totalReports: number
  totalDataSources: number
  totalTemplates: number
  totalTasks: number
  recentReports: Array<{
    id: number
    task_name: string
    generated_at: string
    status: string
  }>
}

export function OverviewStats() {
  const { t } = useI18n()
  const [stats, setStats] = useState<DashboardStats>({
    totalReports: 0,
    totalDataSources: 0,
    totalTemplates: 0,
    totalTasks: 0,
    recentReports: []
  })

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const [reportsRes, dataSourcesRes, templatesRes, tasksRes, historyRes] = await Promise.all([
        api.get('/reports'),
        api.get('/data-sources'),
        api.get('/templates'),
        api.get('/tasks'),
        api.get('/history')
      ])
      setStats({
        totalReports: Array.isArray(reportsRes.data) ? reportsRes.data.length : (reportsRes.data.items?.length || 0),
        totalDataSources: Array.isArray(dataSourcesRes.data) ? dataSourcesRes.data.length : (dataSourcesRes.data.items?.length || 0),
        totalTemplates: Array.isArray(templatesRes.data) ? templatesRes.data.length : (templatesRes.data.items?.length || 0),
        totalTasks: Array.isArray(tasksRes.data) ? tasksRes.data.length : (tasksRes.data.items?.length || 0),
        recentReports: Array.isArray(historyRes.data) ? historyRes.data.slice(0, 5) : (historyRes.data.items?.slice(0, 5) || [])
      })
    } catch (error) {
      console.error('Error fetching stats:', error)
    }
  }

  const statCards = [
    { title: t('overview.totalReports'), value: stats.totalReports, icon: FileText },
    { title: t('overview.dataSources'), value: stats.totalDataSources, icon: Database },
    { title: t('overview.templates'), value: stats.totalTemplates, icon: FileText },
    { title: t('overview.tasks'), value: stats.totalTasks, icon: Users }
  ]

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">{t('overview.title')}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.title} className="border-gray-200 dark:border-gray-700">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  {stat.title}
                </CardTitle>
                <Icon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {stat.value}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="border-gray-200 dark:border-gray-700">
          <CardHeader>
            <CardTitle className="text-gray-900 dark:text-gray-100">{t('overview.quickCreate')}</CardTitle>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              开始创建新的报告任务
            </p>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Button 
                className="w-full bg-gray-900 hover:bg-gray-800 text-white dark:bg-gray-100 dark:hover:bg-gray-200 dark:text-gray-900"
                onClick={() => window.location.href = '/data-sources'}
              >
                {t('overview.createDataSource')}
              </Button>
              <Button 
                variant="outline" 
                className="w-full"
                onClick={() => window.location.href = '/templates'}
              >
                {t('overview.uploadTemplate')}
              </Button>
            </div>
          </CardContent>
        </Card>
        <Card className="border-gray-200 dark:border-gray-700">
          <CardHeader>
            <CardTitle className="text-gray-900 dark:text-gray-100">{t('overview.recentActivity')}</CardTitle>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              查看最近的报告生成记录
            </p>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats.recentReports.length > 0 ? (
                stats.recentReports.map((report) => (
                  <div key={report.id} className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">{report.task_name}</span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {new Date(report.generated_at).toLocaleString()}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">暂无最近活动</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
