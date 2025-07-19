'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { authApi } from '@/lib/api'
import { useI18n } from '@/lib/i18n'
import { setAuthToken } from '@/lib/auth'

interface ErrorResponse {
  response?: {
    data?: {
      detail?: string;
    };
  };
  message?: string;
}

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { t, language, setLanguage } = useI18n()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    // 添加调试信息
    console.log('DEBUG: 前端发送的登录数据:', { username, password })

    try {
      const response = await authApi.login({ username, password })
      const access_token = response.access_token
      
      console.log('登录成功，获得token:', access_token ? `${access_token.substring(0, 20)}...` : 'null')
      
      // 使用统一的token存储方法
      if (access_token) {
        setAuthToken(access_token)
        console.log('Token已存储到localStorage')
      }
      
      console.log('登录成功，准备跳转...')
      
      // 使用强制跳转，确保页面能够正常跳转
      window.location.href = '/'
    } catch (err: unknown) {
      console.error('Login error:', err)
      const error = err as ErrorResponse
      const errorMessage = error.response?.data?.detail || error.message || t('login.loginFailed')
      setError(typeof errorMessage === 'string' ? errorMessage : t('login.invalidCredentials'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>{t('login.title')}</CardTitle>
              <CardDescription>{t('login.description')}</CardDescription>
            </div>
            <Select value={language} onValueChange={(value: 'zh-CN' | 'en-US') => setLanguage(value)}>
              <SelectTrigger className="w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="zh-CN">中文</SelectItem>
                <SelectItem value="en-US">EN</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">{t('login.username')}</Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={t('login.usernamePlaceholder')}
                autoComplete="username"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">{t('login.password')}</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('login.passwordPlaceholder')}
                autoComplete="current-password"
                required
              />
            </div>
            {error && (
              <div className="text-red-600 text-sm bg-red-50 p-3 rounded-md">
                {error}
              </div>
            )}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? t('login.loggingIn') : t('login.loginButton')}
            </Button>
          </form>
          
          {/* Development environment hint */}
          {process.env.NODE_ENV === 'development' && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
              <p className="text-sm text-blue-800 font-medium">{t('login.devHint')}</p>
              <p className="text-sm text-blue-600">{t('login.defaultCredentials')}</p>
            </div>
          )}
          
          <div className="mt-4 text-center text-sm text-gray-600">
            <p className="mb-2">
              {t('login.noAccount')} <a href="/register" className="text-blue-600 hover:underline">{t('login.signUp')}</a>
            </p>
            <a href="/forgot-password" className="text-blue-600 hover:underline">{t('login.forgotPassword')}</a>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
