'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, CheckCircle, AlertCircle, Mail } from 'lucide-react'
import api from '@/lib/api'

export default function VerifyEmailPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get('token')
  
  const [loading, setLoading] = useState(true)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [resendLoading, setResendLoading] = useState(false)

  useEffect(() => {
    if (token) {
      verifyEmail(token)
    } else {
      setError('Invalid verification link')
      setLoading(false)
    }
  }, [token])

  const verifyEmail = async (verificationToken: string) => {
    try {
      const response = await api.post('/auth/verify-email', {
        token: verificationToken
      })

      if (response.status === 200) {
        setSuccess(true)
        // 3秒后自动跳转到登录页面
        setTimeout(() => {
          router.push('/login?verified=true')
        }, 3000)
      }
    } catch (error: any) {
      if (error.response?.data?.detail) {
        setError(error.response.data.detail)
      } else {
        setError('Email verification failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const resendVerification = async () => {
    setResendLoading(true)
    try {
      // 这里需要用户提供邮箱地址，或者从token中解析
      // 为简化，我们显示一个提示让用户重新注册或联系支持
      setError('Please contact support or try registering again if you need a new verification email.')
    } catch (error: any) {
      setError('Failed to resend verification email')
    } finally {
      setResendLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-blue-100 mb-4">
              <Loader2 className="h-6 w-6 text-blue-600 animate-spin" />
            </div>
            <CardTitle className="text-2xl">Verifying Email</CardTitle>
            <CardDescription>
              Please wait while we verify your email address...
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
            <CardTitle className="text-2xl">Email Verified!</CardTitle>
            <CardDescription>
              Your email has been successfully verified. You can now sign in to your account.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>
                Your account is now active. You will be redirected to the login page in a few seconds.
              </AlertDescription>
            </Alert>
            <div className="text-center">
              <Link href="/login">
                <Button className="w-full">
                  Continue to Login
                </Button>
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
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
            <AlertCircle className="h-6 w-6 text-red-600" />
          </div>
          <CardTitle className="text-2xl">Verification Failed</CardTitle>
          <CardDescription>
            We couldn't verify your email address
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {error || 'The verification link is invalid or has expired.'}
            </AlertDescription>
          </Alert>
          
          <div className="space-y-3">
            <p className="text-sm text-gray-600 text-center">
              The verification link may have expired or been used already.
            </p>
            
            <div className="flex flex-col space-y-2">
              <Link href="/register">
                <Button variant="outline" className="w-full">
                  <Mail className="mr-2 h-4 w-4" />
                  Register Again
                </Button>
              </Link>
              
              <Link href="/login">
                <Button variant="ghost" className="w-full">
                  Back to Login
                </Button>
              </Link>
            </div>
          </div>
          
          <div className="text-center">
            <p className="text-xs text-gray-500">
              Need help? Contact our support team
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}