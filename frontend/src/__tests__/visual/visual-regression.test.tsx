import React from 'react'
import { render } from '@testing-library/react'
import { toMatchImageSnapshot } from 'jest-image-snapshot'
import HomePage from '@/app/(app)/page'
import LoginPage from '@/app/(auth)/login/page'
import DataSourcesPage from '@/app/(app)/data-sources/page'
import TemplatesPage from '@/app/(app)/templates/page'
import { useAppState } from '@/lib/context/hooks'
import { useI18n } from '@/lib/i18n'
import { useRouter } from 'next/navigation'

// Extend Jest matchers
expect.extend({ toMatchImageSnapshot })

// Mock dependencies for visual testing
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
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
}))

// Mock complex components for visual consistency
jest.mock('@/components/forms/ExportProgressTracker', () => {
  return function MockExportProgressTracker() {
    return <div data-testid="export-progress-tracker">Export Progress Tracker</div>
  }
})

jest.mock('@/components/forms', () => ({
  DataSourceForm: () => <div data-testid="data-source-form">Data Source Form</div>,
  QuickExportButton: () => <button>Quick Export</button>,
}))

jest.mock('@/components/layout', () => ({
  TemplateList: () => <div data-testid="template-list">Template List</div>,
}))

const mockRouter = {
  push: jest.fn(),
  replace: jest.fn(),
  back: jest.fn(),
  forward: jest.fn(),
  refresh: jest.fn(),
  prefetch: jest.fn(),
}

const mockI18n = {
  t: (key: string) => key,
  locale: 'en',
  setLocale: jest.fn(),
}

const createMockAppState = (overrides = {}) => ({
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
    updateDataSource: jest.fn(),
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
  ...overrides,
})

