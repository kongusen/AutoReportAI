'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Select } from '@/components/ui/Select'
import { ChartPreview } from '@/components/ui/ChartPreview'
import { APIAdapter } from '@/services/apiAdapter'
import { pipelineWebSocketAdapter, subscribeToTask, PipelineTaskUpdate } from '@/services/websocketAdapter'
import { webSocketManager } from '@/lib/websocket-client'
import toast from 'react-hot-toast'

export default function TestNewAPIPage() {
  const [loading, setLoading] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [testResults, setTestResults] = useState<any>(null)
  const [realtimeUpdates, setRealtimeUpdates] = useState<PipelineTaskUpdate[]>([])
  const [selectedTest, setSelectedTest] = useState<string>('placeholders')

  // 初始化WebSocket
  useEffect(() => {
    const initWebSocket = async () => {
      try {
        const token = localStorage.getItem('authToken')
        if (!token) {
          toast.error('请先登录')
          return
        }

        const client = webSocketManager.init({
          url: 'ws://localhost:8000/api/v1/pipeline/ws',
          token,
          debug: true
        })

        client.onConnectionChange((status) => {
          setWsConnected(status === 'connected')
          if (status === 'connected') {
            toast.success('WebSocket连接成功')
          } else if (status === 'error') {
            toast.error('WebSocket连接失败')
          }
        })

        await client.connect()

        // 监听任务更新
        pipelineWebSocketAdapter.onTaskUpdate((update) => {
          setRealtimeUpdates(prev => [update, ...prev.slice(0, 9)]) // 保留最新10条
        })

      } catch (error) {
        console.error('WebSocket初始化失败:', error)
        toast.error('WebSocket连接失败')
      }
    }

    initWebSocket()

    return () => {
      webSocketManager.disconnect()
    }
  }, [])

  // 测试占位符API
  const testPlaceholdersAPI = async () => {
    setLoading(true)
    try {
      const result = await APIAdapter.getPlaceholders(undefined, 0, 10)
      setTestResults({
        type: 'placeholders',
        success: result.success,
        data: result.data,
        error: result.error
      })

      if (result.success) {
        toast.success(`成功获取 ${result.data?.length || 0} 个占位符`)
      } else {
        APIAdapter.handleError(result.error!)
      }
    } catch (error: any) {
      console.error('占位符API测试失败:', error)
      toast.error('占位符API测试失败')
    } finally {
      setLoading(false)
    }
  }

  // 测试模板分析API
  const testTemplateAnalysisAPI = async () => {
    setLoading(true)
    try {
      // 这里需要实际的模板ID和数据源ID
      const templateId = 'test-template-id'
      const dataSourceId = 'test-datasource-id'

      const result = await APIAdapter.analyzeTemplatePlaceholders(
        templateId,
        dataSourceId,
        {
          optimizationLevel: 'enhanced',
          forceReanalyze: true
        }
      )

      setTestResults({
        type: 'template_analysis',
        success: result.success,
        data: result.data,
        progress: result.progress,
        error: result.error
      })

      if (result.success) {
        toast.success('模板分析测试成功')

        // 如果有任务ID，订阅实时更新
        if (result.data?.task_id) {
          await subscribeToTask(
            result.data.task_id,
            (update) => console.log('任务更新:', update),
            (taskId, result) => {
              console.log('任务完成:', taskId, result)
              toast.success('分析任务完成!')
            },
            (taskId, error) => {
              console.error('任务失败:', taskId, error)
              toast.error(`任务失败: ${error}`)
            }
          )
        }
      } else {
        APIAdapter.handleError(result.error!)
      }
    } catch (error: any) {
      console.error('模板分析API测试失败:', error)
      toast.error('模板分析API测试失败')
    } finally {
      setLoading(false)
    }
  }

  // 测试图表生成API
  const testChartAPI = async () => {
    setLoading(true)
    try {
      // 这里需要实际的占位符ID和数据源ID
      const placeholderId = 'test-placeholder-id'
      const dataSourceId = 'test-datasource-id'

      const result = await APIAdapter.testChartGeneration(
        placeholderId,
        dataSourceId,
        'test_with_chart'
      )

      setTestResults({
        type: 'chart',
        success: result.success,
        data: result.data,
        error: result.error
      })

      if (result.success) {
        toast.success('图表生成测试成功')
      } else {
        APIAdapter.handleError(result.error!)
      }
    } catch (error: any) {
      console.error('图表API测试失败:', error)
      toast.error('图表API测试失败')
    } finally {
      setLoading(false)
    }
  }

  // 测试WebSocket连接
  const testWebSocketConnection = async () => {
    const client = webSocketManager.getClient()
    if (!client) {
      toast.error('WebSocket客户端未初始化')
      return
    }

    if (client.isConnected) {
      toast.info('WebSocket已连接')
      console.log('连接信息:', client.getStats())
    } else {
      toast.info('正在连接WebSocket...')
      try {
        await client.connect()
      } catch (error) {
        console.error('WebSocket连接失败:', error)
        toast.error('WebSocket连接失败')
      }
    }
  }

  const testFunctions = {
    placeholders: testPlaceholdersAPI,
    template_analysis: testTemplateAnalysisAPI,
    chart: testChartAPI,
    websocket: testWebSocketConnection
  }

  const testOptions = [
    { value: 'placeholders', label: '占位符API测试' },
    { value: 'template_analysis', label: '模板分析API测试' },
    { value: 'chart', label: '图表生成API测试' },
    { value: 'websocket', label: 'WebSocket连接测试' }
  ]

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            新API接口测试页面
          </h1>
          <p className="text-gray-600">
            测试前端适配新的后端接口和WebSocket实时通知
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 测试控制面板 */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">API测试控制</h2>
                <div className="flex items-center space-x-2">
                  <Badge variant={wsConnected ? 'success' : 'destructive'}>
                    WebSocket {wsConnected ? '已连接' : '未连接'}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">选择测试类型</label>
                  <Select
                    value={selectedTest}
                    onChange={(value) => setSelectedTest(value as string)}
                    options={testOptions}
                  />
                </div>

                <Button
                  onClick={() => testFunctions[selectedTest as keyof typeof testFunctions]()}
                  disabled={loading}
                  className="w-full"
                >
                  {loading ? (
                    <>
                      <LoadingSpinner size="sm" />
                      测试中...
                    </>
                  ) : (
                    '开始测试'
                  )}
                </Button>

                <div className="text-sm text-gray-500 space-y-1">
                  <div>• 请确保后端服务正在运行</div>
                  <div>• 请确保已登录并有有效token</div>
                  <div>• WebSocket地址: ws://localhost:8000/api/v1/pipeline/ws</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 实时更新面板 */}
          <Card>
            <CardHeader>
              <h2 className="text-xl font-semibold">实时任务更新</h2>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {realtimeUpdates.length > 0 ? (
                  realtimeUpdates.map((update, index) => (
                    <div key={index} className="p-3 bg-gray-50 rounded text-sm">
                      <div className="flex justify-between items-center">
                        <span className="font-medium">{update.task_type}</span>
                        <Badge variant={
                          update.status === 'completed' ? 'success' :
                          update.status === 'failed' ? 'destructive' : 'default'
                        }>
                          {update.status}
                        </Badge>
                      </div>
                      <div className="mt-1 text-gray-600">{update.message}</div>
                      <div className="mt-1 flex justify-between text-xs text-gray-500">
                        <span>进度: {(update.progress * 100).toFixed(0)}%</span>
                        <span>{update.task_id.substring(0, 8)}...</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center text-gray-500 py-8">
                    暂无实时更新
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* 测试结果面板 */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <h2 className="text-xl font-semibold">测试结果</h2>
              </CardHeader>
              <CardContent>
                {testResults ? (
                  <div className="space-y-4">
                    <div className="flex items-center space-x-2">
                      <Badge variant={testResults.success ? 'success' : 'destructive'}>
                        {testResults.success ? '成功' : '失败'}
                      </Badge>
                      <span className="text-sm text-gray-600">类型: {testResults.type}</span>
                    </div>

                    {testResults.success ? (
                      <div>
                        {/* 占位符测试结果 */}
                        {testResults.type === 'placeholders' && testResults.data && (
                          <div className="space-y-2">
                            <h4 className="font-medium">占位符列表 ({testResults.data.length}个)</h4>
                            <div className="grid gap-2 max-h-60 overflow-y-auto">
                              {testResults.data.map((item: any, index: number) => (
                                <div key={index} className="p-2 bg-gray-50 rounded text-sm">
                                  <div className="flex justify-between">
                                    <span className="font-medium">{item.display_name}</span>
                                    <Badge variant="outline">{item.kind}</Badge>
                                  </div>
                                  <div className="text-gray-600">{item.text}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* 图表测试结果 */}
                        {testResults.type === 'chart' && testResults.data?.echartsConfig && (
                          <div>
                            <h4 className="font-medium mb-2">生成的图表</h4>
                            <ChartPreview
                              echartsConfig={testResults.data.echartsConfig}
                              chartType={testResults.data.chartType}
                              chartData={testResults.data.chartData}
                              metadata={testResults.data.metadata}
                              title="API测试图表"
                            />
                          </div>
                        )}

                        {/* 模板分析结果 */}
                        {testResults.type === 'template_analysis' && testResults.data && (
                          <div className="space-y-2">
                            <h4 className="font-medium">模板分析结果</h4>
                            {testResults.data.stats && (
                              <div className="grid grid-cols-3 gap-4 p-3 bg-blue-50 rounded">
                                <div className="text-center">
                                  <div className="text-lg font-bold text-blue-600">
                                    {testResults.data.stats.total}
                                  </div>
                                  <div className="text-xs text-gray-600">总占位符</div>
                                </div>
                                <div className="text-center">
                                  <div className="text-lg font-bold text-orange-600">
                                    {testResults.data.stats.need_reanalysis}
                                  </div>
                                  <div className="text-xs text-gray-600">需重新分析</div>
                                </div>
                                <div className="text-center">
                                  <div className="text-lg font-bold text-green-600">
                                    {testResults.data.stats.total - testResults.data.stats.need_reanalysis}
                                  </div>
                                  <div className="text-xs text-gray-600">已完成</div>
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {/* 原始数据 */}
                        <details className="mt-4">
                          <summary className="cursor-pointer text-sm font-medium text-gray-700">
                            查看原始数据
                          </summary>
                          <pre className="mt-2 p-3 bg-gray-100 rounded text-xs overflow-auto max-h-40">
                            {JSON.stringify(testResults.data, null, 2)}
                          </pre>
                        </details>
                      </div>
                    ) : (
                      <div className="text-red-600">
                        <div className="font-medium">错误信息:</div>
                        <div className="mt-1">{testResults.error?.user_friendly_message}</div>
                        <div className="text-sm mt-2">
                          错误代码: {testResults.error?.error_code}
                        </div>
                        {testResults.error?.suggestions && (
                          <div className="mt-2">
                            <div className="text-sm font-medium">建议:</div>
                            <ul className="text-sm list-disc list-inside mt-1">
                              {testResults.error.suggestions.map((suggestion: string, index: number) => (
                                <li key={index}>{suggestion}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center text-gray-500 py-8">
                    请选择测试类型并点击"开始测试"
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}