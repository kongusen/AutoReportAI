'use client'

import React, { createContext, useContext, useCallback, useState, useRef } from 'react'
import { LoadingOverlay, LoadingCard, ProgressBar } from '@/components/ui/loading'
import { cn } from '@/lib/utils'

interface LoadingState {
  id: string
  message?: string
  progress?: number
  type: 'overlay' | 'card' | 'inline' | 'global'
  priority: number
  timestamp: number
}

interface LoadingContextValue {
  // State
  loadingStates: LoadingState[]
  isGlobalLoading: boolean
  
  // Actions
  showLoading: (id: string, options?: Partial<LoadingState>) => void
  hideLoading: (id: string) => void
  updateLoading: (id: string, updates: Partial<LoadingState>) => void
  clearAllLoading: () => void
  
  // Utilities
  isLoading: (id: string) => boolean
  getLoadingState: (id: string) => LoadingState | undefined
  getHighestPriorityLoading: () => LoadingState | undefined
}

const LoadingContext = createContext<LoadingContextValue | undefined>(undefined)

interface LoadingProviderProps {
  children: React.ReactNode
  globalLoadingComponent?: React.ComponentType<{ loading: LoadingState }>
  maxConcurrentLoading?: number
}

export function LoadingProvider({ 
  children, 
  globalLoadingComponent: GlobalLoadingComponent,
  maxConcurrentLoading = 5 
}: LoadingProviderProps) {
  const [loadingStates, setLoadingStates] = useState<LoadingState[]>([])
  const nextIdRef = useRef(0)

  const showLoading = useCallback((id: string, options: Partial<LoadingState> = {}) => {
    setLoadingStates(prev => {
      // Remove existing loading state with same id
      const filtered = prev.filter(state => state.id !== id)
      
      // Create new loading state
      const newState: LoadingState = {
        id,
        message: options.message,
        progress: options.progress,
        type: options.type || 'inline',
        priority: options.priority || 0,
        timestamp: Date.now(),
      }

      // Add new state and sort by priority (higher priority first)
      const newStates = [...filtered, newState].sort((a, b) => b.priority - a.priority)
      
      // Limit concurrent loading states
      return newStates.slice(0, maxConcurrentLoading)
    })
  }, [maxConcurrentLoading])

  const hideLoading = useCallback((id: string) => {
    setLoadingStates(prev => prev.filter(state => state.id !== id))
  }, [])

  const updateLoading = useCallback((id: string, updates: Partial<LoadingState>) => {
    setLoadingStates(prev => prev.map(state => 
      state.id === id ? { ...state, ...updates } : state
    ))
  }, [])

  const clearAllLoading = useCallback(() => {
    setLoadingStates([])
  }, [])

  const isLoading = useCallback((id: string) => {
    return loadingStates.some(state => state.id === id)
  }, [loadingStates])

  const getLoadingState = useCallback((id: string) => {
    return loadingStates.find(state => state.id === id)
  }, [loadingStates])

  const getHighestPriorityLoading = useCallback(() => {
    return loadingStates[0] // Already sorted by priority
  }, [loadingStates])

  const isGlobalLoading = loadingStates.some(state => state.type === 'global')
  const globalLoadingState = loadingStates.find(state => state.type === 'global')

  const contextValue: LoadingContextValue = {
    loadingStates,
    isGlobalLoading,
    showLoading,
    hideLoading,
    updateLoading,
    clearAllLoading,
    isLoading,
    getLoadingState,
    getHighestPriorityLoading,
  }

  return (
    <LoadingContext.Provider value={contextValue}>
      {children}
      
      {/* Global Loading Overlay */}
      {isGlobalLoading && globalLoadingState && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-background/80 backdrop-blur-sm">
          {GlobalLoadingComponent ? (
            <GlobalLoadingComponent loading={globalLoadingState} />
          ) : (
            <LoadingCard
              title={globalLoadingState.message || 'Loading...'}
              showProgress={globalLoadingState.progress !== undefined}
              progress={globalLoadingState.progress || 0}
              className="max-w-sm"
            />
          )}
        </div>
      )}
    </LoadingContext.Provider>
  )
}

