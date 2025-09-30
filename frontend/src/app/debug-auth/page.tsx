'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import toast from 'react-hot-toast'

export default function DebugAuthPage() {
  const [authInfo, setAuthInfo] = useState<any>(null)
  const [testToken, setTestToken] = useState('')

  useEffect(() => {
    checkAuthStatus()
  }, [])

  const checkAuthStatus = () => {
    if (typeof window === 'undefined') return

    const token = localStorage.getItem('authToken')
    const user = localStorage.getItem('user')

    let parsedUser = null
    try {
      if (user) {
        parsedUser = JSON.parse(user)
      }
    } catch (e) {
      console.error('解析用户信息失败:', e)
    }

    setAuthInfo({
      hasToken: !!token,
      tokenLength: token?.length || 0,
      tokenPreview: token ? `${token.substring(0, 10)}...${token.substring(token.length - 10)}` : null,
      hasUser: !!user,
      user: parsedUser,
      timestamp: new Date().toLocaleString()
    })
  }

  const testTokenValidity = async () => {
    const token = localStorage.getItem('authToken')
    if (!token) {
      toast.error('未找到认证token')
      return
    }

    try {
      const response = await fetch('http://localhost:8000/api/v1/users/me', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      const data = await response.json()

      if (response.ok) {
        toast.success('Token验证成功')
        setAuthInfo((prev: any) => ({
          ...prev,
          tokenValid: true,
          userInfo: data.data || data
        }))
      } else {
        toast.error(`Token验证失败: ${data.detail || data.message}`)
        setAuthInfo((prev: any) => ({
          ...prev,
          tokenValid: false,
          tokenError: data.detail || data.message
        }))
      }
    } catch (error: any) {
      toast.error(`Token验证异常: ${error.message}`)
      setAuthInfo((prev: any) => ({
        ...prev,
        tokenValid: false,
        tokenError: error.message
      }))
    }
  }

  const clearAuthData = () => {
    localStorage.removeItem('authToken')
    localStorage.removeItem('user')
    toast.success('认证数据已清除')
    checkAuthStatus()
  }

  const setTestTokenToStorage = () => {
    if (!testToken.trim()) {
      toast.error('请输入有效的token')
      return
    }

    localStorage.setItem('authToken', testToken.trim())
    toast.success('测试token已设置')
    checkAuthStatus()
  }

  const tryQuickLogin = async () => {
    try {
      const formData = new URLSearchParams()
      formData.append('username', 'admin')
      formData.append('password', 'password')

      const response = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
      })

      const data = await response.json()

      if (response.ok && data.success) {
        const token = data.data?.access_token || data.access_token
        const user = data.data?.user || data.user

        if (token) {
          localStorage.setItem('authToken', token)
          if (user) {
            localStorage.setItem('user', JSON.stringify(user))
          }
          toast.success('快速登录成功')
          checkAuthStatus()
        } else {
          toast.error('登录响应中未找到token')
        }
      } else {
        toast.error(`登录失败: ${data.message || data.detail}`)
      }
    } catch (error: any) {
      toast.error(`登录异常: ${error.message}`)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            认证状态调试工具
          </h1>
          <p className="text-gray-600">
            检查和调试前端认证状态，解决登录相关问题
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 认证状态面板 */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">当前认证状态</h2>
                <Button size="sm" variant="outline" onClick={checkAuthStatus}>
                  刷新状态
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {authInfo ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex justify-between">
                      <span className="text-sm">认证Token:</span>
                      <Badge variant={authInfo.hasToken ? 'success' : 'destructive'}>
                        {authInfo.hasToken ? '存在' : '不存在'}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">用户信息:</span>
                      <Badge variant={authInfo.hasUser ? 'success' : 'destructive'}>
                        {authInfo.hasUser ? '存在' : '不存在'}
                      </Badge>
                    </div>
                  </div>

                  {authInfo.hasToken && (
                    <div className="space-y-2">
                      <div className="text-sm">
                        <span className="font-medium">Token长度:</span> {authInfo.tokenLength}
                      </div>
                      <div className="text-sm">
                        <span className="font-medium">Token预览:</span>
                        <code className="ml-2 text-xs bg-gray-100 px-2 py-1 rounded">
                          {authInfo.tokenPreview}
                        </code>
                      </div>
                    </div>
                  )}

                  {authInfo.hasUser && authInfo.user && (
                    <div className="space-y-2">
                      <div className="font-medium text-sm">用户信息:</div>
                      <div className="text-sm bg-gray-50 p-2 rounded">
                        <div>用户名: {authInfo.user.username || 'N/A'}</div>
                        <div>邮箱: {authInfo.user.email || 'N/A'}</div>
                        <div>ID: {authInfo.user.id || 'N/A'}</div>
                      </div>
                    </div>
                  )}

                  {authInfo.tokenValid !== undefined && (
                    <div className="pt-2 border-t">
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Token验证:</span>
                        <Badge variant={authInfo.tokenValid ? 'success' : 'destructive'}>
                          {authInfo.tokenValid ? '有效' : '无效'}
                        </Badge>
                      </div>
                      {authInfo.tokenError && (
                        <div className="text-sm text-red-600 mt-1">
                          错误: {authInfo.tokenError}
                        </div>
                      )}
                    </div>
                  )}

                  <div className="text-xs text-gray-500">
                    检查时间: {authInfo.timestamp}
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-500">加载中...</div>
              )}
            </CardContent>
          </Card>

          {/* 操作面板 */}
          <Card>
            <CardHeader>
              <h2 className="text-xl font-semibold">认证操作</h2>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Token验证 */}
                <div>
                  <Button
                    onClick={testTokenValidity}
                    disabled={!authInfo?.hasToken}
                    className="w-full"
                  >
                    验证当前Token
                  </Button>
                  <p className="text-xs text-gray-500 mt-1">
                    向后端发送请求验证token是否有效
                  </p>
                </div>

                {/* 清除认证数据 */}
                <div>
                  <Button
                    onClick={clearAuthData}
                    variant="destructive"
                    className="w-full"
                  >
                    清除认证数据
                  </Button>
                  <p className="text-xs text-gray-500 mt-1">
                    清除localStorage中的token和用户信息
                  </p>
                </div>

                {/* 快速登录 */}
                <div>
                  <Button
                    onClick={tryQuickLogin}
                    className="w-full"
                  >
                    尝试快速登录
                  </Button>
                  <p className="text-xs text-gray-500 mt-1">
                    使用默认测试账号尝试登录
                  </p>
                </div>

                {/* 手动设置Token */}
                <div className="pt-4 border-t">
                  <label className="block text-sm font-medium mb-2">手动设置测试Token</label>
                  <div className="space-y-2">
                    <Input
                      type="text"
                      placeholder="粘贴有效的JWT token..."
                      value={testToken}
                      onChange={(e) => setTestToken(e.target.value)}
                    />
                    <Button
                      onClick={setTestTokenToStorage}
                      disabled={!testToken.trim()}
                      size="sm"
                      className="w-full"
                    >
                      设置Token
                    </Button>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    如果有有效的token，可以手动设置用于测试
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 帮助信息面板 */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <h2 className="text-xl font-semibold">故障排除指南</h2>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h3 className="font-medium mb-2">如果没有Token:</h3>
                    <ul className="text-sm space-y-1 text-gray-600">
                      <li>1. 点击"尝试快速登录"按钮</li>
                      <li>2. 或者去登录页面: /login</li>
                      <li>3. 或者手动设置有效的token</li>
                      <li>4. 检查后端登录API是否正常</li>
                    </ul>
                  </div>
                  <div>
                    <h3 className="font-medium mb-2">如果Token无效:</h3>
                    <ul className="text-sm space-y-1 text-gray-600">
                      <li>1. Token可能已过期，需要重新登录</li>
                      <li>2. 检查后端JWT配置</li>
                      <li>3. 确认后端认证中间件正常工作</li>
                      <li>4. 清除认证数据后重新登录</li>
                    </ul>
                  </div>
                  <div>
                    <h3 className="font-medium mb-2">测试无认证API:</h3>
                    <ul className="text-sm space-y-1 text-gray-600">
                      <li>• <a href="/test-api-simple" className="text-blue-600 hover:underline">简单API测试页面</a></li>
                      <li>• 健康检查: GET /api/health</li>
                      <li>• 版本信息: GET /api/version</li>
                      <li>• 图表类型: GET /api/v1/chart-test/chart-types</li>
                    </ul>
                  </div>
                  <div>
                    <h3 className="font-medium mb-2">后端服务检查:</h3>
                    <ul className="text-sm space-y-1 text-gray-600">
                      <li>• 确保后端在 http://localhost:8000 运行</li>
                      <li>• 访问 http://localhost:8000/docs 查看API文档</li>
                      <li>• 检查CORS配置是否正确</li>
                      <li>• 查看后端日志输出</li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}