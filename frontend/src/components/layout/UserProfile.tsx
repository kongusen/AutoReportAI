'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { User, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react'
import { useAuth } from '@/lib/auth/AuthContext'
import { useParams, useRouter } from 'next/navigation'

interface UserProfileProps {
  onAuthStateChange?: (isAuthenticated: boolean) => void
}

export function UserProfile({ onAuthStateChange }: UserProfileProps = {}) {
  const { user, isAuthenticated, isLoading, logout, refreshToken } = useAuth()
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [error, setError] = useState<string | null>(null)
  const params = useParams()
  const router = useRouter()
  const locale = params.locale as string || 'en-US'

  // Notify parent component when auth state changes
  useEffect(() => {
    onAuthStateChange?.(isAuthenticated)
  }, [isAuthenticated, onAuthStateChange])

  // Update last updated timestamp when user data changes
  useEffect(() => {
    if (user) {
      setLastUpdated(new Date())
    }
  }, [user])

  const handleManualRefresh = async () => {
    try {
      setIsRefreshing(true)
      setError(null)
      const success = await refreshToken()
      if (success) {
        setLastUpdated(new Date())
      } else {
        setError('Failed to refresh user data')
      }
    } catch (err) {
      console.error('Error refreshing user data:', err)
      setError('Error refreshing user data')
    } finally {
      setIsRefreshing(false)
    }
  }

  const handleLogout = async () => {
    try {
      await logout()
      router.push(`/${locale}/login`)
    } catch (err) {
      console.error('Error during logout:', err)
      // Force redirect even if there's an error
      router.push(`/${locale}/login`)
    }
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="p-4">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
        </div>
      </div>
    )
  }

  // Error state with no user
  if (error && !user) {
    return (
      <div className="p-4">
        <div className="flex items-center space-x-2 text-red-600 dark:text-red-400 mb-3">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">{error}</span>
        </div>
        <Button 
          variant="outline" 
          className="w-full"
          onClick={handleManualRefresh}
          disabled={isRefreshing}
        >
          {isRefreshing ? (
            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4 mr-2" />
          )}
          重试
        </Button>
      </div>
    )
  }

  // Not authenticated state
  if (!isAuthenticated || !user) {
    return (
      <div className="p-4">
        <Button 
          variant="ghost" 
          className="w-full justify-start"
          onClick={() => router.push(`/${locale}/login`)}
        >
          <User className="w-4 h-4 mr-2" />
          登录
        </Button>
      </div>
    )
  }

  // Authenticated state
  return (
    <div className="p-4 border-t border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3 flex-1 min-w-0">
          <User className="w-6 h-6 text-gray-600 dark:text-gray-300 flex-shrink-0" />
          <div className="min-w-0 flex-1">
            <div className="font-medium text-gray-900 dark:text-gray-100 truncate">
              {user.full_name || user.username}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
              {user.email}
            </div>
            {lastUpdated && (
              <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                更新于 {lastUpdated.toLocaleTimeString()}
              </div>
            )}
          </div>
        </div>
        
        <Button
          variant="ghost"
          size="sm"
          onClick={handleManualRefresh}
          disabled={isRefreshing}
          className="flex-shrink-0 ml-2"
          title="刷新用户信息"
        >
          {isRefreshing ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
        </Button>
      </div>

      {/* Status indicators */}
      <div className="flex items-center space-x-2 mb-3">
        {user.is_active ? (
          <div className="flex items-center space-x-1 text-green-600 dark:text-green-400">
            <CheckCircle className="w-3 h-3" />
            <span className="text-xs">活跃</span>
          </div>
        ) : (
          <div className="flex items-center space-x-1 text-red-600 dark:text-red-400">
            <AlertCircle className="w-3 h-3" />
            <span className="text-xs">未激活</span>
          </div>
        )}
        
        {user.is_superuser && (
          <div className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-1 rounded">
            管理员
          </div>
        )}
      </div>

      {/* Error indicator */}
      {error && (
        <div className="flex items-center space-x-2 text-amber-600 dark:text-amber-400 mb-3">
          <AlertCircle className="w-4 h-4" />
          <span className="text-xs">{error}</span>
        </div>
      )}

      <Button 
        variant="outline" 
        className="w-full" 
        onClick={handleLogout}
        disabled={isRefreshing}
      >
        退出登录
      </Button>
    </div>
  )
}
