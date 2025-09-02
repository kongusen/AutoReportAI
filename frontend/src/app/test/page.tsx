'use client'

import { useState, useEffect } from 'react'
import ConnectionTest from '@/components/test/ConnectionTest'
import { Header } from '@/components/layout/Header'
import { useAuthStore } from '@/features/auth/authStore'
import { useRouter } from 'next/navigation'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import {
  CogIcon,
  BeakerIcon,
  CheckBadgeIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'

export default function TestPage() {
  const { isAuthenticated, isLoading } = useAuthStore()
  const router = useRouter()
  const [showAdvanced, setShowAdvanced] = useState(false)

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <main className="py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* 页面头部 */}
          <div className="mb-8">
            <div className="flex items-center space-x-3 mb-4">
              <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg">
                <BeakerIcon className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">系统连接测试</h1>
                <p className="text-gray-600">
                  验证前后端连接和各项服务的运行状态
                </p>
              </div>
            </div>

            {/* 状态概览卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <Card className="p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <CheckBadgeIcon className="w-8 h-8 text-green-500" />
                  </div>
                  <div className="ml-4">
                    <h3 className="text-lg font-semibold text-gray-900">前端状态</h3>
                    <p className="text-green-600">正常运行</p>
                  </div>
                </div>
                <div className="mt-4 text-sm text-gray-600">
                  <div>• React 18 + Next.js 14</div>
                  <div>• TypeScript 完整支持</div>
                  <div>• WebSocket 客户端就绪</div>
                </div>
              </Card>

              <Card className="p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-yellow-100 flex items-center justify-center">
                      <div className="w-3 h-3 bg-yellow-500 rounded-full animate-pulse" />
                    </div>
                  </div>
                  <div className="ml-4">
                    <h3 className="text-lg font-semibold text-gray-900">后端状态</h3>
                    <p className="text-yellow-600">检测中...</p>
                  </div>
                </div>
                <div className="mt-4 text-sm text-gray-600">
                  <div>• FastAPI + Python</div>
                  <div>• PostgreSQL 数据库</div>
                  <div>• Redis 缓存</div>
                </div>
              </Card>

              <Card className="p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <ExclamationTriangleIcon className="w-8 h-8 text-orange-500" />
                  </div>
                  <div className="ml-4">
                    <h3 className="text-lg font-semibold text-gray-900">集成状态</h3>
                    <p className="text-orange-600">等待测试</p>
                  </div>
                </div>
                <div className="mt-4 text-sm text-gray-600">
                  <div>• API 接口连通性</div>
                  <div>• WebSocket 实时通信</div>
                  <div>• 用户认证状态</div>
                </div>
              </Card>
            </div>

            {/* 功能开关 */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-4">
                <Button
                  variant={showAdvanced ? "default" : "outline"}
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="flex items-center space-x-2"
                >
                  <CogIcon className="w-4 h-4" />
                  <span>高级选项</span>
                </Button>
              </div>

              <div className="text-sm text-gray-500">
                基于 AutoReportAI v2.0 统一接口文档
              </div>
            </div>
          </div>

          {/* 主测试组件 */}
          <ConnectionTest />

          {/* 高级选项 */}
          {showAdvanced && (
            <div className="mt-8">
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">高级测试选项</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-900">性能测试</h4>
                    <Button variant="outline" size="sm">
                      API响应时间测试
                    </Button>
                    <Button variant="outline" size="sm">
                      WebSocket延迟测试
                    </Button>
                    <Button variant="outline" size="sm">
                      并发连接测试
                    </Button>
                  </div>
                  
                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-900">集成测试</h4>
                    <Button variant="outline" size="sm">
                      完整业务流程测试
                    </Button>
                    <Button variant="outline" size="sm">
                      数据源连接测试
                    </Button>
                    <Button variant="outline" size="sm">
                      模板解析测试
                    </Button>
                  </div>
                </div>
                
                <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <div className="flex items-start space-x-3">
                    <ExclamationTriangleIcon className="w-5 h-5 text-yellow-600 mt-0.5" />
                    <div className="text-sm">
                      <p className="font-medium text-yellow-800 mb-1">注意事项</p>
                      <p className="text-yellow-700">
                        高级测试功能可能会对系统性能产生影响，建议在开发环境中使用。
                      </p>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          )}

          {/* 技术说明 */}
          <div className="mt-8">
            <Card className="p-6 bg-gray-50">
              <h3 className="text-lg font-semibold mb-4">技术架构说明</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">前端技术栈</h4>
                  <ul className="space-y-1 text-gray-600">
                    <li>• Next.js 14 + React 18</li>
                    <li>• TypeScript 完整类型支持</li>
                    <li>• Tailwind CSS 样式系统</li>
                    <li>• Zustand 状态管理</li>
                    <li>• React Hook Form 表单处理</li>
                    <li>• Axios HTTP客户端</li>
                    <li>• 原生 WebSocket API</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">后端技术栈</h4>
                  <ul className="space-y-1 text-gray-600">
                    <li>• FastAPI + Python 3.9+</li>
                    <li>• PostgreSQL 关系数据库</li>
                    <li>• Redis 缓存和会话</li>
                    <li>• JWT 用户认证</li>
                    <li>• WebSocket 实时通信</li>
                    <li>• Celery 异步任务</li>
                    <li>• Docker 容器化部署</li>
                  </ul>
                </div>
              </div>
              
              <div className="mt-6 pt-4 border-t border-gray-200">
                <h4 className="font-medium text-gray-900 mb-2">集成特性</h4>
                <div className="flex flex-wrap gap-2">
                  <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">
                    统一API响应格式
                  </span>
                  <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs">
                    实时WebSocket通知
                  </span>
                  <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-xs">
                    自动重连机制
                  </span>
                  <span className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-xs">
                    智能缓存策略
                  </span>
                  <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-xs">
                    完整错误处理
                  </span>
                  <span className="px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full text-xs">
                    类型安全保证
                  </span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </main>
    </div>
  )
}