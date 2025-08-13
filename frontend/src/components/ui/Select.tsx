'use client'

import * as React from 'react'
import { ChevronDownIcon, CheckIcon } from '@heroicons/react/24/outline'
import { cn } from '@/utils'

interface SelectOption {
  label: string
  value: string | number
  disabled?: boolean
}

interface SelectProps {
  options: SelectOption[]
  value?: string | number
  placeholder?: string
  disabled?: boolean
  error?: boolean
  className?: string
  onChange?: (value: string | number) => void
}

export function Select({
  options,
  value,
  placeholder = '请选择...',
  disabled = false,
  error = false,
  className,
  onChange,
}: SelectProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const [selectedOption, setSelectedOption] = React.useState<SelectOption | null>(
    options.find(opt => opt.value === value) || null
  )

  const selectRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    const option = options.find(opt => opt.value === value)
    setSelectedOption(option || null)
  }, [value, options])

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (selectRef.current && !selectRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (option: SelectOption) => {
    if (option.disabled) return
    
    setSelectedOption(option)
    setIsOpen(false)
    onChange?.(option.value)
  }

  return (
    <div ref={selectRef} className="relative">
      <button
        type="button"
        className={cn(
          'relative w-full cursor-pointer rounded-md border bg-white py-2 pl-3 pr-10 text-left shadow-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500 sm:text-sm',
          error ? 'border-red-300' : 'border-gray-300',
          disabled ? 'cursor-not-allowed bg-gray-50 text-gray-500' : 'text-gray-900',
          className
        )}
        disabled={disabled}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span className="block truncate">
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
          <ChevronDownIcon
            className={cn(
              'h-5 w-5 text-gray-400 transition-transform',
              isOpen && 'rotate-180'
            )}
            aria-hidden="true"
          />
        </span>
      </button>

      {isOpen && (
        <div className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
          {options.length === 0 ? (
            <div className="relative cursor-default select-none py-2 px-3 text-gray-500">
              暂无选项
            </div>
          ) : (
            options.map((option, index) => (
              <div
                key={`${option.value}-${index}`}
                className={cn(
                  'relative cursor-pointer select-none py-2 pl-3 pr-9 hover:bg-gray-100',
                  option.disabled && 'cursor-not-allowed text-gray-400',
                  selectedOption?.value === option.value && 'bg-gray-100'
                )}
                onClick={() => handleSelect(option)}
              >
                <span
                  className={cn(
                    'block truncate',
                    selectedOption?.value === option.value && 'font-semibold'
                  )}
                >
                  {option.label}
                </span>

                {selectedOption?.value === option.value && (
                  <span className="absolute inset-y-0 right-0 flex items-center pr-4 text-gray-600">
                    <CheckIcon className="h-5 w-5" aria-hidden="true" />
                  </span>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}