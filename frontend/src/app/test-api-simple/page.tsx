'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Select } from '@/components/ui/Select'
import toast from 'react-hot-toast'

export default function TestAPISimplePage() {
  const [loading, setLoading] = useState(false)
  const [testResults, setTestResults] = useState<any>(null)
  const [selectedTest, setSelectedTest] = useState<string>('health')

  // 测试健康检查API - 不需要认证
  const testHealthAPI = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/health', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      })

      const data = await response.json()

      setTestResults({
        type: 'health',
        success: response.ok,
        data: data,
        status: response.status
      })

      if (response.ok) {
        toast.success('健康检查通过')
      } else {
        toast.error('健康检查失败')
      }
    } catch (error: any) {
      console.error('健康检查失败:', error)
      setTestResults({
        type: 'health',
        success: false,
        error: error.message,
        data: null
      })
      toast.error('健康检查异常')
    } finally {
      setLoading(false)
    }
  }

  // 测试后端版本信息API - 通常不需要认证
  const testVersionAPI = async () => {
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/version', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      })

      const data = await response.json()

      setTestResults({
        type: 'version',
        success: response.ok,
        data: data,
        status: response.status
      })

      if (response.ok) {
        toast.success('版本信息获取成功')
      } else {
        toast.error('版本信息获取失败')
      }
    } catch (error: any) {
      console.error('版本API测试失败:', error)
      setTestResults({
        type: 'version',
        success: false,
        error: error.message,
        data: null
      })
      toast.error('版本API测试失败')
    } finally {
      setLoading(false)
    }
  }

  // 测试后端API响应格式 - 使用健康检查端点
  const testAPIResponseFormat = async () => {
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/v1/health', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      })

      const data = await response.json()

      // 检查是否符合新的APIResponse格式
      const hasCorrectFormat = data && typeof data === 'object' &&
        'success' in data && 'message' in data

      setTestResults({
        type: 'api_format',
        success: response.ok && hasCorrectFormat,
        data: data,
        status: response.status,
        formatCheck: {
          hasSuccess: 'success' in data,
          hasMessage: 'message' in data,
          hasData: 'data' in data,
          isCorrectFormat: hasCorrectFormat
        }
      })

      if (response.ok && hasCorrectFormat) {
        toast.success('API格式检查通过')
      } else {
        toast.error('API格式检查失败')
      }
    } catch (error: any) {
      console.error('API格式测试失败:', error)
      setTestResults({
        type: 'api_format',
        success: false,
        error: error.message,
        data: null
      })
      toast.error('API格式测试失败')
    } finally {
      setLoading(false)
    }
  }

  // 测试图表类型支持API - 通常不需要认证
  const testChartTypesAPI = async () => {
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/v1/chart-test/chart-types', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      })

      const data = await response.json()

      setTestResults({
        type: 'chart_types',
        success: response.ok,
        data: data,
        status: response.status
      })

      if (response.ok) {
        toast.success(`获取图表类型成功 (${data.data?.chart_types?.length || 0}种)`)
      } else {
        toast.error('获取图表类型失败')
      }
    } catch (error: any) {
      console.error('图表类型API测试失败:', error)
      setTestResults({
        type: 'chart_types',
        success: false,
        error: error.message,
        data: null
      })
      toast.error('图表类型API测试失败')
    } finally {
      setLoading(false)
    }
  }

  const testFunctions = {
    health: testHealthAPI,
    version: testVersionAPI,
    api_format: testAPIResponseFormat,
    chart_types: testChartTypesAPI
  }

  const testOptions = [
    { value: 'health', label: '前端健康检查' },
    { value: 'version', label: '后端版本信息' },
    { value: 'api_format', label: 'API响应格式检查' },
    { value: 'chart_types', label: '图表类型支持' }
  ]

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            API接口简单测试
          </h1>
          <p className="text-gray-600">
            无需登录的基础API测试，验证后端服务状态和API格式
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 测试控制面板 */}
          <Card>
            <CardHeader>
              <h2 className="text-xl font-semibold">简单测试控制</h2>
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
                  <div>• 这些测试不需要登录认证</div>
                  <div>• 后端地址: http://localhost:8000</div>
                  <div>• 确保后端服务正在运行</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 服务状态面板 */}
          <Card>
            <CardHeader>
              <h2 className="text-xl font-semibold">服务连接状态</h2>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm">前端服务</span>
                  <Badge variant="success">运行中</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm">后端API</span>
                  <Badge variant={testResults?.type === 'health' && testResults?.success ? 'success' : 'secondary'}>
                    {testResults?.type === 'health' ? (testResults?.success ? '正常' : '异常') : '未测试'}
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm">API格式</span>
                  <Badge variant={testResults?.type === 'api_format' && testResults?.success ? 'success' : 'secondary'}>
                    {testResults?.type === 'api_format' ? (testResults?.success ? '兼容' : '不兼容') : '未测试'}
                  </Badge>
                </div>

                <div className="pt-3 border-t text-xs text-gray-500">
                  <div>测试时间: {new Date().toLocaleTimeString()}</div>
                  <div>前端版本: {process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0'}</div>
                </div>
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
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Badge variant={testResults.success ? 'success' : 'destructive'}>
                          {testResults.success ? '成功' : '失败'}
                        </Badge>
                        <span className="text-sm text-gray-600">
                          类型: {testResults.type} | 状态码: {testResults.status || 'N/A'}
                        </span>
                      </div>
                      <span className="text-xs text-gray-500">
                        {new Date().toLocaleString()}
                      </span>
                    </div>

                    {testResults.success ? (
                      <div>
                        {/* 健康检查结果 */}
                        {testResults.type === 'health' && (
                          <div className="p-3 bg-green-50 rounded">
                            <div className="text-sm font-medium text-green-800">前端服务正常运行</div>
                            <div className="text-xs text-green-600 mt-1">
                              Next.js应用运行正常，可以处理API请求
                            </div>
                          </div>
                        )}

                        {/* 版本信息结果 */}
                        {testResults.type === 'version' && testResults.data && (
                          <div className="space-y-2">
                            <h4 className="font-medium">后端版本信息</h4>
                            <div className="grid grid-cols-2 gap-2 text-sm">
                              <div>版本: {testResults.data.version || 'N/A'}</div>
                              <div>环境: {testResults.data.environment || 'N/A'}</div>
                              <div>API版本: {testResults.data.api_version || 'N/A'}</div>
                              <div>构建时间: {testResults.data.build_time || 'N/A'}</div>
                            </div>
                          </div>
                        )}

                        {/* API格式检查结果 */}
                        {testResults.type === 'api_format' && testResults.formatCheck && (
                          <div className="space-y-2">
                            <h4 className="font-medium">API响应格式检查</h4>
                            <div className="grid grid-cols-2 gap-2 text-sm">
                              <div className="flex justify-between">
                                <span>包含success字段:</span>
                                <Badge variant={testResults.formatCheck.hasSuccess ? 'success' : 'destructive'}>
                                  {testResults.formatCheck.hasSuccess ? '是' : '否'}
                                </Badge>
                              </div>
                              <div className="flex justify-between">
                                <span>包含message字段:</span>
                                <Badge variant={testResults.formatCheck.hasMessage ? 'success' : 'destructive'}>
                                  {testResults.formatCheck.hasMessage ? '是' : '否'}
                                </Badge>
                              </div>
                              <div className="flex justify-between">
                                <span>包含data字段:</span>
                                <Badge variant={testResults.formatCheck.hasData ? 'success' : 'secondary'}>
                                  {testResults.formatCheck.hasData ? '是' : '否'}
                                </Badge>
                              </div>
                              <div className="flex justify-between">
                                <span>格式兼容:</span>
                                <Badge variant={testResults.formatCheck.isCorrectFormat ? 'success' : 'destructive'}>
                                  {testResults.formatCheck.isCorrectFormat ? '是' : '否'}
                                </Badge>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* 图表类型结果 */}
                        {testResults.type === 'chart_types' && testResults.data?.data?.chart_types && (
                          <div className="space-y-2">
                            <h4 className="font-medium">
                              支持的图表类型 ({testResults.data.data.chart_types.length}种)
                            </h4>
                            <div className="grid grid-cols-2 gap-2">
                              {testResults.data.data.chart_types.map((chart: any, index: number) => (
                                <div key={index} className="p-2 bg-gray-50 rounded text-sm">
                                  <div className="font-medium">{chart.name}</div>
                                  <div className="text-xs text-gray-600">{chart.key}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* 原始数据 */}
                        <details className="mt-4">
                          <summary className="cursor-pointer text-sm font-medium text-gray-700">
                            查看原始响应数据
                          </summary>
                          <pre className="mt-2 p-3 bg-gray-100 rounded text-xs overflow-auto max-h-40">
                            {JSON.stringify(testResults.data, null, 2)}
                          </pre>
                        </details>
                      </div>
                    ) : (
                      <div className="text-red-600">
                        <div className="font-medium">测试失败</div>
                        <div className="mt-1 text-sm">
                          {testResults.error || '请检查后端服务是否正在运行'}
                        </div>
                        <div className="mt-2 p-3 bg-red-50 rounded text-sm">
                          <div className="font-medium">常见问题排查:</div>
                          <ul className="list-disc list-inside mt-1 space-y-1">
                            <li>确认后端服务已启动 (python -m uvicorn main:app --reload)</li>
                            <li>检查端口8000是否被占用</li>
                            <li>验证后端健康检查端点: http://localhost:8000/api/v1/health</li>
                            <li>查看浏览器控制台是否有CORS错误</li>
                          </ul>
                        </div>
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