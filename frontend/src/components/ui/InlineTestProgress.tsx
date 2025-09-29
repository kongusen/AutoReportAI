import React from 'react'

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
    <div className="bg-gray-50 border border-gray-200 rounded p-2">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-gray-800">
            正在验证SQL
          </div>
          <div className="text-xs text-gray-600">
            执行SQL查询，验证结果
          </div>
        </div>
        <div className="flex space-x-1">
          <div className="w-1.5 h-1.5 bg-gray-600 rounded-full animate-bounce"></div>
          <div className="w-1.5 h-1.5 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
          <div className="w-1.5 h-1.5 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
        </div>
      </div>
    </div>
  )
}