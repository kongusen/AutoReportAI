'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/features/auth/authStore'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter()
  const { token, setLoading, setUser, setToken } = useAuthStore()

  useEffect(() => {
    // 在客户端初始化时检查认证状态
    const initializeAuth = async () => {
      setLoading(true)
      
      try {
        // 从localStorage获取token和用户信息
        const storedToken = localStorage.getItem('authToken')
        const storedUser = localStorage.getItem('user')

        if (storedToken && storedUser) {
          // 恢复认证状态
          setToken(storedToken)
          setUser(JSON.parse(storedUser))
          
          // TODO: 验证token是否仍然有效
          // 这里可以调用 /auth/me 端点验证token
        }
      } catch (error) {
        console.error('Failed to initialize auth:', error)
        // 清除无效的认证信息
        localStorage.removeItem('authToken')
        localStorage.removeItem('user')
      } finally {
        setLoading(false)
      }
    }

    initializeAuth()
  }, [setLoading, setUser, setToken])

  // 监听token变化，设置axios默认headers
  useEffect(() => {
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('authToken', token)
      } else {
        localStorage.removeItem('authToken')
      }
    }
  }, [token])

  return <>{children}</>
}