'use client'

import { useState, useEffect } from 'react'
import { useI18n } from '@/components/providers/I18nProvider'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Eye, EyeOff, CheckCircle, AlertCircle } from 'lucide-react'
import api from '@/lib/api'
import axios from 'axios';

interface FormData {
  username: string
  email: string
  full_name: string
  password: string
  confirm_password: string
  terms_accepted: boolean
}

interface FormErrors {
  username?: string
  email?: string
  full_name?: string
  password?: string
  confirm_password?: string
  terms_accepted?: string
  general?: string
}

export default function RegisterPage() {
  const params = useParams()
  const locale = params.locale as string
  const { t } = useI18n()
  const router = useRouter()
  
  const [formData, setFormData] = useState<FormData>({
    username: '',
    email: '',
    full_name: '',
    password: '',
    confirm_password: '',
    terms_accepted: false
  })
  
  const [errors, setErrors] = useState<FormErrors>({})
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [registrationSuccess, setRegistrationSuccess] = useState(false)

  // 修复：useEffect 必须在组件顶层调用
  useEffect(() => {
    if (registrationSuccess) {
      const timer = setTimeout(() => {
        router.push(`/${locale}/login`)
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [registrationSuccess, router, locale])

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {}

    // 用户名验证
    if (!formData.username.trim()) {
      newErrors.username = t('usernameRequired', 'auth')
    } else if (formData.username.length < 3) {
      newErrors.username = t('usernameMinLength', 'auth')
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.username)) {
      newErrors.username = t('usernamePattern', 'auth')
    }

    // 邮箱验证
    if (!formData.email.trim()) {
      newErrors.email = t('emailRequired', 'auth')
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = t('emailInvalid', 'auth')
    }

    // 全名验证
    if (!formData.full_name.trim()) {
      newErrors.full_name = t('fullNameRequired', 'auth')
    } else if (formData.full_name.length < 2) {
      newErrors.full_name = t('fullNameMinLength', 'auth')
    }

    // 密码验证
    if (!formData.password) {
      newErrors.password = t('passwordRequired', 'auth')
    } else if (formData.password.length < 8) {
      newErrors.password = t('passwordMinLength', 'auth')
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
      newErrors.password = t('passwordPattern', 'auth')
    }

    // 确认密码验证
    if (!formData.confirm_password) {
      newErrors.confirm_password = t('confirmPasswordRequired', 'auth')
    } else if (formData.password !== formData.confirm_password) {
      newErrors.confirm_password = t('passwordsNotMatch', 'auth')
    }

    // 条款验证
    if (!formData.terms_accepted) {
      newErrors.terms_accepted = t('acceptTerms', 'auth')
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    setLoading(true)
    setErrors({})

    try {
      const response = await api.post('/auth/register', {
        username: formData.username,
        email: formData.email,
        full_name: formData.full_name,
        password: formData.password,
        terms_accepted: formData.terms_accepted
      })

      if (response.status === 200 || response.status === 201) {
        setRegistrationSuccess(true)
      }
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        if (error.response?.data?.detail) {
          if (typeof error.response.data.detail === 'string') {
            setErrors({ general: error.response.data.detail })
          } else if (Array.isArray(error.response.data.detail)) {
            const fieldErrors: FormErrors = {}
            error.response.data.detail.forEach((err: any) => {
              if (err.loc && err.loc.length > 1) {
                const field = err.loc[1]
                fieldErrors[field as keyof FormErrors] = err.msg
              }
            })
            setErrors(fieldErrors)
          }
        } else {
          setErrors({ general: t('registrationFailed', 'auth') })
        }
      } else if (error instanceof Error) {
        setErrors({ general: error.message })
      } else {
        setErrors({ general: t('registrationFailed', 'auth') })
      }
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (field: keyof FormData, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    // 清除该字段的错误
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }))
    }
  }

  if (registrationSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
            <CardTitle className="text-2xl">Registration Successful!</CardTitle>
            <CardDescription>
              We've sent a verification email to {formData.email}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Please check your email and click the verification link to activate your account.
              </AlertDescription>
            </Alert>
            <div className="text-center space-y-2">
              <p className="text-sm text-gray-600">
                Didn't receive the email?
              </p>
              <Button variant="outline" size="sm">
                Resend Verification Email
              </Button>
            </div>
            <div className="text-center">
              <Link href={`/${locale}/login`} className="text-sm text-blue-600 hover:text-blue-500">
                Back to Login
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">{t('createAccount', 'auth')}</CardTitle>
          <CardDescription>
            {t('registerDescription', 'auth')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {errors.general && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{errors.general}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="username">{t('username', 'auth')}</Label>
              <Input
                id="username"
                type="text"
                value={formData.username}
                onChange={(e) => handleInputChange('username', e.target.value)}
                placeholder={t('usernamePlaceholder', 'auth')}
                className={errors.username ? 'border-red-500' : ''}
              />
              {errors.username && (
                <p className="text-sm text-red-500">{errors.username}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">{t('email', 'auth')}</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => handleInputChange('email', e.target.value)}
                placeholder={t('emailPlaceholder', 'auth')}
                className={errors.email ? 'border-red-500' : ''}
              />
              {errors.email && (
                <p className="text-sm text-red-500">{errors.email}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="full_name">{t('fullName', 'auth')}</Label>
              <Input
                id="full_name"
                type="text"
                value={formData.full_name}
                onChange={(e) => handleInputChange('full_name', e.target.value)}
                placeholder={t('fullNamePlaceholder', 'auth')}
                className={errors.full_name ? 'border-red-500' : ''}
              />
              {errors.full_name && (
                <p className="text-sm text-red-500">{errors.full_name}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">{t('password', 'auth')}</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => handleInputChange('password', e.target.value)}
                  placeholder={t('passwordPlaceholder', 'auth')}
                  className={errors.password ? 'border-red-500' : ''}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
              {errors.password && (
                <p className="text-sm text-red-500">{errors.password}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm_password">{t('confirmPassword', 'auth')}</Label>
              <div className="relative">
                <Input
                  id="confirm_password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={formData.confirm_password}
                  onChange={(e) => handleInputChange('confirm_password', e.target.value)}
                  placeholder={t('confirmPasswordPlaceholder', 'auth')}
                  className={errors.confirm_password ? 'border-red-500' : ''}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
              {errors.confirm_password && (
                <p className="text-sm text-red-500">{errors.confirm_password}</p>
              )}
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="terms"
                checked={formData.terms_accepted}
                onChange={e => handleInputChange('terms_accepted', (e.target as HTMLInputElement).checked)}
              />
              <Label htmlFor="terms" className="text-sm">
                {t('agreeTo', 'auth')}
                <Link href="/terms" className="text-blue-600 hover:text-blue-500">
                  {t('termsOfService', 'auth')}
                </Link>
                {t('and', 'auth')}
                <Link href="/privacy" className="text-blue-600 hover:text-blue-500">
                  {t('privacyPolicy', 'auth')}
                </Link>
              </Label>
            </div>
            {errors.terms_accepted && (
              <p className="text-sm text-red-500">{errors.terms_accepted}</p>
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('creatingAccount', 'auth')}
                </>
              ) : (
                t('createAccount', 'auth')
              )}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              {t('alreadyHaveAccount', 'auth')}
              <Link href="/login" className="text-blue-600 hover:text-blue-500 font-medium">
                {t('signIn', 'auth')}
              </Link>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}