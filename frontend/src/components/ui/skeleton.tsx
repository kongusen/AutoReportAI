'use client'

import { cn } from '@/lib/utils'
import { forwardRef } from 'react'

// Base Skeleton Component
interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string
  animate?: boolean
}

export const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, animate = true, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'bg-muted rounded-md',
          animate && 'animate-pulse',
          className
        )}
        {...props}
      />
    )
  }
)

Skeleton.displayName = 'Skeleton'

// Text Skeleton Component
interface TextSkeletonProps {
  lines?: number
  className?: string
  lineHeight?: 'sm' | 'md' | 'lg'
  lastLineWidth?: 'full' | 'half' | 'quarter' | 'three-quarters'
}

export const TextSkeleton = forwardRef<HTMLDivElement, TextSkeletonProps>(
  ({ lines = 3, className, lineHeight = 'md', lastLineWidth = 'three-quarters' }, ref) => {
    const heightClasses = {
      sm: 'h-3',
      md: 'h-4',
      lg: 'h-5',
    }

    const lastLineWidths = {
      full: 'w-full',
      half: 'w-1/2',
      quarter: 'w-1/4',
      'three-quarters': 'w-3/4',
    }

    return (
      <div ref={ref} className={cn('space-y-2', className)}>
        {Array.from({ length: lines }).map((_, index) => (
          <Skeleton
            key={index}
            className={cn(
              heightClasses[lineHeight],
              index === lines - 1 ? lastLineWidths[lastLineWidth] : 'w-full'
            )}
          />
        ))}
      </div>
    )
  }
)

TextSkeleton.displayName = 'TextSkeleton'

// Avatar Skeleton Component
interface AvatarSkeletonProps {
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
  shape?: 'circle' | 'square'
}

export const AvatarSkeleton = forwardRef<HTMLDivElement, AvatarSkeletonProps>(
  ({ size = 'md', className, shape = 'circle' }, ref) => {
    const sizeClasses = {
      sm: 'h-8 w-8',
      md: 'h-10 w-10',
      lg: 'h-12 w-12',
      xl: 'h-16 w-16',
    }

    return (
      <Skeleton
        ref={ref}
        className={cn(
          sizeClasses[size],
          shape === 'circle' ? 'rounded-full' : 'rounded-md',
          className
        )}
      />
    )
  }
)

AvatarSkeleton.displayName = 'AvatarSkeleton'

// Card Skeleton Component
interface CardSkeletonProps {
  className?: string
  showImage?: boolean
  imageHeight?: string
  showAvatar?: boolean
  titleLines?: number
  descriptionLines?: number
  showActions?: boolean
}

export const CardSkeleton = forwardRef<HTMLDivElement, CardSkeletonProps>(
  ({ 
    className, 
    showImage = false, 
    imageHeight = 'h-48',
    showAvatar = false,
    titleLines = 1,
    descriptionLines = 2,
    showActions = false
  }, ref) => {
    return (
      <div ref={ref} className={cn(
        'rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden',
        className
      )}>
        {showImage && (
          <Skeleton className={cn('w-full', imageHeight)} />
        )}
        <div className="p-6">
          {showAvatar && (
            <div className="flex items-center space-x-3 mb-4">
              <AvatarSkeleton size="md" />
              <div className="flex-1">
                <Skeleton className="h-4 w-24 mb-1" />
                <Skeleton className="h-3 w-16" />
              </div>
            </div>
          )}
          
          <div className="space-y-3">
            <TextSkeleton lines={titleLines} lineHeight="lg" />
            <TextSkeleton lines={descriptionLines} lineHeight="sm" />
          </div>

          {showActions && (
            <div className="flex items-center space-x-2 mt-6">
              <Skeleton className="h-9 w-20" />
              <Skeleton className="h-9 w-16" />
            </div>
          )}
        </div>
      </div>
    )
  }
)

CardSkeleton.displayName = 'CardSkeleton'

// Table Skeleton Component
interface TableSkeletonProps {
  rows?: number
  columns?: number
  className?: string
  showHeader?: boolean
}

