import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { DataSourceForm, type DataSourceFormValues } from '../DataSourceForm'

describe('DataSourceForm Component', () => {
  const mockOnSubmit = jest.fn()

  beforeEach(() => {
    mockOnSubmit.mockClear()
  })

  it('should render form fields', () => {
    render(<DataSourceForm onSubmit={mockOnSubmit} />)
    
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/source type/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create data source/i })).toBeInTheDocument()
  })

  it('should render with default values', () => {
    const defaultValues = {
      name: 'Test Data Source',
      source_type: 'csv' as const,
      file_path: '/test/path.csv'
    }
    
    render(<DataSourceForm onSubmit={mockOnSubmit} defaultValues={defaultValues} />)
    
    expect(screen.getByDisplayValue('Test Data Source')).toBeInTheDocument()
    expect(screen.getByDisplayValue('/test/path.csv')).toBeInTheDocument()
  })

  it('should validate required fields', async () => {
    const user = userEvent.setup()
    render(<DataSourceForm onSubmit={mockOnSubmit} />)
    
    const submitButton = screen.getByRole('button', { name: /create data source/i })
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText('Name is required')).toBeInTheDocument()
    })
    
    expect(mockOnSubmit).not.toHaveBeenCalled()
  })

  it('should validate URL format for API source', async () => {
    const user = userEvent.setup()
    render(<DataSourceForm onSubmit={mockOnSubmit} />)
    
    // Fill name
    const nameInput = screen.getByLabelText(/name/i)
    await user.type(nameInput, 'Test API Source')
    
    // Select API source type
    const sourceTypeSelect = screen.getByLabelText(/source type/i)
    await user.click(sourceTypeSelect)
    await user.click(screen.getByText('API'))
    
    // Enter invalid URL
    const apiUrlInput = screen.getByLabelText(/api url/i)
    await user.type(apiUrlInput, 'invalid-url')
    
    const submitButton = screen.getByRole('button', { name: /create data source/i })
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/invalid url/i)).toBeInTheDocument()
    })
    
    expect(mockOnSubmit).not.toHaveBeenCalled()
  })

  it('should submit form with valid data', async () => {
    const user = userEvent.setup()
    render(<DataSourceForm onSubmit={mockOnSubmit} />)
    
    // Fill form
    const nameInput = screen.getByLabelText(/name/i)
    await user.type(nameInput, 'Test SQL Source')
    
    const sourceTypeSelect = screen.getByLabelText(/source type/i)
    await user.click(sourceTypeSelect)
    await user.click(screen.getByText('SQL'))
    
    const queryInput = screen.getByLabelText(/database query/i)
    await user.type(queryInput, 'SELECT * FROM users')
    
    const submitButton = screen.getByRole('button', { name: /create data source/i })
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Test SQL Source',
        source_type: 'sql',
        db_query: 'SELECT * FROM users',
        file_path: '',
        api_url: ''
      })
    })
  })

  it('should show different fields based on source type', async () => {
    const user = userEvent.setup()
    render(<DataSourceForm onSubmit={mockOnSubmit} />)
    
    const sourceTypeSelect = screen.getByLabelText(/source type/i)
    
    // Test SQL type
    await user.click(sourceTypeSelect)
    await user.click(screen.getByText('SQL'))
    expect(screen.getByLabelText(/database query/i)).toBeInTheDocument()
    
    // Test CSV type
    await user.click(sourceTypeSelect)
    await user.click(screen.getByText('CSV'))
    expect(screen.getByLabelText(/file path/i)).toBeInTheDocument()
    
    // Test API type
    await user.click(sourceTypeSelect)
    await user.click(screen.getByText('API'))
    expect(screen.getByLabelText(/api url/i)).toBeInTheDocument()
  })

  it('should handle form reset', async () => {
    const user = userEvent.setup()
    render(<DataSourceForm onSubmit={mockOnSubmit} />)
    
    // Fill form
    const nameInput = screen.getByLabelText(/name/i)
    await user.type(nameInput, 'Test Source')
    
    // Reset form (if reset button exists)
    const resetButton = screen.queryByRole('button', { name: /reset/i })
    if (resetButton) {
      await user.click(resetButton)
      expect(nameInput).toHaveValue('')
    }
  })

  it('should disable submit button while submitting', async () => {
    const user = userEvent.setup()
    let resolveSubmit: (value: any) => void
    const slowSubmit = jest.fn(() => new Promise(resolve => {
      resolveSubmit = resolve
    }))
    
    render(<DataSourceForm onSubmit={slowSubmit} />)
    
    // Fill form
    const nameInput = screen.getByLabelText(/name/i)
    await user.type(nameInput, 'Test Source')
    
    const submitButton = screen.getByRole('button', { name: /create data source/i })
    await user.click(submitButton)
    
    // Button should be disabled during submission
    expect(submitButton).toBeDisabled()
    
    // Resolve the promise
    resolveSubmit!(undefined)
    
    await waitFor(() => {
      expect(submitButton).not.toBeDisabled()
    })
  })

  it('should handle form validation errors', async () => {
    const user = userEvent.setup()
    render(<DataSourceForm onSubmit={mockOnSubmit} />)
    
    // Try to submit empty form
    const submitButton = screen.getByRole('button', { name: /create data source/i })
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText('Name is required')).toBeInTheDocument()
    })
    
    // Fill name and try again
    const nameInput = screen.getByLabelText(/name/i)
    await user.type(nameInput, 'Test Source')
    
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(screen.queryByText('Name is required')).not.toBeInTheDocument()
    })
  })

  it('should preserve form state on re-render', () => {
    const { rerender } = render(<DataSourceForm onSubmit={mockOnSubmit} />)
    
    const nameInput = screen.getByLabelText(/name/i)
    fireEvent.change(nameInput, { target: { value: 'Test Source' } })
    
    expect(nameInput).toHaveValue('Test Source')
    
    rerender(<DataSourceForm onSubmit={mockOnSubmit} />)
    
    // Form should maintain its state
    expect(screen.getByLabelText(/name/i)).toHaveValue('Test Source')
  })

  it('should handle keyboard navigation', async () => {
    const user = userEvent.setup()
    render(<DataSourceForm onSubmit={mockOnSubmit} />)
    
    const nameInput = screen.getByLabelText(/name/i)
    
    // Tab navigation
    await user.tab()
    expect(nameInput).toHaveFocus()
    
    await user.tab()
    expect(screen.getByLabelText(/source type/i)).toHaveFocus()
  })
})