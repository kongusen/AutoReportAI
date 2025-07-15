"use client"

import { useState } from 'react'
import { BarChart3, Database, FileText, Settings, Users, Mail, Bot } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { SettingsPanel } from '@/components/SettingsPanel'
import { TemplateUpload } from '@/components/TemplateUpload'
import { EnhancedDataSourceForm } from '@/components/EnhancedDataSourceForm'
import { ETLJobForm } from '@/components/ETLJobForm'
import { Button } from '@/components/ui/button'

interface DashboardStats {
  totalReports: number
  totalDataSources: number
  totalTemplates: number
  totalTasks: number
}

export function Dashboard() {
  const [activeTab, setActiveTab] = useState('overview')
  const [stats] = useState<DashboardStats>({
    totalReports: 42,
    totalDataSources: 8,
    totalTemplates: 15,
    totalTasks: 23
  })

  const menuItems = [
    { id: 'overview', label: '概览', icon: BarChart3 },
    { id: 'data-sources', label: '数据源', icon: Database },
    { id: 'templates', label: '模板', icon: FileText },
    { id: 'tasks', label: '任务', icon: Users },
    { id: 'history', label: '历史记录', icon: FileText },
    { id: 'ai-providers', label: 'AI模型', icon: Bot },
    { id: 'email', label: '邮箱配置', icon: Mail },
    { id: 'settings', label: '设置', icon: Settings }
  ]

  const renderContent = () => {
    switch (activeTab) {
      case 'overview':
        return <Overview stats={stats} />
      case 'data-sources':
        return <DataSourcesSection />
      case 'templates':
        return <TemplatesSection />
      case 'tasks':
        return <TasksSection />
      case 'history':
        return <HistorySection />
      case 'ai-providers':
        return <AIProvidersSection />
      case 'email':
        return <EmailConfigSection />
      case 'settings':
        return <SettingsPanel />
      default:
        return <Overview stats={stats} />
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="flex">
        {/* 侧边栏 */}
        <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">AutoReportAI</h1>
          </div>
          <nav className="px-4 pb-6">
            {menuItems.map((item) => {
              const Icon = item.icon
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`
                    w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors
                    ${activeTab === item.id
                      ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }
                  `}
                >
                  <Icon className="h-5 w-5" />
                  <span>{item.label}</span>
                </button>
              )
            })}
          </nav>
        </div>

        {/* 主内容区 */}
        <div className="flex-1 p-8">
          <div className="max-w-7xl mx-auto">
            {renderContent()}
          </div>
        </div>
      </div>
    </div>
  )
}

function Overview({ stats }: { stats: DashboardStats }) {
  const statCards = [
    { title: '总报告数', value: stats.totalReports, icon: FileText },
    { title: '数据源', value: stats.totalDataSources, icon: Database },
    { title: '模板', value: stats.totalTemplates, icon: FileText },
    { title: '任务', value: stats.totalTasks, icon: Users }
  ]

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">概览</h2>
      
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

      {/* 快速操作 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="border-gray-200 dark:border-gray-700">
          <CardHeader>
            <CardTitle className="text-gray-900 dark:text-gray-100">快速创建</CardTitle>
            <CardDescription className="text-gray-600 dark:text-gray-400">
              开始创建新的报告任务
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Button className="w-full bg-gray-900 hover:bg-gray-800 text-white dark:bg-gray-100 dark:hover:bg-gray-200 dark:text-gray-900">
                创建数据源
              </Button>
              <Button variant="outline" className="w-full">
                上传模板
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-700">
          <CardHeader>
            <CardTitle className="text-gray-900 dark:text-gray-100">最近活动</CardTitle>
            <CardDescription className="text-gray-600 dark:text-gray-400">
              查看最近的报告生成记录
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">销售报告</span>
                <span className="text-sm text-gray-500 dark:text-gray-400">2小时前</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">用户分析</span>
                <span className="text-sm text-gray-500 dark:text-gray-400">5小时前</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function DataSourcesSection() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">数据源管理</h2>
        <Button className="bg-gray-900 hover:bg-gray-800 text-white dark:bg-gray-100 dark:hover:bg-gray-200 dark:text-gray-900">
          新建数据源
        </Button>
      </div>
      <EnhancedDataSourceForm onSubmit={() => {}} />
    </div>
  )
}

function TemplatesSection() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">模板管理</h2>
        <Button className="bg-gray-900 hover:bg-gray-800 text-white dark:bg-gray-100 dark:hover:bg-gray-200 dark:text-gray-900">
          新建模板
        </Button>
      </div>
      <TemplateUpload onUpload={() => {}} />
    </div>
  )
}

function TasksSection() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">任务管理</h2>
        <Button className="bg-gray-900 hover:bg-gray-800 text-white dark:bg-gray-100 dark:hover:bg-gray-200 dark:text-gray-900">
          新建任务
        </Button>
      </div>
      <ETLJobForm onSubmit={() => {}} onCancel={() => {}} />
    </div>
  )
}

function AIProvidersSection() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">AI模型配置</h2>
      <Card className="border-gray-200 dark:border-gray-700">
        <CardHeader>
          <CardTitle className="text-gray-900 dark:text-gray-100">AI提供商</CardTitle>
          <CardDescription className="text-gray-600 dark:text-gray-400">
            配置和管理AI模型提供商
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600 dark:text-gray-400">AI模型配置功能开发中...</p>
        </CardContent>
      </Card>
    </div>
  )
}

function HistorySection() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">历史记录</h2>
      </div>
      <Card className="border-gray-200 dark:border-gray-700">
        <CardHeader>
          <CardTitle className="text-gray-900 dark:text-gray-100">报告生成历史</CardTitle>
          <CardDescription className="text-gray-600 dark:text-gray-400">
            查看所有报告生成记录和状态
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">历史记录功能即将上线</p>
            <Button 
              variant="outline" 
              className="mt-4"
              onClick={() => window.open('/history', '_blank')}
            >
              查看完整历史记录
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function EmailConfigSection() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">邮箱配置</h2>
      <Card className="border-gray-200 dark:border-gray-700">
        <CardHeader>
          <CardTitle className="text-gray-900 dark:text-gray-100">邮件设置</CardTitle>
          <CardDescription className="text-gray-600 dark:text-gray-400">
            配置邮件发送设置
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600 dark:text-gray-400">邮箱配置功能开发中...</p>
        </CardContent>
      </Card>
    </div>
  )
}
