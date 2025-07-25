/**
 * Test Utilities
 * 
 * Common utilities and helpers for API integration tests
 */

import { AxiosResponse } from 'axios'

// Mock response builder
export const createMockResponse = <T>(data: T, status: number = 200): AxiosResponse<T> => ({
  data,
  status,
  statusText: status === 200 ? 'OK' : 'Error',
  headers: {},
  config: {} as any,
  request: {}
})

// Mock error builder
export const createMockError = (status: number, message: string, detail?: string) => ({
  response: {
    status,
    data: {
      detail: detail || message,
      message
    },
    statusText: status >= 400 ? 'Error' : 'OK',
    headers: {},
    config: {} as any,
    request: {}
  },
  message,
  name: 'AxiosError',
  config: {} as any,
  isAxiosError: true
})

// Test data factories
export const createTestUser = (overrides: Partial<any> = {}) => ({
  id: '123',
  username: 'testuser',
  email: 'test@example.com',
  full_name: 'Test User',
  is_active: true,
  is_superuser: false,
  created_at: '2024-01-01T00:00:00Z',
  ...overrides
})

export const createTestDataSource = (overrides: Partial<any> = {}) => ({
  id: '123',
  name: 'Test Data Source',
  source_type: 'sql',
  connection_string: 'postgresql://localhost:5432/test',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  ...overrides
})

export const createTestTemplate = (overrides: Partial<any> = {}) => ({
  id: '123',
  name: 'Test Template',
  description: 'A test template',
  template_type: 'word',
  content: 'Hello {{name}}',
  is_public: false,
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  ...overrides
})

export const createTestReport = (overrides: Partial<any> = {}) => ({
  id: 123,
  task_id: 456,
  status: 'completed',
  file_path: '/reports/test-report.pdf',
  generated_at: '2024-01-01T00:00:00Z',
  ...overrides
})

// API endpoint helpers
export const API_ENDPOINTS = {
  auth: {
    login: '/v1/auth/login',
    me: '/v1/auth/me',
    refresh: '/v1/auth/refresh',
    logout: '/v1/auth/logout',
    register: '/v1/auth/register',
    changePassword: '/v1/auth/change-password'
  },
  dataSources: {
    list: '/v1/data-sources',
    detail: (id: string) => `/v1/data-sources/${id}`,
    test: (id: string) => `/v1/data-sources/${id}/test`,
    preview: (id: string) => `/v1/data-sources/${id}/wide-table`,
    sync: (id: string) => `/v1/data-sources/${id}/sync`
  },
  templates: {
    list: '/v1/templates',
    detail: (id: string) => `/v1/templates/${id}`,
    upload: '/v1/templates/upload',
    download: (id: string) => `/v1/templates/${id}/download`,
    validate: '/v1/templates/validate',
    preview: (id: string) => `/v1/templates/${id}/preview`,
    clone: (id: string) => `/v1/templates/${id}/clone`
  },
  reports: {
    list: '/v1/reports',
    detail: (id: number) => `/v1/reports/${id}`,
    generate: '/v1/reports/generate',
    regenerate: (id: number) => `/v1/reports/${id}/regenerate`,
    download: (id: number) => `/v1/reports/${id}/download`
  },
  placeholders: {
    analyze: '/v1/intelligent-placeholders/analyze',
    fieldMatching: '/v1/intelligent-placeholders/field-matching',
    generateReport: '/v1/intelligent-placeholders/generate-report',
    taskStatus: (taskId: string) => `/v1/intelligent-placeholders/task/${taskId}/status`,
    statistics: '/v1/intelligent-placeholders/statistics'
  }
}

// Test assertion helpers
export const expectApiCall = (mockFn: jest.MockedFunction<any>, endpoint: string, method: string = 'GET') => {
  expect(mockFn).toHaveBeenCalledWith(
    endpoint,
    method === 'GET' ? expect.any(Object) : expect.any(Object),
    method !== 'GET' ? expect.any(Object) : undefined
  )
}

export const expectFormDataCall = (mockFn: jest.MockedFunction<any>, endpoint: string) => {
  expect(mockFn).toHaveBeenCalledWith(
    endpoint,
    expect.any(FormData),
    expect.objectContaining({
      headers: expect.objectContaining({
        'Content-Type': 'multipart/form-data'
      })
    })
  )
}

// Mock localStorage for tests
export const mockLocalStorage = () => {
  const store: Record<string, string> = {}
  
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key]
    }),
    clear: jest.fn(() => {
      Object.keys(store).forEach(key => delete store[key])
    })
  }
}

// Mock sessionStorage for tests
export const mockSessionStorage = () => {
  const store: Record<string, string> = {}
  
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key]
    }),
    clear: jest.fn(() => {
      Object.keys(store).forEach(key => delete store[key])
    })
  }
}

// Setup test environment
export const setupTestEnvironment = () => {
  // Mock window.localStorage
  Object.defineProperty(window, 'localStorage', {
    value: mockLocalStorage(),
    writable: true
  })

  // Mock window.sessionStorage
  Object.defineProperty(window, 'sessionStorage', {
    value: mockSessionStorage(),
    writable: true
  })

  // Mock window.location
  Object.defineProperty(window, 'location', {
    value: {
      href: 'http://localhost:3000',
      origin: 'http://localhost:3000',
      pathname: '/',
      search: '',
      hash: '',
      reload: jest.fn()
    },
    writable: true
  })

  // Mock window.navigator
  Object.defineProperty(window, 'navigator', {
    value: {
      userAgent: 'Mozilla/5.0 (Test Environment)'
    },
    writable: true
  })

  // Mock console methods to reduce noise in tests
  jest.spyOn(console, 'log').mockImplementation(() => {})
  jest.spyOn(console, 'warn').mockImplementation(() => {})
  jest.spyOn(console, 'error').mockImplementation(() => {})
}

// Cleanup test environment
export const cleanupTestEnvironment = () => {
  jest.restoreAllMocks()
}

// Async test helpers
export const waitFor = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

export const waitForCondition = async (
  condition: () => boolean,
  timeout: number = 5000,
  interval: number = 100
): Promise<void> => {
  const startTime = Date.now()
  
  while (!condition() && Date.now() - startTime < timeout) {
    await waitFor(interval)
  }
  
  if (!condition()) {
    throw new Error(`Condition not met within ${timeout}ms`)
  }
}

// Error testing helpers
export const expectToThrowAsync = async (
  asyncFn: () => Promise<any>,
  expectedError?: any
) => {
  let error: any
  
  try {
    await asyncFn()
  } catch (e) {
    error = e
  }
  
  expect(error).toBeDefined()
  
  if (expectedError) {
    expect(error).toEqual(expectedError)
  }
  
  return error
}

// Performance testing helpers
export const measurePerformance = async <T>(
  fn: () => Promise<T>
): Promise<{ result: T; duration: number }> => {
  const startTime = performance.now()
  const result = await fn()
  const endTime = performance.now()
  
  return {
    result,
    duration: endTime - startTime
  }
}

// Retry testing helpers
export const withRetry = async <T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  delay: number = 100
): Promise<T> => {
  let lastError: any
  
  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error
      if (i < maxRetries) {
        await waitFor(delay)
      }
    }
  }
  
  throw lastError
}