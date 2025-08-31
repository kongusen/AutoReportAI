/**
 * 智能按钮组件 - 集成加载状态、进度反馈和错误处理
 */

import React, { useState, useCallback } from 'react'
import { cn } from '@/utils'
import { ProgressIndicator } from './ProgressIndicator'

export interface SmartButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  // 加载状态
  loading?: boolean
  // 进度值 0-100
  progress?: number
  // 成功状态
  success?: boolean
  // 错误状态
  error?: boolean
  // 变体样式
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'ghost'
  // 尺寸
  size?: 'sm' | 'md' | 'lg'
  // 图标
  icon?: React.ReactNode
  // 加载时的图标
  loadingIcon?: React.ReactNode
  // 成功图标
  successIcon?: React.ReactNode
  // 错误图标
  errorIcon?: React.ReactNode
  // 是否显示进度条
  showProgress?: boolean
  // 加载文本
  loadingText?: string
  // 成功文本
  successText?: string
  // 错误文本
  errorText?: string
  // 自动重置成功/错误状态的延迟时间（毫秒）
  autoResetDelay?: number
  // 点击处理函数（支持异步）
  onAsyncClick?: () => Promise<void>
}

export const SmartButton: React.FC<SmartButtonProps> = ({
  children,
  loading = false,
  progress = 0,
  success = false,
  error = false,
  variant = 'primary',
  size = 'md',
  icon,
  loadingIcon,
  successIcon,
  errorIcon,
  showProgress = false,
  loadingText,
  successText,
  errorText,
  autoResetDelay = 2000,
  onAsyncClick,
  onClick,
  disabled,
  className,
  ...props
}) => {
  const [internalLoading, setInternalLoading] = useState(false)
  const [internalSuccess, setInternalSuccess] = useState(false)
  const [internalError, setInternalError] = useState(false)
  const [internalProgress, setInternalProgress] = useState(0)

  // 使用内部状态或外部状态
  const isLoading = loading || internalLoading
  const isSuccess = success || internalSuccess
  const isError = error || internalError
  const currentProgress = progress || internalProgress

  // 重置内部状态
  const resetInternalState = useCallback(() => {
    setInternalSuccess(false)
    setInternalError(false)
    setInternalProgress(0)
  }, [])

  // 异步点击处理
  const handleAsyncClick = useCallback(async (event: React.MouseEvent<HTMLButtonElement>) => {
    if (onAsyncClick) {
      event.preventDefault()
      
      try {
        setInternalLoading(true)
        setInternalError(false)
        setInternalProgress(0)
        
        // 模拟进度更新
        let currentProgress = 0
        const progressInterval = setInterval(() => {
          currentProgress += Math.random() * 20
          if (currentProgress > 90) {
            clearInterval(progressInterval)
            return
          }
          setInternalProgress(Math.min(90, currentProgress))
        }, 200)
        
        await onAsyncClick()
        
        clearInterval(progressInterval)
        setInternalProgress(100)
        setInternalSuccess(true)
        
        // 自动重置成功状态
        if (autoResetDelay > 0) {
          setTimeout(resetInternalState, autoResetDelay)
        }
        
      } catch (error) {
        setInternalError(true)
        console.error('AsyncButton error:', error)
        
        // 自动重置错误状态
        if (autoResetDelay > 0) {
          setTimeout(resetInternalState, autoResetDelay)
        }
      } finally {
        setInternalLoading(false)
      }
    } else if (onClick) {
      onClick(event)
    }
  }, [onAsyncClick, onClick, autoResetDelay, resetInternalState])

  // 样式类
  const baseClasses = 'relative inline-flex items-center justify-center font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed'
  
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm rounded-md',
    md: 'px-4 py-2 text-sm rounded-md',
    lg: 'px-6 py-3 text-base rounded-lg'
  }

  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500 border border-transparent',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-500 border border-gray-300',
    success: 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500 border border-transparent',
    warning: 'bg-yellow-600 text-white hover:bg-yellow-700 focus:ring-yellow-500 border border-transparent',
    error: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500 border border-transparent',
    ghost: 'bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-gray-500 border border-gray-300'
  }

  // 根据状态调整样式
  let currentVariant = variant
  if (isSuccess) currentVariant = 'success'
  if (isError) currentVariant = 'error'

  // 当前显示的图标
  let currentIcon = icon
  if (isLoading && loadingIcon) currentIcon = loadingIcon
  if (isSuccess && successIcon) currentIcon = successIcon
  if (isError && errorIcon) currentIcon = errorIcon

  // 当前显示的文本
  let currentText = children
  if (isLoading && loadingText) currentText = loadingText
  if (isSuccess && successText) currentText = successText
  if (isError && errorText) currentText = errorText

  return (
    <button
      className={cn(
        baseClasses,
        sizeClasses[size],
        variantClasses[currentVariant],
        isLoading && 'cursor-wait',
        className
      )}
      disabled={disabled || isLoading}
      onClick={handleAsyncClick}
      {...props}
    >
      {/* 进度背景 */}
      {showProgress && isLoading && (
        <div 
          className="absolute inset-0 bg-white bg-opacity-20 rounded-inherit transition-all duration-300"
          style={{ width: `${currentProgress}%` }}
        />
      )}
      
      {/* 内容 */}
      <div className="relative flex items-center space-x-2">
        {/* 图标或加载指示器 */}
        {isLoading ? (
          <ProgressIndicator
            size="sm"
            shape="circular"
            variant="default"
            indeterminate
            className="text-current"
          />
        ) : currentIcon ? (
          <span className="flex-shrink-0">{currentIcon}</span>
        ) : null}
        
        {/* 文本 */}
        {currentText && (
          <span className="whitespace-nowrap">{currentText}</span>
        )}
      </div>
    </button>
  )
}

// 确认按钮组件
export interface ConfirmButtonProps extends SmartButtonProps {
  confirmTitle?: string
  confirmMessage?: string
  confirmText?: string
  cancelText?: string
  dangerous?: boolean
}

export const ConfirmButton: React.FC<ConfirmButtonProps> = ({
  confirmTitle = "确认操作",
  confirmMessage = "确定要执行此操作吗？",
  confirmText = "确认",
  cancelText = "取消",
  dangerous = false,
  onAsyncClick,
  onClick,
  children,
  variant = 'primary',
  ...props
}) => {
  const [showConfirm, setShowConfirm] = useState(false)

  const handleClick = useCallback((event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault()
    setShowConfirm(true)
  }, [])

  const handleConfirm = useCallback(async () => {
    setShowConfirm(false)
    if (onAsyncClick) {
      await onAsyncClick()
    } else if (onClick) {
      onClick({} as React.MouseEvent<HTMLButtonElement>)
    }
  }, [onAsyncClick, onClick])

  const handleCancel = useCallback(() => {
    setShowConfirm(false)
  }, [])

  return (
    <>
      <SmartButton
        variant={dangerous ? 'error' : variant}
        onClick={handleClick}
        {...props}
      >
        {children}
      </SmartButton>

      {/* 确认对话框 */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {confirmTitle}
            </h3>
            <p className="text-gray-600 mb-6">
              {confirmMessage}
            </p>
            <div className="flex space-x-3">
              <SmartButton
                variant="secondary"
                onClick={handleCancel}
                className="flex-1"
              >
                {cancelText}
              </SmartButton>
              <SmartButton
                variant={dangerous ? 'error' : 'primary'}
                onAsyncClick={handleConfirm}
                className="flex-1"
              >
                {confirmText}
              </SmartButton>
            </div>
          </div>
        </div>
      )}
    </>
  )
}