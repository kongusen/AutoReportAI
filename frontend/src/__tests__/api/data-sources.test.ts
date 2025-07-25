/**
 * Data Sources API Integration Tests
 */

import { enhancedDataSourceApiService } from '@/lib/api/services/enhanced-data-source-service'
import { httpClient } from '@/lib/api/client'
import type { DataSource, DataSourceCreate } from '@/types/api'

// Mock the HTTP client
jest.mock('@/lib/api/client')
const mockedHttpClient = httpClient as jest.Mocked<typeof httpClient>

describe('Data Sources API Service', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('getDataSources', () => {
    it('should successfully fetch data sources with pagination', async () => {
      const mockDataSources: DataSource[] = [
        {
          id: '123',
          name: 'Test Data Source',
          source_type: 'sql',
          connection_string: 'postgresql://localhost:5432/test',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z'
        }
      ]

      const mockResponse = {
        data: mockDataSources
      }

      mockedHttpClient.get.mockResolvedValue(mockResponse)

      const result = await enhancedDataSourceApiService.getDataSources(1, 10)

      expect(mockedHttpClient.get).toHaveBeenCalledWith('/v1/data-sources', {
        params: { page: 1, limit: 10 }
      })
      expect(result).toEqual(mockDataSources)
    })

    it('should handle empty data sources list', async () => {
      const mockResponse = {
        data: []
      }

      mockedHttpClient.get.mockResolvedValue(mockResponse)

      const result = await enhancedDataSourceApiService.getDataSources()

      expect(result).toEqual([])
    })

    it('should handle API errors', async () => {
      const mockError = {
        response: {
          status: 500,
          data: {
            detail: 'Internal Server Error'
          }
        }
      }

      mockedHttpClient.get.mockRejectedValue(mockError)

      await expect(enhancedDataSourceApiService.getDataSources()).rejects.toEqual(mockError)
    })
  })

  describe('getDataSourceById', () => {
    it('should successfully fetch data source by ID', async () => {
      const mockDataSource: DataSource = {
        id: '123',
        name: 'Test Data Source',
        source_type: 'sql',
        connection_string: 'postgresql://localhost:5432/test',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z'
      }

      const mockResponse = {
        data: mockDataSource
      }

      mockedHttpClient.get.mockResolvedValue(mockResponse)

      const result = await enhancedDataSourceApiService.getDataSourceById('123')

      expect(mockedHttpClient.get).toHaveBeenCalledWith('/v1/data-sources/123')
      expect(result).toEqual(mockDataSource)
    })

    it('should handle not found error', async () => {
      const mockError = {
        response: {
          status: 404,
          data: {
            detail: 'Data source not found'
          }
        }
      }

      mockedHttpClient.get.mockRejectedValue(mockError)

      await expect(enhancedDataSourceApiService.getDataSourceById('999')).rejects.toEqual(mockError)
    })
  })

  describe('createDataSource', () => {
    it('should successfully create data source', async () => {
      const createData: DataSourceCreate = {
        name: 'New Data Source',
        source_type: 'sql',
        connection_string: 'postgresql://localhost:5432/test',
        is_active: true
      }

      const mockCreatedDataSource: DataSource = {
        id: '123',
        ...createData,
        created_at: '2024-01-01T00:00:00Z'
      }

      const mockResponse = {
        data: mockCreatedDataSource
      }

      mockedHttpClient.post.mockResolvedValue(mockResponse)

      const result = await enhancedDataSourceApiService.createDataSource(createData)

      expect(mockedHttpClient.post).toHaveBeenCalledWith('/v1/data-sources', createData)
      expect(result).toEqual(mockCreatedDataSource)
    })

    it('should handle validation errors', async () => {
      const createData: DataSourceCreate = {
        name: '',
        source_type: 'sql',
        is_active: true
      }

      const mockError = {
        response: {
          status: 422,
          data: {
            detail: 'Validation error',
            errors: [
              { field: 'name', message: 'Name is required' }
            ]
          }
        }
      }

      mockedHttpClient.post.mockRejectedValue(mockError)

      await expect(enhancedDataSourceApiService.createDataSource(createData)).rejects.toEqual(mockError)
    })
  })

  describe('updateDataSource', () => {
    it('should successfully update data source', async () => {
      const updateData = {
        name: 'Updated Data Source',
        is_active: false
      }

      const mockUpdatedDataSource: DataSource = {
        id: '123',
        name: 'Updated Data Source',
        source_type: 'sql',
        connection_string: 'postgresql://localhost:5432/test',
        is_active: false,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z'
      }

      const mockResponse = {
        data: mockUpdatedDataSource
      }

      mockedHttpClient.put.mockResolvedValue(mockResponse)

      const result = await enhancedDataSourceApiService.updateDataSource('123', updateData)

      expect(mockedHttpClient.put).toHaveBeenCalledWith('/v1/data-sources/123', updateData)
      expect(result).toEqual(mockUpdatedDataSource)
    })
  })

  describe('deleteDataSource', () => {
    it('should successfully delete data source', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Data source deleted successfully'
        }
      }

      mockedHttpClient.delete.mockResolvedValue(mockResponse)

      const result = await enhancedDataSourceApiService.deleteDataSource('123')

      expect(mockedHttpClient.delete).toHaveBeenCalledWith('/v1/data-sources/123')
      expect(result).toEqual(mockResponse.data)
    })

    it('should handle delete errors', async () => {
      const mockError = {
        response: {
          status: 403,
          data: {
            detail: 'Permission denied'
          }
        }
      }

      mockedHttpClient.delete.mockRejectedValue(mockError)

      await expect(enhancedDataSourceApiService.deleteDataSource('123')).rejects.toEqual(mockError)
    })
  })

  describe('testDataSource', () => {
    it('should successfully test data source connection', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Connection successful',
          details: {
            response_time: 0.123,
            connection_status: 'success'
          }
        }
      }

      mockedHttpClient.post.mockResolvedValue(mockResponse)

      const result = await enhancedDataSourceApiService.testDataSource('123')

      expect(mockedHttpClient.post).toHaveBeenCalledWith('/v1/data-sources/123/test')
      expect(result).toEqual(mockResponse.data)
    })

    it('should handle connection test failures', async () => {
      const mockResponse = {
        data: {
          success: false,
          message: 'Connection failed',
          details: {
            error: 'Connection timeout'
          }
        }
      }

      mockedHttpClient.post.mockResolvedValue(mockResponse)

      const result = await enhancedDataSourceApiService.testDataSource('123')

      expect(result.success).toBe(false)
      expect(result.message).toBe('Connection failed')
    })
  })

  describe('previewDataSource', () => {
    it('should successfully preview data source data', async () => {
      const mockResponse = {
        data: {
          fields: ['id', 'name', 'email'],
          rows: [
            { id: 1, name: 'John Doe', email: 'john@example.com' },
            { id: 2, name: 'Jane Smith', email: 'jane@example.com' }
          ]
        }
      }

      mockedHttpClient.get.mockResolvedValue(mockResponse)

      const result = await enhancedDataSourceApiService.previewDataSource('123', 10)

      expect(mockedHttpClient.get).toHaveBeenCalledWith('/v1/data-sources/123/wide-table', {
        params: { limit: 10 }
      })
      expect(result).toEqual(mockResponse.data)
    })

    it('should handle preview errors', async () => {
      const mockError = {
        response: {
          status: 400,
          data: {
            detail: 'Data source not configured properly'
          }
        }
      }

      mockedHttpClient.get.mockRejectedValue(mockError)

      await expect(enhancedDataSourceApiService.previewDataSource('123')).rejects.toEqual(mockError)
    })
  })

  describe('syncDataSource', () => {
    it('should successfully sync data source', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Data source synced successfully',
          details: {
            records_synced: 100,
            sync_status: 'success'
          }
        }
      }

      mockedHttpClient.post.mockResolvedValue(mockResponse)

      const result = await enhancedDataSourceApiService.syncDataSource('123')

      expect(mockedHttpClient.post).toHaveBeenCalledWith('/v1/data-sources/123/sync')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('getActiveDataSources', () => {
    it('should successfully fetch active data sources', async () => {
      const mockDataSources: DataSource[] = [
        {
          id: '123',
          name: 'Active Data Source',
          source_type: 'sql',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z'
        }
      ]

      const mockResponse = {
        data: mockDataSources
      }

      mockedHttpClient.get.mockResolvedValue(mockResponse)

      const result = await enhancedDataSourceApiService.getActiveDataSources()

      expect(mockedHttpClient.get).toHaveBeenCalledWith('/v1/data-sources', {
        params: { is_active: true }
      })
      expect(result).toEqual(mockDataSources)
    })
  })
})

