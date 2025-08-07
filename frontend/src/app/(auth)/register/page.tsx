'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { useAuthStore } from '@/features/auth/authStore'
import { registerSchema } from '@/features/auth/validations'
import { RegisterForm } from '@/types'


export default function RegisterPage() {
  const router = useRouter()
  const { register: registerUser, isLoading } = useAuthStore()
  const [error, setError] = useState<string>('')
  const [success, setSuccess] = useState<string>('')

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  })

  const onSubmit = async (data: RegisterForm) => {
    try {
      setError('')
      setSuccess('')
      await registerUser(data)
      setSuccess('注册成功！请使用您的账号登录。')
      setTimeout(() => {
        router.push('/auth/login')
      }, 2000)
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.response?.data?.error || err.response?.data?.detail || '注册失败，请稍后重试'
      setError(typeof errorMessage === 'string' ? errorMessage : '注册失败')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900">AutoReportAI</h1>
          <p className="mt-2 text-sm text-gray-600">智能报告生成平台</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>注册</CardTitle>
            <CardDescription>
              创建您的账号以开始使用系统
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-md p-4">
                  <div className="flex">
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-red-800">
                        注册失败
                      </h3>
                      <div className="mt-2 text-sm text-red-700">
                        <p>{error}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {success && (
                <div className="bg-green-50 border border-green-200 rounded-md p-4">
                  <div className="flex">
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-green-800">
                        注册成功
                      </h3>
                      <div className="mt-2 text-sm text-green-700">
                        <p>{success}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                    用户名
                  </label>
                  <Input
                    id="username"
                    type="text"
                    autoComplete="username"
                    error={!!errors.username}
                    {...register('username')}
                  />
                  {errors.username && (
                    <p className="mt-1 text-sm text-red-600">{errors.username.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                    邮箱
                  </label>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    error={!!errors.email}
                    {...register('email')}
                  />
                  {errors.email && (
                    <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                    密码
                  </label>
                  <Input
                    id="password"
                    type="password"
                    autoComplete="new-password"
                    error={!!errors.password}
                    {...register('password')}
                  />
                  {errors.password && (
                    <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                    确认密码
                  </label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    error={!!errors.confirmPassword}
                    {...register('confirmPassword')}
                  />
                  {errors.confirmPassword && (
                    <p className="mt-1 text-sm text-red-600">{errors.confirmPassword.message}</p>
                  )}
                </div>
              </div>

              <Button
                type="submit"
                className="w-full"
                loading={isLoading}
                disabled={isLoading || !!success}
              >
                注册
              </Button>

              <div className="text-center">
                <span className="text-sm text-gray-600">
                  已有账号？{' '}
                  <Link
                    href="/auth/login"
                    className="font-medium text-black hover:text-gray-800"
                  >
                    立即登录
                  </Link>
                </span>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}