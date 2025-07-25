'use client'

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle, 
} from '@/components/ui/dialog'
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select'
import { 
  FileText, 
  Edit, 
  Trash2, 
  Copy, 
  Plus,
  Search,
  Filter
} from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useApiCall } from '@/lib/hooks/useApiCall'
import { useErrorNotification } from '@/components/providers/ErrorNotificationProvider'
import { TemplateApiService } from '@/lib/api/services/template-service'
import type { Template, TemplateCreate } from '@/types/api'
import { LoadingSpinner } from '@/components/ui/loading'
import { ErrorSeverity } from '@/lib/error-handler'

// Template form schema
const templateSchema = z.object({
  name: z.string().min(1, 'Template name is required'),
  description: z.string().optional(),
  template_type: z.enum(['word', 'excel', 'powerpoint', 'pdf']),
  content: z.string().min(1, 'Template content is required'),
  is_public: z.boolean().default(false),
})

type TemplateFormData = z.infer<typeof templateSchema>

interface TemplateEditorFormProps {
  template?: Template
  onSave: (data: TemplateFormData) => void
  onCancel: () => void
  isLoading?: boolean
}

function TemplateEditorForm({ template, onSave, onCancel, isLoading }: TemplateEditorFormProps) {
  const form = useForm<TemplateFormData>({
    resolver: zodResolver(templateSchema),
    defaultValues: {
      name: template?.name || '',
      description: template?.description || '',
      template_type: (template?.template_type as any) || 'word',
      content: template?.content || '',
      is_public: template?.is_public || false,
    },
  })

  const handleSubmit = (data: TemplateFormData) => {
    onSave(data)
  }

  return (
    <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">Template Name</Label>
          <Input
            id="name"
            {...form.register('name')}
            placeholder="Enter template name"
          />
          {form.formState.errors.name && (
            <p className="text-sm text-red-600">{form.formState.errors.name.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="template_type">Template Type</Label>
          <Select
            value={form.watch('template_type')}
            onValueChange={(value) => form.setValue('template_type', value as any)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select template type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="word">Word Document</SelectItem>
              <SelectItem value="excel">Excel Spreadsheet</SelectItem>
              <SelectItem value="powerpoint">PowerPoint Presentation</SelectItem>
              <SelectItem value="pdf">PDF Document</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Input
          id="description"
          {...form.register('description')}
          placeholder="Enter template description (optional)"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="content">Template Content</Label>
        <Textarea
          id="content"
          {...form.register('content')}
          placeholder="Enter your template content with placeholders like {{name}}, {{date}}, etc."
          rows={10}
          className="font-mono"
        />
        {form.formState.errors.content && (
          <p className="text-sm text-red-600">{form.formState.errors.content.message}</p>
        )}
      </div>

      <div className="flex items-center space-x-2">
        <input
          type="checkbox"
          id="is_public"
          {...form.register('is_public')}
          className="rounded"
        />
        <Label htmlFor="is_public">Make this template public</Label>
      </div>

      <div className="flex justify-end space-x-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving...' : 'Save Template'}
        </Button>
      </div>
    </form>
  )
}

export function TemplateEditor() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [isEditorOpen, setIsEditorOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterType, setFilterType] = useState<string>('all')
  const { showToast, showError } = useErrorNotification()

  const templateApi = new TemplateApiService()

  // Load templates
  const loadTemplatesApi = useApiCall(
    () => templateApi.getTemplates(1, 50),
    {
      loadingMessage: 'Loading templates...',
      errorContext: 'fetch templates',
      onSuccess: (data) => {
        setTemplates(data)
      }
    }
  )

  // Save template
  const saveTemplateApi = useApiCall(
    async (data: { template?: Template; formData: TemplateFormData }) => {
      if (data.template) {
        return await templateApi.updateTemplate(data.template.id, data.formData)
      } else {
        return await templateApi.createTemplate(data.formData)
      }
    },
    {
      loadingMessage: 'Saving template...',
      errorContext: 'save template',
      onSuccess: (result) => {
        showToast({ severity: 'low' as ErrorSeverity, title: 'Success', message: 'Template saved successfully' })
        setIsEditorOpen(false)
        setSelectedTemplate(null)
        loadTemplatesApi.execute()
      }
    }
  )

  // Delete template
  const deleteTemplateApi = useApiCall(
    (templateId: string) => templateApi.deleteTemplate(templateId),
    {
      loadingMessage: 'Deleting template...',
      errorContext: 'delete template',
      onSuccess: () => {
        showToast({ severity: 'low' as ErrorSeverity, title: 'Success', message: 'Template deleted successfully' })
        loadTemplatesApi.execute()
      }
    }
  )

  // Clone template
  const cloneTemplateApi = useApiCall(
    (data: { templateId: string; newName: string }) => 
      templateApi.cloneTemplate(data.templateId, data.newName),
    {
      loadingMessage: 'Cloning template...',
      errorContext: 'clone template',
      onSuccess: () => {
        showToast({ severity: 'low' as ErrorSeverity, title: 'Success', message: 'Template cloned successfully' })
        loadTemplatesApi.execute()
      }
    }
  )

  useEffect(() => {
    loadTemplatesApi.execute()
  }, [])

  const handleSaveTemplate = async (data: TemplateFormData) => {
    await saveTemplateApi.execute({ template: selectedTemplate, formData: data })
  }

  const handleDeleteTemplate = async (templateId: string) => {
    if (!confirm('Are you sure you want to delete this template?')) return
    await deleteTemplateApi.execute(templateId)
  }

  const handleDuplicateTemplate = async (template: Template) => {
    const newName = `${template.name} (Copy)`
    await cloneTemplateApi.execute({ templateId: template.id, newName })
  }

  const filteredTemplates = templates.filter(template => {
    const matchesSearch = template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         template.description?.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesFilter = filterType === 'all' || template.template_type === filterType
    return matchesSearch && matchesFilter
  })

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'word': return 'bg-blue-100 text-blue-800'
      case 'excel': return 'bg-green-100 text-green-800'
      case 'powerpoint': return 'bg-orange-100 text-orange-800'
      case 'pdf': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  // Show loading state
  if (loadTemplatesApi.isLoading && !loadTemplatesApi.data) {
    return <LoadingSpinner />
  }

  // Show error state
  if (loadTemplatesApi.isError && !loadTemplatesApi.data) {
    return (
      <div className="text-destructive p-4 text-center">
        Failed to load templates
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Template Editor</h2>
          <p className="text-gray-600">Create and manage your document templates</p>
        </div>
        <Button onClick={() => {
          setSelectedTemplate(null)
          setIsEditorOpen(true)
        }}>
          <Plus className="mr-2 h-4 w-4" />
          New Template
        </Button>
      </div>

      {/* Search and Filter */}
      <div className="flex items-center space-x-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
          <Input
            placeholder="Search templates..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={filterType} onValueChange={setFilterType}>
          <SelectTrigger className="w-48">
            <Filter className="mr-2 h-4 w-4" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="word">Word</SelectItem>
            <SelectItem value="excel">Excel</SelectItem>
            <SelectItem value="powerpoint">PowerPoint</SelectItem>
            <SelectItem value="pdf">PDF</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredTemplates.map((template) => (
          <Card key={template.id} className="hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle className="text-lg">{template.name}</CardTitle>
                  <CardDescription className="mt-1">
                    {template.description || 'No description'}
                  </CardDescription>
                </div>
                <Badge className={getTypeColor(template.template_type)}>
                  {template.template_type.toUpperCase()}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="text-sm text-gray-500">
                  Created: {new Date(template.created_at).toLocaleDateString()}
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1">
                    {template.is_public && (
                      <Badge variant="secondary">Public</Badge>
                    )}
                    {template.is_active && (
                      <Badge variant="default">Active</Badge>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSelectedTemplate(template)
                      setIsEditorOpen(true)
                    }}
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDuplicateTemplate(template)}
                    disabled={cloneTemplateApi.isLoading}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeleteTemplate(template.id)}
                    disabled={deleteTemplateApi.isLoading}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredTemplates.length === 0 && (
        <div className="text-center py-12">
          <FileText className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No templates found</h3>
          <p className="mt-1 text-sm text-gray-500">
            {searchTerm || filterType !== 'all' 
              ? 'Try adjusting your search or filter criteria.'
              : 'Get started by creating your first template.'
            }
          </p>
          {!searchTerm && filterType === 'all' && (
            <div className="mt-6">
              <Button onClick={() => {
                setSelectedTemplate(null)
                setIsEditorOpen(true)
              }}>
                <Plus className="mr-2 h-4 w-4" />
                Create Template
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Template Editor Dialog */}
      <Dialog open={isEditorOpen} onOpenChange={setIsEditorOpen}>
        <DialogContent className="sm:max-w-[800px]">
          <DialogHeader>
            <DialogTitle>
              {selectedTemplate ? 'Edit Template' : 'Create New Template'}
            </DialogTitle>
            <DialogDescription>
              {selectedTemplate 
                ? 'Make changes to your template below.'
                : 'Create a new template with placeholders for dynamic content.'
              }
            </DialogDescription>
          </DialogHeader>
          <TemplateEditorForm
            template={selectedTemplate ?? undefined}
            onSave={handleSaveTemplate}
            onCancel={() => {
              setIsEditorOpen(false)
              setSelectedTemplate(null)
            }}
            isLoading={saveTemplateApi.isLoading}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}