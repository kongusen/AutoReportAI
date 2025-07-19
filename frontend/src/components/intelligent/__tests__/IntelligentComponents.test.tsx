import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { 
  IntelligentPlaceholderManager,
  PlaceholderAnalyzer,
  FieldMatcher,
  AIAssistant,
  ErrorBoundary,
  ReportGenerator
} from '../index'

// Mock API client
jest.mock('@/lib/api-client', () => ({
  __esModule: true,
  default: {
    get: jest.fn().mockResolvedValue({ data: [] }),
    post: jest.fn().mockResolvedValue({ data: { success: true } }),
  },
}))

// Mock window.alert for test environment
Object.defineProperty(window, 'alert', {
  writable: true,
  value: jest.fn(),
})

// Mock scrollIntoView for test environment
Object.defineProperty(Element.prototype, 'scrollIntoView', {
  writable: true,
  value: jest.fn(),
})

// Mock components that might cause issues in test environment
jest.mock('@/components/ui/tabs', () => ({
  Tabs: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs">{children}</div>,
  TabsContent: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs-content">{children}</div>,
  TabsList: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs-list">{children}</div>,
  TabsTrigger: ({ children }: { children: React.ReactNode }) => <button data-testid="tabs-trigger">{children}</button>,
}))

describe('Intelligent Components', () => {
  describe('ErrorBoundary', () => {
    it('should render children when no error occurs', () => {
      render(
        <ErrorBoundary>
          <div>Test content</div>
        </ErrorBoundary>
      )
      
      expect(screen.getByText('Test content')).toBeInTheDocument()
    })

    it('should render error UI when error occurs', () => {
      const ThrowError = () => {
        throw new Error('Test error')
      }

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      )
      
      expect(screen.getByText('组件错误')).toBeInTheDocument()
      expect(screen.getByText(/智能功能组件遇到了一个错误/)).toBeInTheDocument()
    })
  })

  describe('IntelligentPlaceholderManager', () => {
    it('should render with default props', () => {
      render(<IntelligentPlaceholderManager />)
      
      expect(screen.getByText('智能占位符管理')).toBeInTheDocument()
      expect(screen.getByText(/使用AI技术分析和处理模板中的智能占位符/)).toBeInTheDocument()
    })

    it('should render tabs correctly', () => {
      render(<IntelligentPlaceholderManager />)
      
      expect(screen.getByText('占位符分析')).toBeInTheDocument()
      expect(screen.getAllByText('字段映射')).toHaveLength(2) // Tab and content title
      expect(screen.getByText('AI理解')).toBeInTheDocument()
      expect(screen.getByText('AI助手')).toBeInTheDocument()
    })
  })

  describe('ReportGenerator', () => {
    it('should render with default props', () => {
      render(<ReportGenerator />)
      
      expect(screen.getByText('报告生成配置')).toBeInTheDocument()
    })
  })

  describe('PlaceholderAnalyzer', () => {
    it('should render configuration panel', () => {
      render(<PlaceholderAnalyzer />)
      
      expect(screen.getByText('分析配置')).toBeInTheDocument()
      expect(screen.getByText('模板内容')).toBeInTheDocument()
      expect(screen.getByText('数据源')).toBeInTheDocument()
    })

    it('should have analyze button disabled when no content', () => {
      render(<PlaceholderAnalyzer />)
      
      const analyzeButton = screen.getByRole('button', { name: /分析占位符/ })
      expect(analyzeButton).toBeDisabled()
    })
  })

  describe('FieldMatcher', () => {
    it('should show waiting message when no placeholder selected', () => {
      render(<FieldMatcher placeholder={null} dataSourceId={null} />)
      
      expect(screen.getByText('字段映射')).toBeInTheDocument()
      expect(screen.getByText('等待选择占位符...')).toBeInTheDocument()
    })

    it('should show placeholder info when placeholder is provided', () => {
      const mockPlaceholder = {
        placeholder_text: '{{统计:投诉总数}}',
        placeholder_type: '统计',
        description: '投诉总数',
        position: 0,
        context_before: '本月',
        context_after: '件投诉',
        confidence: 0.95
      }

      render(<FieldMatcher placeholder={mockPlaceholder} dataSourceId={1} />)
      
      expect(screen.getByText('{{统计:投诉总数}}')).toBeInTheDocument()
      expect(screen.getByText('投诉总数')).toBeInTheDocument()
    })
  })

  describe('AIAssistant', () => {
    it('should render chat interface', () => {
      render(<AIAssistant />)
      
      expect(screen.getByText('AI智能助手')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('输入您的问题...')).toBeInTheDocument()
    })

    it('should show welcome message', () => {
      render(<AIAssistant />)
      
      expect(screen.getByText(/您好！我是智能占位符助手/)).toBeInTheDocument()
    })

    it('should show quick questions', () => {
      render(<AIAssistant />)
      
      expect(screen.getByText('常见问题:')).toBeInTheDocument()
      expect(screen.getAllByText(/如何优化占位符的匹配准确率/)).toHaveLength(2) // Multiple buttons with same text
    })
  })
})

describe('Component Integration', () => {
  it('should handle placeholder selection flow', async () => {
    const mockOnPlaceholderUpdate = jest.fn()
    
    render(
      <IntelligentPlaceholderManager 
        onPlaceholderUpdate={mockOnPlaceholderUpdate}
      />
    )
    
    // Component should render without errors
    expect(screen.getByText('智能占位符管理')).toBeInTheDocument()
  })

  it('should handle report generation flow', async () => {
    const mockOnReportGenerated = jest.fn()
    
    render(<ReportGenerator />)
    
    // Component should render without errors
    expect(screen.getByText('报告生成配置')).toBeInTheDocument()
  })
})

describe('Error Handling', () => {
  it('should handle API errors gracefully', async () => {
    const apiClient = require('@/lib/api-client').default
    apiClient.post.mockRejectedValue(new Error('API Error'))
    
    render(<PlaceholderAnalyzer />)
    
    // Fill in template content
    const textarea = screen.getByPlaceholderText(/输入包含.*格式占位符的模板内容/)
    fireEvent.change(textarea, { target: { value: '{{统计:测试}}' } })
    
    // Click analyze button
    const analyzeButton = screen.getByRole('button', { name: /分析占位符/ })
    fireEvent.click(analyzeButton)
    
    // Should handle error without crashing
    await waitFor(() => {
      expect(analyzeButton).not.toBeDisabled()
    })
  })
})