'use client'

import { useState, useEffect } from 'react'
import { useAppState } from '@/lib/context/hooks'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { DataSourceForm, QuickExportButton } from '@/components/forms'
import { Plus, TestTube, Eye, Edit, Trash2, Loader2 } from 'lucide-react'
import { DataSource } from '@/types/api'

interface PreviewData {
  columns: string[]
  data: any[]
  row_count: number
}

export default function DataSourcesPage() {
  const { dataSources, ui } = useAppState()
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingSource, setEditingSource] = useState<DataSource | null>(null)
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [isPreviewOpen, setIsPreviewOpen] = useState(false)
  const [testingConnection, setTestingConnection] = useState<number | null>(null)
  const [previewingData, setPreviewingData] = useState<number | null>(null)

  const fetchDataSources = async () => {
    try {
      ui.setLoading(true)
      ui.clearError()
      const response = await api.get('/data-sources')
      const dataSourcesData = Array.isArray(response.data) ? response.data : (response.data.items || [])
      dataSources.setDataSources(dataSourcesData)
    } catch (err) {
      ui.setError('Failed to fetch data sources.')
      console.error(err)
    } finally {
      ui.setLoading(false)
    }
  }

  useEffect(() => {
    // Only fetch if we don't have data or if it's stale
    if (dataSources.dataSources.length === 0) {
      fetchDataSources()
    }
  }, [])

  const handleCreateSource = async (values: any) => {
    try {
      const response = await api.post('/data-sources', values)
      dataSources.addDataSource(response.data)
      setIsDialogOpen(false)
    } catch (error: any) {
      console.error('Failed to create data source:', error)
      ui.setError(error.response?.data?.detail || 'Failed to create data source')
    }
  }

  const handleEditSource = async (values: any) => {
    if (!editingSource) return
    
    try {
      const response = await api.put(`/data-sources/${editingSource.id}`, values)
      dataSources.updateDataSource(editingSource.id, response.data)
      setIsDialogOpen(false)
      setEditingSource(null)
    } catch (error: any) {
      console.error('Failed to edit data source:', error)
      ui.setError(error.response?.data?.detail || 'Failed to edit data source')
    }
  }

  const handleEdit = (source: DataSource) => {
    setEditingSource(source)
    setIsDialogOpen(true)
  }

  const handleDelete = async (sourceId: number) => {
    if (!confirm('Are you sure you want to delete this data source?')) return
    
    try {
      await api.delete(`/data-sources/${sourceId}`)
      dataSources.deleteDataSource(sourceId)
    } catch (err: any) {
      console.error('Failed to delete data source:', err)
      ui.setError(err.response?.data?.detail || 'Failed to delete data source')
    }
  }

  const handleTestConnection = async (sourceId: number) => {
    setTestingConnection(sourceId)
    try {
      const response = await api.post(`/data-sources/${sourceId}/test`)
      alert(response.data.msg || 'Connection test successful!')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Connection test failed')
    } finally {
      setTestingConnection(null)
    }
  }

  const handlePreviewData = async (sourceId: number) => {
    setPreviewingData(sourceId)
    try {
      const response = await api.get(`/data-sources/${sourceId}/preview?limit=10`)
      setPreviewData(response.data)
      setIsPreviewOpen(true)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to preview data')
    } finally {
      setPreviewingData(null)
    }
  }

  const openCreateDialog = () => {
    setEditingSource(null)
    setIsDialogOpen(true)
  }

  const getSourceTypeColor = (type: string) => {
    switch (type) {
      case 'sql': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'csv': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'api': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    }
  }

  if (ui.loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading data sources...</span>
      </div>
    )
  }

  if (ui.error) {
    return <div className="text-center text-red-500">{ui.error}</div>
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Data Sources</h2>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={openCreateDialog}>
              <Plus className="mr-2 h-4 w-4" />
              Add New Data Source
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>
                {editingSource ? 'Edit Data Source' : 'Create New Data Source'}
              </DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <DataSourceForm 
                onSubmit={editingSource ? handleEditSource : handleCreateSource}
                defaultValues={editingSource ? {
                  name: editingSource.name,
                  source_type: editingSource.source_type as 'sql' | 'csv' | 'api',
                  db_query: editingSource.db_query || '',
                  file_path: editingSource.file_path || '',
                  api_url: editingSource.api_url || ''
                } : undefined}
              />
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Configuration</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {dataSources.dataSources.length > 0 ? (
              dataSources.dataSources.map((source) => (
                <TableRow key={source.id}>
                  <TableCell className="font-medium">{source.name}</TableCell>
                  <TableCell>
                    <Badge className={getSourceTypeColor(source.source_type)}>
                      {source.source_type.toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell className="max-w-xs">
                    <div className="text-sm text-gray-600 truncate">
                      {source.source_type === 'sql' && source.db_query && (
                        <code className="text-xs">{source.db_query}</code>
                      )}
                      {source.source_type === 'csv' && source.file_path && (
                        <span>{source.file_path}</span>
                      )}
                      {source.source_type === 'api' && source.api_url && (
                        <span>{source.api_url}</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTestConnection(source.id)}
                        disabled={testingConnection === source.id}
                      >
                        {testingConnection === source.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <TestTube className="h-4 w-4" />
                        )}
                        Test
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handlePreviewData(source.id)}
                        disabled={previewingData === source.id}
                      >
                        {previewingData === source.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                        Preview
                      </Button>
                      <QuickExportButton
                        sourceId={source.id}
                        sourceName={source.name}
                        sourceType="data_source"
                        variant="outline"
                        size="sm"
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(source)}
                      >
                        <Edit className="h-4 w-4" />
                        Edit
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDelete(source.id)}
                        className="text-red-600 hover:text-red-700"
                      >
                        <Trash2 className="h-4 w-4" />
                        Delete
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={4} className="h-24 text-center">
                  No data sources found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Data Preview Dialog */}
      <Dialog open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
        <DialogContent className="sm:max-w-[800px]">
          <DialogHeader>
            <DialogTitle>Data Preview</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            {previewData && (
              <div className="space-y-4">
                <div className="text-sm text-gray-600">
                  Showing {previewData.row_count} rows with {previewData.columns.length} columns
                </div>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {previewData.columns.map((column) => (
                          <TableHead key={column}>{column}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {previewData.data.map((row, index) => (
                        <TableRow key={index}>
                          {previewData.columns.map((column) => (
                            <TableCell key={column} className="max-w-xs truncate">
                              {String(row[column] || '')}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}