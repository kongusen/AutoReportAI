/**
 * API请求Hook - 提供统一的加载状态、错误处理和进度跟踪
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import { ApiClient, ApiRequestOptions } from '@/lib/api-client'
import { useToast } from '@/hooks/useToast'

export interface UseApiRequestOptions extends ApiRequestOptions {
  // 是否立即执行
  immediate?: boolean
  // 成功回调
  onSuccess?: (data: any) => void
  // 错误回调
  onError?: (error: any) => void
  // 完成回调（无论成功失败）
  onComplete?: () => void
  // 是否显示详细进度
  showProgress?: boolean
  // 自定义成功消息
  successMessage?: string
  // 自定义错误消息
  errorMessage?: string
}

export interface ApiRequestState<T = any> {
  data: T | null
  loading: boolean
  error: Error | null
  progress: number
  executed: boolean
}

export function useApiRequest<T = any>(
  method: 'GET' | 'POST' | 'PUT' | 'DELETE',
  url: string,
  options: UseApiRequestOptions = {}
) {
  const {
    immediate = false,
    onSuccess,
    onError,
    onComplete,
    showProgress = false,
    successMessage,
    errorMessage,
    showToast = true,
    ...apiOptions
  } = options

  const { showSuccess, showError } = useToast()
  const abortControllerRef = useRef<AbortController | null>(null)

  const [state, setState] = useState<ApiRequestState<T>>({
    data: null,
    loading: false,
    error: null,
    progress: 0,
    executed: false
  })

  // 更新进度
  const updateProgress = useCallback((progress: number) => {
    setState(prev => ({ ...prev, progress }))
  }, [])

  // 执行请求
  const execute = useCallback(async (requestData?: any, requestOptions?: ApiRequestOptions) => {
    // 取消之前的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    // 创建新的AbortController
    const abortController = new AbortController()
    abortControllerRef.current = abortController

    setState(prev => ({
      ...prev,
      loading: true,
      error: null,
      progress: 0,
      executed: true
    }))

    try {
      const mergedOptions = {
        ...apiOptions,
        ...requestOptions,
        signal: abortController.signal,
        showToast,
        onProgress: showProgress ? updateProgress : undefined
      }

      let result: T
      switch (method) {
        case 'GET':
          result = await ApiClient.get<T>(url, mergedOptions)
          break
        case 'POST':
          result = await ApiClient.post<T>(url, requestData, mergedOptions)
          break
        case 'PUT':
          result = await ApiClient.put<T>(url, requestData, mergedOptions)
          break
        case 'DELETE':
          result = await ApiClient.delete<T>(url, mergedOptions)
          break
      }

      setState(prev => ({
        ...prev,
        data: result,
        loading: false,
        progress: 100
      }))

      // 成功回调
      onSuccess?.(result)
      if (successMessage) {
        showSuccess(successMessage)
      }

      return result
    } catch (error: any) {
      // 如果是手动取消，不显示错误
      if (error.name === 'AbortError' || abortController.signal.aborted) {
        return
      }

      const errorObj = error instanceof Error ? error : new Error(String(error))
      
      setState(prev => ({
        ...prev,
        error: errorObj,
        loading: false,
        progress: 0
      }))

      // 错误回调
      onError?.(errorObj)
      if (errorMessage && showToast) {
        showError(errorMessage)
      }

      throw errorObj
    } finally {
      onComplete?.()
      abortControllerRef.current = null
    }
  }, [method, url, apiOptions, showProgress, updateProgress, onSuccess, onError, onComplete, successMessage, errorMessage, showToast, showSuccess, showError])

  // 重置状态
  const reset = useCallback(() => {
    setState({
      data: null,
      loading: false,
      error: null,
      progress: 0,
      executed: false
    })
  }, [])

  // 取消请求
  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      setState(prev => ({
        ...prev,
        loading: false,
        progress: 0
      }))
    }
  }, [])

  // 立即执行选项
  useEffect(() => {
    if (immediate && method === 'GET') {
      execute()
    }
  }, [immediate, method, execute])

  return {
    ...state,
    execute,
    reset,
    cancel,
    refresh: () => execute()
  }
}

// 专门用于GET请求的Hook
export function useApiGet<T = any>(url: string, options: UseApiRequestOptions = {}) {
  return useApiRequest<T>('GET', url, { immediate: true, ...options })
}

// 专门用于POST请求的Hook
export function useApiPost<T = any>(url: string, options: UseApiRequestOptions = {}) {
  return useApiRequest<T>('POST', url, options)
}

// 专门用于PUT请求的Hook
export function useApiPut<T = any>(url: string, options: UseApiRequestOptions = {}) {
  return useApiRequest<T>('PUT', url, options)
}

// 专门用于DELETE请求的Hook
export function useApiDelete<T = any>(url: string, options: UseApiRequestOptions = {}) {
  return useApiRequest<T>('DELETE', url, options)
}

// 批量请求Hook
export function useApiBatch() {
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<Error | null>(null)
  
  const execute = useCallback(async (
    requests: Array<{ method: 'GET' | 'POST' | 'PUT' | 'DELETE', url: string, data?: any, options?: ApiRequestOptions }>
  ) => {
    setLoading(true)
    setProgress(0)
    setError(null)
    
    try {
      const results = await ApiClient.batch(requests, (completed, total) => {
        setProgress((completed / total) * 100)
      })
      
      return results
    } catch (error: any) {
      const errorObj = error instanceof Error ? error : new Error(String(error))
      setError(errorObj)
      throw errorObj
    } finally {
      setLoading(false)
      setProgress(100)
    }
  }, [])
  
  return {
    loading,
    progress,
    error,
    execute
  }
}