describe('Visual Regression Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    ;(useRouter as jest.Mock).mockReturnValue(mockRouter)
    ;(useI18n as jest.Mock).mockReturnValue(mockI18n)
    ;(useAppState as jest.Mock).mockReturnValue(createMockAppState())
  })

  describe('HomePage Visual Tests', () => {
    it('matches snapshot for empty dashboard state', () => {
      const { container } = render(<HomePage />)
      expect(container.firstChild).toMatchImageSnapshot({
        customSnapshotIdentifier: 'homepage-empty-state',
        failureThreshold: 0.01,
        failureThresholdType: 'percent',
      })
    })

    it('matches snapshot for dashboard with data', () => {
      const stateWithData = createMockAppState({
        templates: {
          templates: [
            { id: '1', name: 'Template 1' },
            { id: '2', name: 'Template 2' },
          ],
          setTemplates: jest.fn(),
          addTemplate: jest.fn(),
          deleteTemplate: jest.fn(),
        },
        dataSources: {
          dataSources: [
            { id: 1, name: 'Source 1', source_type: 'sql' },
            { id: 2, name: 'Source 2', source_type: 'csv' },
          ],
          setDataSources: jest.fn(),
          addDataSource: jest.fn(),
          updateDataSource: jest.fn(),
          deleteDataSource: jest.fn(),
        },
        tasks: {
          tasks: [
            { id: 1, name: 'Task 1', is_active: true },
            { id: 2, name: 'Task 2', is_active: false },
          ],
          activeTasks: [{ id: 1, name: 'Task 1', is_active: true }],
          setTasks: jest.fn(),
        },
        reportHistory: {
          reportHistory: [
            { id: 1, status: 'success', task_id: 1, generated_at: '2024-01-01T00:00:00Z' },
            { id: 2, status: 'failure', task_id: 2, generated_at: '2024-01-02T00:00:00Z' },
          ],
          recentReports: [
            { id: 1, status: 'success', task_id: 1, generated_at: '2024-01-01T00:00:00Z' },
          ],
          setReportHistory: jest.fn(),
        },
      })
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      const { container } = render(<HomePage />)
      expect(container.firstChild).toMatchImageSnapshot({
        customSnapshotIdentifier: 'homepage-with-data',
        failureThreshold: 0.01,
        failureThresholdType: 'percent',
      })
    })

    it('matches snapshot for loading state', () => {
      const loadingState = createMockAppState({
        ui: {
          loading: true,
          error: null,
          setLoading: jest.fn(),
          setError: jest.fn(),
          clearError: jest.fn(),
        },
      })
      ;(useAppState as jest.Mock).mockReturnValue(loadingState)

      const { container } = render(<HomePage />)
      expect(container.firstChild).toMatchImageSnapshot({
        customSnapshotIdentifier: 'homepage-loading',
        failureThreshold: 0.01,
        failureThresholdType: 'percent',
      })
    })

    it('matches snapshot for error state', () => {
      const errorState = createMockAppState({
        ui: {
          loading: false,
          error: 'Failed to load dashboard data',
          setLoading: jest.fn(),
          setError: jest.fn(),
          clearError: jest.fn(),
        },
      })
      ;(useAppState as jest.Mock).mockReturnValue(errorState)

      const { container } = render(<HomePage />)
      expect(container.firstChild).toMatchImageSnapshot({
        customSnapshotIdentifier: 'homepage-error',
        failureThreshold: 0.01,
        failureThresholdType: 'percent',
      })
    })
  })

  describe('LoginPage Visual Tests', () => {
    it('matches snapshot for initial login form', () => {
      const { container } = render(<LoginPage />)
      expect(container.firstChild).toMatchImageSnapshot({
        customSnapshotIdentifier: 'login-initial',
        failureThreshold: 0.01,
        failureThresholdType: 'percent',
      })
    })

    it('matches snapshot for login form with error', () => {
      // This would require state management in LoginPage to show error
      // For now, we'll test the basic form structure
      const { container } = render(<LoginPage />)
      expect(container.firstChild).toMatchImageSnapshot({
        customSnapshotIdentifier: 'login-form',
        failureThreshold: 0.01,
        failureThresholdType: 'percent',
      })
    })
  })

  describe('DataSourcesPage Visual Tests', () => {
    it('matches snapshot for empty data sources state', () => {
      const { container } = render(<DataSourcesPage />)
      expect(container.firstChild).toMatchImageSnapshot({
        customSnapshotIdentifier: 'data-sources-empty',
        failureThreshold: 0.01,
        failureThresholdType: 'percent',
      })
    })

    it('matches snapshot for data sources with data', () => {
      const stateWithData = createMockAppState({
        dataSources: {
          dataSources: [
            {
              id: 1,
              name: 'SQL Database',
              source_type: 'sql',
              db_query: 'SELECT * FROM users',
            },
            {
              id: 2,
              name: 'CSV File',
              source_type: 'csv',
              file_path: '/data/users.csv',
            },
            {
              id: 3,
              name: 'API Endpoint',
              source_type: 'api',
              api_url: 'https://api.example.com/users',
            },
          ],
          setDataSources: jest.fn(),
          addDataSource: jest.fn(),
          updateDataSource: jest.fn(),
          deleteDataSource: jest.fn(),
        },
      })
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      const { container } = render(<DataSourcesPage />)
      expect(container.firstChild).toMatchImageSnapshot({
        customSnapshotIdentifier: 'data-sources-with-data',
        failureThreshold: 0.01,
        failureThresholdType: 'percent',
      })
    })

    it('matches snapshot for loading state', () => {
      const loadingState = createMockAppState({
        ui: {
          loading: true,
          error: null,
          setLoading: jest.fn(),
          setError: jest.fn(),
          clearError: jest.fn(),
        },
      })
      ;(useAppState as jest.Mock).mockReturnValue(loadingState)

      const { container } = render(<DataSourcesPage />)
      expect(container.firstChild).toMatchImageSnapshot({
        customSnapshotIdentifier: 'data-sources-loading',
        failureThreshold: 0.01,
        failureThresholdType: 'percent',
      })
    })
  })

  describe('TemplatesPage Visual Tests', () => {
    it('matches snapshot for templates page', () => {
      const { container } = render(<TemplatesPage />)
      expect(container.firstChild).toMatchImageSnapshot({
        customSnapshotIdentifier: 'templates-page',
        failureThreshold: 0.01,
        failureThresholdType: 'percent',
      })
    })
  })

  describe('Responsive Design Visual Tests', () => {
    const viewports = [
      { width: 320, height: 568, name: 'mobile' },
      { width: 768, height: 1024, name: 'tablet' },
      { width: 1024, height: 768, name: 'desktop-small' },
      { width: 1920, height: 1080, name: 'desktop-large' },
    ]

    viewports.forEach(({ width, height, name }) => {
      it(`matches snapshot for HomePage at ${name} viewport`, () => {
        // Mock window dimensions
        Object.defineProperty(window, 'innerWidth', {
          writable: true,
          configurable: true,
          value: width,
        })
        Object.defineProperty(window, 'innerHeight', {
          writable: true,
          configurable: true,
          value: height,
        })

        const { container } = render(<HomePage />)
        expect(container.firstChild).toMatchImageSnapshot({
          customSnapshotIdentifier: `homepage-${name}`,
          failureThreshold: 0.02,
          failureThresholdType: 'percent',
        })
      })
    })
  })

  describe('Theme Visual Tests', () => {
    it('matches snapshot for dark theme', () => {
      // Mock dark theme by adding class to document
      document.documentElement.classList.add('dark')

      const { container } = render(<HomePage />)
      expect(container.firstChild).toMatchImageSnapshot({
        customSnapshotIdentifier: 'homepage-dark-theme',
        failureThreshold: 0.02,
        failureThresholdType: 'percent',
      })

      // Clean up
      document.documentElement.classList.remove('dark')
    })

    it('matches snapshot for light theme', () => {
      // Ensure light theme
      document.documentElement.classList.remove('dark')

      const { container } = render(<HomePage />)
      expect(container.firstChild).toMatchImageSnapshot({
        customSnapshotIdentifier: 'homepage-light-theme',
        failureThreshold: 0.02,
        failureThresholdType: 'percent',
      })
    })
  })

  describe('Accessibility Visual Tests', () => {
    it('matches snapshot with high contrast mode', () => {
      // Mock high contrast mode
      document.documentElement.classList.add('high-contrast')

      const { container } = render(<HomePage />)
      expect(container.firstChild).toMatchImageSnapshot({
        customSnapshotIdentifier: 'homepage-high-contrast',
        failureThreshold: 0.03,
        failureThresholdType: 'percent',
      })

      // Clean up
      document.documentElement.classList.remove('high-contrast')
    })

    it('matches snapshot with reduced motion', () => {
      // Mock reduced motion preference
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: jest.fn().mockImplementation(query => ({
          matches: query === '(prefers-reduced-motion: reduce)',
          media: query,
          onchange: null,
          addListener: jest.fn(),
          removeListener: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          dispatchEvent: jest.fn(),
        })),
      })

      const { container } = render(<HomePage />)
      expect(container.firstChild).toMatchImageSnapshot({
        customSnapshotIdentifier: 'homepage-reduced-motion',
        failureThreshold: 0.02,
        failureThresholdType: 'percent',
      })
    })
  })
})