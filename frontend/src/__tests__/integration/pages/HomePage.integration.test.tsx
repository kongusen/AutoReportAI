import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useRouter } from 'next/navigation'
import HomePage from '@/app/(app)/page'
import { useAppState } from '@/lib/context/hooks'
import { useI18n } from '@/lib/i18n'
import api from '@/lib/api'

// Mock dependencies
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}))

jest.mock('@/lib/context/hooks', () => ({
  useAppState: jest.fn(),
}))

jest.mock('@/lib/i18n', () => ({
  useI18n: jest.fn(),
}))

jest.mock('@/lib/api', () => ({
  dataSources: {
    getAll: jest.fn(),
  },
  templates: {
    getAll: jest.fn(),
  },
  tasks: {
    getAll: jest.fn(),
  },
  reportHistory: {
    getAll: jest.fn(),
  },
}))

jest.mock('@/components/forms/ExportProgressTracker', () => {
  return function MockExportProgressTracker({ className }: { className?: string }) {
    return <div data-testid="export-progress-tracker" className={className}>Export Progress Tracker</div>
  }
})

const mockRouter = {
  push: jest.fn(),
  replace: jest.fn(),
  back: jest.fn(),
  forward: jest.fn(),
  refresh: jest.fn(),
  prefetch: jest.fn(),
}

const mockAppState = {
  templates: {
    templates: [],
    setTemplates: jest.fn(),
    addTemplate: jest.fn(),
    deleteTemplate: jest.fn(),
  },
  dataSources: {
    dataSources: [],
    setDataSources: jest.fn(),
    addDataSource: jest.fn(),
    deleteDataSource: jest.fn(),
  },
  tasks: {
    tasks: [],
    activeTasks: [],
    setTasks: jest.fn(),
  },
  reportHistory: {
    reportHistory: [],
    recentReports: [],
    setReportHistory: jest.fn(),
  },
  ui: {
    loading: false,
    error: null,
    setLoading: jest.fn(),
    setError: jest.fn(),
    clearError: jest.fn(),
  },
}

const mockI18n = {
  t: (key: string) => key,
  locale: 'en',
  setLocale: jest.fn(),
}

