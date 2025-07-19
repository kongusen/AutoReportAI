'use client'

import React, { Component, ErrorInfo, ReactNode } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  AlertTriangle, 
  RefreshCw, 
  Bug, 
  Copy,
  ChevronDown,
  ChevronRight
} from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
  showDetails: boolean
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false
    }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo
    })

    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo)
    }

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }

    // In production, you might want to send error to logging service
    // logErrorToService(error, errorInfo)
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false
    })
  }

  handleCopyError = () => {
    const { error, errorInfo } = this.state
    const errorText = `
Error: ${error?.message}
Stack: ${error?.stack}
Component Stack: ${errorInfo?.componentStack}
    `.trim()
    
    navigator.clipboard.writeText(errorText).then(() => {
      // Could show a toast notification here
      console.log('Error details copied to clipboard')
    })
  }

  toggleDetails = () => {
    this.setState(prev => ({ showDetails: !prev.showDetails }))
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback
      }

      // Default error UI
      return (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="flex items-center text-red-800">
              <AlertTriangle className="w-5 h-5 mr-2" />
              组件错误
            </CardTitle>
            <CardDescription className="text-red-600">
              智能功能组件遇到了一个错误，请尝试刷新或联系技术支持。
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Error Summary */}
              <div className="p-3 bg-white border border-red-200 rounded">
                <div className="flex items-start space-x-2">
                  <Bug className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-red-800">
                      {this.state.error?.name || 'Unknown Error'}
                    </p>
                    <p className="text-sm text-red-600 mt-1">
                      {this.state.error?.message || '发生了未知错误'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Error Metadata */}
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className="text-red-600 border-red-200">
                  时间: {new Date().toLocaleString()}
                </Badge>
                <Badge variant="outline" className="text-red-600 border-red-200">
                  环境: {process.env.NODE_ENV}
                </Badge>
                <Badge variant="outline" className="text-red-600 border-red-200">
                  组件: 智能功能组件
                </Badge>
              </div>

              {/* Actions */}
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={this.handleRetry}
                  className="bg-red-600 hover:bg-red-700"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  重试
                </Button>
                
                <Button
                  variant="outline"
                  onClick={this.handleCopyError}
                  className="border-red-200 text-red-600 hover:bg-red-50"
                >
                  <Copy className="w-4 h-4 mr-2" />
                  复制错误信息
                </Button>
                
                <Button
                  variant="ghost"
                  onClick={this.toggleDetails}
                  className="text-red-600 hover:bg-red-50"
                >
                  {this.state.showDetails ? (
                    <ChevronDown className="w-4 h-4 mr-2" />
                  ) : (
                    <ChevronRight className="w-4 h-4 mr-2" />
                  )}
                  {this.state.showDetails ? '隐藏' : '显示'}详细信息
                </Button>
              </div>

              {/* Error Details */}
              {this.state.showDetails && (
                <div className="space-y-3">
                  {/* Error Stack */}
                  {this.state.error?.stack && (
                    <div>
                      <h4 className="text-sm font-medium text-red-800 mb-2">错误堆栈:</h4>
                      <pre className="text-xs bg-gray-100 p-3 rounded overflow-x-auto border">
                        {this.state.error.stack}
                      </pre>
                    </div>
                  )}

                  {/* Component Stack */}
                  {this.state.errorInfo?.componentStack && (
                    <div>
                      <h4 className="text-sm font-medium text-red-800 mb-2">组件堆栈:</h4>
                      <pre className="text-xs bg-gray-100 p-3 rounded overflow-x-auto border">
                        {this.state.errorInfo.componentStack}
                      </pre>
                    </div>
                  )}
                </div>
              )}

              {/* Help Text */}
              <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded">
                <p className="font-medium mb-1">故障排除建议:</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>检查网络连接是否正常</li>
                  <li>确认API服务是否可用</li>
                  <li>尝试刷新页面</li>
                  <li>如果问题持续存在，请联系技术支持</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )
    }

    return this.props.children
  }
}

// Hook version for functional components
export function useErrorHandler() {
  const [error, setError] = React.useState<Error | null>(null)

  const resetError = React.useCallback(() => {
    setError(null)
  }, [])

  const captureError = React.useCallback((error: Error) => {
    setError(error)
    console.error('Error captured by useErrorHandler:', error)
  }, [])

  // Throw error to trigger error boundary
  if (error) {
    throw error
  }

  return { captureError, resetError }
}

// Higher-order component for wrapping components with error boundary
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<Props, 'children'>
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  )

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`
  
  return WrappedComponent
}