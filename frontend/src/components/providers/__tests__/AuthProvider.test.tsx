import React from 'react'
import { render, screen, act, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { AuthProvider, useAuth } from '../AuthProvider'

// Mock API client
jest.mock('@/lib/api-client', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
    get: jest.fn(),
    setAuthToken: jest.fn(),
    clearAuthToken: jest.fn(),
  },
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

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
  }),
}))

// Test component that uses auth context
function TestComponent() {
  const { user, login, logout, loading, error } = useAuth()
  
  return (
    <div>
      <div data-testid="user">{user ? user.email : 'no-user'}</div>
      <div data-testid="loading">{loading ? 'loading' : 'not-loading'}</div>
      <div data-testid="error">{error || 'no-error'}</div>
      
      <button 
        data-testid="login"
        onClick={() => login('test@example.com', 'password')}
      >
        Login
      </button>
      
      <button 
        data-testid="logout"
        onClick={() => logout()}
      >
        Logout
      </button>
    </div>
  )
}

describe('AuthProvider', () => {
  const apiClient = require('@/lib/api-client').default

  beforeEach(() => {
    jest.clearAllMocks()
    mockLocalStorage.getItem.mockReturnValue(null)
  })

  it('should provide initial auth state', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    expect(screen.getByTestId('user')).toHaveTextContent('no-user')
    expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
    expect(screen.getByTestId('error')).toHaveTextContent('no-error')
  })

  it('should handle successful login', async () => {
    const user = userEvent.setup()
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      username: 'testuser',
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
    const mockToken = 'mock-jwt-token'

    apiClient.post.mockResolvedValue({
      data: {
        access_token: mockToken,
        user: mockUser
      }
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    const loginButton = screen.getByTestId('login')
    await user.click(loginButton)

    // Should show loading state
    expect(screen.getByTestId('loading')).toHaveTextContent('loading')

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('test@example.com')
      expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
      expect(screen.getByTestId('error')).toHaveTextContent('no-error')
    })

    // Should call API with correct credentials
    expect(apiClient.post).toHaveBeenCalledWith('/auth/login', {
      email: 'test@example.com',
      password: 'password'
    })

    // Should store token and set auth header
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('auth_token', mockToken)
    expect(apiClient.setAuthToken).toHaveBeenCalledWith(mockToken)
  })

  it('should handle login failure', async () => {
    const user = userEvent.setup()
    const errorMessage = 'Invalid credentials'

    apiClient.post.mockRejectedValue({
      response: {
        status: 401,
        data: { detail: errorMessage }
      }
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    const loginButton = screen.getByTestId('login')
    await user.click(loginButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent(errorMessage)
      expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
      expect(screen.getByTestId('user')).toHaveTextContent('no-user')
    })

    // Should not store token or set auth header
    expect(mockLocalStorage.setItem).not.toHaveBeenCalled()
    expect(apiClient.setAuthToken).not.toHaveBeenCalled()
  })

  it('should handle logout', async () => {
    const user = userEvent.setup()
    
    // Set initial authenticated state
    mockLocalStorage.getItem.mockReturnValue('existing-token')
    apiClient.get.mockResolvedValue({
      data: {
        id: 1,
        email: 'test@example.com',
        username: 'testuser',
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    // Wait for initial auth check
    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('test@example.com')
    })

    const logoutButton = screen.getByTestId('logout')
    await user.click(logoutButton)

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('no-user')
    })

    // Should clear token and auth header
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('auth_token')
    expect(apiClient.clearAuthToken).toHaveBeenCalled()
  })

  it('should restore auth state from localStorage on mount', async () => {
    const mockToken = 'stored-token'
    const mockUser = {
      id: 1,
      email: 'stored@example.com',
      username: 'storeduser',
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }

    mockLocalStorage.getItem.mockReturnValue(mockToken)
    apiClient.get.mockResolvedValue({ data: mockUser })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    // Should show loading initially
    expect(screen.getByTestId('loading')).toHaveTextContent('loading')

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('stored@example.com')
      expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
    })

    // Should set auth token and fetch user data
    expect(apiClient.setAuthToken).toHaveBeenCalledWith(mockToken)
    expect(apiClient.get).toHaveBeenCalledWith('/auth/me')
  })

  it('should handle invalid stored token', async () => {
    const mockToken = 'invalid-token'

    mockLocalStorage.getItem.mockReturnValue(mockToken)
    apiClient.get.mockRejectedValue({
      response: { status: 401 }
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('no-user')
      expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
    })

    // Should clear invalid token
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('auth_token')
    expect(apiClient.clearAuthToken).toHaveBeenCalled()
  })

  it('should provide register functionality', async () => {
    const TestRegisterComponent = () => {
      const { register, loading, error } = useAuth()
      
      return (
        <div>
          <div data-testid="loading">{loading ? 'loading' : 'not-loading'}</div>
          <div data-testid="error">{error || 'no-error'}</div>
          
          <button 
            data-testid="register"
            onClick={() => register('new@example.com', 'password', 'newuser')}
          >
            Register
          </button>
        </div>
      )
    }

    const user = userEvent.setup()
    const mockUser = {
      id: 2,
      email: 'new@example.com',
      username: 'newuser',
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }

    apiClient.post.mockResolvedValue({
      data: {
        access_token: 'new-token',
        user: mockUser
      }
    })

    render(
      <AuthProvider>
        <TestRegisterComponent />
      </AuthProvider>
    )

    const registerButton = screen.getByTestId('register')
    await user.click(registerButton)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
      expect(screen.getByTestId('error')).toHaveTextContent('no-error')
    })

    expect(apiClient.post).toHaveBeenCalledWith('/auth/register', {
      email: 'new@example.com',
      password: 'password',
      username: 'newuser'
    })
  })

  it('should handle concurrent auth operations', async () => {
    const user = userEvent.setup()
    
    apiClient.post.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({
        data: {
          access_token: 'token',
          user: { id: 1, email: 'test@example.com' }
        }
      }), 100))
    )

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    const loginButton = screen.getByTestId('login')
    
    // Click login multiple times quickly
    await user.click(loginButton)
    await user.click(loginButton)
    await user.click(loginButton)

    // Should only make one API call
    expect(apiClient.post).toHaveBeenCalledTimes(1)
  })

  it('should throw error when useAuth is used outside provider', () => {
    const TestComponentWithoutProvider = () => {
      try {
        useAuth()
        return <div>Should not render</div>
      } catch (error) {
        return <div data-testid="error">Error caught</div>
      }
    }

    // Suppress console.error for this test
    const originalError = console.error
    console.error = jest.fn()

    expect(() => {
      render(<TestComponentWithoutProvider />)
    }).toThrow('useAuth must be used within an AuthProvider')

    console.error = originalError
  })

  it('should clear error on successful operation', async () => {
    const user = userEvent.setup()

    // First, cause an error
    apiClient.post.mockRejectedValueOnce({
      response: { status: 401, data: { detail: 'Login failed' } }
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    const loginButton = screen.getByTestId('login')
    await user.click(loginButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('Login failed')
    })

    // Then, make a successful request
    apiClient.post.mockResolvedValue({
      data: {
        access_token: 'token',
        user: { id: 1, email: 'test@example.com' }
      }
    })

    await user.click(loginButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('no-error')
      expect(screen.getByTestId('user')).toHaveTextContent('test@example.com')
    })
  })
})