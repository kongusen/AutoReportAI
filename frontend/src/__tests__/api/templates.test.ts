/**
 * Templates API Integration Tests
 */

import { TemplateApiService } from '@/lib/api/services/template-service'
import { httpClient } from '@/lib/api/client'
import type { Template, TemplateCreate } from '@/types/api'

// Mock the HTTP client
jest.mock('@/lib/api/client')
const mockedHttpClient = httpClient as jest.Mocked<typeof httpClient>

describe('Templates API Service', () => {
  let templateApi: TemplateApiService

  beforeEach(() => {
    jest.clearAllMocks()
    templateApi = new TemplateApiService()
  })

  describe('getTemplates', () => {
    it('should successfully fetch templates with pagination', async () => {
      const mockTemplates: Template[] = [
        {
          id: '123',
          name: 'Test Template',
          description: 'A test template',
          template_type: 'word',
          content: 'Hello {{name}}',
          is_public: false,
          is_active: true,
          created_at: '2024-01-01T00:00:00Z'
        }
      ]

      const mockResponse = {
        data: {
          data: {
            items: mockTemplates
          }
        }
      }

      mockedHttpClient.get.mockResolvedValue(mockResponse)

      const result = await templateApi.getTemplates(1, 10)

      expect(mockedHttpClient.get).toHaveBeenCalledWith('/v1/templates', {
        params: { skip: 0, limit: 10 }
      })
      expect(result).toEqual(mockTemplates)
    })

    it('should handle empty templates list', async () => {
      const mockResponse = {
        data: {
          data: {
            items: []
          }
        }
      }

      mockedHttpClient.get.mockResolvedValue(mockResponse)

      const result = await templateApi.getTemplates()

      expect(result).toEqual([])
    })
  })

  describe('getTemplateById', () => {
    it('should successfully fetch template by ID', async () => {
      const mockTemplate: Template = {
        id: '123',
        name: 'Test Template',
        description: 'A test template',
        template_type: 'word',
        content: 'Hello {{name}}',
        is_public: false,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z'
      }

      const mockResponse = {
        data: {
          data: mockTemplate
        }
      }

      mockedHttpClient.get.mockResolvedValue(mockResponse)

      const result = await templateApi.getTemplateById('123')

      expect(mockedHttpClient.get).toHaveBeenCalledWith('/v1/templates/123')
      expect(result).toEqual(mockTemplate)
    })

    it('should handle not found error', async () => {
      const mockError = {
        response: {
          status: 404,
          data: {
            detail: 'Template not found'
          }
        }
      }

      mockedHttpClient.get.mockRejectedValue(mockError)

      await expect(templateApi.getTemplateById('999')).rejects.toEqual(mockError)
    })
  })

  describe('createTemplate', () => {
    it('should successfully create template', async () => {
      const createData: TemplateCreate = {
        name: 'New Template',
        description: 'A new template',
        template_type: 'word',
        content: 'Hello {{name}}',
        is_public: false
      }

      const mockCreatedTemplate: Template = {
        id: '123',
        ...createData,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z'
      }

      const mockResponse = {
        data: mockCreatedTemplate
      }

      mockedHttpClient.post.mockResolvedValue(mockResponse)

      const result = await templateApi.createTemplate(createData)

      expect(mockedHttpClient.post).toHaveBeenCalledWith('/v1/templates', createData)
      expect(result).toEqual(mockCreatedTemplate)
    })

    it('should handle validation errors', async () => {
      const createData: TemplateCreate = {
        name: '',
        template_type: 'word',
        content: '',
        is_public: false
      }

      const mockError = {
        response: {
          status: 422,
          data: {
            detail: 'Validation error',
            errors: [
              { field: 'name', message: 'Name is required' },
              { field: 'content', message: 'Content is required' }
            ]
          }
        }
      }

      mockedHttpClient.post.mockRejectedValue(mockError)

      await expect(templateApi.createTemplate(createData)).rejects.toEqual(mockError)
    })
  })

  describe('updateTemplate', () => {
    it('should successfully update template', async () => {
      const updateData = {
        name: 'Updated Template',
        description: 'An updated template'
      }

      const mockUpdatedTemplate: Template = {
        id: '123',
        name: 'Updated Template',
        description: 'An updated template',
        template_type: 'word',
        content: 'Hello {{name}}',
        is_public: false,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z'
      }

      const mockResponse = {
        data: {
          data: mockUpdatedTemplate
        }
      }

      mockedHttpClient.put.mockResolvedValue(mockResponse)

      const result = await templateApi.updateTemplate('123', updateData)

      expect(mockedHttpClient.put).toHaveBeenCalledWith('/v1/templates/123', updateData)
      expect(result).toEqual(mockUpdatedTemplate)
    })
  })

  describe('deleteTemplate', () => {
    it('should successfully delete template', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Template deleted successfully'
        }
      }

      mockedHttpClient.delete.mockResolvedValue(mockResponse)

      const result = await templateApi.deleteTemplate('123')

      expect(mockedHttpClient.delete).toHaveBeenCalledWith('/v1/templates/123')
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

      await expect(templateApi.deleteTemplate('123')).rejects.toEqual(mockError)
    })
  })

  describe('uploadTemplate', () => {
    it('should successfully upload template file', async () => {
      const formData = new FormData()
      formData.append('file', new Blob(['template content']), 'template.docx')
      formData.append('name', 'Uploaded Template')

      const mockUploadedTemplate: Template = {
        id: '123',
        name: 'Uploaded Template',
        template_type: 'word',
        content: 'template content',
        original_filename: 'template.docx',
        is_public: false,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z'
      }

      const mockResponse = {
        data: mockUploadedTemplate
      }

      mockedHttpClient.post.mockResolvedValue(mockResponse)

      const result = await templateApi.uploadTemplate(formData)

      expect(mockedHttpClient.post).toHaveBeenCalledWith('/v1/templates/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      expect(result).toEqual(mockUploadedTemplate)
    })
  })

  describe('downloadTemplate', () => {
    it('should successfully download template file', async () => {
      const mockBlob = new Blob(['template content'], { type: 'application/octet-stream' })

      const mockResponse = {
        data: mockBlob
      }

      mockedHttpClient.get.mockResolvedValue(mockResponse)

      const result = await templateApi.downloadTemplate('123')

      expect(mockedHttpClient.get).toHaveBeenCalledWith('/v1/templates/123/download', {
        responseType: 'blob'
      })
      expect(result).toEqual(mockBlob)
    })
  })

  describe('validateTemplate', () => {
    it('should successfully validate template content', async () => {
      const templateContent = 'Hello {{name}}, your order {{order_id}} is ready.'

      const mockResponse = {
        data: {
          valid: true,
          errors: []
        }
      }

      mockedHttpClient.post.mockResolvedValue(mockResponse)

      const result = await templateApi.validateTemplate(templateContent)

      expect(mockedHttpClient.post).toHaveBeenCalledWith('/v1/templates/validate', {
        content: templateContent
      })
      expect(result).toEqual(mockResponse.data)
    })

    it('should handle validation errors', async () => {
      const templateContent = 'Hello {{name}, your order {{order_id}} is ready.'

      const mockResponse = {
        data: {
          valid: false,
          errors: [
            {
              message: 'Unclosed placeholder at position 7',
              line: 1,
              column: 7
            }
          ]
        }
      }

      mockedHttpClient.post.mockResolvedValue(mockResponse)

      const result = await templateApi.validateTemplate(templateContent)

      expect(result.valid).toBe(false)
      expect(result.errors).toHaveLength(1)
    })
  })

  describe('previewTemplate', () => {
    it('should successfully preview template', async () => {
      const mockResponse = {
        data: {
          data: {
            content: 'Hello {{name}}, your order {{order_id}} is ready.',
            placeholders: [
              { name: 'name', found: true },
              { name: 'order_id', found: true }
            ]
          }
        }
      }

      mockedHttpClient.get.mockResolvedValue(mockResponse)

      const result = await templateApi.previewTemplate('123')

      expect(mockedHttpClient.get).toHaveBeenCalledWith('/v1/templates/123/preview')
      expect(result).toEqual(mockResponse.data.data)
    })
  })

  describe('cloneTemplate', () => {
    it('should successfully clone template', async () => {
      const newName = 'Cloned Template'

      const mockClonedTemplate: Template = {
        id: '456',
        name: newName,
        description: 'A test template',
        template_type: 'word',
        content: 'Hello {{name}}',
        is_public: false,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z'
      }

      const mockResponse = {
        data: {
          data: mockClonedTemplate
        }
      }

      mockedHttpClient.post.mockResolvedValue(mockResponse)

      const result = await templateApi.cloneTemplate('123', newName)

      expect(mockedHttpClient.post).toHaveBeenCalledWith('/v1/templates/123/clone', {
        name: newName
      })
      expect(result).toEqual(mockClonedTemplate)
    })
  })
})

