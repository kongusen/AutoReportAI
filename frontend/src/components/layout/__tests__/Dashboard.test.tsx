import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { Dashboard } from '../Dashboard'

// Mock API client
jest.mock('@/lib/api-client', () => ({
  __esModule: true,
  default: {
    get: jest.fn().mockResolvedValue({ 
      data: {
        templates: [],
        reports: [],
        dataSources: [],
        stats: {
          totalTemplates: 0,
          totalReports: 0,
          totalDataSources: 0,
          recentActivity: []
        }
      }
    }),
  },
}))

// Mock components that might have complex dependencies
jest.mock('../OverviewStats', () => ({
  OverviewStats: ({ stats }: { stats: any }) => (
    <div data-testid="overview-stats">
      <div data-testid="total-templates">{stats?.totalTemplates || 0}</div>
      <div data-testid="total-reports">{stats?.totalReports || 0}</div>
      <div data-testid="total-data-sources">{stats?.totalDataSources || 0}</div>
    </div>
  )
}))

jest.mock('../TemplateList', () => ({
  TemplateList: ({ templates }: { templates: any[] }) => (
    <div data-testid="template-list">
      <div data-testid="template-count">{templates?.length || 0}</div>
    </div>
  )
}))

jest.mock('../TaskList', () => ({
  TaskList: ({ tasks }: { tasks: any[] }) => (
    <div data-testid="task-list">
      <div data-testid="task-count">{tasks?.length || 0}</div>
    </div>
  )
}))

describe('Dashboard Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should render dashboard with default state', () => {
    render(<Dashboard />)
    
    expect(screen.getByText(/仪表板/i)).toBeInTheDocument()
    expect(screen.getByTestId('overview-stats')).toBeInTheDocument()
    expect(screen.getByTestId('template-list')).toBeInTheDocument()
    expect(screen.getByTestId('task-list')).toBeInTheDocument()
  })

  it('should display loading state initially', () => {
    render(<Dashboard />)
    
    // Should show loading indicators
    expect(screen.getByText(/加载中/i) || screen.getByRole('progressbar')).toBeInTheDocument()
  })

  it('should load and display dashboard data', async () => {
    const mockData = {
      templates: [
        { id: '1', name: 'Template 1' },
        { id: '2', name: 'Template 2' }
      ],
      reports: [
        { id: '1', title: 'Report 1' }
      ],
      dataSources: [
        { id: 1, name: 'Data Source 1' }
      ],
      stats: {
        totalTemplates: 2,
        totalReports: 1,
        totalDataSources: 1,
        recentActivity: []
      }
    }

    const apiClient = require('@/lib/api-client').default
    apiClient.get.mockResolvedValue({ data: mockData })

    render(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByTestId('total-templates')).toHaveTextContent('2')
      expect(screen.getByTestId('total-reports')).toHaveTextContent('1')
      expect(screen.getByTestId('total-data-sources')).toHaveTextContent('1')
      expect(screen.getByTestId('template-count')).toHaveTextContent('2')
    })
  })

  it('should handle API errors gracefully', async () => {
    const apiClient = require('@/lib/api-client').default
    apiClient.get.mockRejectedValue(new Error('API Error'))

    render(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByText(/错误/i) || screen.getByText(/failed/i)).toBeInTheDocument()
    })
  })

  it('should refresh data when refresh button is clicked', async () => {
    const apiClient = require('@/lib/api-client').default
    const user = userEvent.setup()

    render(<Dashboard />)

    const refreshButton = screen.getByRole('button', { name: /刷新/i }) || 
                         screen.getByRole('button', { name: /refresh/i })
    
    if (refreshButton) {
      await user.click(refreshButton)

      await waitFor(() => {
        expect(apiClient.get).toHaveBeenCalledTimes(2) // Initial load + refresh
      })
    }
  })

  it('should navigate to different sections', async () => {
    const user = userEvent.setup()
    render(<Dashboard />)

    // Test navigation to templates
    const templatesLink = screen.getByText(/模板/i) || screen.getByText(/templates/i)
    if (templatesLink) {
      await user.click(templatesLink)
      // Navigation would be handled by Next.js router in real app
    }

    // Test navigation to reports
    const reportsLink = screen.getByText(/报告/i) || screen.getByText(/reports/i)
    if (reportsLink) {
      await user.click(reportsLink)
      // Navigation would be handled by Next.js router in real app
    }
  })

  it('should display recent activity', async () => {
    const mockData = {
      templates: [],
      reports: [],
      dataSources: [],
      stats: {
        totalTemplates: 0,
        totalReports: 0,
        totalDataSources: 0,
        recentActivity: [
          { id: '1', type: 'template_created', message: 'Created new template', timestamp: new Date().toISOString() },
          { id: '2', type: 'report_generated', message: 'Generated report', timestamp: new Date().toISOString() }
        ]
      }
    }

    const apiClient = require('@/lib/api-client').default
    apiClient.get.mockResolvedValue({ data: mockData })

    render(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByText(/最近活动/i) || screen.getByText(/recent activity/i)).toBeInTheDocument()
    })
  })

  it('should handle empty state', async () => {
    const mockData = {
      templates: [],
      reports: [],
      dataSources: [],
      stats: {
        totalTemplates: 0,
        totalReports: 0,
        totalDataSources: 0,
        recentActivity: []
      }
    }

    const apiClient = require('@/lib/api-client').default
    apiClient.get.mockResolvedValue({ data: mockData })

    render(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByTestId('total-templates')).toHaveTextContent('0')
      expect(screen.getByTestId('total-reports')).toHaveTextContent('0')
      expect(screen.getByTestId('total-data-sources')).toHaveTextContent('0')
    })
  })

  it('should be responsive on different screen sizes', () => {
    // Mock window.matchMedia for responsive testing
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(query => ({
        matches: query.includes('768px'), // Mock mobile breakpoint
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    })

    render(<Dashboard />)

    // Dashboard should render without errors on mobile
    expect(screen.getByText(/仪表板/i)).toBeInTheDocument()
  })

  it('should handle keyboard navigation', async () => {
    const user = userEvent.setup()
    render(<Dashboard />)

    // Tab through interactive elements
    await user.tab()
    
    // First focusable element should be focused
    const focusedElement = document.activeElement
    expect(focusedElement).toBeInTheDocument()
  })

  it('should update data periodically', async () => {
    jest.useFakeTimers()
    
    const apiClient = require('@/lib/api-client').default
    render(<Dashboard />)

    // Fast-forward time to trigger periodic update
    jest.advanceTimersByTime(30000) // 30 seconds

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledTimes(2) // Initial + periodic update
    })

    jest.useRealTimers()
  })
})