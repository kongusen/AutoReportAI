'use client'

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { PlusCircle, Upload, Trash2, FileText, Edit } from 'lucide-react'
import Link from 'next/link'
import { useI18n } from '@/lib/i18n'
import { useAppState } from '@/lib/context/hooks'

export function TemplateList() {
  const { t } = useI18n()
  const { templates, ui } = useAppState()
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false)
  const [uploadForm, setUploadForm] = useState({
    name: '',
    description: '',
    file: null as File | null
  })
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    // Only fetch if we don't have templates or if they're stale
    if (templates.templates.length === 0) {
      fetchTemplates()
    }
  }, [])

  const fetchTemplates = async () => {
    try {
      ui.setLoading(true)
      ui.clearError()
      // Mock API call - replace with actual API when backend is ready
      const response = { data: { items: [] } }
      const templatesData = Array.isArray(response.data) ? response.data : (response.data.items || [])
      templates.setTemplates(templatesData)
    } catch (error) {
      console.error('Error fetching templates:', error)
      ui.setError('Failed to fetch templates')
    } finally {
      ui.setLoading(false)
    }
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!uploadForm.file || !uploadForm.name.trim()) return

    setUploading(true)
    try {
      // Mock upload - replace with actual API when backend is ready
      const mockTemplate = {
        id: Date.now().toString(),
        name: uploadForm.name,
        description: uploadForm.description,
        template_type: 'document' as const,
        is_public: false,
        is_active: true,
        user_id: 'mock-user-id',
        created_at: new Date().toISOString()
      }
      const mockResponse = { status: 200, data: mockTemplate }
      
      if (mockResponse.status === 200 || mockResponse.status === 201) {
        templates.addTemplate(mockResponse.data)
        setUploadDialogOpen(false)
        setUploadForm({ name: '', description: '', file: null })
      } else {
        ui.setError('Upload failed')
      }
    } catch (error) {
      console.error('Error uploading template:', error)
      ui.setError('Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm(t('common.confirm'))) return

    try {
      // Mock delete - replace with actual API when backend is ready
      const mockResponse = { status: 200 }
      
      if (mockResponse.status === 200 || mockResponse.status === 204) {
        templates.deleteTemplate(id)
      } else {
        ui.setError('Delete failed')
      }
    } catch (error) {
      console.error('Error deleting template:', error)
      ui.setError(t('common.error'))
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      if (!file.name.endsWith('.docx')) {
        alert('Please select a .docx file')
        return
      }
      setUploadForm(prev => ({ ...prev, file }))
    }
  }

  if (ui.loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">{t('common.loading')}</div>
      </div>
    )
  }

  if (ui.error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-red-500">{ui.error}</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">{t('templates.title')}</h1>
          <p className="text-gray-600">{t('templates.description')}</p>
        </div>
        <div className="flex space-x-2">
          <Link href="/templates/new">
            <Button variant="outline">
              <Edit className="w-4 h-4 mr-2" />
              Create Template
            </Button>
          </Link>
          <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <PlusCircle className="w-4 h-4 mr-2" />
                {t('templates.upload')}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t('templates.uploadNew')}</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleUpload} className="space-y-4">
                <div>
                  <Label htmlFor="name">{t('templates.name')}</Label>
                  <Input
                    id="name"
                    value={uploadForm.name}
                    onChange={(e) => setUploadForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder={t('templates.name')}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="description">{t('templates.description')} ({t('common.optional')})</Label>
                  <Textarea
                    id="description"
                    value={uploadForm.description}
                    onChange={(e) => setUploadForm(prev => ({ ...prev, description: e.target.value }))}
                    placeholder={t('templates.description')}
                  />
                </div>
                <div>
                  <Label htmlFor="file">{t('templates.upload')} (.docx)</Label>
                  <Input
                    id="file"
                    type="file"
                    accept=".docx"
                    onChange={handleFileChange}
                    required
                  />
                </div>
                <div className="flex justify-end space-x-2">
                  <Button type="button" variant="outline" onClick={() => setUploadDialogOpen(false)}>
                    {t('common.cancel')}
                  </Button>
                  <Button type="submit" disabled={uploading}>
                    {uploading ? (
                      <>
                        <Upload className="w-4 h-4 mr-2 animate-spin" />
                        {t('common.loading')}
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4 mr-2" />
                        {t('common.submit')}
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('templates.title')}</CardTitle>
          <CardDescription>
            {templates.templates.length} {t('templates.noTemplates').toLowerCase().includes('template') ? t('templates.noTemplates') : `${templates.templates.length === 1 ? 'template' : 'templates'} available`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {templates.templates.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">{t('templates.noTemplates')}</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('templates.name')}</TableHead>
                  <TableHead>{t('templates.description')}</TableHead>
                  <TableHead>{t('templates.filePath')}</TableHead>
                  <TableHead>{t('templates.placeholders')}</TableHead>
                  <TableHead className="text-right">{t('templates.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {templates.templates.map((template) => (
                  <TableRow key={template.id}>
                    <TableCell className="font-medium">{template.name}</TableCell>
                    <TableCell>{template.description || '-'}</TableCell>
                    <TableCell className="text-sm text-gray-500">-</TableCell>
                    <TableCell>
                      0 {t('templates.placeholders')}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex space-x-2 justify-end">
                        <Link href={`/templates/${template.id}/edit`}>
                          <Button
                            variant="outline"
                            size="sm"
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                        </Link>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDelete(template.id)}
                          className="text-red-600 hover:text-red-800"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
} 