describe('Templates Integration Flow', () => {
  let templateApi: TemplateApiService

  beforeEach(() => {
    jest.clearAllMocks()
    templateApi = new TemplateApiService()
  })

  it('should complete full template lifecycle', async () => {
    const createData: TemplateCreate = {
      name: 'Test Template',
      description: 'A test template',
      template_type: 'word',
      content: 'Hello {{name}}',
      is_public: false
    }

    const createdTemplate: Template = {
      id: '123',
      ...createData,
      is_active: true,
      created_at: '2024-01-01T00:00:00Z'
    }

    const updatedTemplate: Template = {
      ...createdTemplate,
      name: 'Updated Test Template',
      updated_at: '2024-01-02T00:00:00Z'
    }

    // Mock responses
    mockedHttpClient.post.mockResolvedValueOnce({ data: createdTemplate })
    mockedHttpClient.get.mockResolvedValueOnce({ data: { data: createdTemplate } })
    mockedHttpClient.post.mockResolvedValueOnce({ 
      data: { valid: true, errors: [] } 
    })
    mockedHttpClient.put.mockResolvedValueOnce({ data: { data: updatedTemplate } })
    mockedHttpClient.delete.mockResolvedValueOnce({ 
      data: { success: true, message: 'Deleted successfully' } 
    })

    // Step 1: Create
    const createResult = await templateApi.createTemplate(createData)
    expect(createResult.id).toBe('123')

    // Step 2: Read
    const readResult = await templateApi.getTemplateById('123')
    expect(readResult.name).toBe('Test Template')

    // Step 3: Validate
    const validateResult = await templateApi.validateTemplate(createData.content!)
    expect(validateResult.valid).toBe(true)

    // Step 4: Update
    const updateResult = await templateApi.updateTemplate('123', {
      name: 'Updated Test Template'
    })
    expect(updateResult.name).toBe('Updated Test Template')

    // Step 5: Delete
    const deleteResult = await templateApi.deleteTemplate('123')
    expect(deleteResult.success).toBe(true)

    // Verify all API calls were made
    expect(mockedHttpClient.post).toHaveBeenCalledTimes(2) // create + validate
    expect(mockedHttpClient.get).toHaveBeenCalledTimes(1)
    expect(mockedHttpClient.put).toHaveBeenCalledTimes(1)
    expect(mockedHttpClient.delete).toHaveBeenCalledTimes(1)
  })

  it('should handle template upload and download flow', async () => {
    const formData = new FormData()
    formData.append('file', new Blob(['template content']), 'template.docx')

    const uploadedTemplate: Template = {
      id: '123',
      name: 'Uploaded Template',
      template_type: 'word',
      content: 'template content',
      is_public: false,
      is_active: true,
      created_at: '2024-01-01T00:00:00Z'
    }

    const mockBlob = new Blob(['template content'])

    // Mock responses
    mockedHttpClient.post.mockResolvedValueOnce({ data: uploadedTemplate })
    mockedHttpClient.get.mockResolvedValueOnce({ data: mockBlob })

    // Step 1: Upload
    const uploadResult = await templateApi.uploadTemplate(formData)
    expect(uploadResult.id).toBe('123')

    // Step 2: Download
    const downloadResult = await templateApi.downloadTemplate('123')
    expect(downloadResult).toEqual(mockBlob)

    // Verify API calls
    expect(mockedHttpClient.post).toHaveBeenCalledWith('/v1/templates/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    expect(mockedHttpClient.get).toHaveBeenCalledWith('/v1/templates/123/download', {
      responseType: 'blob'
    })
  })
})