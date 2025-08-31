/**
 * 进度指示器组件 - 支持多种样式和动画
 */

import React from 'react'
import { cn } from '@/utils'

export interface ProgressIndicatorProps {
  // 进度值 0-100
  progress?: number
  // 是否显示百分比文本
  showText?: boolean
  // 是否是不确定的进度（循环动画）
  indeterminate?: boolean
  // 尺寸
  size?: 'sm' | 'md' | 'lg'
  // 样式变体
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info'
  // 形状
  shape?: 'linear' | 'circular' | 'ring'
  // 自定义类名
  className?: string
  // 标签
  label?: string
  // 子步骤
  steps?: Array<{ label: string; completed: boolean }>
  // 动画速度
  speed?: 'slow' | 'normal' | 'fast'
}

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  progress = 0,
  showText = false,
  indeterminate = false,
  size = 'md',
  variant = 'default',
  shape = 'linear',
  className,
  label,
  steps,
  speed = 'normal'
}) => {
  const sizeClasses = {
    sm: {
      linear: 'h-1',
      circular: 'w-4 h-4',
      ring: 'w-6 h-6'
    },
    md: {
      linear: 'h-2',
      circular: 'w-6 h-6', 
      ring: 'w-8 h-8'
    },
    lg: {
      linear: 'h-3',
      circular: 'w-8 h-8',
      ring: 'w-10 h-10'
    }
  }

  const variantClasses = {
    default: 'text-blue-600 bg-blue-600',
    success: 'text-green-600 bg-green-600',
    warning: 'text-yellow-600 bg-yellow-600', 
    error: 'text-red-600 bg-red-600',
    info: 'text-indigo-600 bg-indigo-600'
  }

  const speedClasses = {
    slow: 'duration-1000',
    normal: 'duration-500',
    fast: 'duration-200'
  }

  // 线性进度条
  if (shape === 'linear') {
    return (
      <div className={cn('space-y-2', className)}>
        {label && (
          <div className="flex justify-between items-center text-sm">
            <span className="font-medium text-gray-700">{label}</span>
            {showText && !indeterminate && (
              <span className="text-gray-500">{Math.round(progress)}%</span>
            )}
          </div>
        )}
        
        <div className={cn(
          'w-full bg-gray-200 rounded-full overflow-hidden',
          sizeClasses[size].linear
        )}>
          <div
            className={cn(
              'h-full rounded-full transition-all ease-out',
              variantClasses[variant].split(' ')[1],
              speedClasses[speed],
              indeterminate && 'animate-pulse'
            )}
            style={{
              width: indeterminate ? '100%' : `${Math.min(100, Math.max(0, progress))}%`,
              background: indeterminate 
                ? `linear-gradient(90deg, transparent, ${variantClasses[variant].split(' ')[1]}, transparent)`
                : undefined
            }}
          />
        </div>

        {steps && (
          <div className="space-y-1">
            {steps.map((step, index) => (
              <div key={index} className="flex items-center space-x-2 text-sm">
                <div className={cn(
                  'w-2 h-2 rounded-full',
                  step.completed ? variantClasses[variant].split(' ')[1] : 'bg-gray-300'
                )} />
                <span className={cn(
                  step.completed ? 'text-gray-900' : 'text-gray-500'
                )}>
                  {step.label}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  // 环形进度条
  if (shape === 'ring') {
    const radius = 16
    const circumference = 2 * Math.PI * radius
    const strokeDashoffset = circumference - (progress / 100) * circumference

    return (
      <div className={cn('relative inline-flex items-center justify-center', className)}>
        <svg
          className={cn(
            'transform -rotate-90',
            sizeClasses[size].ring
          )}
          viewBox="0 0 40 40"
        >
          {/* 背景圆环 */}
          <circle
            cx="20"
            cy="20"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            className="text-gray-200"
          />
          {/* 进度圆环 */}
          <circle
            cx="20"
            cy="20"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={indeterminate ? 0 : strokeDashoffset}
            className={cn(
              'transition-all ease-out',
              variantClasses[variant].split(' ')[0],
              speedClasses[speed],
              indeterminate && 'animate-spin'
            )}
            style={{
              strokeDasharray: indeterminate ? `${circumference * 0.25} ${circumference}` : circumference
            }}
          />
        </svg>
        {showText && !indeterminate && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-xs font-medium">
              {Math.round(progress)}%
            </span>
          </div>
        )}
      </div>
    )
  }

  // 圆形进度条（简单版本）
  return (
    <div className={cn(
      'rounded-full border-4 animate-spin',
      sizeClasses[size].circular,
      variantClasses[variant].split(' ')[0],
      'border-current border-r-transparent',
      className
    )} />
  )
}

// 多步骤进度组件
export interface StepProgressProps {
  steps: Array<{
    id: string
    title: string
    description?: string
    status: 'pending' | 'active' | 'completed' | 'error'
  }>
  className?: string
}

export const StepProgress: React.FC<StepProgressProps> = ({
  steps,
  className
}) => {
  return (
    <div className={cn('space-y-4', className)}>
      {steps.map((step, index) => {
        const isLast = index === steps.length - 1
        
        return (
          <div key={step.id} className="relative">
            {/* 连接线 */}
            {!isLast && (
              <div className="absolute left-4 top-8 w-px h-6 bg-gray-300" />
            )}
            
            <div className="flex items-start space-x-3">
              {/* 状态图标 */}
              <div className={cn(
                'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center border-2',
                {
                  'bg-gray-100 border-gray-300 text-gray-400': step.status === 'pending',
                  'bg-blue-100 border-blue-500 text-blue-600': step.status === 'active',
                  'bg-green-100 border-green-500 text-green-600': step.status === 'completed',
                  'bg-red-100 border-red-500 text-red-600': step.status === 'error',
                }
              )}>
                {step.status === 'completed' && (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                )}
                {step.status === 'error' && (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                )}
                {(step.status === 'pending' || step.status === 'active') && (
                  <span className="text-sm font-medium">{index + 1}</span>
                )}
              </div>
              
              {/* 步骤内容 */}
              <div className="flex-1 min-w-0">
                <h3 className={cn(
                  'text-sm font-medium',
                  {
                    'text-gray-500': step.status === 'pending',
                    'text-gray-900': step.status === 'active' || step.status === 'completed',
                    'text-red-900': step.status === 'error',
                  }
                )}>
                  {step.title}
                </h3>
                {step.description && (
                  <p className={cn(
                    'text-sm mt-1',
                    {
                      'text-gray-400': step.status === 'pending',
                      'text-gray-600': step.status === 'active' || step.status === 'completed',
                      'text-red-600': step.status === 'error',
                    }
                  )}>
                    {step.description}
                  </p>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}