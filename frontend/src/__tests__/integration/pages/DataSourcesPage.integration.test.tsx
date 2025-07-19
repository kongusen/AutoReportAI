import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DataSourcesPage from '@/app/(app)/data-sources/page'
import { useAppState } from '@/lib/context/hooks'
import api from '@/lib/api'

// Mock dependencies
jest.mock('@/lib/context/hooks', () => ({
  useAppState: jest.fn(),
}))

jest.mock('@/lib/api', () => ({
  dataSources: {
    getAll: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
    test: jest.fn(),
    preview: jest.fn(),
  },
}))

jest.mock('@/components/forms', () => ({
  DataSourceForm: ({ onSubmit, defaultValues }: any) => (
    <div data-testid="data-source-form">
      <button onClick={() => onSubmit({ name: 'Test Source', source_type: 'sql' })}>
        Submit Form
      </button>
      {defaultValues && <div data-testid="default-values">{JSON.stringify(defaultValues)}</div>}
    </div>
  ),
  QuickExportButton: ({ sourceId, sourceName }: any) => (
    <button data-testid={`export-${sourceId}`}>Export {sourceName}</button>
  ),
}))

// Mock window.confirm
Object.defineProperty(window, 'confirm', {
  value: jest.fn(),
})

// Mock window.alert
Object.defineProperty(window, 'alert', {
  value: jest.fn(),
})

const mockAppState = {
  dataSources: {
    dataSources: [],
    setDataSources: jest.fn(),
    addDataSource: jest.fn(),
    updateDataSource: jest.fn(),
    deleteDataSource: jest.fn(),
  },
  ui: {
    loading: false,
    error: null,
    setLoading: jest.fn(),
    setError: jest.fn(),
    clearError: jest.fn(),
  },
}

