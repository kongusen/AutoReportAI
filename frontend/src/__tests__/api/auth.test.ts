/**
 * Authentication API Integration Tests
 */

import { authApiService } from '@/lib/api/services/auth-service'
import { httpClient } from '@/lib/api/client'
import { getAuthToken, setAuthToken, removeAuthToken } from '@/lib/auth'

// Mock the HTTP client
jest.mock('@/lib/api/client')
const mockedHttpClient = httpClient as jest.Mocked<typeof httpClient>

// Mock auth utilities
jest.mock('@/lib/auth')
const mockedGetAuthToken = getAuthToken as jest.MockedFunction<typeof getAuthToken>
const mockedSetAuthToken = setAuthToken as jest.MockedFunction<typeof setAuthToken>
const mockedRemoveAuthToken = removeAuthToken as jest.MockedFunction<typeof removeAuthToken>

describe('Authentication API Service', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('login', () => {
    it('should successfully login with valid credentials', async () => {
      const mockResponse = {
        data: {
          access_token: 'mock-token',
          token_type: 'bearer',
          user: {
            id: '123',
            username: 'testuser',
            email: 'test@example.com',
            is_active: true
          }
        }
      }

      mockedHttpClient.post.mockResolvedValue(mockResponse)

      const result = await authApiService.login({
        username: 'testuser',
        password: 'password123'
      })

      expect(mockedHttpClient.post).toHaveBeenCalledWith(
        '/v1/auth/login',
        expect.any(URLSearchParams),
        {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        }
      )

      expect(result).toEqual(mockResponse.data)
    })

    it('should handle login failure with invalid credentials', async () => {
      const mockError = {
        response: {
          status: 401,
          data: {
            detail: 'Invalid credentials'
          }
        }
      }

      mockedHttpClient.post.mockRejectedValue(mockError)

      await expect(authApiService.login({
        username: 'testuser',
        password: 'wrongpassword'
      })).rejects.toEqual(mockError)
    })

    it('should format form data correctly', async () => {
      const mockResponse = { data: { access_token: 'token' } }
      mockedHttpClient.post.mockResolvedValue(mockResponse)

      await authApiService.login({
        username: 'testuser',
        password: 'password123'
      })

      const formData = mockedHttpClient.post.mock.calls[0][1] as URLSearchParams
      expect(formData.get('username')).toBe('testuser')
      expect(formData.get('password')).toBe('password123')
      expect(formData.get('grant_type')).toBe('password')
    })
  })

  describe('getCurrentUser', () => {
    it('should successfully get current user', async () => {
      const mockUser = {
        id: '123',
        username: 'testuser',
        email: 'test@example.com',
        is_active: true
      }

      mockedHttpClient.get.mockResolvedValue({ data: mockUser })

      const result = await authApiService.getCurrentUser()

      expect(mockedHttpClient.get).toHaveBeenCalledWith('/v1/auth/me')
      expect(result).toEqual(mockUser)
    })

    it('should handle unauthorized access', async () => {
      const mockError = {
        response: {
          status: 401,
          data: {
            detail: 'Not authenticated'
          }
        }
      }

      mockedHttpClient.get.mockRejectedValue(mockError)

      await expect(authApiService.getCurrentUser()).rejects.toEqual(mockError)
    })
  })

  describe('refreshToken', () => {
    it('should successfully refresh token', async () => {
      const mockResponse = {
        data: {
          data: {
            access_token: 'new-token',
            token_type: 'bearer'
          }
        }
      }

      mockedHttpClient.post.mockResolvedValue(mockResponse)

      const result = await authApiService.refreshToken()

      expect(mockedHttpClient.post).toHaveBeenCalledWith('/v1/auth/refresh')
      expect(result).toEqual(mockResponse.data.data)
    })
  })

  describe('logout', () => {
    it('should successfully logout', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Logged out successfully'
        }
      }

      mockedHttpClient.post.mockResolvedValue(mockResponse)

      const result = await authApiService.logout()

      expect(mockedHttpClient.post).toHaveBeenCalledWith('/v1/auth/logout', {})
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('validateToken', () => {
    it('should return valid true when user exists', async () => {
      const mockUser = {
        id: '123',
        username: 'testuser',
        email: 'test@example.com'
      }

      mockedHttpClient.get.mockResolvedValue({ data: mockUser })

      const result = await authApiService.validateToken()

      expect(result).toEqual({
        valid: true,
        user: mockUser
      })
    })

    it('should return valid false when token is invalid', async () => {
      mockedHttpClient.get.mockRejectedValue(new Error('Invalid token'))

      const result = await authApiService.validateToken()

      expect(result).toEqual({
        valid: false
      })
    })
  })

  describe('register', () => {
    it('should successfully register new user', async () => {
      const mockResponse = {
        data: {
          id: '123',
          user: {
            id: '123',
            username: 'newuser',
            email: 'new@example.com',
            is_active: true
          }
        }
      }

      const registerData = {
        username: 'newuser',
        email: 'new@example.com',
        password: 'password123',
        fullName: 'New User'
      }

      mockedHttpClient.post.mockResolvedValue(mockResponse)

      const result = await authApiService.register(registerData)

      expect(mockedHttpClient.post).toHaveBeenCalledWith('/v1/auth/register', registerData)
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('changePassword', () => {
    it('should successfully change password', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Password changed successfully'
        }
      }

      const changePasswordData = {
        currentPassword: 'oldpassword',
        newPassword: 'newpassword'
      }

      mockedHttpClient.post.mockResolvedValue(mockResponse)

      const result = await authApiService.changePassword(changePasswordData)

      expect(mockedHttpClient.post).toHaveBeenCalledWith('/v1/auth/change-password', changePasswordData)
      expect(result).toEqual(mockResponse.data)
    })
  })
})

describe('Authentication Integration Flow', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should complete full authentication flow', async () => {
    // Mock successful login
    const loginResponse = {
      data: {
        access_token: 'mock-token',
        token_type: 'bearer',
        user: {
          id: '123',
          username: 'testuser',
          email: 'test@example.com'
        }
      }
    }

    // Mock successful user fetch
    const userResponse = {
      data: {
        id: '123',
        username: 'testuser',
        email: 'test@example.com',
        is_active: true
      }
    }

    mockedHttpClient.post.mockResolvedValueOnce(loginResponse)
    mockedHttpClient.get.mockResolvedValueOnce(userResponse)

    // Step 1: Login
    const loginResult = await authApiService.login({
      username: 'testuser',
      password: 'password123'
    })

    expect(loginResult.access_token).toBe('mock-token')

    // Step 2: Get current user
    const userResult = await authApiService.getCurrentUser()

    expect(userResult.username).toBe('testuser')

    // Verify API calls
    expect(mockedHttpClient.post).toHaveBeenCalledWith(
      '/v1/auth/login',
      expect.any(URLSearchParams),
      expect.any(Object)
    )
    expect(mockedHttpClient.get).toHaveBeenCalledWith('/v1/auth/me')
  })

  it('should handle authentication errors gracefully', async () => {
    const loginError = {
      response: {
        status: 401,
        data: {
          detail: 'Invalid credentials'
        }
      }
    }

    mockedHttpClient.post.mockRejectedValue(loginError)

    await expect(authApiService.login({
      username: 'testuser',
      password: 'wrongpassword'
    })).rejects.toEqual(loginError)

    // Should not attempt to get user after failed login
    expect(mockedHttpClient.get).not.toHaveBeenCalled()
  })
})

describe('Authentication Error Scenarios', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should handle network errors', async () => {
    const networkError = new Error('Network Error')
    mockedHttpClient.post.mockRejectedValue(networkError)

    await expect(authApiService.login({
      username: 'testuser',
      password: 'password123'
    })).rejects.toThrow('Network Error')
  })

  it('should handle server errors', async () => {
    const serverError = {
      response: {
        status: 500,
        data: {
          detail: 'Internal Server Error'
        }
      }
    }

    mockedHttpClient.post.mockRejectedValue(serverError)

    await expect(authApiService.login({
      username: 'testuser',
      password: 'password123'
    })).rejects.toEqual(serverError)
  })

  it('should handle malformed responses', async () => {
    const malformedResponse = {
      data: null
    }

    mockedHttpClient.post.mockResolvedValue(malformedResponse)

    const result = await authApiService.login({
      username: 'testuser',
      password: 'password123'
    })

    expect(result).toBeNull()
  })
})