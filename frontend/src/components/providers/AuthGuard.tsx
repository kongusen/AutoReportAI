'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getAuthToken, removeAuthToken } from '@/lib/auth'

interface AuthGuardProps {
  children: React.ReactNode
}

export function AuthGuard({ children }: AuthGuardProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    const token = getAuthToken()
    
    console.log('AuthGuard: 检查认证状态, token:', token ? `${token.substring(0, 20)}...` : 'null')
    
    if (!token) {
      console.log('AuthGuard: 未找到token, 跳转登录')
      setIsAuthenticated(false)
      setLoading(false)
      router.push('/login')
      return
    }

    // 简化版本：直接验证token格式而不调用API
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      const isExpired = payload.exp * 1000 < Date.now()
      
      console.log('AuthGuard: token payload:', payload)
      console.log('AuthGuard: token过期状态:', isExpired)
      
      if (isExpired) {
        console.log('AuthGuard: token已过期, 清除并跳转登录')
        removeAuthToken()
        setIsAuthenticated(false)
        router.push('/login')
      } else {
        console.log('AuthGuard: token有效, 设置认证状态为true')
      setIsAuthenticated(true)
      }
    } catch (error) {
      console.log('AuthGuard: token解析失败:', error)
      removeAuthToken()
      setIsAuthenticated(false)
      router.push('/login')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-gray-900"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null // 已经重定向到登录页
  }

  return <>{children}</>
}