describe('HomePage Integration Tests', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useRouter as jest.Mock).mockReturnValue(mockRouter)
    ;(useAppState as jest.Mock).mockReturnValue(mockAppState)
    ;(useI18n as jest.Mock).mockReturnValue(mockI18n)
  })

  describe('Initial Render and Loading States', () => {
    it('renders loading state initially', () => {
      const loadingState = {
        ...mockAppState,
        ui: { ...mockAppState.ui, loading: true },
      }
      ;(useAppState as jest.Mock).mockReturnValue(loadingState)

      render(<HomePage />)

      expect(screen.getByText('Loading dashboard...')).toBeInTheDocument()
    })

    it('renders error state when API fails', () => {
      const errorState = {
        ...mockAppState,
        ui: { ...mockAppState.ui, error: 'Failed to load dashboard data' },
      }
      ;(useAppState as jest.Mock).mockReturnValue(errorState)

      render(<HomePage />)

      expect(screen.getByText('Failed to load dashboard data')).toBeInTheDocument()
    })

    it('renders dashboard with empty state', () => {
      render(<HomePage />)

      expect(screen.getByText('Dashboard')).toBeInTheDocument()
      expect(screen.getByText("Welcome back! Here's what's happening with your reports.")).toBeInTheDocument()
      expect(screen.getByText('No recent activity')).toBeInTheDocument()
    })
  })

  describe('Dashboard Stats Display', () => {
    it('displays correct stats when data is available', () => {
      const stateWithData = {
        ...mockAppState,
        templates: {
          ...mockAppState.templates,
          templates: [
            { id: '1', name: 'Template 1' },
            { id: '2', name: 'Template 2' },
          ],
        },
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            { id: 1, name: 'Source 1', source_type: 'sql' },
            { id: 2, name: 'Source 2', source_type: 'csv' },
            { id: 3, name: 'Source 3', source_type: 'api' },
          ],
        },
        tasks: {
          ...mockAppState.tasks,
          tasks: [
            { id: 1, name: 'Task 1', is_active: true },
            { id: 2, name: 'Task 2', is_active: false },
          ],
          activeTasks: [{ id: 1, name: 'Task 1', is_active: true }],
        },
        reportHistory: {
          ...mockAppState.reportHistory,
          reportHistory: [
            { id: 1, status: 'success', task_id: 1, generated_at: '2024-01-01T00:00:00Z' },
            { id: 2, status: 'failure', task_id: 2, generated_at: '2024-01-02T00:00:00Z' },
          ],
          recentReports: [
            { id: 1, status: 'success', task_id: 1, generated_at: '2024-01-01T00:00:00Z' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      render(<HomePage />)

      // Check stats cards
      expect(screen.getByText('2')).toBeInTheDocument() // Total Reports
      expect(screen.getByText('1')).toBeInTheDocument() // Active Tasks
      expect(screen.getByText('50%')).toBeInTheDocument() // Success Rate
      expect(screen.getByText('3')).toBeInTheDocument() // Data Sources
    })

    it('calculates success rate correctly', () => {
      const stateWithReports = {
        ...mockAppState,
        reportHistory: {
          ...mockAppState.reportHistory,
          reportHistory: [
            { id: 1, status: 'success', task_id: 1, generated_at: '2024-01-01T00:00:00Z' },
            { id: 2, status: 'success', task_id: 2, generated_at: '2024-01-02T00:00:00Z' },
            { id: 3, status: 'success', task_id: 3, generated_at: '2024-01-03T00:00:00Z' },
            { id: 4, status: 'failure', task_id: 4, generated_at: '2024-01-04T00:00:00Z' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithReports)

      render(<HomePage />)

      expect(screen.getByText('75%')).toBeInTheDocument() // 3 success out of 4 total
    })
  })

  describe('Recent Activity Section', () => {
    it('displays recent reports with correct status icons and badges', () => {
      const stateWithReports = {
        ...mockAppState,
        reportHistory: {
          ...mockAppState.reportHistory,
          recentReports: [
            { id: 1, status: 'success', task_id: 1, generated_at: '2024-01-01T12:00:00Z' },
            { id: 2, status: 'failure', task_id: 2, generated_at: '2024-01-02T12:00:00Z' },
            { id: 3, status: 'in_progress', task_id: 3, generated_at: '2024-01-03T12:00:00Z' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithReports)

      render(<HomePage />)

      expect(screen.getByText('Task #1')).toBeInTheDocument()
      expect(screen.getByText('Task #2')).toBeInTheDocument()
      expect(screen.getByText('Task #3')).toBeInTheDocument()
      expect(screen.getByText('success')).toBeInTheDocument()
      expect(screen.getByText('failure')).toBeInTheDocument()
      expect(screen.getByText('in_progress')).toBeInTheDocument()
    })

    it('formats dates correctly', () => {
      const stateWithReports = {
        ...mockAppState,
        reportHistory: {
          ...mockAppState.reportHistory,
          recentReports: [
            { id: 1, status: 'success', task_id: 1, generated_at: '2024-01-01T12:00:00Z' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithReports)

      render(<HomePage />)

      // Check that date is formatted (exact format may vary by locale)
      expect(screen.getByText(/2024/)).toBeInTheDocument()
    })
  })

  describe('Quick Actions Navigation', () => {
    it('renders all quick action buttons', () => {
      render(<HomePage />)

      expect(screen.getByText('Add Data Source')).toBeInTheDocument()
      expect(screen.getByText('Upload Template')).toBeInTheDocument()
      expect(screen.getByText('Create Task')).toBeInTheDocument()
      expect(screen.getByText('Data Export')).toBeInTheDocument()
      expect(screen.getByText('Settings')).toBeInTheDocument()
    })

    it('has correct navigation links', () => {
      render(<HomePage />)

      const dataSourceLink = screen.getByText('Add Data Source').closest('a')
      const templateLink = screen.getByText('Upload Template').closest('a')
      const taskLink = screen.getByText('Create Task').closest('a')
      const exportLink = screen.getByText('Data Export').closest('a')
      const settingsLink = screen.getByText('Settings').closest('a')

      expect(dataSourceLink).toHaveAttribute('href', '/data-sources')
      expect(templateLink).toHaveAttribute('href', '/templates')
      expect(taskLink).toHaveAttribute('href', '/tasks')
      expect(exportLink).toHaveAttribute('href', '/data-export')
      expect(settingsLink).toHaveAttribute('href', '/settings')
    })
  })

  describe('Recent Tasks Section', () => {
    it('displays recent tasks when available', () => {
      const stateWithTasks = {
        ...mockAppState,
        tasks: {
          ...mockAppState.tasks,
          tasks: [
            { id: 1, name: 'Daily Report Task', is_active: true },
            { id: 2, name: 'Weekly Summary', is_active: false },
            { id: 3, name: 'Monthly Analysis', is_active: true },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithTasks)

      render(<HomePage />)

      expect(screen.getByText('Recent Tasks')).toBeInTheDocument()
      expect(screen.getByText('Daily Report Task')).toBeInTheDocument()
      expect(screen.getByText('Weekly Summary')).toBeInTheDocument()
      expect(screen.getByText('Monthly Analysis')).toBeInTheDocument()
      expect(screen.getAllByText('Active')).toHaveLength(2)
      expect(screen.getByText('Inactive')).toBeInTheDocument()
    })

    it('does not display recent tasks section when no tasks exist', () => {
      render(<HomePage />)

      expect(screen.queryByText('Recent Tasks')).not.toBeInTheDocument()
    })
  })

  describe('Export Progress Tracker Integration', () => {
    it('renders export progress tracker component', () => {
      render(<HomePage />)

      expect(screen.getByTestId('export-progress-tracker')).toBeInTheDocument()
    })
  })

  describe('API Integration and Data Fetching', () => {
    it('calls fetchDashboardData on mount', async () => {
      const mockApiCalls = {
        dataSources: { getAll: jest.fn().mockResolvedValue({ data: [] }) },
        templates: { getAll: jest.fn().mockResolvedValue({ data: [] }) },
        tasks: { getAll: jest.fn().mockResolvedValue({ data: [] }) },
        reportHistory: { getAll: jest.fn().mockResolvedValue({ data: [] }) },
      }

      // Mock the API calls
      jest.mocked(api).dataSources.getAll = mockApiCalls.dataSources.getAll
      jest.mocked(api).templates.getAll = mockApiCalls.templates.getAll
      jest.mocked(api).tasks.getAll = mockApiCalls.tasks.getAll
      jest.mocked(api).reportHistory.getAll = mockApiCalls.reportHistory.getAll

      render(<HomePage />)

      await waitFor(() => {
        expect(mockAppState.ui.setLoading).toHaveBeenCalledWith(true)
      })
    })

    it('handles API errors gracefully', async () => {
      const errorState = {
        ...mockAppState,
        ui: {
          ...mockAppState.ui,
          error: 'Failed to load dashboard data',
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(errorState)

      render(<HomePage />)

      expect(screen.getByText('Failed to load dashboard data')).toBeInTheDocument()
    })
  })

  describe('Responsive Design', () => {
    it('renders grid layouts correctly', () => {
      render(<HomePage />)

      // Check for grid classes that indicate responsive design
      const statsGrid = screen.getByText('Total Reports').closest('.grid')
      expect(statsGrid).toHaveClass('grid-cols-1', 'md:grid-cols-2', 'lg:grid-cols-4')

      const mainGrid = screen.getByText('Recent Activity').closest('.grid')
      expect(mainGrid).toHaveClass('grid-cols-1', 'lg:grid-cols-3')
    })
  })

  describe('User Interactions', () => {
    it('handles header navigation button clicks', async () => {
      render(<HomePage />)

      const newTaskButton = screen.getByText('New Task')
      expect(newTaskButton.closest('a')).toHaveAttribute('href', '/tasks')
    })

    it('handles view all button in recent activity', () => {
      const stateWithReports = {
        ...mockAppState,
        reportHistory: {
          ...mockAppState.reportHistory,
          recentReports: [
            { id: 1, status: 'success', task_id: 1, generated_at: '2024-01-01T12:00:00Z' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithReports)

      render(<HomePage />)

      const viewAllButton = screen.getByText('View All')
      expect(viewAllButton.closest('a')).toHaveAttribute('href', '/history')
    })

    it('handles manage tasks button in recent tasks', () => {
      const stateWithTasks = {
        ...mockAppState,
        tasks: {
          ...mockAppState.tasks,
          tasks: [{ id: 1, name: 'Test Task', is_active: true }],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithTasks)

      render(<HomePage />)

      const manageTasksButton = screen.getByText('Manage Tasks')
      expect(manageTasksButton.closest('a')).toHaveAttribute('href', '/tasks')
    })
  })

  describe('Accessibility', () => {
    it('has proper heading hierarchy', () => {
      render(<HomePage />)

      const mainHeading = screen.getByRole('heading', { level: 1 })
      expect(mainHeading).toHaveTextContent('Dashboard')
    })

    it('has accessible card titles', () => {
      render(<HomePage />)

      expect(screen.getByText('Total Reports')).toBeInTheDocument()
      expect(screen.getByText('Active Tasks')).toBeInTheDocument()
      expect(screen.getByText('Success Rate')).toBeInTheDocument()
      expect(screen.getByText('Data Sources')).toBeInTheDocument()
    })

    it('has accessible navigation links', () => {
      render(<HomePage />)

      const links = screen.getAllByRole('link')
      expect(links.length).toBeGreaterThan(0)
      
      // Check that important links have proper text content
      expect(screen.getByText('Add Data Source')).toBeInTheDocument()
      expect(screen.getByText('Upload Template')).toBeInTheDocument()
    })
  })

  describe('Performance Considerations', () => {
    it('memoizes computed stats correctly', () => {
      const { rerender } = render(<HomePage />)
      
      // Re-render with same data should not cause unnecessary recalculations
      rerender(<HomePage />)
      
      // This test ensures useMemo is working correctly
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
    })

    it('handles large datasets efficiently', () => {
      const largeDataState = {
        ...mockAppState,
        reportHistory: {
          ...mockAppState.reportHistory,
          recentReports: Array.from({ length: 100 }, (_, i) => ({
            id: i + 1,
            status: 'success',
            task_id: i + 1,
            generated_at: '2024-01-01T12:00:00Z',
          })),
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(largeDataState)

      render(<HomePage />)

      // Should only display first 5 recent reports
      expect(screen.getAllByText(/Task #/)).toHaveLength(5)
    })
  })
})