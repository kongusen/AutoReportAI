'use client'

import { Progress } from '@/components/ui/progress'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { forwardRef } from 'react'

interface ProgressIndicatorProps {
  progress: number
  title?: string
  description?: string
  showPercentage?: boolean
  className?: string
  variant?: 'default' | 'compact' | 'card'
  size?: 'sm' | 'md' | 'lg'
}

export const ProgressIndicator = forwardRef<HTMLDivElement, ProgressIndicatorProps>(
  ({ 
    progress, 
    title, 
    description, 
    showPercentage = true, 
    className,
    variant = 'default',
    size = 'md'
  }, ref) => {
    const sizeClasses = {
      sm: 'h-1',
      md: 'h-2',
      lg: 'h-3',
    }

    if (variant === 'compact') {
      return (
        <div ref={ref} className={cn('flex items-center space-x-2', className)}>
          <Progress value={progress} className={cn('flex-1', sizeClasses[size])} />
          {showPercentage && (
            <span className="text-sm text-muted-foreground min-w-[3rem]">
              {Math.round(progress)}%
            </span>
          )}
        </div>
      )
    }

    if (variant === 'card') {
      return (
        <Card ref={ref} className={cn('w-full', className)}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">{title || 'Progress'}</CardTitle>
            {description && (
              <p className="text-xs text-muted-foreground">{description}</p>
            )}
          </CardHeader>
          <CardContent className="space-y-2">
            <Progress value={progress} className={sizeClasses[size]} />
            {showPercentage && (
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>0%</span>
                <span>{Math.round(progress)}%</span>
                <span>100%</span>
              </div>
            )}
          </CardContent>
        </Card>
      )
    }

    return (
      <div ref={ref} className={cn('space-y-2', className)}>
        {(title || description) && (
          <div className="space-y-1">
            {title && <h4 className="text-sm font-medium">{title}</h4>}
            {description && <p className="text-xs text-muted-foreground">{description}</p>}
          </div>
        )}
        <div className="flex items-center space-x-2">
          <Progress value={progress} className={cn('flex-1', sizeClasses[size])} />
          {showPercentage && (
            <span className="text-sm text-muted-foreground min-w-[3rem]">
              {Math.round(progress)}%
            </span>
          )}
        </div>
      </div>
    )
  }
)

ProgressIndicator.displayName = 'ProgressIndicator' 