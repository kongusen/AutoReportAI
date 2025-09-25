'use client'

import React from 'react'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'

interface DeprecationNoticeProps {
  apiEndpoint: string
  deprecationMessage?: string
  replacement?: Record<string, string>
  onDismiss?: () => void
  showDetails?: boolean
}

/**
 * API弃用提示组件
 * 当检测到调用了弃用的API接口时显示迁移指导
 */
export default function DeprecationNotice({
  apiEndpoint,
  deprecationMessage,
  replacement,
  onDismiss,
  showDetails = true
}: DeprecationNoticeProps) {
  return (
    <Card className="p-4 bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800">
      <div className="space-y-3">
        {/* 标题 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Badge variant="outline" className="text-yellow-700 border-yellow-600">
              ⚠️ API弃用警告
            </Badge>
            <span className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              接口已升级
            </span>
          </div>
          {onDismiss && (
            <Button
              onClick={onDismiss}
              variant="ghost"
              size="sm"
              className="text-yellow-600 hover:text-yellow-800"
            >
              ✕
            </Button>
          )}
        </div>

        {/* 弃用接口信息 */}
        <div className="space-y-2">
          <div className="text-sm">
            <span className="font-medium">弃用接口:</span>
            <code className="ml-2 px-2 py-1 bg-yellow-100 dark:bg-yellow-900 rounded text-xs">
              {apiEndpoint}
            </code>
          </div>

          {deprecationMessage && (
            <div className="text-sm text-yellow-700 dark:text-yellow-300">
              <span className="font-medium">说明:</span> {deprecationMessage}
            </div>
          )}
        </div>

        {/* 迁移指导 */}
        {replacement && showDetails && (
          <div className="space-y-2">
            <div className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              推荐使用新接口:
            </div>
            <div className="space-y-1">
              {Object.entries(replacement).map(([action, endpoint]) => (
                <div key={action} className="flex items-center space-x-2 text-sm">
                  <Badge variant="outline" size="sm" className="text-green-600 border-green-600">
                    {action}
                  </Badge>
                  <code className="px-2 py-1 bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300 rounded text-xs">
                    {endpoint}
                  </code>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 迁移说明 */}
        <div className="text-xs text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900 p-2 rounded">
          💡 <strong>自动迁移:</strong> 系统已自动使用新接口，您的操作不受影响。建议开发团队更新相关代码。
        </div>
      </div>
    </Card>
  )
}