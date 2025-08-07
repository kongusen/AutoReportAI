'use client'

import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/utils'

const spinnerVariants = cva(
  'animate-spin rounded-full border-2 border-gray-300 border-t-gray-900',
  {
    variants: {
      size: {
        sm: 'h-4 w-4',
        md: 'h-6 w-6',
        lg: 'h-8 w-8',
        xl: 'h-12 w-12',
      },
    },
    defaultVariants: {
      size: 'md',
    },
  }
)

interface LoadingSpinnerProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof spinnerVariants> {
  text?: string
}

export function LoadingSpinner({ className, size, text, ...props }: LoadingSpinnerProps) {
  return (
    <div className={cn('flex items-center gap-2', className)} {...props}>
      <div className={cn(spinnerVariants({ size }))} />
      {text && <span className="text-sm text-gray-600">{text}</span>}
    </div>
  )
}