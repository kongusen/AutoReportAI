'use client'

import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/utils'

const progressVariants = cva(
  'relative w-full overflow-hidden rounded-full bg-gray-200',
  {
    variants: {
      size: {
        sm: 'h-2',
        default: 'h-3',
        lg: 'h-4',
      },
    },
    defaultVariants: {
      size: 'default',
    },
  }
)

const progressBarVariants = cva(
  'h-full w-full flex-1 transition-all duration-300 ease-in-out',
  {
    variants: {
      variant: {
        default: 'bg-gray-900',
        success: 'bg-green-500',
        warning: 'bg-yellow-500',
        error: 'bg-red-500',
        info: 'bg-blue-500',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export interface ProgressProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof progressVariants>,
    VariantProps<typeof progressBarVariants> {
  value: number
  max?: number
  showPercent?: boolean
  animated?: boolean
  status?: 'pending' | 'processing' | 'completed' | 'failed' | 'warning'
  message?: string
  errorDetails?: string
  showMessage?: boolean
  onRetry?: () => void
}

export function Progress({
  className,
  value,
  max = 100,
  size,
  variant = 'default',
  showPercent = false,
  animated = false,
  status,
  message,
  errorDetails,
  showMessage = true,
  onRetry,
  ...props
}: ProgressProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)
  
  // 根据状态自动设置variant
  const getVariantByStatus = (status?: string) => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'failed':
        return 'error'
      case 'warning':
        return 'warning'
      case 'processing':
        return 'info'
      default:
        return variant
    }
  }
  
  const finalVariant = status ? getVariantByStatus(status) : variant
  const isAnimated = animated || (status === 'processing' && percentage < 100)
  
  return (
    <div className="w-full">
      <div
        className={cn(progressVariants({ size }), className)}
        {...props}
      >
        <div
          className={cn(
            progressBarVariants({ variant: finalVariant }),
            isAnimated && 'animate-pulse'
          )}
          style={{
            transform: `translateX(-${100 - percentage}%)`,
          }}
        />
      </div>
      
      <div className="mt-1 flex items-center justify-between">
        {/* 状态消息 */}
        {showMessage && message && (
          <div className={cn(
            "text-xs flex-1",
            status === 'failed' ? 'text-red-600' : 
            status === 'completed' ? 'text-green-600' :
            status === 'warning' ? 'text-yellow-600' :
            'text-gray-600'
          )}>
            {message}
          </div>
        )}
        
        {/* 百分比显示 */}
        {showPercent && (
          <div className="text-xs text-gray-600 ml-2">
            {Math.round(percentage)}%
          </div>
        )}
      </div>
      
      {/* 错误详情和重试按钮 */}
      {status === 'failed' && (
        <div className="mt-2 space-y-1">
          {errorDetails && (
            <details className="text-xs text-gray-500">
              <summary className="cursor-pointer hover:text-gray-700">
                错误详情
              </summary>
              <pre className="mt-1 p-2 bg-gray-50 rounded text-xs overflow-auto max-h-20">
                {errorDetails}
              </pre>
            </details>
          )}
          {onRetry && (
            <button
              onClick={onRetry}
              className="text-xs text-blue-600 hover:text-blue-800 underline"
            >
              重试
            </button>
          )}
        </div>
      )}
      
      {/* 警告状态的额外信息 */}
      {status === 'warning' && errorDetails && (
        <div className="mt-1 text-xs text-yellow-700 bg-yellow-50 p-2 rounded">
          {errorDetails}
        </div>
      )}
    </div>
  )
}