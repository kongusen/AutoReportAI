'use client'

import * as React from 'react'
import { CheckIcon } from '@heroicons/react/24/outline'
import { cn } from '@/utils'

export interface CheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
  description?: string
  error?: string
  indeterminate?: boolean
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, description, error, indeterminate = false, ...props }, ref) => {
    const inputRef = React.useRef<HTMLInputElement>(null)

    React.useEffect(() => {
      if (inputRef.current) {
        inputRef.current.indeterminate = indeterminate
      }
    }, [indeterminate])

    React.useImperativeHandle(ref, () => inputRef.current!)

    return (
      <div className="relative flex items-start">
        <div className="flex h-6 items-center">
          <input
            ref={inputRef}
            type="checkbox"
            className={cn(
              'h-4 w-4 rounded border-gray-300 text-gray-600 focus:ring-2 focus:ring-gray-500 focus:ring-offset-2',
              error && 'border-red-300',
              props.disabled && 'cursor-not-allowed opacity-50',
              className
            )}
            {...props}
          />
        </div>
        
        {(label || description) && (
          <div className="ml-3 text-sm leading-6">
            {label && (
              <label
                htmlFor={props.id}
                className={cn(
                  'font-medium text-gray-900 cursor-pointer',
                  props.disabled && 'cursor-not-allowed text-gray-500'
                )}
              >
                {label}
              </label>
            )}
            {description && (
              <p className="text-gray-500">{description}</p>
            )}
            {error && (
              <p className="mt-1 text-red-600">{error}</p>
            )}
          </div>
        )}
      </div>
    )
  }
)

Checkbox.displayName = 'Checkbox'

export { Checkbox }