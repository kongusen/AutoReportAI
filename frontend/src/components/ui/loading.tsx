'use client'

import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'
import { forwardRef } from 'react'

// Loading Spinner Component
interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
  color?: 'primary' | 'secondary' | 'muted'
}

export const LoadingSpinner = forwardRef<HTMLDivElement, LoadingSpinnerProps>(
  ({ size = 'md', className, color = 'primary' }, ref) => {
    const sizeClasses = {
      sm: 'h-4 w-4',
      md: 'h-6 w-6',
      lg: 'h-8 w-8',
      xl: 'h-12 w-12',
    }

    const colorClasses = {
      primary: 'text-primary',
      secondary: 'text-secondary-foreground',
      muted: 'text-muted-foreground',
    }

    return (
      <div ref={ref} className={cn('flex items-center justify-center', className)}>
        <Loader2 
          className={cn(
            'animate-spin',
            sizeClasses[size],
            colorClasses[color]
          )}
        />
      </div>
    )
  }
)

LoadingSpinner.displayName = 'LoadingSpinner'

// Loading Overlay Component
interface LoadingOverlayProps {
  isLoading: boolean
  children: React.ReactNode
  className?: string
  spinnerSize?: 'sm' | 'md' | 'lg' | 'xl'
  message?: string
  blur?: boolean
}

export const LoadingOverlay = forwardRef<HTMLDivElement, LoadingOverlayProps>(
  ({ isLoading, children, className, spinnerSize = 'lg', message, blur = true }, ref) => {
    return (
      <div ref={ref} className={cn('relative', className)}>
        {children}
        {isLoading && (
          <div 
            className={cn(
              'absolute inset-0 z-50 flex flex-col items-center justify-center',
              'bg-background/80 backdrop-blur-sm',
              blur && 'backdrop-blur-md'
            )}
          >
            <LoadingSpinner size={spinnerSize} />
            {message && (
              <p className="mt-4 text-sm text-muted-foreground animate-pulse">
                {message}
              </p>
            )}
          </div>
        )}
      </div>
    )
  }
)

LoadingOverlay.displayName = 'LoadingOverlay'

// Loading Button Component
interface LoadingButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  isLoading?: boolean
  loadingText?: string
  spinnerSize?: 'sm' | 'md'
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'
  size?: 'default' | 'sm' | 'lg' | 'icon'
}

export const LoadingButton = forwardRef<HTMLButtonElement, LoadingButtonProps>(
  ({ 
    isLoading = false, 
    loadingText, 
    spinnerSize = 'sm', 
    children, 
    disabled, 
    className,
    ...props 
  }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          'inline-flex items-center justify-center gap-2',
          'whitespace-nowrap rounded-md text-sm font-medium',
          'ring-offset-background transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          'disabled:pointer-events-none disabled:opacity-50',
          // Default variant styles
          'bg-primary text-primary-foreground hover:bg-primary/90',
          // Size styles
          'h-10 px-4 py-2',
          className
        )}
        {...props}
      >
        {isLoading && (
          <Loader2 className={cn(
            'animate-spin',
            spinnerSize === 'sm' ? 'h-4 w-4' : 'h-5 w-5'
          )} />
        )}
        {isLoading ? loadingText || 'Loading...' : children}
      </button>
    )
  }
)

LoadingButton.displayName = 'LoadingButton'

// Loading Dots Component
interface LoadingDotsProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
  color?: 'primary' | 'secondary' | 'muted'
}

export const LoadingDots = forwardRef<HTMLDivElement, LoadingDotsProps>(
  ({ className, size = 'md', color = 'primary' }, ref) => {
    const sizeClasses = {
      sm: 'h-1 w-1',
      md: 'h-2 w-2',
      lg: 'h-3 w-3',
    }

    const colorClasses = {
      primary: 'bg-primary',
      secondary: 'bg-secondary-foreground',
      muted: 'bg-muted-foreground',
    }

    return (
      <div ref={ref} className={cn('flex items-center space-x-1', className)}>
        {[0, 1, 2].map((index) => (
          <div
            key={index}
            className={cn(
              'rounded-full animate-pulse',
              sizeClasses[size],
              colorClasses[color]
            )}
            style={{
              animationDelay: `${index * 0.2}s`,
              animationDuration: '1.4s',
            }}
          />
        ))}
      </div>
    )
  }
)

LoadingDots.displayName = 'LoadingDots'

// Progress Bar Component
interface ProgressBarProps {
  progress: number
  className?: string
  showPercentage?: boolean
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error'
  size?: 'sm' | 'md' | 'lg'
  animated?: boolean
}

export const ProgressBar = forwardRef<HTMLDivElement, ProgressBarProps>(
  ({ 
    progress, 
    className, 
    showPercentage = false, 
    color = 'primary',
    size = 'md',
    animated = true
  }, ref) => {
    const sizeClasses = {
      sm: 'h-1',
      md: 'h-2',
      lg: 'h-3',
    }

    const colorClasses = {
      primary: 'bg-primary',
      secondary: 'bg-secondary',
      success: 'bg-green-500',
      warning: 'bg-yellow-500',
      error: 'bg-red-500',
    }

    const clampedProgress = Math.min(Math.max(progress, 0), 100)

    return (
      <div ref={ref} className={cn('w-full', className)}>
        <div className={cn(
          'w-full bg-secondary rounded-full overflow-hidden',
          sizeClasses[size]
        )}>
          <div
            className={cn(
              'h-full transition-all duration-300 ease-out',
              colorClasses[color],
              animated && 'animate-pulse'
            )}
            style={{ width: `${clampedProgress}%` }}
          />
        </div>
        {showPercentage && (
          <div className="mt-1 text-xs text-muted-foreground text-center">
            {Math.round(clampedProgress)}%
          </div>
        )}
      </div>
    )
  }
)

ProgressBar.displayName = 'ProgressBar'

// Loading Card Component
interface LoadingCardProps {
  className?: string
  title?: string
  description?: string
  showProgress?: boolean
  progress?: number
}

export const LoadingCard = forwardRef<HTMLDivElement, LoadingCardProps>(
  ({ className, title, description, showProgress = false, progress = 0 }, ref) => {
    return (
      <div ref={ref} className={cn(
        'rounded-lg border bg-card text-card-foreground shadow-sm p-6',
        className
      )}>
        <div className="flex items-center space-x-4">
          <LoadingSpinner size="lg" />
          <div className="flex-1 space-y-2">
            {title && (
              <h3 className="text-lg font-semibold">{title}</h3>
            )}
            {description && (
              <p className="text-sm text-muted-foreground">{description}</p>
            )}
            {showProgress && (
              <ProgressBar 
                progress={progress} 
                showPercentage 
                className="mt-3"
              />
            )}
          </div>
        </div>
      </div>
    )
  }
)

LoadingCard.displayName = 'LoadingCard'