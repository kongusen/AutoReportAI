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

interface SystemPerformance {
  overall_status: string
  analysis_result: string | any
  timestamp: string
  analyzed_by: string
}

interface OptimizationSettings {
  integration_modes: Array<{
    mode: string
    name: string
    description: string
    features: string[]
  }>
  optimization_levels: Array<{
    level: string
    name: string
    description: string
  }>
  current_defaults: {
    integration_mode: string
    optimization_level: string
    max_optimization_iterations: number
    confidence_threshold: number
    enable_learning: boolean
    enable_performance_monitoring: boolean
  }
}

interface SystemHealth {
  overall_status: string
  components: Record<string, any>
  checks: string[]
  timestamp: string
}

export default function ReactAgentInsights() {
  const [performance, setPerformance] = useState<SystemPerformance | null>(null)
  const [settings, setSettings] = useState<OptimizationSettings | null>(null)
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [loading, setLoading] = useState(false)
  const [testLoading, setTestLoading] = useState(false)
  const [selectedMode, setSelectedMode] = useState('intelligent')
  const { showToast } = useToast()

  useEffect(() => {
    loadSystemData()
  }, [])

  const loadSystemData = async () => {
    setLoading(true)
    try {
      const [perfData, settingsData, healthData] = await Promise.allSettled([
        apiClient.getSystemPerformance(selectedMode),
        apiClient.getOptimizationSettings(),
        apiClient.getSystemHealth()
      ])
      
      // 处理性能数据
      if (perfData.status === 'fulfilled') {
        setPerformance(perfData.value)
      } else {
        console.error('Failed to fetch performance data:', perfData.reason)
        setPerformance(null)
      }
      
      // 处理设置数据
      if (settingsData.status === 'fulfilled') {
        setSettings(settingsData.value)
      } else {
        console.error('Failed to fetch settings data:', settingsData.reason)
        setSettings(null)
      }
      
      // 处理健康数据
      if (healthData.status === 'fulfilled') {
        setHealth(healthData.value)
      } else {
        console.error('Failed to fetch health data:', healthData.reason)
        setHealth(null)
      }
      
    } catch (error) {
      console.error('Failed to load system data:', error)
      showToast('无法获取系统洞察数据', 'error')
    } finally {
      setLoading(false)
    }
  }

  const testConfiguration = async () => {
    if (!settings) return
    
    setTestLoading(true)
    try {
      const testConfig = {
        integration_mode: selectedMode,
        optimization_level: settings.current_defaults.optimization_level,
        test_data: {
          business_intent: 'System performance test',
          data_source_context: {
            type: 'test',
            complexity: 'medium'
          }
        }
      }
      
      const result = await apiClient.testSystemConfiguration(testConfig)
      
      showToast(
        `配置测试完成: ${result.test_results?.success ? '通过' : '失败'}`, 
        result.test_results?.success ? 'success' : 'error'
      )
    } catch (error) {
      console.error('Configuration test failed:', error)
      showToast('配置测试失败', 'error')
    } finally {
      setTestLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
        return 'success'
      case 'degraded':
        return 'warning'
      case 'unhealthy':
        return 'destructive'
      default:
        return 'secondary'
    }
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
        <h2 className="text-2xl font-bold">React Agent 系统洞察</h2>
        <div className="flex gap-2">
          <select 
            value={selectedMode}
            onChange={(e) => setSelectedMode(e.target.value)}
            className="px-3 py-1 border rounded"
          >
            <option value="basic">基础模式</option>
            <option value="enhanced">增强模式</option>
            <option value="intelligent">智能模式</option>
            <option value="learning">学习模式</option>
          </select>
          <Button onClick={loadSystemData} variant="outline" size="sm">
            刷新
          </Button>
        </div>
      </div>

      {/* 系统健康状态 */}
      <Card>
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">系统健康状态</h3>
            {health && (
              <Badge variant={getStatusColor(health.overall_status)}>
                {health.overall_status?.toUpperCase()}
              </Badge>
            )}
          </div>
          
          {health ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {health.components && Object.entries(health.components).map(([mode, component]) => (
                  <div key={mode} className="border rounded p-3">
                    <div className="text-sm font-medium">{mode} 模式</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {typeof component === 'object' && component?.status 
                        ? component.status 
                        : typeof component === 'string'
                        ? component
                        : 'Unknown'}
                    </div>
                  </div>
                ))}
                {(!health.components || Object.keys(health.components).length === 0) && (
                  <div className="col-span-full text-center py-4 text-gray-500">
                    暂无系统组件信息
                  </div>
                )}
              </div>
              
              <div className="mt-4">
                <h4 className="text-sm font-medium mb-2">健康检查结果:</h4>
                <div className="space-y-1">
                  {health.checks && health.checks.length > 0 ? health.checks.map((check, index) => (
                    <div key={index} className="text-xs text-gray-600">
                      ✓ {typeof check === 'string' ? check : JSON.stringify(check)}
                    </div>
                  )) : (
                    <div className="text-xs text-gray-500">暂无健康检查结果</div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              暂无系统健康数据
            </div>
          )}
        </div>
      </Card>

      {/* 性能分析 */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">性能分析</h3>
          
          {performance ? (
            <div className="space-y-4">
              <div className="bg-gray-50 rounded p-4">
                <div className="text-sm whitespace-pre-wrap">
                  {typeof performance.analysis_result === 'string' 
                    ? performance.analysis_result
                    : typeof performance.analysis_result === 'object' 
                    ? (
                        <div className="space-y-2">
                          {performance.analysis_result.response && (
                            <div>
                              <div className="font-medium text-gray-700 mb-1">分析响应:</div>
                              <div className="text-gray-600">{performance.analysis_result.response}</div>
                            </div>
                          )}
                          {performance.analysis_result.status && (
                            <div>
                              <div className="font-medium text-gray-700 mb-1">状态:</div>
                              <Badge variant={performance.analysis_result.status === 'success' ? 'default' : 'secondary'}>
                                {performance.analysis_result.status}
                              </Badge>
                            </div>
                          )}
                          {performance.analysis_result.conversation_time && (
                            <div>
                              <div className="font-medium text-gray-700 mb-1">处理时间:</div>
                              <div className="text-gray-600">{performance.analysis_result.conversation_time}ms</div>
                            </div>
                          )}
                          {performance.analysis_result.reasoning_steps && Array.isArray(performance.analysis_result.reasoning_steps) && (
                            <div>
                              <div className="font-medium text-gray-700 mb-1">推理步骤:</div>
                              <ul className="list-disc list-inside text-gray-600 space-y-1">
                                {performance.analysis_result.reasoning_steps.map((step: any, index: number) => (
                                  <li key={index}>{typeof step === 'string' ? step : JSON.stringify(step)}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {performance.analysis_result.tool_calls && Array.isArray(performance.analysis_result.tool_calls) && (
                            <div>
                              <div className="font-medium text-gray-700 mb-1">工具调用:</div>
                              <div className="text-gray-600">{performance.analysis_result.tool_calls.length} 次调用</div>
                            </div>
                          )}
                          {performance.analysis_result.metadata && (
                            <div>
                              <div className="font-medium text-gray-700 mb-1">元数据:</div>
                              <pre className="text-xs text-gray-600 bg-white rounded p-2 overflow-x-auto">
                                {JSON.stringify(performance.analysis_result.metadata, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      )
                    : JSON.stringify(performance.analysis_result, null, 2)
                  }
                </div>
              </div>
              
              <div className="flex justify-between text-xs text-gray-500">
                <span>分析者: {performance.analyzed_by || '未知'}</span>
                <span>时间: {formatDateTime(performance.timestamp)}</span>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              暂无性能分析数据
            </div>
          )}
        </div>
      </Card>

      {/* 优化设置 */}
      <Card>
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">优化配置</h3>
            <Button 
              onClick={testConfiguration} 
              disabled={testLoading}
              size="sm"
            >
              {testLoading ? <LoadingSpinner size="sm" /> : '测试配置'}
            </Button>
          </div>
          
          {settings ? (
            <div className="space-y-6">
              {/* 集成模式 */}
              <div>
                <h4 className="font-medium mb-3">集成模式</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {settings.integration_modes && settings.integration_modes.length > 0 ? settings.integration_modes.map((mode) => (
                    <div 
                      key={mode.mode}
                      className={`border rounded p-4 cursor-pointer transition-colors ${
                        selectedMode === mode.mode ? 'border-blue-500 bg-blue-50' : ''
                      }`}
                      onClick={() => setSelectedMode(mode.mode)}
                    >
                      <div className="font-medium">{mode.name}</div>
                      <div className="text-sm text-gray-600 mt-1">{mode.description}</div>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {mode.features?.map((feature) => (
                          <Badge key={feature} variant="outline" className="text-xs">
                            {feature}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )) : (
                    <div className="col-span-full text-center py-4 text-gray-500">
                      暂无集成模式配置
                    </div>
                  )}
                </div>
              </div>

              {/* 当前配置 */}
              <div>
                <h4 className="font-medium mb-3">当前默认配置</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-gray-600">集成模式</label>
                    <div className="font-medium">{settings.current_defaults?.integration_mode}</div>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">优化级别</label>
                    <div className="font-medium">{settings.current_defaults?.optimization_level}</div>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">最大优化迭代次数</label>
                    <div className="font-medium">{settings.current_defaults?.max_optimization_iterations}</div>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">置信度阈值</label>
                    <div className="font-medium">
                      <Progress value={settings.current_defaults?.confidence_threshold * 100} className="mt-1" />
                      {(settings.current_defaults?.confidence_threshold * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
                
                <div className="flex gap-4 mt-4">
                  <div className="flex items-center gap-2">
                    <input 
                      type="checkbox" 
                      checked={settings.current_defaults?.enable_learning}
                      disabled
                      id="enable-learning"
                    />
                    <label htmlFor="enable-learning" className="text-sm">启用学习系统</label>
                  </div>
                  <div className="flex items-center gap-2">
                    <input 
                      type="checkbox" 
                      checked={settings.current_defaults?.enable_performance_monitoring}
                      disabled
                      id="enable-monitoring"
                    />
                    <label htmlFor="enable-monitoring" className="text-sm">启用性能监控</label>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              暂无优化配置数据
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}