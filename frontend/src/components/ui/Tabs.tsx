'use client'

import * as React from 'react'
import { cn } from '@/utils'

interface TabItem {
  key: string
  label: string
  disabled?: boolean
  icon?: React.ReactNode
}

interface TabsProps {
  items: TabItem[]
  activeKey?: string
  defaultActiveKey?: string
  onChange?: (key: string) => void
  className?: string
  variant?: 'line' | 'card'
  size?: 'sm' | 'default' | 'lg'
  children?: React.ReactNode
}

interface TabPanelProps {
  children: React.ReactNode
  value: string
  activeValue: string
  className?: string
}

const TabsContext = React.createContext<{
  activeKey: string
  setActiveKey: (key: string) => void
}>({
  activeKey: '',
  setActiveKey: () => {},
})

export function Tabs({
  items,
  activeKey,
  defaultActiveKey,
  onChange,
  className,
  variant = 'line',
  size = 'default',
  children,
}: TabsProps) {
  const [internalActiveKey, setInternalActiveKey] = React.useState(
    defaultActiveKey || items[0]?.key || ''
  )
  
  const isControlled = activeKey !== undefined
  const currentActiveKey = isControlled ? activeKey : internalActiveKey

  const handleTabChange = (key: string) => {
    if (!isControlled) {
      setInternalActiveKey(key)
    }
    onChange?.(key)
  }

  const sizeClasses = {
    sm: 'px-3 py-2 text-sm',
    default: 'px-4 py-2.5 text-sm',
    lg: 'px-6 py-3 text-base',
  }

  const variantClasses = {
    line: {
      container: 'border-b border-gray-200',
      tab: 'border-b-2 border-transparent hover:border-gray-300 hover:text-gray-700',
      activeTab: 'border-gray-900 text-gray-900',
      inactiveTab: 'text-gray-500',
    },
    card: {
      container: 'bg-gray-100 p-1 rounded-lg',
      tab: 'rounded-md hover:bg-white hover:shadow-sm',
      activeTab: 'bg-white shadow-sm text-gray-900',
      inactiveTab: 'text-gray-600',
    },
  }

  const currentVariant = variantClasses[variant]

  return (
    <TabsContext.Provider value={{ activeKey: currentActiveKey, setActiveKey: handleTabChange }}>
      <div className={className}>
        {/* Tab Navigation */}
        <div className={cn('flex', currentVariant.container)}>
          {items.map((item) => (
            <button
              key={item.key}
              type="button"
              className={cn(
                'flex items-center gap-2 font-medium transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2',
                sizeClasses[size],
                currentVariant.tab,
                currentActiveKey === item.key
                  ? currentVariant.activeTab
                  : currentVariant.inactiveTab,
                item.disabled && 'cursor-not-allowed opacity-50'
              )}
              disabled={item.disabled}
              onClick={() => !item.disabled && handleTabChange(item.key)}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="mt-4">
          {children}
        </div>
      </div>
    </TabsContext.Provider>
  )
}

export function TabPanel({ children, value, activeValue, className }: TabPanelProps) {
  if (value !== activeValue) return null
  
  return (
    <div className={cn('animate-fade-in', className)}>
      {children}
    </div>
  )
}

export function useTabsContext() {
  const context = React.useContext(TabsContext)
  if (!context) {
    throw new Error('useTabsContext must be used within a Tabs component')
  }
  return context
}