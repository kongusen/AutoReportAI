'use client'

/**
 * API优化测试页面
 */

import { useEffect } from 'react'
import { useAuthStore } from '@/features/auth/authStore'
import { useRouter } from 'next/navigation'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import ComprehensiveAPITest from '@/components/test/ComprehensiveAPITest'

export default function APITestPage() {
  const { isAuthenticated, isLoading } = useAuthStore()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <ComprehensiveAPITest />
    </div>
  )
}