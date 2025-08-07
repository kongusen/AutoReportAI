'use client'

import { useWebSocketIntegration } from '@/hooks/useWebSocketIntegration'
import { ConnectionState } from '@/lib/websocket'
import { 
  SignalIcon, 
  ExclamationCircleIcon, 
  ArrowsRightLeftIcon,
  XCircleIcon
} from '@heroicons/react/24/outline'
import { useEffect, useState } from 'react'

export function ConnectionStatusIndicator() {
  const { connectionState } = useWebSocketIntegration()
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    // 只有在连接状态不是OPEN时才显示指示器
    if (connectionState !== ConnectionState.OPEN) {
      setIsVisible(true)
      
      // 3秒后自动隐藏成功状态的指示器
      if (connectionState === ConnectionState.CONNECTING) {
        const timer = setTimeout(() => {
          setIsVisible(false)
        }, 3000)
        return () => clearTimeout(timer)
      }
    } else {
      // 连接成功后短暂显示成功状态
      setIsVisible(true)
      const timer = setTimeout(() => {
        setIsVisible(false)
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [connectionState])

  if (!isVisible) return null

  const getStatusInfo = () => {
    switch (connectionState) {
      case ConnectionState.CONNECTING:
        return {
          icon: <ArrowsRightLeftIcon className="w-4 h-4 animate-spin" />,
          text: '连接中...',
          bgColor: 'bg-blue-100',
          textColor: 'text-blue-800',
          borderColor: 'border-blue-200'
        }
      case ConnectionState.OPEN:
        return {
          icon: <SignalIcon className="w-4 h-4" />,
          text: '已连接',
          bgColor: 'bg-green-100',
          textColor: 'text-green-800',
          borderColor: 'border-green-200'
        }
      case ConnectionState.CLOSING:
        return {
          icon: <ArrowsRightLeftIcon className="w-4 h-4 animate-spin" />,
          text: '断开中...',
          bgColor: 'bg-yellow-100',
          textColor: 'text-yellow-800',
          borderColor: 'border-yellow-200'
        }
      case ConnectionState.CLOSED:
        return {
          icon: <XCircleIcon className="w-4 h-4" />,
          text: '已断开',
          bgColor: 'bg-red-100',
          textColor: 'text-red-800',
          borderColor: 'border-red-200'
        }
      default:
        return {
          icon: <ExclamationCircleIcon className="w-4 h-4" />,
          text: '未知状态',
          bgColor: 'bg-gray-100',
          textColor: 'text-gray-800',
          borderColor: 'border-gray-200'
        }
    }
  }

  const statusInfo = getStatusInfo()

  return (
    <div className={`fixed bottom-4 right-4 ${statusInfo.bgColor} ${statusInfo.borderColor} border rounded-lg px-3 py-2 shadow-lg z-50 flex items-center space-x-2`}>
      <div className={statusInfo.textColor}>
        {statusInfo.icon}
      </div>
      <span className={`text-sm font-medium ${statusInfo.textColor}`}>
        {statusInfo.text}
      </span>
    </div>
  )
}