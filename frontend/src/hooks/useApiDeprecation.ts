'use client'

import { useState, useEffect, useCallback } from 'react'

interface DeprecationInfo {
  endpoint: string
  message?: string
  replacement?: Record<string, string>
  timestamp: number
}

interface UseApiDeprecationReturn {
  deprecations: DeprecationInfo[]
  addDeprecation: (deprecation: Omit<DeprecationInfo, 'timestamp'>) => void
  dismissDeprecation: (endpoint: string) => void
  clearAllDeprecations: () => void
  hasDeprecations: boolean
}

/**
 * API弃用管理Hook
 * 用于跟踪和显示API弃用警告
 */
export function useApiDeprecation(): UseApiDeprecationReturn {
  const [deprecations, setDeprecations] = useState<DeprecationInfo[]>([])

  // 从localStorage加载已保存的弃用信息
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const savedDeprecations = localStorage.getItem('api_deprecations')
      if (savedDeprecations) {
        try {
          const parsed = JSON.parse(savedDeprecations)
          // 只保留24小时内的弃用信息
          const validDeprecations = parsed.filter((dep: DeprecationInfo) =>
            Date.now() - dep.timestamp < 24 * 60 * 60 * 1000
          )
          setDeprecations(validDeprecations)
        } catch (e) {
          console.warn('Failed to parse saved deprecations:', e)
        }
      }
    }
  }, [])

  // 保存弃用信息到localStorage
  const saveDeprecations = useCallback((deps: DeprecationInfo[]) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('api_deprecations', JSON.stringify(deps))
    }
  }, [])

  // 添加新的弃用信息
  const addDeprecation = useCallback((deprecation: Omit<DeprecationInfo, 'timestamp'>) => {
    setDeprecations(prev => {
      // 检查是否已存在相同的弃用信息（避免重复）
      const exists = prev.find(dep => dep.endpoint === deprecation.endpoint)
      if (exists) {
        return prev
      }

      const newDeprecation: DeprecationInfo = {
        ...deprecation,
        timestamp: Date.now()
      }

      const updated = [...prev, newDeprecation]
      saveDeprecations(updated)
      return updated
    })
  }, [saveDeprecations])

  // 忽略特定的弃用警告
  const dismissDeprecation = useCallback((endpoint: string) => {
    setDeprecations(prev => {
      const updated = prev.filter(dep => dep.endpoint !== endpoint)
      saveDeprecations(updated)
      return updated
    })
  }, [saveDeprecations])

  // 清空所有弃用警告
  const clearAllDeprecations = useCallback(() => {
    setDeprecations([])
    if (typeof window !== 'undefined') {
      localStorage.removeItem('api_deprecations')
    }
  }, [])

  return {
    deprecations,
    addDeprecation,
    dismissDeprecation,
    clearAllDeprecations,
    hasDeprecations: deprecations.length > 0
  }
}

// 全局弃用监听器 - 监听API响应中的弃用警告
export function setupDeprecationListener(addDeprecation: UseApiDeprecationReturn['addDeprecation']) {
  // 监听fetch响应
  const originalFetch = window.fetch
  window.fetch = async (...args) => {
    const response = await originalFetch(...args)

    // 检查是否是弃用的接口
    if (response.status === 410 && response.headers.get('x-deprecated') === 'true') {
      try {
        const data = await response.clone().json()
        addDeprecation({
          endpoint: args[0] as string,
          message: data.message,
          replacement: data.replacement
        })
      } catch (e) {
        // 忽略解析错误
      }
    }

    return response
  }

  // 返回清理函数
  return () => {
    window.fetch = originalFetch
  }
}

export default useApiDeprecation