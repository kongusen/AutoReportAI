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
}

export function Progress({
  className,
  value,
  max = 100,
  size,
  variant = 'default',
  showPercent = false,
  animated = false,
  ...props
}: ProgressProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)

  return (
    <div className="w-full">
      <div
        className={cn(progressVariants({ size }), className)}
        {...props}
      >
        <div
          className={cn(
            progressBarVariants({ variant }),
            animated && 'animate-pulse'
          )}
          style={{
            transform: `translateX(-${100 - percentage}%)`,
          }}
        />
      </div>
      {showPercent && (
        <div className="mt-1 text-right text-xs text-gray-600">
          {Math.round(percentage)}%
        </div>
      )}
    </div>
  )
}