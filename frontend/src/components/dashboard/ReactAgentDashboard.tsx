'use client'

import React, { useState, useEffect } from 'react'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Progress } from '@/components/ui/Progress'
import { apiClient } from '@/lib/api-client'
import { useToast } from '@/hooks/useToast'

interface AgentStats {
  total_agents: number
  active_agents: number
  processing_tasks: number
  completed_today: number
  success_rate: number
}

interface SystemMetrics {
  performance_score: number
  response_time: number
  memory_usage: number
  cpu_usage: number
  queue_size: number
}

export default function ReactAgentDashboard() {
  const [agentStats, setAgentStats] = useState<AgentStats | null>(null)
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null)
  const [systemHealth, setSystemHealth] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const { toast } = useToast()

  useEffect(() => {
    loadDashboardData()
    
    // 设置自动刷新
    const interval = setInterval(loadDashboardData, 30000) // 30秒刷新一次
    return () => clearInterval(interval)
  }, [])

  const loadDashboardData = async () => {
    try {
      const [healthData, perfData] = await Promise.all([
        apiClient.getSystemHealth(),
        apiClient.getSystemPerformance('intelligent')
      ])
      
      setSystemHealth(healthData)
      
      // 模拟一些指标数据（真实应用中应该从后端获取）
      setAgentStats({
        total_agents: 3,
        active_agents: 3,
        processing_tasks: 2,
        completed_today: 15,
        success_rate: 95.2
      })
      
      setSystemMetrics({
        performance_score: 87,
        response_time: 245,
        memory_usage: 68,
        cpu_usage: 34,
        queue_size: 3
      })
      
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
      toast({
        title: '加载失败',
        description: '无法获取React Agent仪表板数据',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const getHealthStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
        return 'text-green-600 bg-green-100'
      case 'degraded':
        return 'text-yellow-600 bg-yellow-100'
      case 'unhealthy':
        return 'text-red-600 bg-red-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  const getPerformanceColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">React Agent 仪表板</h2>
          <p className="text-gray-600">智能代理系统实时监控</p>
        </div>
        <div className="flex items-center space-x-2">
          {systemHealth && (
            <Badge className={getHealthStatusColor(systemHealth.overall_status)}>
              系统状态: {systemHealth.overall_status?.toUpperCase()}
            </Badge>
          )}
        </div>
      </div>

      {/* 核心指标概览 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {agentStats && (
          <>
            <Card>
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">活跃代理</p>
                    <p className="text-2xl font-bold text-green-600">
                      {agentStats.active_agents}
                    </p>
                  </div>
                  <div className="text-xs text-gray-500">
                    总共 {agentStats.total_agents} 个
                  </div>
                </div>
              </div>
            </Card>

            <Card>
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">处理中任务</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {agentStats.processing_tasks}
                    </p>
                  </div>
                  <div className="text-xs text-gray-500">
                    实时队列
                  </div>
                </div>
              </div>
            </Card>

            <Card>
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">今日完成</p>
                    <p className="text-2xl font-bold text-purple-600">
                      {agentStats.completed_today}
                    </p>
                  </div>
                  <div className="text-xs text-gray-500">
                    任务数
                  </div>
                </div>
              </div>
            </Card>

            <Card>
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">成功率</p>
                    <p className="text-2xl font-bold text-green-600">
                      {agentStats.success_rate}%
                    </p>
                  </div>
                  <div className="text-xs text-gray-500">
                    24小时平均
                  </div>
                </div>
              </div>
            </Card>
          </>
        )}
      </div>

      {/* 系统性能指标 */}
      {systemMetrics && (
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold mb-4">系统性能指标</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium">整体性能评分</span>
                  <span className={`font-bold ${getPerformanceColor(systemMetrics.performance_score)}`}>
                    {systemMetrics.performance_score}/100
                  </span>
                </div>
                <Progress value={systemMetrics.performance_score} className="h-2" />
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium">平均响应时间</span>
                  <span className="font-bold text-blue-600">
                    {systemMetrics.response_time}ms
                  </span>
                </div>
                <Progress value={(1000 - systemMetrics.response_time) / 10} className="h-2" />
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium">内存使用率</span>
                  <span className="font-bold text-orange-600">
                    {systemMetrics.memory_usage}%
                  </span>
                </div>
                <Progress value={systemMetrics.memory_usage} className="h-2" />
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium">CPU使用率</span>
                  <span className="font-bold text-green-600">
                    {systemMetrics.cpu_usage}%
                  </span>
                </div>
                <Progress value={systemMetrics.cpu_usage} className="h-2" />
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium">任务队列大小</span>
                  <span className="font-bold text-purple-600">
                    {systemMetrics.queue_size}
                  </span>
                </div>
                <Progress value={(10 - systemMetrics.queue_size) * 10} className="h-2" />
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* 代理状态详情 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold">工作流编排代理</h4>
              <Badge variant="default">运行中</Badge>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">负载:</span>
                <span>中等</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">今日处理:</span>
                <span>8 个任务</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">成功率:</span>
                <span className="text-green-600">100%</span>
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold">任务协调代理</h4>
              <Badge variant="default">运行中</Badge>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">负载:</span>
                <span>低</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">今日处理:</span>
                <span>4 个任务</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">成功率:</span>
                <span className="text-green-600">97%</span>
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold">上下文感知代理</h4>
              <Badge variant="default">运行中</Badge>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">负载:</span>
                <span>高</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">今日处理:</span>
                <span>12 个任务</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">成功率:</span>
                <span className="text-yellow-600">89%</span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* 最近活动 */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">最近活动</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b">
              <div>
                <p className="font-medium">模板分析完成</p>
                <p className="text-sm text-gray-600">工作流编排代理处理了模板 #1234 的占位符分析</p>
              </div>
              <div className="text-sm text-gray-500">2 分钟前</div>
            </div>
            <div className="flex items-center justify-between py-2 border-b">
              <div>
                <p className="font-medium">报告生成任务启动</p>
                <p className="text-sm text-gray-600">任务协调代理开始处理月度销售报告生成</p>
              </div>
              <div className="text-sm text-gray-500">5 分钟前</div>
            </div>
            <div className="flex items-center justify-between py-2 border-b">
              <div>
                <p className="font-medium">系统性能优化</p>
                <p className="text-sm text-gray-600">上下文感知代理完成了智能缓存优化</p>
              </div>
              <div className="text-sm text-gray-500">15 分钟前</div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}