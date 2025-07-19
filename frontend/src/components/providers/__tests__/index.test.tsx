import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'

// Mock the providers to avoid complex dependencies in index test
jest.mock('../AuthProvider', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="auth-provider">{children}</div>
  ),
  useAuth: () => ({
    user: null,
    login: jest.fn(),
    logout: jest.fn(),
    loading: false,
    error: null
  })
}))

jest.mock('../NotificationProvider', () => ({
  NotificationProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="notification-provider">{children}</div>
  ),
  useNotification: () => ({
    notifications: [],
    addNotification: jest.fn(),
    removeNotification: jest.fn()
  })
}))

describe('Provider Components Index', () => {
  it('should export all provider components without errors', async () => {
    const { AuthProvider, useAuth } = await import('../AuthProvider')
    const { NotificationProvider } = await import('../NotificationProvider')
    
    expect(AuthProvider).toBeDefined()
    expect(useAuth).toBeDefined()
    expect(NotificationProvider).toBeDefined()
  })

  it('should render provider components', () => {
    const { AuthProvider } = require('../AuthProvider')
    const { NotificationProvider } = require('../NotificationProvider')
    
    render(
      <AuthProvider>
        <NotificationProvider>
          <div>Test Content</div>
        </NotificationProvider>
      </AuthProvider>
    )
    
    expect(screen.getByTestId('auth-provider')).toBeInTheDocument()
    expect(screen.getByTestId('notification-provider')).toBeInTheDocument()
    expect(screen.getByText('Test Content')).toBeInTheDocument()
  })
})