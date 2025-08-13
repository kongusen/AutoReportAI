'use client'

import * as React from 'react'
import { cn } from '@/utils'

export interface SwitchProps {
  checked?: boolean
  defaultChecked?: boolean
  disabled?: boolean
  size?: 'sm' | 'default' | 'lg'
  label?: string
  description?: string
  onChange?: (checked: boolean) => void
  className?: string
  id?: string
}

export function Switch({
  checked,
  defaultChecked = false,
  disabled = false,
  size = 'default',
  label,
  description,
  onChange,
  className,
  id,
}: SwitchProps) {
  const [internalChecked, setInternalChecked] = React.useState(defaultChecked)
  const isControlled = checked !== undefined
  const switchChecked = isControlled ? checked : internalChecked

  const handleToggle = () => {
    if (disabled) return
    
    const newChecked = !switchChecked
    if (!isControlled) {
      setInternalChecked(newChecked)
    }
    onChange?.(newChecked)
  }

  const sizeClasses = {
    sm: {
      container: 'h-5 w-9',
      thumb: 'h-4 w-4',
      translate: 'translate-x-4',
    },
    default: {
      container: 'h-6 w-11',
      thumb: 'h-5 w-5',
      translate: 'translate-x-5',
    },
    lg: {
      container: 'h-7 w-12',
      thumb: 'h-6 w-6',
      translate: 'translate-x-5',
    },
  }

  const currentSize = sizeClasses[size]

  return (
    <div className={cn('flex items-center', className)}>
      <button
        type="button"
        role="switch"
        aria-checked={switchChecked}
        aria-describedby={description ? `${id}-description` : undefined}
        className={cn(
          'relative inline-flex flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2',
          currentSize.container,
          switchChecked ? 'bg-gray-600' : 'bg-gray-200',
          disabled && 'cursor-not-allowed opacity-50'
        )}
        disabled={disabled}
        onClick={handleToggle}
      >
        <span
          aria-hidden="true"
          className={cn(
            'pointer-events-none inline-block transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
            currentSize.thumb,
            switchChecked ? currentSize.translate : 'translate-x-0'
          )}
        />
      </button>

      {(label || description) && (
        <div className="ml-3">
          {label && (
            <label
              htmlFor={id}
              className={cn(
                'text-sm font-medium text-gray-900 cursor-pointer',
                disabled && 'cursor-not-allowed text-gray-500'
              )}
            >
              {label}
            </label>
          )}
          {description && (
            <p
              id={`${id}-description`}
              className="text-sm text-gray-500"
            >
              {description}
            </p>
          )}
        </div>
      )}
    </div>
  )
}