export function useLoading() {
  const context = useContext(LoadingContext)
  if (context === undefined) {
    throw new Error('useLoading must be used within a LoadingProvider')
  }
  return context
}

// Higher-order component for automatic loading management
interface WithLoadingProps {
  loadingId?: string
  loadingMessage?: string
  loadingType?: LoadingState['type']
  loadingPriority?: number
  showLoadingAfter?: number
}

export function withLoading<P extends object>(
  Component: React.ComponentType<P>,
  defaultOptions: WithLoadingProps = {}
) {
  return function WithLoadingComponent(props: P & WithLoadingProps) {
    const {
      loadingId = 'component-loading',
      loadingMessage,
      loadingType = 'inline',
      loadingPriority = 0,
      showLoadingAfter = 200,
      ...componentProps
    } = { ...defaultOptions, ...props }

    const { showLoading, hideLoading, isLoading: isLoadingState } = useLoading()
    const [showLoading_, setShowLoading_] = useState(false)
    const timeoutRef = useRef<NodeJS.Timeout | undefined>(undefined)

    const startLoading = useCallback(() => {
      timeoutRef.current = setTimeout(() => {
        setShowLoading_(true)
        showLoading(loadingId, {
          message: loadingMessage,
          type: loadingType,
          priority: loadingPriority,
        })
      }, showLoadingAfter)
    }, [loadingId, loadingMessage, loadingType, loadingPriority, showLoadingAfter, showLoading])

    const stopLoading = useCallback(() => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
      setShowLoading_(false)
      hideLoading(loadingId)
    }, [loadingId, hideLoading])

    React.useEffect(() => {
      return () => {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current)
        }
        hideLoading(loadingId)
      }
    }, [loadingId, hideLoading])

    const isLoading = isLoadingState(loadingId)

    return (
      <LoadingOverlay isLoading={isLoading && showLoading_}>
        <Component 
          {...(componentProps as P)} 
          startLoading={startLoading}
          stopLoading={stopLoading}
          isLoading={isLoading}
        />
      </LoadingOverlay>
    )
  }
}

// Hook for managing component-level loading
export function useComponentLoading(id: string, options: Partial<LoadingState> = {}) {
  const { showLoading, hideLoading, updateLoading, isLoading, getLoadingState } = useLoading()

  const start = useCallback((overrides: Partial<LoadingState> = {}) => {
    showLoading(id, { ...options, ...overrides })
  }, [id, options, showLoading])

  const stop = useCallback(() => {
    hideLoading(id)
  }, [id, hideLoading])

  const update = useCallback((updates: Partial<LoadingState>) => {
    updateLoading(id, updates)
  }, [id, updateLoading])

  const loading = isLoading(id)
  const state = getLoadingState(id)

  return {
    loading,
    state,
    start,
    stop,
    update,
  }
}

// Hook for async operations with automatic loading management
export function useAsyncLoading<T extends any[], R>(
  asyncFn: (...args: T) => Promise<R>,
  loadingId: string,
  options: Partial<LoadingState> = {}
) {
  const [data, setData] = useState<R | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const { start, stop, loading } = useComponentLoading(loadingId, options)

  const execute = useCallback(async (...args: T) => {
    try {
      setError(null)
      start()
      const result = await asyncFn(...args)
      setData(result)
      return result
    } catch (err) {
      setError(err as Error)
      throw err
    } finally {
      stop()
    }
  }, [asyncFn, start, stop])

  const reset = useCallback(() => {
    setData(null)
    setError(null)
    stop()
  }, [stop])

  return {
    data,
    error,
    loading,
    execute,
    reset,
  }
}

// Hook for form submission with loading
export function useFormLoading(onSubmit: (data: any) => Promise<void>) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const handleSubmit = useCallback(async (data: any) => {
    if (isSubmitting) return

    setIsSubmitting(true)
    setSubmitError(null)

    try {
      await onSubmit(data)
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'An error occurred')
      throw error
    } finally {
      setIsSubmitting(false)
    }
  }, [onSubmit, isSubmitting])

  return {
    isSubmitting,
    submitError,
    handleSubmit,
    clearError: () => setSubmitError(null),
  }
}