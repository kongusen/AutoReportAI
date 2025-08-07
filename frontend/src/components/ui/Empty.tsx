'use client'

import * as React from 'react'
import { cn } from '@/utils'

interface EmptyProps {
  image?: React.ReactNode
  title?: string
  description?: string
  action?: React.ReactNode
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

const DefaultEmptyIcon = () => (
  <svg
    className="mx-auto h-12 w-12 text-gray-400"
    stroke="currentColor"
    fill="none"
    viewBox="0 0 48 48"
    aria-hidden="true"
  >
    <path
      d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

export function Empty({
  image,
  title = '暂无数据',
  description,
  action,
  className,
  size = 'md',
}: EmptyProps) {
  const sizeClasses = {
    sm: 'py-8',
    md: 'py-12',
    lg: 'py-16',
  }

  const textSizeClasses = {
    sm: {
      title: 'text-sm',
      description: 'text-xs',
    },
    md: {
      title: 'text-base',
      description: 'text-sm',
    },
    lg: {
      title: 'text-lg',
      description: 'text-base',
    },
  }

  return (
    <div className={cn('text-center', sizeClasses[size], className)}>
      <div className="mx-auto mb-4">
        {image || <DefaultEmptyIcon />}
      </div>
      
      <h3 className={cn(
        'font-medium text-gray-900',
        textSizeClasses[size].title
      )}>
        {title}
      </h3>
      
      {description && (
        <p className={cn(
          'mt-1 text-gray-500',
          textSizeClasses[size].description
        )}>
          {description}
        </p>
      )}
      
      {action && (
        <div className="mt-6">
          {action}
        </div>
      )}
    </div>
  )
}