export const TableSkeleton = forwardRef<HTMLDivElement, TableSkeletonProps>(
  ({ rows = 5, columns = 4, className, showHeader = true }, ref) => {
    return (
      <div ref={ref} className={cn('w-full', className)}>
        <div className="rounded-md border">
          {showHeader && (
            <div className="border-b p-4">
              <div className="flex space-x-4">
                {Array.from({ length: columns }).map((_, index) => (
                  <Skeleton key={index} className="h-4 flex-1" />
                ))}
              </div>
            </div>
          )}
          <div className="divide-y">
            {Array.from({ length: rows }).map((_, rowIndex) => (
              <div key={rowIndex} className="p-4">
                <div className="flex space-x-4">
                  {Array.from({ length: columns }).map((_, colIndex) => (
                    <Skeleton 
                      key={colIndex} 
                      className={cn(
                        'h-4 flex-1',
                        colIndex === 0 && 'w-1/4',
                        colIndex === columns - 1 && 'w-1/6'
                      )} 
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }
)

TableSkeleton.displayName = 'TableSkeleton'

// List Skeleton Component
interface ListSkeletonProps {
  items?: number
  className?: string
  showAvatar?: boolean
  showIcon?: boolean
  variant?: 'simple' | 'detailed'
}

export const ListSkeleton = forwardRef<HTMLDivElement, ListSkeletonProps>(
  ({ items = 5, className, showAvatar = false, showIcon = false, variant = 'simple' }, ref) => {
    return (
      <div ref={ref} className={cn('space-y-3', className)}>
        {Array.from({ length: items }).map((_, index) => (
          <div key={index} className="flex items-center space-x-3 p-3 rounded-lg border">
            {showIcon && <Skeleton className="h-5 w-5" />}
            {showAvatar && <AvatarSkeleton size="sm" />}
            <div className="flex-1 space-y-1">
              <Skeleton className="h-4 w-3/4" />
              {variant === 'detailed' && (
                <>
                  <Skeleton className="h-3 w-1/2" />
                  <Skeleton className="h-3 w-1/4" />
                </>
              )}
            </div>
            <Skeleton className="h-8 w-16" />
          </div>
        ))}
      </div>
    )
  }
)

ListSkeleton.displayName = 'ListSkeleton'

// Form Skeleton Component
interface FormSkeletonProps {
  fields?: number
  className?: string
  showSubmitButton?: boolean
  showTitle?: boolean
}

export const FormSkeleton = forwardRef<HTMLDivElement, FormSkeletonProps>(
  ({ fields = 4, className, showSubmitButton = true, showTitle = true }, ref) => {
    return (
      <div ref={ref} className={cn('space-y-6', className)}>
        {showTitle && (
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64" />
          </div>
        )}
        
        <div className="space-y-4">
          {Array.from({ length: fields }).map((_, index) => (
            <div key={index} className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-10 w-full" />
            </div>
          ))}
        </div>

        {showSubmitButton && (
          <div className="flex space-x-2">
            <Skeleton className="h-10 w-24" />
            <Skeleton className="h-10 w-20" />
          </div>
        )}
      </div>
    )
  }
)

FormSkeleton.displayName = 'FormSkeleton'

// Navigation Skeleton Component
interface NavigationSkeletonProps {
  items?: number
  className?: string
  showLogo?: boolean
  showUserMenu?: boolean
}

export const NavigationSkeleton = forwardRef<HTMLDivElement, NavigationSkeletonProps>(
  ({ items = 5, className, showLogo = true, showUserMenu = true }, ref) => {
    return (
      <div ref={ref} className={cn('flex items-center justify-between p-4 border-b', className)}>
        {showLogo && <Skeleton className="h-8 w-32" />}
        
        <div className="flex items-center space-x-6">
          {Array.from({ length: items }).map((_, index) => (
            <Skeleton key={index} className="h-4 w-16" />
          ))}
        </div>

        {showUserMenu && (
          <div className="flex items-center space-x-3">
            <Skeleton className="h-4 w-20" />
            <AvatarSkeleton size="sm" />
          </div>
        )}
      </div>
    )
  }
)

NavigationSkeleton.displayName = 'NavigationSkeleton'

// Dashboard Skeleton Component
interface DashboardSkeletonProps {
  className?: string
  showStats?: boolean
  showCharts?: boolean
  showRecentActivity?: boolean
}

export const DashboardSkeleton = forwardRef<HTMLDivElement, DashboardSkeletonProps>(
  ({ className, showStats = true, showCharts = true, showRecentActivity = true }, ref) => {
    return (
      <div ref={ref} className={cn('space-y-6', className)}>
        {/* Header */}
        <div className="space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
        </div>

        {/* Stats Cards */}
        {showStats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="p-6 rounded-lg border bg-card">
                <div className="flex items-center justify-between">
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-20" />
                    <Skeleton className="h-8 w-16" />
                  </div>
                  <Skeleton className="h-8 w-8 rounded-full" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Charts */}
        {showCharts && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="p-6 rounded-lg border bg-card">
              <Skeleton className="h-6 w-32 mb-4" />
              <Skeleton className="h-64 w-full" />
            </div>
            <div className="p-6 rounded-lg border bg-card">
              <Skeleton className="h-6 w-32 mb-4" />
              <Skeleton className="h-64 w-full" />
            </div>
          </div>
        )}

        {/* Recent Activity */}
        {showRecentActivity && (
          <div className="p-6 rounded-lg border bg-card">
            <Skeleton className="h-6 w-32 mb-4" />
            <ListSkeleton items={5} variant="detailed" showAvatar />
          </div>
        )}
      </div>
    )
  }
)

DashboardSkeleton.displayName = 'DashboardSkeleton'