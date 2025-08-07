'use client'

import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/utils'

const avatarVariants = cva(
  'relative flex shrink-0 overflow-hidden rounded-full bg-gray-100',
  {
    variants: {
      size: {
        sm: 'h-8 w-8',
        default: 'h-10 w-10',
        lg: 'h-12 w-12',
        xl: 'h-16 w-16',
      },
    },
    defaultVariants: {
      size: 'default',
    },
  }
)

export interface AvatarProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof avatarVariants> {
  src?: string
  alt?: string
  fallback?: string
  showFallback?: boolean
}

export function Avatar({
  className,
  size,
  src,
  alt,
  fallback,
  showFallback = true,
  ...props
}: AvatarProps) {
  const [imageError, setImageError] = React.useState(false)
  const [imageLoaded, setImageLoaded] = React.useState(false)

  const handleImageError = () => {
    setImageError(true)
  }

  const handleImageLoad = () => {
    setImageLoaded(true)
    setImageError(false)
  }

  // 生成初始字母
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }

  const shouldShowFallback = !src || imageError || !imageLoaded

  return (
    <div className={cn(avatarVariants({ size }), className)} {...props}>
      {src && !imageError && (
        <img
          className={cn(
            'aspect-square h-full w-full object-cover',
            !imageLoaded && 'opacity-0'
          )}
          src={src}
          alt={alt || 'Avatar'}
          onError={handleImageError}
          onLoad={handleImageLoad}
        />
      )}
      
      {shouldShowFallback && showFallback && (
        <div className="flex h-full w-full items-center justify-center bg-gray-200 text-gray-600">
          {fallback ? (
            <span className={cn(
              'font-medium',
              size === 'sm' && 'text-xs',
              size === 'default' && 'text-sm',
              size === 'lg' && 'text-base',
              size === 'xl' && 'text-lg'
            )}>
              {typeof fallback === 'string' && fallback.length > 2
                ? getInitials(fallback)
                : fallback}
            </span>
          ) : (
            <svg
              className={cn(
                'text-gray-400',
                size === 'sm' && 'h-4 w-4',
                size === 'default' && 'h-5 w-5',
                size === 'lg' && 'h-6 w-6',
                size === 'xl' && 'h-8 w-8'
              )}
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                clipRule="evenodd"
              />
            </svg>
          )}
        </div>
      )}
    </div>
  )
}