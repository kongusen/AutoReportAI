import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { AIAssistant } from '../AIAssistant'

// Mock API client
jest.mock('@/lib/api-client', () => ({
  __esModule: true,
  default: {
    get: jest.fn().mockResolvedValue({ data: [] }),
    post: jest.fn().mockResolvedValue({ data: { success: true } }),
  },
}))

// Mock scrollIntoView
Object.defineProperty(Element.prototype, 'scrollIntoView', {
  writable: true,
  value: jest.fn(),
})

describe('AIAssistant Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should render with default props', () => {
    render(<AIAssistant />)
    
    expect(screen.getByText('AI智能助手')).toBeInTheDocument()
    expect(screen.getByText('获取智能占位符处理的专业建议和帮助')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('输入您的问题...')).toBeInTheDocument()
  })

  it('should display welcome message on initial load', () => {
    render(<AIAssistant />)
    
    expect(screen.getByText(/您好！我是智能占位符助手/)).toBeInTheDocument()
    expect(screen.getByText('常见问题:')).toBeInTheDocument()
  })

  it('should display quick questions', () => {
    render(<AIAssistant />)
    
    expect(screen.getByText('如何优化占位符的匹配准确率？')).toBeInTheDocument()
    expect(screen.getByText('这个数据源适合什么类型的报告？')).toBeInTheDocument()
    expect(screen.getByText('如何处理字段匹配置信度较低的情况？')).toBeInTheDocument()
    expect(screen.getByText('推荐的模板结构是什么？')).toBeInTheDocument()
  })

  it('should handle user input and send messages', async () => {
    const user = userEvent.setup()
    render(<AIAssistant />)
    
    const input = screen.getByPlaceholderText('输入您的问题...')
    const sendButton = screen.getByRole('button', { name: /send/i })
    
    await user.type(input, '测试问题')
    expect(input).toHaveValue('测试问题')
    
    await user.click(sendButton)
    
    // Should show user message
    expect(screen.getByText('测试问题')).toBeInTheDocument()
    
    // Input should be cleared
    expect(input).toHaveValue('')
  })

  it('should handle Enter key to send message', async () => {
    const user = userEvent.setup()
    render(<AIAssistant />)
    
    const input = screen.getByPlaceholderText('输入您的问题...')
    
    await user.type(input, '测试Enter键')
    await user.keyboard('{Enter}')
    
    expect(screen.getByText('测试Enter键')).toBeInTheDocument()
  })

  it('should handle Shift+Enter for new line', async () => {
    const user = userEvent.setup()
    render(<AIAssistant />)
    
    const input = screen.getByPlaceholderText('输入您的问题...')
    
    await user.type(input, '第一行')
    await user.keyboard('{Shift>}{Enter}{/Shift}')
    await user.type(input, '第二行')
    
    expect(input).toHaveValue('第一行\n第二行')
  })

  it('should disable send button when input is empty', () => {
    render(<AIAssistant />)
    
    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).toBeDisabled()
  })

  it('should enable send button when input has content', async () => {
    const user = userEvent.setup()
    render(<AIAssistant />)
    
    const input = screen.getByPlaceholderText('输入您的问题...')
    const sendButton = screen.getByRole('button', { name: /send/i })
    
    await user.type(input, '测试内容')
    expect(sendButton).not.toBeDisabled()
  })

  it('should show loading state when sending message', async () => {
    const user = userEvent.setup()
    render(<AIAssistant />)
    
    const input = screen.getByPlaceholderText('输入您的问题...')
    const sendButton = screen.getByRole('button', { name: /send/i })
    
    await user.type(input, '测试加载状态')
    await user.click(sendButton)
    
    // Should show loading spinner
    expect(screen.getByTestId('loading-spinner') || screen.getByRole('button', { name: /loading/i })).toBeInTheDocument()
  })

  it('should show typing indicator during AI response', async () => {
    const user = userEvent.setup()
    render(<AIAssistant />)
    
    const input = screen.getByPlaceholderText('输入您的问题...')
    
    await user.type(input, '测试打字指示器')
    await user.keyboard('{Enter}')
    
    // Should show typing indicator (animated dots)
    await waitFor(() => {
      const typingIndicator = screen.getByText((content, element) => {
        return element?.className?.includes('animate-bounce') || false
      })
      expect(typingIndicator).toBeInTheDocument()
    }, { timeout: 1000 })
  })

  it('should handle quick question clicks', async () => {
    const user = userEvent.setup()
    render(<AIAssistant />)
    
    const quickQuestion = screen.getByText('如何优化占位符的匹配准确率？')
    await user.click(quickQuestion)
    
    expect(screen.getByText('如何优化占位符的匹配准确率？')).toBeInTheDocument()
  })

  it('should display context information when provided', () => {
    const context = {
      templateId: 'template-123',
      dataSourceId: 456,
      currentTask: '占位符分析'
    }
    
    render(<AIAssistant context={context} />)
    
    expect(screen.getByText(/上下文:/)).toBeInTheDocument()
    expect(screen.getByText(/模板/)).toBeInTheDocument()
    expect(screen.getByText(/数据源/)).toBeInTheDocument()
  })

  it('should handle suggestion application', async () => {
    const mockOnSuggestionApply = jest.fn()
    const user = userEvent.setup()
    
    render(<AIAssistant onSuggestionApply={mockOnSuggestionApply} />)
    
    const input = screen.getByPlaceholderText('输入您的问题...')
    await user.type(input, '如何优化占位符的匹配准确率？')
    await user.keyboard('{Enter}')
    
    // Wait for AI response with suggestions
    await waitFor(() => {
      const suggestionButton = screen.getByText('调整置信度阈值到0.8')
      expect(suggestionButton).toBeInTheDocument()
    }, { timeout: 3000 })
    
    const suggestionButton = screen.getByText('调整置信度阈值到0.8')
    await user.click(suggestionButton)
    
    expect(mockOnSuggestionApply).toHaveBeenCalledWith('调整置信度阈值到0.8')
  })

  it('should display message timestamps', async () => {
    const user = userEvent.setup()
    render(<AIAssistant />)
    
    const input = screen.getByPlaceholderText('输入您的问题...')
    await user.type(input, '测试时间戳')
    await user.keyboard('{Enter}')
    
    // Should show timestamp
    await waitFor(() => {
      const timestamp = screen.getByText(/\d{1,2}:\d{2}:\d{2}/)
      expect(timestamp).toBeInTheDocument()
    })
  })

  it('should handle message rating', async () => {
    const user = userEvent.setup()
    render(<AIAssistant />)
    
    const input = screen.getByPlaceholderText('输入您的问题...')
    await user.type(input, '测试评分')
    await user.keyboard('{Enter}')
    
    // Wait for AI response
    await waitFor(() => {
      const thumbsUpButton = screen.getByRole('button', { name: /thumbs up/i })
      expect(thumbsUpButton).toBeInTheDocument()
    }, { timeout: 3000 })
    
    const thumbsUpButton = screen.getByRole('button', { name: /thumbs up/i })
    await user.click(thumbsUpButton)
    
    // Should not throw error (rating is logged)
    expect(thumbsUpButton).toBeInTheDocument()
  })

  it('should handle message copying', async () => {
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: jest.fn().mockResolvedValue(undefined),
      },
    })
    
    const user = userEvent.setup()
    render(<AIAssistant />)
    
    const input = screen.getByPlaceholderText('输入您的问题...')
    await user.type(input, '测试复制')
    await user.keyboard('{Enter}')
    
    // Wait for AI response
    await waitFor(() => {
      const copyButton = screen.getByRole('button', { name: /copy/i })
      expect(copyButton).toBeInTheDocument()
    }, { timeout: 3000 })
    
    const copyButton = screen.getByRole('button', { name: /copy/i })
    await user.click(copyButton)
    
    expect(navigator.clipboard.writeText).toHaveBeenCalled()
  })

  it('should handle error responses gracefully', async () => {
    // Mock API to throw error
    const apiClient = require('@/lib/api-client').default
    apiClient.post.mockRejectedValueOnce(new Error('API Error'))
    
    const user = userEvent.setup()
    render(<AIAssistant />)
    
    const input = screen.getByPlaceholderText('输入您的问题...')
    await user.type(input, '测试错误处理')
    await user.keyboard('{Enter}')
    
    // Should show error message
    await waitFor(() => {
      expect(screen.getByText(/抱歉，我暂时无法回答您的问题/)).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('should scroll to bottom when new messages are added', async () => {
    const user = userEvent.setup()
    render(<AIAssistant />)
    
    const input = screen.getByPlaceholderText('输入您的问题...')
    await user.type(input, '测试滚动')
    await user.keyboard('{Enter}')
    
    // scrollIntoView should be called
    await waitFor(() => {
      expect(Element.prototype.scrollIntoView).toHaveBeenCalled()
    })
  })
})