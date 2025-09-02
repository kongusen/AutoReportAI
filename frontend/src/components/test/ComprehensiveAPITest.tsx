'use client'

/**
 * 综合API测试组件 - 测试优化后的所有API接口和WebSocket功能
 */

import React, { useState, useEffect } from 'react'
import { 
  SystemService, 
  AuthService, 
  DataSourceService, 
  TemplateService,
  ReportService,
  TaskService 
} from '@/services/apiService'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useAuthStore } from '@/features/auth/authStore'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { 
  CheckCircleIcon, 
  XCircleIcon, 
  ClockIcon,
  WifiIcon,
  BeakerIcon
} from '@heroicons/react/24/outline'

interface TestResult {
  service: string
  method: string
  status: 'pending' | 'running' | 'success' | 'error'
  message?: string
  duration?: number
  data?: any
}

export function ComprehensiveAPITest() {
  const [tests, setTests] = useState<TestResult[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [webSocketTests, setWebSocketTests] = useState<any[]>([])
  const { user, isAuthenticated } = useAuthStore()

  // WebSocket集成测试
  const { 
    isConnected, 
    connectionInfo, 
    messages, 
    send: sendMessage,
    subscribe,
    unsubscribe 
  } = useWebSocket({
    autoConnect: true,
    channels: ['test', 'system', 'notifications'],
    onMessage: handleWebSocketMessage,
    debug: true
  })

  function handleWebSocketMessage(message: any) {
    setWebSocketTests(prev => [...prev.slice(-9), {
      timestamp: new Date(),
      type: message.type,
      data: message.data,
      channel: message.channel
    }])
  }

  // 初始化测试项目
  const initializeTests = () => {
    const testCases: Omit<TestResult, 'status' | 'duration'>[] = [
      // 系统服务测试
      { service: 'SystemService', method: 'getHealth' },
      { service: 'SystemService', method: 'getDashboardStats' },
      { service: 'SystemService', method: 'getDetailedHealth' },
      
      // 认证服务测试
      { service: 'AuthService', method: 'getCurrentUser' },
      
      // 数据源服务测试
      { service: 'DataSourceService', method: 'list' },
      
      // 模板服务测试
      { service: 'TemplateService', method: 'list' },
      
      // 报告服务测试
      { service: 'ReportService', method: 'list' },
      
      // 任务服务测试
      { service: 'TaskService', method: 'list' },
    ]

    setTests(testCases.map(test => ({ ...test, status: 'pending' })))
  }

  useEffect(() => {
    initializeTests()
  }, [])

  // 更新测试结果
  const updateTestResult = (service: string, method: string, updates: Partial<TestResult>) => {
    setTests(prev => 
      prev.map(test => 
        test.service === service && test.method === method
          ? { ...test, ...updates }
          : test
      )
    )
  }

  // 运行单个测试
  const runSingleTest = async (test: TestResult) => {
    const startTime = Date.now()
    updateTestResult(test.service, test.method, { status: 'running' })

    try {
      let result: any

      switch (test.service) {
        case 'SystemService':
          if (test.method === 'getHealth') {
            result = await SystemService.getHealth()
          } else if (test.method === 'getDashboardStats') {
            result = await SystemService.getDashboardStats()
          } else if (test.method === 'getDetailedHealth') {
            result = await SystemService.getDetailedHealth()
          }
          break

        case 'AuthService':
          if (test.method === 'getCurrentUser') {
            result = await AuthService.getCurrentUser()
          }
          break

        case 'DataSourceService':
          if (test.method === 'list') {
            result = await DataSourceService.list({ page: 1, size: 3 })
          }
          break

        case 'TemplateService':
          if (test.method === 'list') {
            result = await TemplateService.list({ page: 1, size: 3 })
          }
          break

        case 'ReportService':
          if (test.method === 'list') {
            result = await ReportService.list({ page: 1, size: 3 })
          }
          break

        case 'TaskService':
          if (test.method === 'list') {
            result = await TaskService.list({ page: 1, size: 3 })
          }
          break
      }

      updateTestResult(test.service, test.method, {
        status: 'success',
        message: '测试通过',
        duration: Date.now() - startTime,
        data: result
      })

    } catch (error: any) {
      updateTestResult(test.service, test.method, {
        status: 'error',
        message: error.message || '测试失败',
        duration: Date.now() - startTime
      })
    }
  }

  // 运行所有测试
  const runAllTests = async () => {
    if (!isAuthenticated) {
      alert('请先登录以运行完整测试')
      return
    }

    setIsRunning(true)
    initializeTests()

    // 等待测试初始化
    setTimeout(async () => {
      for (const test of tests) {
        await runSingleTest(test)
        // 间隔200ms避免过快请求
        await new Promise(resolve => setTimeout(resolve, 200))
      }
      setIsRunning(false)
    }, 100)
  }

  // WebSocket测试功能
  const testWebSocketMessage = () => {
    if (isConnected) {
      sendMessage({
        type: 'test_message',
        data: {
          test: true,
          timestamp: new Date().toISOString(),
          message: '前端WebSocket测试消息'
        }
      })
    }
  }

  const testChannelSubscription = async () => {
    const testChannel = 'test_channel_' + Date.now()
    await subscribe(testChannel)
    
    setTimeout(async () => {
      await unsubscribe(testChannel)
    }, 5000)
  }

  // 计算测试统计
  const stats = {
    total: tests.length,
    success: tests.filter(t => t.status === 'success').length,
    error: tests.filter(t => t.status === 'error').length,
    running: tests.filter(t => t.status === 'running').length,
    pending: tests.filter(t => t.status === 'pending').length
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
        return <ClockIcon className="w-5 h-5 text-gray-400" />
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
        return <Badge variant="outline" size="sm">待测试</Badge>
    }
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* 测试概览 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <BeakerIcon className="w-6 h-6" />
            <span>API接口优化测试</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between mb-4">
            <div className="grid grid-cols-5 gap-4 text-sm">
              <div className="text-center">
                <div className="text-2xl font-bold">{stats.total}</div>
                <div className="text-gray-500">总计</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{stats.success}</div>
                <div className="text-gray-500">成功</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{stats.error}</div>
                <div className="text-gray-500">失败</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{stats.running}</div>
                <div className="text-gray-500">运行中</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-600">{stats.pending}</div>
                <div className="text-gray-500">待测试</div>
              </div>
            </div>
            
            <Button 
              onClick={runAllTests} 
              disabled={isRunning}
              className="ml-4"
            >
              {isRunning ? '测试中...' : '运行所有测试'}
            </Button>
          </div>

          {/* 用户状态 */}
          <div className="text-sm text-gray-600">
            用户状态: {isAuthenticated ? `已登录 (${user?.username})` : '未登录'}
          </div>
        </CardContent>
      </Card>

      {/* WebSocket状态 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <WifiIcon className="w-6 h-6" />
            <span>WebSocket连接测试</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium mb-3">连接信息</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>状态:</span>
                  <span className={isConnected ? 'text-green-600' : 'text-red-600'}>
                    {isConnected ? '已连接' : '已断开'}
                  </span>
                </div>
                {connectionInfo && (
                  <>
                    <div className="flex justify-between">
                      <span>会话ID:</span>
                      <span className="font-mono text-xs">
                        {connectionInfo.sessionId?.slice(-8)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>运行时间:</span>
                      <span>{Math.floor((connectionInfo.uptime || 0) / 1000)}s</span>
                    </div>
                    <div className="flex justify-between">
                      <span>消息统计:</span>
                      <span>↑{connectionInfo.messagesSent} ↓{connectionInfo.messagesReceived}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>订阅频道:</span>
                      <span>{connectionInfo.subscriptions?.length || 0}个</span>
                    </div>
                  </>
                )}
              </div>
            </div>

            <div>
              <h4 className="font-medium mb-3">测试操作</h4>
              <div className="space-y-2">
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={testWebSocketMessage}
                  disabled={!isConnected}
                  className="w-full"
                >
                  发送测试消息
                </Button>
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={testChannelSubscription}
                  disabled={!isConnected}
                  className="w-full"
                >
                  测试频道订阅
                </Button>
              </div>
            </div>
          </div>

          {/* 最近消息 */}
          {webSocketTests.length > 0 && (
            <div className="mt-6">
              <h4 className="font-medium mb-3">最近WebSocket消息</h4>
              <div className="bg-gray-50 rounded-lg p-3 max-h-32 overflow-y-auto">
                <div className="space-y-1 text-xs font-mono">
                  {webSocketTests.slice(-5).map((msg, index) => (
                    <div key={index} className="text-gray-700">
                      <span className="text-gray-500">
                        {msg.timestamp.toLocaleTimeString()}
                      </span>
                      {' '}
                      <span className="text-blue-600">{msg.type}</span>
                      {msg.channel && (
                        <span className="text-purple-600"> @{msg.channel}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* API测试结果 */}
      <Card>
        <CardHeader>
          <CardTitle>API测试结果</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {tests.map((test, index) => (
              <div 
                key={index}
                className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50"
              >
                <div className="flex items-center space-x-3">
                  {getStatusIcon(test.status)}
                  <div>
                    <div className="font-medium">
                      {test.service}.{test.method}()
                    </div>
                    {test.message && (
                      <div className="text-sm text-gray-600">
                        {test.message}
                        {test.duration && ` (${test.duration}ms)`}
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  {getStatusBadge(test.status)}
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => runSingleTest(test)}
                    disabled={test.status === 'running' || isRunning}
                  >
                    重试
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 使用说明 */}
      <Card>
        <CardHeader>
          <CardTitle>测试说明</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm space-y-2">
            <p><strong>优化功能测试项目:</strong></p>
            <ul className="list-disc list-inside space-y-1 text-gray-600">
              <li>✅ 新的API服务层架构 (SystemService, AuthService等)</li>
              <li>✅ 统一的错误处理和用户提示</li>
              <li>✅ 类型安全的API调用</li>
              <li>✅ WebSocket实时通信和状态监控</li>
              <li>✅ 智能缓存和性能优化</li>
              <li>✅ 实时连接状态指示</li>
              <li>✅ 频道订阅和消息处理</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default ComprehensiveAPITest