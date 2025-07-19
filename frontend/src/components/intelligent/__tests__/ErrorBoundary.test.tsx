import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { ErrorBoundary, useErrorHandler, withErrorBoundary } from '../ErrorBoundary'

// Component that throws an error
const ThrowError = ({ shouldThrow = false }: { shouldThrow?: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error')
  }
  return <div>No error</div>
}

// Component that uses useErrorHandler hook
const ComponentWithErrorHandler = ({ shouldError = false }: { shouldError?: boolean }) => {
  const handleError = useErrorHandler()
  
  React.useEffect(() => {
    if (shouldError) {
      handleError(new Error('Hook error'))
    }
  }, [shouldError, handleError])
  
  return <div>Component with error handler</div>
}

describe('ErrorBoundary Component', () => {
  // Suppress console.error for error boundary tests
  const originalError = console.error
  beforeAll(() => {
    console.error = jest.fn()
  })
  
  afterAll(() => {
    console.error = originalError
  })

  it('should render children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <div>Test content</div>
      </ErrorBoundary>
    )
    
    expect(screen.getByText('Test content')).toBeInTheDocument()
  })

  it('should render error UI when error occurs', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )
    
    expect(screen.getByText('组件错误')).toBeInTheDocument()
    expect(screen.getByText(/智能功能组件遇到了一个错误/)).toBeInTheDocument()
  })

  it('should display error message when provided', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )
    
    expect(screen.getByText(/Test error/)).toBeInTheDocument()
  })

  it('should render custom fallback when provided', () => {
    const CustomFallback = ({ error }: { error: Error }) => (
      <div>Custom error: {error.message}</div>
    )
    
    render(
      <ErrorBoundary fallback={CustomFallback}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )
    
    expect(screen.getByText('Custom error: Test error')).toBeInTheDocument()
  })

  it('should call onError callback when error occurs', () => {
    const onError = jest.fn()
    
    render(
      <ErrorBoundary onError={onError}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )
    
    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String)
      })
    )
  })

  it('should reset error state when resetKeys change', () => {
    const { rerender } = render(
      <ErrorBoundary resetKeys={['key1']}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )
    
    expect(screen.getByText('组件错误')).toBeInTheDocument()
    
    rerender(
      <ErrorBoundary resetKeys={['key2']}>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    )
    
    expect(screen.getByText('No error')).toBeInTheDocument()
  })

  it('should call onReset callback when error is reset', () => {
    const onReset = jest.fn()
    
    const { rerender } = render(
      <ErrorBoundary resetKeys={['key1']} onReset={onReset}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )
    
    rerender(
      <ErrorBoundary resetKeys={['key2']} onReset={onReset}>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    )
    
    expect(onReset).toHaveBeenCalled()
  })

  it('should isolate errors to specific boundary', () => {
    render(
      <div>
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
        <div>Other content</div>
      </div>
    )
    
    expect(screen.getByText('组件错误')).toBeInTheDocument()
    expect(screen.getByText('Other content')).toBeInTheDocument()
  })
})

describe('useErrorHandler Hook', () => {
  it('should provide error handler function', () => {
    render(
      <ErrorBoundary>
        <ComponentWithErrorHandler />
      </ErrorBoundary>
    )
    
    expect(screen.getByText('Component with error handler')).toBeInTheDocument()
  })

  it('should trigger error boundary when error is handled', () => {
    render(
      <ErrorBoundary>
        <ComponentWithErrorHandler shouldError={true} />
      </ErrorBoundary>
    )
    
    expect(screen.getByText('组件错误')).toBeInTheDocument()
  })

  it('should throw error when used outside error boundary', () => {
    const TestComponent = () => {
      useErrorHandler()
      return <div>Test</div>
    }
    
    expect(() => {
      render(<TestComponent />)
    }).toThrow('useErrorHandler must be used within an ErrorBoundary')
  })
})

describe('withErrorBoundary HOC', () => {
  it('should wrap component with error boundary', () => {
    const TestComponent = () => <div>Wrapped component</div>
    const WrappedComponent = withErrorBoundary(TestComponent)
    
    render(<WrappedComponent />)
    
    expect(screen.getByText('Wrapped component')).toBeInTheDocument()
  })

  it('should handle errors in wrapped component', () => {
    const WrappedComponent = withErrorBoundary(ThrowError)
    
    render(<WrappedComponent shouldThrow={true} />)
    
    expect(screen.getByText('组件错误')).toBeInTheDocument()
  })

  it('should pass props to wrapped component', () => {
    const TestComponent = ({ message }: { message: string }) => <div>{message}</div>
    const WrappedComponent = withErrorBoundary(TestComponent)
    
    render(<WrappedComponent message="Test message" />)
    
    expect(screen.getByText('Test message')).toBeInTheDocument()
  })

  it('should accept error boundary options', () => {
    const onError = jest.fn()
    const TestComponent = () => <ThrowError shouldThrow={true} />
    const WrappedComponent = withErrorBoundary(TestComponent, {
      onError,
      fallback: ({ error }) => <div>HOC Error: {error.message}</div>
    })
    
    render(<WrappedComponent />)
    
    expect(screen.getByText('HOC Error: Test error')).toBeInTheDocument()
    expect(onError).toHaveBeenCalled()
  })
})