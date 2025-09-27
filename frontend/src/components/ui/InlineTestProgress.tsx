import React from 'react'
import { PlayIcon } from '@heroicons/react/24/outline'

interface InlineTestProgressProps {
  isTesting: boolean
  placeholderName: string
}

export const InlineTestProgress: React.FC<InlineTestProgressProps> = ({
  isTesting,
  placeholderName
}) => {
  if (!isTesting) return null

  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
      <div className="flex items-center space-x-3">
        <PlayIcon className="w-4 h-4 text-yellow-600 animate-pulse" />
        <div className="flex-1">
          <div className="text-sm font-medium text-yellow-800 mb-1">
            正在测试SQL
          </div>
          <div className="text-xs text-yellow-600">
            执行SQL查询，验证结果...
          </div>
        </div>
        <div className="flex space-x-1">
          <div className="w-2 h-2 bg-yellow-400 rounded-full animate-bounce"></div>
          <div className="w-2 h-2 bg-yellow-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
          <div className="w-2 h-2 bg-yellow-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
        </div>
      </div>
    </div>
  )
}