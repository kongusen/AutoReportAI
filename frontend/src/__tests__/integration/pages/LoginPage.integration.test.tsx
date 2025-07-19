import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useRouter } from 'next/navigation'
import LoginPage from '@/app/(auth)/login/page'
import api from '@/lib/api'

// Mock dependencies
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}))

jest.mock('@/lib/api', () => ({
  post: jest.fn(),
}))

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
})

const mockRouter = {
  push: jest.fn(),
  replace: jest.fn(),
  back: jest.fn(),
  forward: jest.fn(),
  refresh: jest.fn(),
  prefetch: jest.fn(),
}

describe('LoginPage Integration Tests', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useRouter as jest.Mock).mockReturnValue(mockRouter)
    mockLocalStorage.setItem.mockClear()
  })

  describe('Initial Render', () => {
    it('renders login form with all required elements', () => {
      render(<LoginPage />)

      expect(screen.getByText('登录')).toBeInTheDocument()
      expect(screen.getByText('请输入您的用户名和密码')).toBeInTheDocument()
      expect(screen.getByLabelText('用户名')).toBeInTheDocument()
      expect(screen.getByLabelText('密码')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '登录' })).toBeInTheDocument()
    })

    it('has proper form structure and accessibility', () => {
      render(<LoginPage />)

      const usernameInput = screen.getByLabelText('用户名')
      const passwordInput = screen.getByLabelText('密码')
      
      expect(usernameInput).toHaveAttribute('type', 'text')
      expect(usernameInput).toHaveAttribute('required')
      expect(passwordInput).toHaveAttribute('type', 'password')
      expect(passwordInput).toHaveAttribute('required')
    })

    it('renders with proper styling and layout', () => {
      render(<LoginPage />)

      // Use getAllByText to handle multiple elements with same text
      const loginElements = screen.getAllByText('登录')
      const titleElement = loginElements.find(el => 
        el.getAttribute('data-slot') === 'card-title'
      )
      
      expect(titleElement).toBeInTheDocument()
      const container = titleElement?.closest('.min-h-screen')
      expect(container).toHaveClass('min-h-screen', 'flex', 'items-center', 'justify-center')
    })
  })

  describe('User Input Handling', () => {
    it('updates username field correctly', async () => {
      render(<LoginPage />)

      const usernameInput = screen.getByLabelText('用户名')
      await user.type(usernameInput, 'testuser')

      expect(usernameInput).toHaveValue('testuser')
    })

    it('updates password field correctly', async () => {
      render(<LoginPage />)

      const passwordInput = screen.getByLabelText('密码')
      await user.type(passwordInput, 'password123')

      expect(passwordInput).toHaveValue('password123')
    })
  })

  describe('API Integration', () => {
    it('makes correct API call on form submission', async () => {
      const mockApiResponse = {
        data: { access_token: 'mock-token' },
      }
      ;(api.post as jest.Mock).mockResolvedValue(mockApiResponse)

      render(<LoginPage />)

      const usernameInput = screen.getByLabelText('用户名')
      const passwordInput = screen.getByLabelText('密码')
      const submitButton = screen.getByRole('button', { name: '登录' })

      await user.type(usernameInput, 'testuser')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(api.post).toHaveBeenCalledWith(
          '/auth/access-token', 
          expect.any(URLSearchParams), 
          {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
          }
        )
      })
    })

    it('sends correct form data in API request', async () => {
      const mockApiResponse = {
        data: { access_token: 'mock-token' },
      }
      ;(api.post as jest.Mock).mockResolvedValue(mockApiResponse)

      render(<LoginPage />)

      const usernameInput = screen.getByLabelText('用户名')
      const passwordInput = screen.getByLabelText('密码')
      const submitButton = screen.getByRole('button', { name: '登录' })

      await user.type(usernameInput, 'testuser')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        const callArgs = (api.post as jest.Mock).mock.calls[0]
        const formData = callArgs[1] as URLSearchParams
        
        expect(formData.get('username')).toBe('testuser')
        expect(formData.get('password')).toBe('password123')
        expect(formData.get('grant_type')).toBe('password')
      })
    })
  })

  describe('Successful Login Flow', () => {
    it('stores access token in localStorage on successful login', async () => {
      const mockApiResponse = {
        data: { access_token: 'mock-access-token-12345' },
      }
      ;(api.post as jest.Mock).mockResolvedValue(mockApiResponse)

      render(<LoginPage />)

      const usernameInput = screen.getByLabelText('用户名')
      const passwordInput = screen.getByLabelText('密码')
      const submitButton = screen.getByRole('button', { name: '登录' })

      await user.type(usernameInput, 'testuser')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockLocalStorage.setItem).toHaveBeenCalledWith('access_token', 'mock-access-token-12345')
      })
    })

    it('redirects to dashboard on successful login', async () => {
      const mockApiResponse = {
        data: { access_token: 'mock-token' },
      }
      ;(api.post as jest.Mock).mockResolvedValue(mockApiResponse)

      render(<LoginPage />)

      const usernameInput = screen.getByLabelText('用户名')
      const passwordInput = screen.getByLabelText('密码')
      const submitButton = screen.getByRole('button', { name: '登录' })

      await user.type(usernameInput, 'testuser')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockRouter.push).toHaveBeenCalledWith('/')
      })
    })
  })

  describe('Error Handling', () => {
    it('displays error message on login failure', async () => {
      const mockError = {
        response: {
          data: {
            detail: '用户名或密码错误'
          }
        }
      }
      ;(api.post as jest.Mock).mockRejectedValue(mockError)

      render(<LoginPage />)

      const usernameInput = screen.getByLabelText('用户名')
      const passwordInput = screen.getByLabelText('密码')
      const submitButton = screen.getByRole('button', { name: '登录' })

      await user.type(usernameInput, 'wronguser')
      await user.type(passwordInput, 'wrongpassword')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('用户名或密码错误')).toBeInTheDocument()
      })
    })

    it('displays generic error message when no specific error is provided', async () => {
      const mockError = new Error('Network error')
      ;(api.post as jest.Mock).mockRejectedValue(mockError)

      render(<LoginPage />)

      const usernameInput = screen.getByLabelText('用户名')
      const passwordInput = screen.getByLabelText('密码')
      const submitButton = screen.getByRole('button', { name: '登录' })

      await user.type(usernameInput, 'testuser')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('登录失败，请重试')).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper form labels and associations', () => {
      render(<LoginPage />)

      const usernameInput = screen.getByLabelText('用户名')
      const passwordInput = screen.getByLabelText('密码')

      expect(usernameInput).toHaveAttribute('id', 'username')
      expect(passwordInput).toHaveAttribute('id', 'password')
    })
  })

  describe('Responsive Design', () => {
    it('has responsive layout classes', () => {
      render(<LoginPage />)

      // Use getAllByText to handle multiple elements with same text
      const loginElements = screen.getAllByText('登录')
      const titleElement = loginElements.find(el => 
        el.getAttribute('data-slot') === 'card-title'
      )
      
      expect(titleElement).toBeInTheDocument()
      const container = titleElement?.closest('.min-h-screen')
      expect(container).toHaveClass('min-h-screen', 'flex', 'items-center', 'justify-center')

      const card = titleElement?.closest('[data-slot="card"]')
      expect(card).toHaveClass('w-full', 'max-w-md')
    })
  })
})