describe('DataSourcesPage Integration Tests', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useAppState as jest.Mock).mockReturnValue(mockAppState)
    ;(window.confirm as jest.Mock).mockReturnValue(true)
    ;(window.alert as jest.Mock).mockImplementation(() => {})
  })

  describe('Initial Render and Loading States', () => {
    it('renders loading state', () => {
      const loadingState = {
        ...mockAppState,
        ui: { ...mockAppState.ui, loading: true },
      }
      ;(useAppState as jest.Mock).mockReturnValue(loadingState)

      render(<DataSourcesPage />)

      expect(screen.getByText('Loading data sources...')).toBeInTheDocument()
    })

    it('renders error state', () => {
      const errorState = {
        ...mockAppState,
        ui: { ...mockAppState.ui, error: 'Failed to fetch data sources.' },
      }
      ;(useAppState as jest.Mock).mockReturnValue(errorState)

      render(<DataSourcesPage />)

      expect(screen.getByText('Failed to fetch data sources.')).toBeInTheDocument()
    })

    it('renders empty state when no data sources exist', () => {
      render(<DataSourcesPage />)

      expect(screen.getByText('Data Sources')).toBeInTheDocument()
      expect(screen.getByText('No data sources found.')).toBeInTheDocument()
      expect(screen.getByText('Add New Data Source')).toBeInTheDocument()
    })
  })

  describe('Data Sources Display', () => {
    it('displays data sources in table format', () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
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
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      render(<DataSourcesPage />)

      expect(screen.getByText('SQL Database')).toBeInTheDocument()
      expect(screen.getByText('CSV File')).toBeInTheDocument()
      expect(screen.getByText('API Endpoint')).toBeInTheDocument()
      expect(screen.getByText('SQL')).toBeInTheDocument()
      expect(screen.getByText('CSV')).toBeInTheDocument()
      expect(screen.getByText('API')).toBeInTheDocument()
    })

    it('displays correct configuration details for each source type', () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
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
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      render(<DataSourcesPage />)

      expect(screen.getByText('SELECT * FROM users')).toBeInTheDocument()
      expect(screen.getByText('/data/users.csv')).toBeInTheDocument()
      expect(screen.getByText('https://api.example.com/users')).toBeInTheDocument()
    })

    it('applies correct badge colors for different source types', () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            { id: 1, name: 'SQL Source', source_type: 'sql' },
            { id: 2, name: 'CSV Source', source_type: 'csv' },
            { id: 3, name: 'API Source', source_type: 'api' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      render(<DataSourcesPage />)

      const sqlBadge = screen.getByText('SQL')
      const csvBadge = screen.getByText('CSV')
      const apiBadge = screen.getByText('API')

      expect(sqlBadge).toHaveClass('bg-blue-100', 'text-blue-800')
      expect(csvBadge).toHaveClass('bg-green-100', 'text-green-800')
      expect(apiBadge).toHaveClass('bg-purple-100', 'text-purple-800')
    })
  })

  describe('Create Data Source Flow', () => {
    it('opens create dialog when add button is clicked', async () => {
      render(<DataSourcesPage />)

      const addButton = screen.getByText('Add New Data Source')
      await user.click(addButton)

      expect(screen.getByText('Create New Data Source')).toBeInTheDocument()
      expect(screen.getByTestId('data-source-form')).toBeInTheDocument()
    })

    it('creates new data source successfully', async () => {
      const mockResponse = {
        data: { id: 4, name: 'New Source', source_type: 'sql' },
      }
      ;(api.dataSources.create as jest.Mock).mockResolvedValue(mockResponse)

      render(<DataSourcesPage />)

      const addButton = screen.getByText('Add New Data Source')
      await user.click(addButton)

      const submitButton = screen.getByText('Submit Form')
      await user.click(submitButton)

      await waitFor(() => {
        expect(api.dataSources.create).toHaveBeenCalledWith({
          name: 'Test Source',
          source_type: 'sql',
        })
        expect(mockAppState.dataSources.addDataSource).toHaveBeenCalledWith(mockResponse.data)
      })
    })

    it('handles create data source error', async () => {
      const mockError = {
        response: {
          data: {
            detail: 'Data source name already exists',
          },
        },
      }
      ;(api.dataSources.create as jest.Mock).mockRejectedValue(mockError)

      render(<DataSourcesPage />)

      const addButton = screen.getByText('Add New Data Source')
      await user.click(addButton)

      const submitButton = screen.getByText('Submit Form')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockAppState.ui.setError).toHaveBeenCalledWith('Data source name already exists')
      })
    })
  })

  describe('Edit Data Source Flow', () => {
    it('opens edit dialog with pre-filled data', async () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            {
              id: 1,
              name: 'Existing Source',
              source_type: 'sql',
              db_query: 'SELECT * FROM table',
            },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      render(<DataSourcesPage />)

      const editButton = screen.getByText('Edit')
      await user.click(editButton)

      expect(screen.getByText('Edit Data Source')).toBeInTheDocument()
      expect(screen.getByTestId('default-values')).toHaveTextContent(
        JSON.stringify({
          name: 'Existing Source',
          source_type: 'sql',
          db_query: 'SELECT * FROM table',
          file_path: '',
          api_url: '',
        })
      )
    })

    it('updates data source successfully', async () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            {
              id: 1,
              name: 'Existing Source',
              source_type: 'sql',
              db_query: 'SELECT * FROM table',
            },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      const mockResponse = {
        data: { id: 1, name: 'Updated Source', source_type: 'sql' },
      }
      ;(api.dataSources.update as jest.Mock).mockResolvedValue(mockResponse)

      render(<DataSourcesPage />)

      const editButton = screen.getByText('Edit')
      await user.click(editButton)

      const submitButton = screen.getByText('Submit Form')
      await user.click(submitButton)

      await waitFor(() => {
        expect(api.dataSources.update).toHaveBeenCalledWith(1, {
          name: 'Test Source',
          source_type: 'sql',
        })
        expect(mockAppState.dataSources.updateDataSource).toHaveBeenCalledWith(1, mockResponse.data)
      })
    })
  })

  describe('Delete Data Source Flow', () => {
    it('deletes data source after confirmation', async () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            { id: 1, name: 'Source to Delete', source_type: 'sql' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)
      ;(api.dataSources.delete as jest.Mock).mockResolvedValue({})

      render(<DataSourcesPage />)

      const deleteButton = screen.getByText('Delete')
      await user.click(deleteButton)

      expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to delete this data source?')

      await waitFor(() => {
        expect(api.dataSources.delete).toHaveBeenCalledWith(1)
        expect(mockAppState.dataSources.deleteDataSource).toHaveBeenCalledWith(1)
      })
    })

    it('does not delete when user cancels confirmation', async () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            { id: 1, name: 'Source to Delete', source_type: 'sql' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)
      ;(window.confirm as jest.Mock).mockReturnValue(false)

      render(<DataSourcesPage />)

      const deleteButton = screen.getByText('Delete')
      await user.click(deleteButton)

      expect(window.confirm).toHaveBeenCalled()
      expect(api.dataSources.delete).not.toHaveBeenCalled()
    })

    it('handles delete error gracefully', async () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            { id: 1, name: 'Source to Delete', source_type: 'sql' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      const mockError = {
        response: {
          data: {
            detail: 'Cannot delete data source in use',
          },
        },
      }
      ;(api.dataSources.delete as jest.Mock).mockRejectedValue(mockError)

      render(<DataSourcesPage />)

      const deleteButton = screen.getByText('Delete')
      await user.click(deleteButton)

      await waitFor(() => {
        expect(mockAppState.ui.setError).toHaveBeenCalledWith('Cannot delete data source in use')
      })
    })
  })

  describe('Test Connection Feature', () => {
    it('tests connection successfully', async () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            { id: 1, name: 'Test Source', source_type: 'sql' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      const mockResponse = {
        data: { msg: 'Connection test successful!' },
      }
      ;(api.dataSources.test as jest.Mock).mockResolvedValue(mockResponse)

      render(<DataSourcesPage />)

      const testButton = screen.getByText('Test')
      await user.click(testButton)

      await waitFor(() => {
        expect(api.dataSources.test).toHaveBeenCalledWith(1)
        expect(window.alert).toHaveBeenCalledWith('Connection test successful!')
      })
    })

    it('handles connection test failure', async () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            { id: 1, name: 'Test Source', source_type: 'sql' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      const mockError = {
        response: {
          data: {
            detail: 'Connection failed: Invalid credentials',
          },
        },
      }
      ;(api.dataSources.test as jest.Mock).mockRejectedValue(mockError)

      render(<DataSourcesPage />)

      const testButton = screen.getByText('Test')
      await user.click(testButton)

      await waitFor(() => {
        expect(window.alert).toHaveBeenCalledWith('Connection failed: Invalid credentials')
      })
    })
  })

  describe('Data Preview Feature', () => {
    it('opens preview dialog with data', async () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            { id: 1, name: 'Preview Source', source_type: 'sql' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      const mockPreviewData = {
        data: {
          columns: ['id', 'name', 'email'],
          data: [
            { id: 1, name: 'John Doe', email: 'john@example.com' },
            { id: 2, name: 'Jane Smith', email: 'jane@example.com' },
          ],
          row_count: 2,
        },
      }
      ;(api.dataSources.preview as jest.Mock).mockResolvedValue(mockPreviewData)

      render(<DataSourcesPage />)

      const previewButton = screen.getByText('Preview')
      await user.click(previewButton)

      await waitFor(() => {
        expect(api.dataSources.preview).toHaveBeenCalledWith(1, { limit: 10 })
        expect(screen.getByText('Data Preview')).toBeInTheDocument()
        expect(screen.getByText('Showing 2 rows with 3 columns')).toBeInTheDocument()
        expect(screen.getByText('John Doe')).toBeInTheDocument()
        expect(screen.getByText('jane@example.com')).toBeInTheDocument()
      })
    })

    it('handles preview error', async () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            { id: 1, name: 'Preview Source', source_type: 'sql' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      const mockError = {
        response: {
          data: {
            detail: 'Failed to preview data',
          },
        },
      }
      ;(api.dataSources.preview as jest.Mock).mockRejectedValue(mockError)

      render(<DataSourcesPage />)

      const previewButton = screen.getByText('Preview')
      await user.click(previewButton)

      await waitFor(() => {
        expect(window.alert).toHaveBeenCalledWith('Failed to preview data')
      })
    })
  })

  describe('Quick Export Integration', () => {
    it('renders quick export buttons for each data source', () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            { id: 1, name: 'Export Source 1', source_type: 'sql' },
            { id: 2, name: 'Export Source 2', source_type: 'csv' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      render(<DataSourcesPage />)

      expect(screen.getByTestId('export-1')).toBeInTheDocument()
      expect(screen.getByTestId('export-2')).toBeInTheDocument()
      expect(screen.getByText('Export Export Source 1')).toBeInTheDocument()
      expect(screen.getByText('Export Export Source 2')).toBeInTheDocument()
    })
  })

  describe('API Integration and Data Fetching', () => {
    it('fetches data sources on mount when none exist', async () => {
      const mockResponse = {
        data: [
          { id: 1, name: 'Fetched Source', source_type: 'sql' },
        ],
      }
      ;(api.dataSources.getAll as jest.Mock).mockResolvedValue(mockResponse)

      render(<DataSourcesPage />)

      await waitFor(() => {
        expect(mockAppState.ui.setLoading).toHaveBeenCalledWith(true)
        expect(api.dataSources.getAll).toHaveBeenCalled()
        expect(mockAppState.dataSources.setDataSources).toHaveBeenCalledWith(mockResponse.data)
        expect(mockAppState.ui.setLoading).toHaveBeenCalledWith(false)
      })
    })

    it('does not fetch when data sources already exist', () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            { id: 1, name: 'Existing Source', source_type: 'sql' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      render(<DataSourcesPage />)

      expect(api.dataSources.getAll).not.toHaveBeenCalled()
    })

    it('handles fetch error on mount', async () => {
      const mockError = new Error('Network error')
      ;(api.dataSources.getAll as jest.Mock).mockRejectedValue(mockError)

      render(<DataSourcesPage />)

      await waitFor(() => {
        expect(mockAppState.ui.setError).toHaveBeenCalledWith('Failed to fetch data sources.')
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper table structure', () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            { id: 1, name: 'Test Source', source_type: 'sql' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      render(<DataSourcesPage />)

      expect(screen.getByRole('table')).toBeInTheDocument()
      expect(screen.getByRole('columnheader', { name: 'Name' })).toBeInTheDocument()
      expect(screen.getByRole('columnheader', { name: 'Type' })).toBeInTheDocument()
      expect(screen.getByRole('columnheader', { name: 'Configuration' })).toBeInTheDocument()
      expect(screen.getByRole('columnheader', { name: 'Actions' })).toBeInTheDocument()
    })

    it('has proper heading hierarchy', () => {
      render(<DataSourcesPage />)

      const heading = screen.getByRole('heading', { level: 2 })
      expect(heading).toHaveTextContent('Data Sources')
    })

    it('has accessible buttons with proper labels', () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            { id: 1, name: 'Test Source', source_type: 'sql' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      render(<DataSourcesPage />)

      expect(screen.getByRole('button', { name: 'Test' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Preview' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument()
    })
  })

  describe('Responsive Design', () => {
    it('has responsive layout classes', () => {
      render(<DataSourcesPage />)

      const container = screen.getByText('Data Sources').closest('.flex-1')
      expect(container).toHaveClass('flex-1', 'space-y-4', 'p-8', 'pt-6')
    })

    it('handles table overflow on small screens', () => {
      const stateWithData = {
        ...mockAppState,
        dataSources: {
          ...mockAppState.dataSources,
          dataSources: [
            { id: 1, name: 'Test Source', source_type: 'sql' },
          ],
        },
      }
      ;(useAppState as jest.Mock).mockReturnValue(stateWithData)

      render(<DataSourcesPage />)

      const tableContainer = screen.getByRole('table').closest('.rounded-md')
      expect(tableContainer).toHaveClass('rounded-md', 'border')
    })
  })
})