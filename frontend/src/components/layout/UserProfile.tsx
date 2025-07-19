'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { User } from 'lucide-react'
import api from '@/lib/api'

interface UserProfile {
  id: number
  username: string
  email: string
  // ...其他字段
}

export function UserProfile() {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchUserProfile()
  }, [])

  const fetchUserProfile = async () => {
    try {
      // 优先尝试 /user-profile/me
      let response
      try {
        response = await api.get('/user-profile/me')
      } catch {
        // 兼容老接口 /users/me
        try {
          response = await api.get('/users/me')
        } catch {
          // 如果都失败了，使用默认用户信息
          setUser({
            id: 1,
            username: 'admin',
            email: 'admin@example.com'
          })
          return
        }
      }
      setUser(response.data || response)
    } catch (error) {
      console.error('Error fetching user profile:', error)
      // 设置默认用户信息
      setUser({
        id: 1,
        username: 'admin',
        email: 'admin@example.com'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    window.location.href = '/login'
  }

  if (loading) {
    return (
      <div className="p-4">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div className="h-3 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="p-4">
        <Button 
          variant="ghost" 
          className="w-full justify-start"
          onClick={() => window.location.href = '/login'}
        >
          <User className="w-4 h-4 mr-2" />
          登录
        </Button>
      </div>
    )
  }

  return (
    <div className="p-4 border-t border-gray-200 dark:border-gray-700">
      <div className="flex items-center space-x-3">
        <User className="w-6 h-6 text-gray-600 dark:text-gray-300" />
        <div>
          <div className="font-medium text-gray-900 dark:text-gray-100">{user.username}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">{user.email}</div>
        </div>
      </div>
      <Button variant="outline" className="w-full mt-4" onClick={handleLogout}>
        退出登录
      </Button>
    </div>
  )
}
