'use client'

import React, { useState } from 'react'
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline'
import { Button } from './Button'

interface ExpandablePanelProps {
  title: string
  children: React.ReactNode
  defaultExpanded?: boolean
  className?: string
  triggerClassName?: string
}

export function ExpandablePanel({ 
  title, 
  children, 
  defaultExpanded = false,
  className = "",
  triggerClassName = ""
}: ExpandablePanelProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  return (
    <div className={`border border-gray-200 rounded-lg ${className}`}>
      <Button
        type="button"
        variant="ghost"
        onClick={() => setIsExpanded(!isExpanded)}
        className={`w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 rounded-lg ${triggerClassName}`}
      >
        <span className="font-medium text-gray-900">{title}</span>
        {isExpanded ? (
          <ChevronUpIcon className="w-5 h-5 text-gray-500" />
        ) : (
          <ChevronDownIcon className="w-5 h-5 text-gray-500" />
        )}
      </Button>
      
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-100">
          <div className="pt-4">
            {children}
          </div>
        </div>
      )}
    </div>
  )
}