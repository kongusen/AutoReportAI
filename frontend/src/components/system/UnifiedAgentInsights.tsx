'use client'

import React, { useState, useEffect } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { apiClient } from '@/lib/api-client'
import { useToast } from '@/hooks/useToast'
import { formatDateTime } from '@/utils'
import {
  CpuChipIcon,
  CogIcon,
  CloudIcon,
  ChartBarIcon,
  PlayIcon,
  PauseIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline'

interface AgentArchitectureStatus {
  unified_facade: {
    status: string
    supported_categories: string[]
    active_services: number
  }
  service_orchestrator: {
    status: string
    active_tasks: number
    total_tasks_processed: number
  }
  agent_controller: {
    status: string
    registered_tools: string[]
    context_managers: number
  }
  task_execution: {
    recent_tasks: Array<{
      task_id: string
      type: string
      status: string
      created_at: string
      completion_time?: number
    }>
    success_rate: number
    average_execution_time: number
  }
}

interface SystemHealth {
  overall_status: string
  components: {
    unified_facade: string
    service_orchestrator: string
    agent_controller: string
    llm_services: string
    tool_chain: string
  }
  last_checked: string
}

interface PerformanceMetrics {
  task_throughput: {
    per_hour: number
    per_day: number
  }
  resource_usage: {
    memory_usage: number
    cpu_usage: number
    token_usage: number
  }
  error_rates: {
    template_analysis: number
    sql_generation: number
    placeholder_analysis: number
  }
  last_updated: string
}

export default function UnifiedAgentInsights() {
  const [architectureStatus, setArchitectureStatus] = useState<AgentArchitectureStatus | null>(null)
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null)
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics | null>(null)
  const [loading, setLoading] = useState(false)
  const [testLoading, setTestLoading] = useState(false)
  const [selectedTaskType, setSelectedTaskType] = useState('template_analysis')
  const { showToast } = useToast()

  useEffect(() => {
    loadSystemData()
    // Set up polling for real-time updates
    const interval = setInterval(loadSystemData, 30000) // Update every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const loadSystemData = async () => {
    setLoading(true)
    try {
      const [architectureData, healthData, performanceData] = await Promise.allSettled([
        apiClient.getUnifiedAIArchitectureStatus(),
        apiClient.getUnifiedAISystemHealth(),
        apiClient.getUnifiedAIPerformanceMetrics()
      ])
      
      // 处理架构状态数据
      if (architectureData.status === 'fulfilled') {
        setArchitectureStatus(architectureData.value)
      } else {
        console.error('Failed to fetch architecture data:', architectureData.reason)
        setArchitectureStatus(null)
      }
      
      // 处理健康状态数据
      if (healthData.status === 'fulfilled') {
        setSystemHealth(healthData.value)
      } else {
        console.error('Failed to fetch health data:', healthData.reason)
        setSystemHealth(null)
      }
      
      // 处理性能数据
      if (performanceData.status === 'fulfilled') {
        setPerformanceMetrics(performanceData.value)
      } else {
        console.error('Failed to fetch performance data:', performanceData.reason)
        setPerformanceMetrics(null)
      }
      
    } catch (error) {
      console.error('Failed to load system data:', error)
      showToast('无法获取系统洞察数据', 'error')
    } finally {
      setLoading(false)
    }
  }

  const testAgentTask = async () => {
    setTestLoading(true)
    try {
      const testResult = await apiClient.testUnifiedAITask(selectedTaskType)
      
      if (testResult.status === 'completed' || testResult.success) {
        showToast(
          `${selectedTaskType}任务测试成功`,
          'success'
        )
      } else {
        showToast(
          `${selectedTaskType}任务测试失败`,
          'error'
        )
      }
      
      // 刷新数据以显示最新状态
      loadSystemData()
      
    } catch (error) {
      console.error('Task test failed:', error)
      showToast('任务测试失败', 'error')
    } finally {
      setTestLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'completed':
        return 'success'
      case 'degraded':
      case 'running':
        return 'warning'
      case 'unhealthy':
      case 'failed':
        return 'destructive'
      default:
        return 'secondary'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'completed':
        return <PlayIcon className="w-4 h-4" />
      case 'running':
        return <LoadingSpinner size="sm" />
      case 'degraded':
        return <ExclamationTriangleIcon className="w-4 h-4" />
      default:
        return <PauseIcon className="w-4 h-4" />
    }
  }

  if (loading && !architectureStatus) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <CpuChipIcon className="w-8 h-8 text-blue-600" />
          <h2 className="text-2xl font-bold">统一Agent架构</h2>
          <Badge variant="default" className="ml-2">自主智能Agent</Badge>
        </div>
        <div className="flex gap-2">
          <select 
            value={selectedTaskType}
            onChange={(e) => setSelectedTaskType(e.target.value)}
            className="px-3 py-1 border rounded text-sm"
          >
            <option value="template_analysis">模板分析</option>
            <option value="placeholder_analysis">占位符分析</option>
            <option value="sql_generation">SQL生成</option>
            <option value="workflow_orchestration">工作流编排</option>
          </select>
          <Button onClick={testAgentTask} variant="outline" size="sm" disabled={testLoading}>
            {testLoading ? <LoadingSpinner size="sm" /> : '测试任务'}
          </Button>
          <Button onClick={loadSystemData} variant="outline" size="sm">
            刷新
          </Button>
        </div>
      </div>

      {/* 系统健康状态 */}
      <Card>
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <CloudIcon className="w-5 h-5 text-green-600" />
              <h3 className="text-lg font-semibold">架构组件状态</h3>
            </div>
            {systemHealth && (
              <Badge variant={getStatusColor(systemHealth.overall_status)}>
                {systemHealth.overall_status?.toUpperCase()}
              </Badge>
            )}
          </div>
          
          {systemHealth ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(systemHealth.components).map(([component, status]) => (
                  <div key={component} className="border rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(status)}
                        <span className="text-sm font-medium capitalize">
                          {component.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <Badge variant={getStatusColor(status)} size="sm">
                        {status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="text-xs text-gray-500 text-right">
                最后检查: {formatDateTime(systemHealth.last_checked)}
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              暂无系统健康数据
            </div>
          )}
        </div>
      </Card>

      {/* 架构状态详情 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <div className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <CogIcon className="w-5 h-5 text-blue-600" />
              <h3 className="text-lg font-semibold">统一AI门面</h3>
            </div>
            
            {architectureStatus ? (
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">状态</span>
                  <Badge variant={getStatusColor(architectureStatus.unified_facade.status)}>
                    {architectureStatus.unified_facade.status}
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">活跃服务</span>
                  <span className="font-medium">{architectureStatus.unified_facade.active_services}</span>
                </div>
                <div>
                  <div className="text-sm text-gray-600 mb-2">支持的任务类型</div>
                  <div className="flex flex-wrap gap-1">
                    {architectureStatus.unified_facade.supported_categories.map((category) => (
                      <Badge key={category} variant="outline" className="text-xs">
                        {category}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-4 text-gray-500">暂无数据</div>
            )}
          </div>
        </Card>

        <Card>
          <div className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <ChartBarIcon className="w-5 h-5 text-green-600" />
              <h3 className="text-lg font-semibold">任务执行统计</h3>
            </div>
            
            {architectureStatus ? (
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">活跃任务</span>
                  <span className="font-medium">{architectureStatus.service_orchestrator.active_tasks}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">总处理任务</span>
                  <span className="font-medium">{architectureStatus.service_orchestrator.total_tasks_processed}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">成功率</span>
                  <span className="font-medium">{architectureStatus.task_execution.success_rate}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">平均执行时间</span>
                  <span className="font-medium">{architectureStatus.task_execution.average_execution_time}s</span>
                </div>
              </div>
            ) : (
              <div className="text-center py-4 text-gray-500">暂无数据</div>
            )}
          </div>
        </Card>
      </div>

      {/* 性能指标 */}
      {performanceMetrics && (
        <Card>
          <div className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <ChartBarIcon className="w-5 h-5 text-purple-600" />
              <h3 className="text-lg font-semibold">性能指标</h3>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-blue-50 rounded-lg p-4">
                <div className="text-sm text-blue-600 mb-1">任务吞吐量</div>
                <div className="text-xl font-bold text-blue-800">{performanceMetrics.task_throughput.per_hour}/h</div>
                <div className="text-xs text-blue-600">{performanceMetrics.task_throughput.per_day}/日</div>
              </div>
              
              <div className="bg-green-50 rounded-lg p-4">
                <div className="text-sm text-green-600 mb-1">内存使用率</div>
                <div className="text-xl font-bold text-green-800">{performanceMetrics.resource_usage.memory_usage}%</div>
                <Progress value={performanceMetrics.resource_usage.memory_usage} className="mt-2 h-2" />
              </div>
              
              <div className="bg-yellow-50 rounded-lg p-4">
                <div className="text-sm text-yellow-600 mb-1">CPU使用率</div>
                <div className="text-xl font-bold text-yellow-800">{performanceMetrics.resource_usage.cpu_usage}%</div>
                <Progress value={performanceMetrics.resource_usage.cpu_usage} className="mt-2 h-2" />
              </div>
              
              <div className="bg-purple-50 rounded-lg p-4">
                <div className="text-sm text-purple-600 mb-1">Token使用量</div>
                <div className="text-xl font-bold text-purple-800">{performanceMetrics.resource_usage.token_usage.toLocaleString()}</div>
                <div className="text-xs text-purple-600">今日累计</div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* 最近任务 */}
      <Card>
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <InformationCircleIcon className="w-5 h-5 text-gray-600" />
            <h3 className="text-lg font-semibold">最近任务执行</h3>
          </div>
          
          {architectureStatus ? (
            <div className="space-y-3">
              {architectureStatus.task_execution.recent_tasks.map((task) => (
                <div key={task.task_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(task.status)}
                    <div>
                      <div className="font-medium text-sm">{task.task_id}</div>
                      <div className="text-xs text-gray-500">{task.type}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge variant={getStatusColor(task.status)} size="sm">
                      {task.status}
                    </Badge>
                    <div className="text-xs text-gray-500 mt-1">
                      {task.completion_time ? `${task.completion_time}s` : '运行中'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              暂无任务数据
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}