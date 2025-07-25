'use client'

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger,
  DialogFooter 
} from '@/components/ui/dialog'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Checkbox } from '@/components/ui/checkbox'
import { 
  Download, 
  FileText, 
  Database, 
  Filter, 
  Settings,
  Loader2,
  CheckCircle,
  AlertCircle,
  Package,
  Plus,
  Trash2
} from 'lucide-react'
import api from '@/lib/api'
import axios from 'axios';

interface ExportFormat {
  name: string
  value: string
  description: string
  mime_type: string
}

interface ExportItem {
  id: string
  type: 'data_source' | 'task' | 'history'
  source_id: number
  name: string
  export_format: string
  filters?: Record<string, unknown>
  columns?: string[]
  limit?: number
}

interface DataExportDialogProps {
  trigger?: React.ReactNode
  defaultType?: 'data_source' | 'task' | 'history'
  defaultSourceId?: number
  defaultSourceName?: string
}

export function DataExportDialog({ 
  trigger, 
  defaultType = 'data_source',
  defaultSourceId,
  defaultSourceName 
}: DataExportDialogProps) {
  const [open, setOpen] = useState(false)
  const [exportFormats, setExportFormats] = useState<ExportFormat[]>([])
  const [exportItems, setExportItems] = useState<ExportItem[]>([])
  const [currentItem, setCurrentItem] = useState<Partial<ExportItem>>({
    type: defaultType,
    source_id: defaultSourceId,
    name: defaultSourceName || '',
    export_format: 'csv',
    filters: {},
    columns: [],
    limit: 1000
  })
  
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [availableColumns, setAvailableColumns] = useState<string[]>([])
  const [selectedColumns, setSelectedColumns] = useState<string[]>([])
  const [filters, setFilters] = useState<Record<string, unknown>>({})
  const [bulkExport, setBulkExport] = useState(false)

  useEffect(() => {
    if (open) {
      fetchExportFormats()
      if (currentItem.source_id && currentItem.type === 'data_source') {
        fetchAvailableColumns(currentItem.source_id)
      }
    }
  }, [open, currentItem.source_id, currentItem.type])

  const fetchExportFormats = async () => {
    try {
      const response = await api.get('/v1/data-export/export-formats')
      setExportFormats(response.data.formats || [])
    } catch (error) {
      console.error('Failed to fetch export formats:', error)
    }
  }

  const fetchAvailableColumns = async (sourceId: number) => {
    try {
      const response = await api.get(`/v1/enhanced-data-sources/${sourceId}/preview?limit=1`)
      setAvailableColumns(response.data.columns || [])
    } catch (error) {
      console.error('Failed to fetch columns:', error)
    }
  }

  const addExportItem = () => {
    if (!currentItem.source_id || !currentItem.name) return

    const newItem: ExportItem = {
      id: Date.now().toString(),
      type: currentItem.type!,
      source_id: currentItem.source_id,
      name: currentItem.name,
      export_format: currentItem.export_format || 'csv',
      filters: Object.keys(filters).length > 0 ? filters : undefined,
      columns: selectedColumns.length > 0 ? selectedColumns : undefined,
      limit: currentItem.limit
    }

    setExportItems(prev => [...prev, newItem])
    
    // 重置当前项
    setCurrentItem({
      type: 'data_source',
      source_id: undefined,
      name: '',
      export_format: 'csv',
      limit: 1000
    })
    setSelectedColumns([])
    setFilters({})
  }

  const removeExportItem = (id: string) => {
    setExportItems(prev => prev.filter(item => item.id !== id))
  }

  const handleSingleExport = async () => {
    if (!currentItem.source_id) return

    setExporting(true)
    try {
      const exportData = {
        [`${currentItem.type}_id`]: currentItem.source_id,
        export_format: currentItem.export_format,
        filters: Object.keys(filters).length > 0 ? filters : undefined,
        columns: selectedColumns.length > 0 ? selectedColumns : undefined,
        limit: currentItem.limit
      }

      const response = await api.post('/v1/data-export/export-data', exportData, {
        responseType: 'blob'
      })

      // 创建下载链接
      const blob = new Blob([response.data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      
      // 从响应头获取文件名
      const contentDisposition = response.headers['content-disposition']
      let filename = `export.${currentItem.export_format}`
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/)
        if (filenameMatch) {
          filename = filenameMatch[1]
        }
      }
      
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      setOpen(false)
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        alert(error.response?.data?.detail || 'Export failed')
      } else if (error instanceof Error) {
        alert(error.message || 'Export failed')
      } else {
        alert('Export failed')
      }
    } finally {
      setExporting(false)
    }
  }

  const handleBulkExport = async () => {
    if (exportItems.length === 0) return

    setExporting(true)
    try {
      const bulkData = {
        export_items: exportItems.map(item => ({
          [`${item.type}_id`]: item.source_id,
          export_format: item.export_format,
          filters: item.filters,
          columns: item.columns,
          limit: item.limit
        })),
        export_format: 'zip',
        include_metadata: true
      }

      const response = await api.post('/v1/data-export/bulk-export', bulkData, {
        responseType: 'blob'
      })

      // 创建下载链接
      const blob = new Blob([response.data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `bulk_export_${new Date().toISOString().slice(0, 10)}.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      setOpen(false)
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        alert(error.response?.data?.detail || 'Bulk export failed')
      } else if (error instanceof Error) {
        alert(error.message || 'Bulk export failed')
      } else {
        alert('Bulk export failed')
      }
    } finally {
      setExporting(false)
    }
  }

  const addFilter = (column: string, operator: string, value: string) => {
    setFilters(prev => ({
      ...prev,
      [column]: { operator, value }
    }))
  }

  const removeFilter = (column: string) => {
    setFilters(prev => {
      const newFilters = { ...prev }
      delete newFilters[column]
      return newFilters
    })
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export Data
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center">
            <Download className="mr-2 h-5 w-5" />
            Data Export
          </DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="single" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="single">Single Export</TabsTrigger>
            <TabsTrigger value="bulk">Bulk Export</TabsTrigger>
          </TabsList>

          <TabsContent value="single" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* 基本设置 */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Export Settings</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label>Export Type</Label>
                    <Select
                      value={currentItem.type}
                      onValueChange={(value: string) => setCurrentItem(prev => ({ ...prev, type: value as 'data_source' | 'task' | 'history' }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="data_source">Data Source</SelectItem>
                        <SelectItem value="task">Task</SelectItem>
                        <SelectItem value="history">History</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Source ID</Label>
                    <Input
                      type="number"
                      value={currentItem.source_id || ''}
                      onChange={(e) => setCurrentItem(prev => ({ 
                        ...prev, 
                        source_id: parseInt(e.target.value) || undefined 
                      }))}
                      placeholder="Enter source ID"
                    />
                  </div>

                  <div>
                    <Label>Export Format</Label>
                    <Select
                      value={currentItem.export_format}
                      onValueChange={(value) => setCurrentItem(prev => ({ ...prev, export_format: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {exportFormats.map((format) => (
                          <SelectItem key={format.value} value={format.value}>
                            {format.name} - {format.description}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Row Limit</Label>
                    <Input
                      type="number"
                      value={currentItem.limit || ''}
                      onChange={(e) => setCurrentItem(prev => ({ 
                        ...prev, 
                        limit: parseInt(e.target.value) || undefined 
                      }))}
                      placeholder="Max rows to export"
                    />
                  </div>
                </CardContent>
              </Card>

              {/* 列选择和过滤器 */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Advanced Options</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {availableColumns.length > 0 && (
                    <div>
                      <Label>Select Columns</Label>
                      <div className="max-h-32 overflow-y-auto border rounded p-2 space-y-1">
                        {availableColumns.map((column) => (
                          <div key={column} className="flex items-center space-x-2">
                            <Checkbox
                              checked={selectedColumns.includes(column)}
                              onChange={(e) => {
                                const checked = (e.target as HTMLInputElement).checked
                                if (checked) {
                                  setSelectedColumns(prev => [...prev, column])
                                } else {
                                  setSelectedColumns(prev => prev.filter(c => c !== column))
                                }
                              }}
                            />
                            <Label className="text-sm">{column}</Label>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div>
                    <Label>Filters</Label>
                    <div className="space-y-2">
                      {Object.entries(filters).map(([column, filter]) => (
                        <div key={column} className="flex items-center space-x-2">
                          <Badge variant="outline">{column}</Badge>
                          <Badge variant="secondary">
                            {(filter as Record<string, string>).operator} {(filter as Record<string, string>).value}
                          </Badge>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => removeFilter(column)}
                          >
                            ×
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSingleExport} disabled={exporting || !currentItem.source_id}>
                {exporting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Exporting...
                  </>
                ) : (
                  <>
                    <Download className="mr-2 h-4 w-4" />
                    Export
                  </>
                )}
              </Button>
            </DialogFooter>
          </TabsContent>

          <TabsContent value="bulk" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* 添加导出项 */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Add Export Item</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label>Name</Label>
                    <Input
                      value={currentItem.name}
                      onChange={(e) => setCurrentItem(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="Export item name"
                    />
                  </div>

                  <div>
                    <Label>Type</Label>
                    <Select
                      value={currentItem.type}
                      onValueChange={(value: string) => setCurrentItem(prev => ({ ...prev, type: value as 'data_source' | 'task' | 'history' }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="data_source">Data Source</SelectItem>
                        <SelectItem value="task">Task</SelectItem>
                        <SelectItem value="history">History</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Source ID</Label>
                    <Input
                      type="number"
                      value={currentItem.source_id || ''}
                      onChange={(e) => setCurrentItem(prev => ({ 
                        ...prev, 
                        source_id: parseInt(e.target.value) || undefined 
                      }))}
                    />
                  </div>

                  <div>
                    <Label>Format</Label>
                    <Select
                      value={currentItem.export_format}
                      onValueChange={(value) => setCurrentItem(prev => ({ ...prev, export_format: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {exportFormats.map((format) => (
                          <SelectItem key={format.value} value={format.value}>
                            {format.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <Button 
                    onClick={addExportItem}
                    disabled={!currentItem.source_id || !currentItem.name}
                    className="w-full"
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Add to Export List
                  </Button>
                </CardContent>
              </Card>

              {/* 导出项列表 */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Export Items ({exportItems.length})</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {exportItems.map((item) => (
                      <div key={item.id} className="flex items-center justify-between p-2 border rounded">
                        <div>
                          <p className="font-medium">{item.name}</p>
                          <div className="flex space-x-2">
                            <Badge variant="outline">{item.type}</Badge>
                            <Badge variant="secondary">{item.export_format}</Badge>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => removeExportItem(item.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                    {exportItems.length === 0 && (
                      <p className="text-gray-500 text-center py-4">
                        No export items added yet
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleBulkExport} 
                disabled={exporting || exportItems.length === 0}
              >
                {exporting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Exporting...
                  </>
                ) : (
                  <>
                    <Package className="mr-2 h-4 w-4" />
                    Bulk Export ({exportItems.length})
                  </>
                )}
              </Button>
            </DialogFooter>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}