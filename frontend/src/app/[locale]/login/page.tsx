'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useI18n } from '@/components/providers/I18nProvider'
import { useAuth } from '@/lib/auth/AuthContext'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { Loader2 } from 'lucide-react'

interface ErrorResponse {
  response?: {
    data?: {
      detail?: string;
    };
    status?: number;
  };
  message?: string;
}

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [pendingRedirect, setPendingRedirect] = useState(false)
  const { t, currentLocale, setLocale } = useI18n()
  const params = useParams()
  const locale = params.locale as string
  const router = useRouter()
  const searchParams = useSearchParams()
  const redirectPath = searchParams.get('redirect') || `/${locale}/dashboard`
  
  // Get authentication context
  const { login, isAuthenticated, isLoading } = useAuth()

  // Redirect if already authenticated
  useEffect(() => {
    if (pendingRedirect && isAuthenticated && !isLoading) {
      router.push(redirectPath)
    }
  }, [pendingRedirect, isAuthenticated, isLoading, router, redirectPath])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!username.trim() || !password.trim()) {
      setError(t('requiredFields', 'auth') || '请填写用户名和密码')
      return
    }

    try {
      await login(username, password)
      setPendingRedirect(true)
    } catch (err: unknown) {
      console.error('Login error:', err)
      const error = err as ErrorResponse
      let errorMessage = t('loginFailed', 'auth') || '登录失败'
      
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error.message) {
        errorMessage = error.message
      } else if (error.response?.status === 401) {
        errorMessage = t('invalidCredentials', 'auth') || '用户名或密码错误'
      } else if (error.response?.status && error.response.status >= 500) {
        errorMessage = t('serverError', 'auth') || '服务器错误，请稍后重试'
      }
      
      setError(errorMessage)
    }
  }

  const handleLocaleChange = (value: 'zh-CN' | 'en-US') => {
    setLocale(value)
    router.push(`/${value}/login`)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>{t('title', 'auth')}</CardTitle>
              <CardDescription>{t('description', 'auth')}</CardDescription>
            </div>
            <Select value={currentLocale} onValueChange={handleLocaleChange}>
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
              <Label htmlFor="username">{t('username', 'auth')}</Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={t('usernamePlaceholder', 'auth')}
                autoComplete="username"
                required
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">{t('password', 'auth')}</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('passwordPlaceholder', 'auth')}
                autoComplete="current-password"
                required
                disabled={isLoading}
              />
            </div>
            {error && (
              <div className="text-red-600 text-sm bg-red-50 p-3 rounded-md">
                {error}
              </div>
            )}
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('loggingIn', 'auth')}
                </>
              ) : (
                t('loginButton', 'auth')
              )}
            </Button>
          </form>
          
          {/* Development environment hint */}
          {process.env.NODE_ENV === 'development' && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
              <p className="text-sm text-blue-800 font-medium">{t('devHint', 'auth')}</p>
              <p className="text-sm text-blue-600">{t('defaultCredentials', 'auth')}</p>
            </div>
          )}
          
          <div className="mt-4 text-center text-sm text-gray-600">
            <p className="mb-2">
              {t('noAccount', 'auth')} <Link href={`/${locale}/register`} className="text-blue-600 hover:underline">{t('signUp', 'auth')}</Link>
            </p>
            <Link href={`/${locale}/forgot-password`} className="text-blue-600 hover:underline">{t('forgotPassword', 'auth')}</Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
