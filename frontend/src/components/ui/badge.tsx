'use client'

import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border border-transparent px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'bg-gray-900 text-gray-50 hover:bg-gray-900/80',
        secondary: 'bg-gray-100 text-gray-900 hover:bg-gray-100/80',
        destructive: 'bg-red-500 text-gray-50 hover:bg-red-500/80',
        success: 'bg-green-500 text-gray-50 hover:bg-green-500/80',
        warning: 'bg-yellow-500 text-gray-50 hover:bg-yellow-500/80',
        info: 'bg-blue-500 text-gray-50 hover:bg-blue-500/80',
        purple: 'bg-purple-500 text-gray-50 hover:bg-purple-500/80',
        outline: 'border-gray-200 text-gray-950 hover:bg-gray-100',
      },
      size: {
        default: 'px-2.5 py-0.5 text-xs',
        sm: 'px-2 py-0.5 text-xs',
        lg: 'px-3 py-1 text-sm',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  icon?: React.ReactNode
}

function Badge({ className, variant, size, icon, children, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props}>
      {icon && <span className="mr-1">{icon}</span>}
      {children}
    </div>
  )
}

export { Badge, badgeVariants }