describe('Data Sources Integration Flow', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should complete full CRUD flow', async () => {
    const createData: DataSourceCreate = {
      name: 'Test Data Source',
      source_type: 'sql',
      connection_string: 'postgresql://localhost:5432/test',
      is_active: true
    }

    const createdDataSource: DataSource = {
      id: '123',
      ...createData,
      created_at: '2024-01-01T00:00:00Z'
    }

    const updatedDataSource: DataSource = {
      ...createdDataSource,
      name: 'Updated Test Data Source',
      updated_at: '2024-01-02T00:00:00Z'
    }

    // Mock responses
    mockedHttpClient.post.mockResolvedValueOnce({ data: createdDataSource })
    mockedHttpClient.get.mockResolvedValueOnce({ data: createdDataSource })
    mockedHttpClient.put.mockResolvedValueOnce({ data: updatedDataSource })
    mockedHttpClient.delete.mockResolvedValueOnce({ 
      data: { success: true, message: 'Deleted successfully' } 
    })

    // Step 1: Create
    const createResult = await enhancedDataSourceApiService.createDataSource(createData)
    expect(createResult.id).toBe('123')

    // Step 2: Read
    const readResult = await enhancedDataSourceApiService.getDataSourceById('123')
    expect(readResult.name).toBe('Test Data Source')

    // Step 3: Update
    const updateResult = await enhancedDataSourceApiService.updateDataSource('123', {
      name: 'Updated Test Data Source'
    })
    expect(updateResult.name).toBe('Updated Test Data Source')

    // Step 4: Delete
    const deleteResult = await enhancedDataSourceApiService.deleteDataSource('123')
    expect(deleteResult.success).toBe(true)

    // Verify all API calls were made
    expect(mockedHttpClient.post).toHaveBeenCalledTimes(1)
    expect(mockedHttpClient.get).toHaveBeenCalledTimes(1)
    expect(mockedHttpClient.put).toHaveBeenCalledTimes(1)
    expect(mockedHttpClient.delete).toHaveBeenCalledTimes(1)
  })
})