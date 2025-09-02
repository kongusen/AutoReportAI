'use client'

import { useState, useEffect } from 'react'
import { useWebSocket } from '@/hooks/useWebSocket'
import { apiClient } from '@/lib/api-client'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import {
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  WifiIcon,
  ServerIcon,
  CircleStackIcon
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

interface TestResult {
  name: string
  status: 'pending' | 'running' | 'success' | 'error'
  message?: string
  data?: any
  duration?: number
}

export function ConnectionTest() {
  const [tests, setTests] = useState<TestResult[]>([])
  const [isRunning, setIsRunning] = useState(false)
  
  const { 
    status: wsStatus, 
    isConnected: wsConnected, 
    connectionInfo,
    connect: wsConnect,
    disconnect: wsDisconnect,
    send: wsSend
  } = useWebSocket({
    autoConnect: false,
    debug: true,
    onConnectionChange: (status, error) => {
      updateTestResult('WebSocket连接', 
        status === 'connected' ? 'success' : 
        status === 'error' ? 'error' : 'running',
        error?.message || `状态: ${status}`
      )
    }
  })

  const initialTests: TestResult[] = [
    { name: 'API健康检查', status: 'pending' },
    { name: 'WebSocket连接', status: 'pending' },
    { name: '用户认证', status: 'pending' },
    { name: '数据源API', status: 'pending' },
    { name: '模板API', status: 'pending' },
    { name: '仪表板数据', status: 'pending' }
  ]

  useEffect(() => {
    setTests(initialTests)
  }, [])

  const updateTestResult = (name: string, status: TestResult['status'], message?: string, data?: any, duration?: number) => {
    setTests(prev => prev.map(test => 
      test.name === name 
        ? { ...test, status, message, data, duration }
        : test
    ))
  }

  const runSingleTest = async (testName: string): Promise<void> => {
    const startTime = Date.now()
    updateTestResult(testName, 'running')

    try {
      switch (testName) {
        case 'API健康检查':
          const health = await apiClient.getHealthStatus()
          updateTestResult(testName, 'success', `系统状态: ${health.status}`, health, Date.now() - startTime)
          break

        case 'WebSocket连接':
          await wsConnect()
          // 状态更新通过onConnectionChange处理
          break

        case '用户认证':
          if (!apiClient.isAuthenticated()) {
            updateTestResult(testName, 'error', '未登录', null, Date.now() - startTime)
            return
          }
          const user = await apiClient.getCurrentUser()
          updateTestResult(testName, 'success', `用户: ${user.username}`, user, Date.now() - startTime)
          break

        case '数据源API':
          const dataSources = await apiClient.getDataSources({ page: 1, size: 1 })
          updateTestResult(testName, 'success', `数据源总数: ${dataSources.total}`, dataSources, Date.now() - startTime)
          break

        case '模板API':
          const templates = await apiClient.getTemplates({ page: 1, size: 1 })
          updateTestResult(testName, 'success', `模板总数: ${templates.total}`, templates, Date.now() - startTime)
          break

        case '仪表板数据':
          const stats = await apiClient.getDashboardStats()
          updateTestResult(testName, 'success', 
            `用户: ${stats.total_users}, 报告: ${stats.total_reports}`, 
            stats, Date.now() - startTime)
          break

        default:
          updateTestResult(testName, 'error', '未知测试', null, Date.now() - startTime)
      }
    } catch (error: any) {
      updateTestResult(testName, 'error', error.message || '测试失败', error, Date.now() - startTime)
    }
  }

  const runAllTests = async () => {
    setIsRunning(true)
    setTests(initialTests)
    
    try {
      for (const test of initialTests) {
        await runSingleTest(test.name)
        // 短暂延迟，避免过快的请求
        await new Promise(resolve => setTimeout(resolve, 500))
      }
      toast.success('所有测试完成')
    } catch (error) {
      toast.error('测试过程中发生错误')
    } finally {
      setIsRunning(false)
    }
  }

  const testWebSocketMessage = () => {
    if (wsConnected) {
      wsSend({
        type: 'ping' as any,
        data: { test: true, timestamp: new Date().toISOString() }
      })
      toast.success('WebSocket测试消息已发送')
    } else {
      toast.error('WebSocket未连接')
    }
  }

  const getStatusIcon = (status: TestResult['status']) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon className="w-5 h-5 text-green-500" />
      case 'error':
        return <XCircleIcon className="w-5 h-5 text-red-500" />
      case 'running':
        return <LoadingSpinner size="sm" />
      default:
        return <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
    }
  }

  const getStatusBadge = (status: TestResult['status']) => {
    switch (status) {
      case 'success':
        return <Badge variant="success" size="sm">成功</Badge>
      case 'error':
        return <Badge variant="destructive" size="sm">失败</Badge>
      case 'running':
        return <Badge variant="secondary" size="sm">运行中</Badge>
      default:
        return <Badge variant="secondary" size="sm">待测试</Badge>
    }
  }

  const formatDuration = (duration?: number) => {
    if (!duration) return ''
    return `(${duration}ms)`
  }

  const successCount = tests.filter(t => t.status === 'success').length
  const errorCount = tests.filter(t => t.status === 'error').length

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">连接测试</h2>
          <p className="text-gray-600 mt-1">测试前后端API和WebSocket连接状态</p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="text-sm text-gray-500">
            成功: {successCount} | 失败: {errorCount}
          </div>
          <Button
            onClick={runAllTests}
            disabled={isRunning}
            className="flex items-center space-x-2"
          >
            <ArrowPathIcon className="w-4 h-4" />
            <span>{isRunning ? '测试中...' : '运行测试'}</span>
          </Button>
        </div>
      </div>

      {/* WebSocket状态卡片 */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center space-x-2">
            <WifiIcon className="w-5 h-5" />
            <span>WebSocket连接状态</span>
          </h3>
          <div className="flex items-center space-x-2">
            {getStatusBadge(wsConnected ? 'success' : 'error')}
            <span className="text-sm text-gray-600">{wsStatus}</span>
          </div>
        </div>
        
        {connectionInfo && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 text-sm">
            <div>
              <span className="text-gray-500">会话ID:</span>
              <div className="font-mono text-xs truncate" title={connectionInfo.sessionId}>
                {connectionInfo.sessionId?.slice(-8) || 'N/A'}
              </div>
            </div>
            <div>
              <span className="text-gray-500">消息:</span>
              <div>↑{connectionInfo.messagesSent} ↓{connectionInfo.messagesReceived}</div>
            </div>
            <div>
              <span className="text-gray-500">订阅:</span>
              <div>{connectionInfo.subscriptions?.length || 0} 个频道</div>
            </div>
            <div>
              <span className="text-gray-500">运行时间:</span>
              <div>{connectionInfo.uptime ? Math.floor(connectionInfo.uptime / 1000) + 's' : '0s'}</div>
            </div>
          </div>
        )}

        <div className="flex space-x-2">
          <Button size="sm" onClick={wsConnect} disabled={wsConnected || wsStatus === 'connecting'}>
            连接
          </Button>
          <Button size="sm" variant="outline" onClick={wsDisconnect} disabled={!wsConnected}>
            断开
          </Button>
          <Button size="sm" variant="outline" onClick={testWebSocketMessage} disabled={!wsConnected}>
            发送测试消息
          </Button>
        </div>
      </Card>

      {/* 测试结果列表 */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
          <ServerIcon className="w-5 h-5" />
          <span>API连接测试</span>
        </h3>

        <div className="space-y-3">
          {tests.map((test) => (
            <div
              key={test.name}
              className="flex items-center justify-between p-4 rounded-lg border hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center space-x-3">
                {getStatusIcon(test.status)}
                <div>
                  <div className="font-medium">{test.name}</div>
                  {test.message && (
                    <div className="text-sm text-gray-600">
                      {test.message} {formatDuration(test.duration)}
                    </div>
                  )}
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                {getStatusBadge(test.status)}
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => runSingleTest(test.name)}
                  disabled={test.status === 'running' || isRunning}
                >
                  重试
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* 详细信息面板 */}
      {tests.some(t => t.data) && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
            <CircleStackIcon className="w-5 h-5" />
            <span>测试详细信息</span>
          </h3>
          
          <div className="space-y-4">
            {tests.filter(t => t.data).map((test) => (
              <details key={test.name} className="border rounded-lg">
                <summary className="p-3 cursor-pointer hover:bg-gray-50 font-medium">
                  {test.name} - 响应数据
                </summary>
                <div className="p-3 border-t bg-gray-50">
                  <pre className="text-xs overflow-auto max-h-48 bg-white p-2 rounded border">
                    {JSON.stringify(test.data, null, 2)}
                  </pre>
                </div>
              </details>
            ))}
          </div>
        </Card>
      )}

      {/* 使用说明 */}
      <Card className="p-6 bg-blue-50 border-blue-200">
        <h3 className="text-lg font-semibold mb-2 text-blue-900">使用说明</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• <strong>API健康检查</strong>: 检查后端服务是否正常运行</li>
          <li>• <strong>WebSocket连接</strong>: 测试实时通信连接状态</li>
          <li>• <strong>用户认证</strong>: 验证当前用户登录状态</li>
          <li>• <strong>数据源API</strong>: 测试数据源管理接口</li>
          <li>• <strong>模板API</strong>: 测试模板管理接口</li>
          <li>• <strong>仪表板数据</strong>: 测试仪表板统计数据接口</li>
        </ul>
      </Card>
    </div>
  )
}

export default ConnectionTest