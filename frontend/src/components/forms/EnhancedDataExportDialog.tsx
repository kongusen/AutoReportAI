'use client'

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger,
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
import { Progress } from '@/components/ui/progress'
import { 
  Download, 
  Loader2, 
  Plus, 
  Eye, 
  X, 
  Package,
  Trash2,
  Search,
  Upload
} from 'lucide-react'
import api from '@/lib/api'
import axios from 'axios';

interface ExportFormat {
  name: string
  value: string
  description: string
  mime_type: string
  supports_streaming?: boolean
  max_size?: number
}

interface ExportItem {
  id: string
  type: 'data_source' | 'task' | 'history'
  source_id: number
  name: string
  export_format: string
  filters?: Record<string, { operator: string; value: string }>
  columns?: string[]
  limit?: number
  date_range?: {
    start?: string
    end?: string
  }
}

interface ExportTemplate {
  id: string
  name: string
  description?: string
  items: ExportItem[]
  created_at: string
}

interface DataSource {
  id: number
  name: string
  type: string
  status: string
}

interface EnhancedDataExportDialogProps {
  trigger?: React.ReactNode
  defaultType?: 'data_source' | 'task' | 'history'
  defaultSourceId?: number
  defaultSourceName?: string
  onExportComplete?: (result: unknown) => void
}

export function EnhancedDataExportDialog({ 
  trigger, 
  defaultType = 'data_source',
  defaultSourceId,
  defaultSourceName,
  onExportComplete
}: EnhancedDataExportDialogProps) {
  const [open, setOpen] = useState(false)
  const [exportFormats, setExportFormats] = useState<ExportFormat[]>([])
  const [exportItems, setExportItems] = useState<ExportItem[]>([])
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [exportTemplates, setExportTemplates] = useState<ExportTemplate[]>([])
  
  const [currentItem, setCurrentItem] = useState<Partial<ExportItem>>({
    type: defaultType,
    source_id: defaultSourceId,
    name: defaultSourceName || '',
    export_format: 'csv',
    filters: {},
    columns: [],
    limit: 1000,
    date_range: {}
  })
  
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [exportProgress, setExportProgress] = useState(0)
  const [exportStatus, setExportStatus] = useState<string>('')
  const [availableColumns, setAvailableColumns] = useState<string[]>([])
  const [selectedColumns, setSelectedColumns] = useState<string[]>([])
  const [filters, setFilters] = useState<Record<string, { operator: string; value: string }>>({})
  const [previewData, setPreviewData] = useState<Record<string, unknown>[]>([])
  const [showPreview, setShowPreview] = useState(false)
  
  // 模板相关状态
  const [templateName, setTemplateName] = useState('')
  const [templateDescription, setTemplateDescription] = useState('')
  const [savingTemplate, setSavingTemplate] = useState(false)
  
  // 搜索和过滤
  const [searchTerm, setSearchTerm] = useState('')
  const [filterColumn, setFilterColumn] = useState('')
  const [filterOperator, setFilterOperator] = useState('equals')
  const [filterValue, setFilterValue] = useState('')

  useEffect(() => {
    if (open) {
      fetchInitialData()
    }
  }, [open])

  useEffect(() => {
    if (currentItem.source_id && currentItem.type === 'data_source') {
      fetchAvailableColumns(currentItem.source_id)
    }
  }, [currentItem.source_id, currentItem.type])

  const fetchInitialData = async () => {
    setLoading(true)
    try {
      const [formatsRes, sourcesRes, templatesRes] = await Promise.all([
        api.get('/v1/data-export/export-formats'),
        api.get('/enhanced-data-sources'),
        api.get('/v1/data-export/templates').catch(() => ({ data: { templates: [] } }))
      ])
      
      setExportFormats(formatsRes.data.formats || [])
      setDataSources(sourcesRes.data.data_sources || [])
      setExportTemplates(templatesRes.data.templates || [])
    } catch (error) {
      console.error('Failed to fetch initial data:', error)
    } finally {
      setLoading(false)
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

  const fetchPreviewData = async () => {
    if (!currentItem.source_id) return

    setLoading(true)
    try {
      const params = new URLSearchParams({
        limit: '10',
        ...(selectedColumns.length > 0 && { columns: selectedColumns.join(',') }),
        ...(Object.keys(filters).length > 0 && { filters: JSON.stringify(filters) })
      })

      const response = await api.get(`/v1/enhanced-data-sources/${currentItem.source_id}/preview?${params}`)
      setPreviewData(response.data.data || [])
      setShowPreview(true)
    } catch (error) {
      console.error('Failed to fetch preview:', error)
    } finally {
      setLoading(false)
    }
  }

  const addFilter = () => {
    if (!filterColumn || !filterValue) return

    setFilters(prev => ({
      ...prev,
      [filterColumn]: { operator: filterOperator, value: filterValue }
    }))
    
    setFilterColumn('')
    setFilterValue('')
  }

  const removeFilter = (column: string) => {
    setFilters(prev => {
      const newFilters = { ...prev }
      delete newFilters[column]
      return newFilters
    })
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
      limit: currentItem.limit,
      date_range: currentItem.date_range
    }

    setExportItems(prev => [...prev, newItem])
    resetCurrentItem()
  }

  const resetCurrentItem = () => {
    setCurrentItem({
      type: 'data_source',
      source_id: undefined,
      name: '',
      export_format: 'csv',
      limit: 1000,
      date_range: {}
    })
    setSelectedColumns([])
    setFilters({})
    setShowPreview(false)
  }

  const removeExportItem = (id: string) => {
    setExportItems(prev => prev.filter(item => item.id !== id))
  }

  const handleSingleExport = async () => {
    if (!currentItem.source_id) return

    setExporting(true)
    setExportProgress(0)
    setExportStatus('准备导出...')

    try {
      const exportData = {
        [`${currentItem.type}_id`]: currentItem.source_id,
        export_format: currentItem.export_format,
        filters: Object.keys(filters).length > 0 ? filters : undefined,
        columns: selectedColumns.length > 0 ? selectedColumns : undefined,
        limit: currentItem.limit,
        date_range: currentItem.date_range
      }

      // 模拟进度更新
      const progressInterval = setInterval(() => {
        setExportProgress(prev => Math.min(prev + 10, 90))
      }, 200)

      setExportStatus('正在导出数据...')
      const response = await api.post('/v1/data-export/export-data', exportData, {
        responseType: 'blob'
      })

      clearInterval(progressInterval)
      setExportProgress(100)
      setExportStatus('导出完成')

      // 创建下载链接
      const blob = new Blob([response.data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      
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

      onExportComplete?.(response.data)
      setOpen(false)
    } catch (error: unknown) {
      console.error('Export failed:', error)
      setExportStatus('导出失败')
      if (axios.isAxiosError(error)) {
        alert(error.response?.data?.detail || 'Export failed')
      } else if (error instanceof Error) {
        alert(error.message || 'Export failed')
      } else {
        alert('Export failed')
      }
    } finally {
      setExporting(false)
      setExportProgress(0)
      setExportStatus('')
    }
  }

  const handleBulkExport = async () => {
    if (exportItems.length === 0) return

    setExporting(true)
    setExportProgress(0)
    setExportStatus('准备批量导出...')

    try {
      const bulkData = {
        export_items: exportItems.map(item => ({
          [`${item.type}_id`]: item.source_id,
          export_format: item.export_format,
          filters: item.filters,
          columns: item.columns,
          limit: item.limit,
          date_range: item.date_range
        })),
        export_format: 'zip',
        include_metadata: true
      }

      const progressInterval = setInterval(() => {
        setExportProgress(prev => Math.min(prev + 5, 90))
      }, 300)

      setExportStatus('正在批量导出数据...')
      const response = await api.post('/v1/data-export/bulk-export', bulkData, {
        responseType: 'blob'
      })

      clearInterval(progressInterval)
      setExportProgress(100)
      setExportStatus('批量导出完成')

      const blob = new Blob([response.data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `bulk_export_${new Date().toISOString().slice(0, 10)}.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      onExportComplete?.(response.data)
      setOpen(false)
    } catch (error: unknown) {
      console.error('Bulk export failed:', error)
      setExportStatus('批量导出失败')
      if (axios.isAxiosError(error)) {
        alert(error.response?.data?.detail || 'Bulk export failed')
      } else if (error instanceof Error) {
        alert(error.message || 'Bulk export failed')
      } else {
        alert('Bulk export failed')
      }
    } finally {
      setExporting(false)
      setExportProgress(0)
      setExportStatus('')
    }
  }

  const saveAsTemplate = async () => {
    if (!templateName || exportItems.length === 0) return

    setSavingTemplate(true)
    try {
      const templateData = {
        name: templateName,
        description: templateDescription,
        items: exportItems
      }

      await api.post('/v1/data-export/templates', templateData)
      
      // 重新获取模板列表
      const response = await api.get('/v1/data-export/templates')
      setExportTemplates(response.data.templates || [])
      
      setTemplateName('')
      setTemplateDescription('')
      alert('模板保存成功！')
    } catch (error: unknown) {
      console.error('Failed to save template:', error)
      if (axios.isAxiosError(error)) {
        alert(error.response?.data?.detail || 'Failed to save template')
      } else if (error instanceof Error) {
        alert(error.message || 'Failed to save template')
      } else {
        alert('Failed to save template')
      }
    } finally {
      setSavingTemplate(false)
    }
  }

  const loadTemplate = (template: ExportTemplate) => {
    setExportItems(template.items)
    alert(`已加载模板: ${template.name}`)
  }

  const filteredDataSources = dataSources.filter(source =>
    source.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Enhanced Export
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-6xl max-h-[95vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center">
            <Download className="mr-2 h-5 w-5" />
            Enhanced Data Export
          </DialogTitle>
        </DialogHeader>

        {loading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin" />
            <span className="ml-2">Loading...</span>
          </div>
        )}

        {!loading && (
          <Tabs defaultValue="single" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="single">Single Export</TabsTrigger>
              <TabsTrigger value="bulk">Bulk Export</TabsTrigger>
              <TabsTrigger value="templates">Templates</TabsTrigger>
            </TabsList>

            <TabsContent value="single" className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* 数据源选择 */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Data Source</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <Label>Search Sources</Label>
                      <div className="relative">
                        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                          placeholder="Search data sources..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                          className="pl-8"
                        />
                      </div>
                    </div>

                    <div className="max-h-48 overflow-y-auto space-y-2">
                      {filteredDataSources.map((source) => (
                        <div
                          key={source.id}
                          className={`p-3 border rounded cursor-pointer transition-colors ${
                            currentItem.source_id === source.id
                              ? 'border-primary bg-primary/5'
                              : 'hover:bg-gray-50'
                          }`}
                          onClick={() => setCurrentItem(prev => ({
                            ...prev,
                            source_id: source.id,
                            name: source.name
                          }))}
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="font-medium">{source.name}</p>
                              <p className="text-sm text-gray-500">{source.type}</p>
                            </div>
                            <Badge variant={source.status === 'active' ? 'default' : 'secondary'}>
                              {source.status}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* 导出设置 */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Export Settings</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
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
                              <div>
                                <div className="font-medium">{format.name}</div>
                                <div className="text-sm text-gray-500">{format.description}</div>
                              </div>
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
                        placeholder="Max rows (default: 1000)"
                      />
                    </div>

                    <div>
                      <Label>Date Range (Optional)</Label>
                      <div className="grid grid-cols-2 gap-2">
                        <Input
                          type="date"
                          value={currentItem.date_range?.start || ''}
                          onChange={(e) => setCurrentItem(prev => ({
                            ...prev,
                            date_range: { ...prev.date_range, start: e.target.value }
                          }))}
                          placeholder="Start date"
                        />
                        <Input
                          type="date"
                          value={currentItem.date_range?.end || ''}
                          onChange={(e) => setCurrentItem(prev => ({
                            ...prev,
                            date_range: { ...prev.date_range, end: e.target.value }
                          }))}
                          placeholder="End date"
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* 高级选项 */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Advanced Options</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {availableColumns.length > 0 && (
                      <div>
                        <Label>Select Columns</Label>
                        <div className="max-h-32 overflow-y-auto border rounded p-2 space-y-1">
                          <div className="flex items-center space-x-2 mb-2">
                            <Checkbox
                              checked={selectedColumns.length === availableColumns.length}
                              onChange={(e) => {
                                const checked = (e.target as HTMLInputElement).checked
                                if (checked) {
                                  setSelectedColumns([...availableColumns])
                                } else {
                                  setSelectedColumns([])
                                }
                              }}
                            />
                            <Label className="text-sm font-medium">Select All</Label>
                          </div>
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
                      <Label>Add Filter</Label>
                      <div className="space-y-2">
                        <Select value={filterColumn} onValueChange={setFilterColumn}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select column" />
                          </SelectTrigger>
                          <SelectContent>
                            {availableColumns.map((column) => (
                              <SelectItem key={column} value={column}>
                                {column}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        
                        <div className="grid grid-cols-2 gap-2">
                          <Select value={filterOperator} onValueChange={setFilterOperator}>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="equals">Equals</SelectItem>
                              <SelectItem value="contains">Contains</SelectItem>
                              <SelectItem value="starts_with">Starts With</SelectItem>
                              <SelectItem value="greater_than">Greater Than</SelectItem>
                              <SelectItem value="less_than">Less Than</SelectItem>
                            </SelectContent>
                          </Select>
                          
                          <Input
                            value={filterValue}
                            onChange={(e) => setFilterValue(e.target.value)}
                            placeholder="Filter value"
                          />
                        </div>
                        
                        <Button 
                          size="sm" 
                          onClick={addFilter}
                          disabled={!filterColumn || !filterValue}
                          className="w-full"
                        >
                          <Plus className="mr-2 h-4 w-4" />
                          Add Filter
                        </Button>
                      </div>

                      <div className="space-y-2 mt-3">
                        {Object.entries(filters).map(([column, filter]) => (
                          <div key={column} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                            <div className="flex items-center space-x-2">
                              <Badge variant="outline">{column}</Badge>
                              <Badge variant="secondary">
                                {filter.operator} &quot;{filter.value}&quot;
                              </Badge>
                            </div>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => removeFilter(column)}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* 预览和导出 */}
              <div className="space-y-4">
                <div className="flex space-x-2">
                  <Button
                    variant="outline"
                    onClick={fetchPreviewData}
                    disabled={!currentItem.source_id || loading}
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    Preview Data
                  </Button>
                  
                  <Button
                    onClick={handleSingleExport}
                    disabled={exporting || !currentItem.source_id}
                  >
                    {exporting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Exporting...
                      </>
                    ) : (
                      <>
                        <Download className="mr-2 h-4 w-4" />
                        Export Data
                      </>
                    )}
                  </Button>
                </div>

                {exporting && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">{exportStatus}</span>
                      <span className="text-sm">{exportProgress}%</span>
                    </div>
                    <Progress value={exportProgress} />
                  </div>
                )}

                {showPreview && previewData.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Data Preview</CardTitle>
                      <CardDescription>
                        Showing first 10 rows of filtered data
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b">
                              {previewData[0] && Object.keys(previewData[0] as Record<string, unknown>).map((key) => (
                                <th key={key} className="text-left p-2 font-medium">
                                  {key}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {previewData.map((row, index) => (
                              <tr key={index} className="border-b">
                                {Object.values(row).map((value: unknown, cellIndex) => (
                                  <td key={cellIndex} className="p-2">
                                    {String(value)}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
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
                      <Label>Item Name</Label>
                      <Input
                        value={currentItem.name}
                        onChange={(e) => setCurrentItem(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="Export item name"
                      />
                    </div>

                    <div>
                      <Label>Data Source</Label>
                      <Select
                        value={currentItem.source_id?.toString()}
                        onValueChange={(value) => {
                          const source = dataSources.find(s => s.id === parseInt(value))
                          setCurrentItem(prev => ({ 
                            ...prev, 
                            source_id: parseInt(value),
                            name: prev.name || source?.name || ''
                          }))
                        }}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select data source" />
                        </SelectTrigger>
                        <SelectContent>
                          {dataSources.map((source) => (
                            <SelectItem key={source.id} value={source.id.toString()}>
                              {source.name} ({source.type})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
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
                    <CardTitle className="text-lg">
                      Export Items ({exportItems.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {exportItems.map((item) => (
                        <div key={item.id} className="flex items-center justify-between p-3 border rounded">
                          <div>
                            <p className="font-medium">{item.name}</p>
                            <div className="flex space-x-2 mt-1">
                              <Badge variant="outline">{item.type}</Badge>
                              <Badge variant="secondary">{item.export_format}</Badge>
                              {item.limit && (
                                <Badge variant="outline">Limit: {item.limit}</Badge>
                              )}
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
                        <p className="text-gray-500 text-center py-8">
                          No export items added yet
                        </p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* 保存为模板 */}
              {exportItems.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Save as Template</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <Label>Template Name</Label>
                        <Input
                          value={templateName}
                          onChange={(e) => setTemplateName(e.target.value)}
                          placeholder="Enter template name"
                        />
                      </div>
                      <div>
                        <Label>Description (Optional)</Label>
                        <Input
                          value={templateDescription}
                          onChange={(e) => setTemplateDescription(e.target.value)}
                          placeholder="Template description"
                        />
                      </div>
                    </div>
                    <Button
                      onClick={saveAsTemplate}
                      disabled={!templateName || savingTemplate}
                      variant="outline"
                    >
                      {savingTemplate ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <span className="mr-2 h-4 w-4">💾</span>
                          Save Template
                        </>
                      )}
                    </Button>
                  </CardContent>
                </Card>
              )}

              <div className="flex justify-between">
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
              </div>

              {exporting && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">{exportStatus}</span>
                    <span className="text-sm">{exportProgress}%</span>
                  </div>
                  <Progress value={exportProgress} />
                </div>
              )}
            </TabsContent>

            <TabsContent value="templates" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Export Templates</CardTitle>
                  <CardDescription>
                    Save and reuse export configurations
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {exportTemplates.map((template) => (
                      <div key={template.id} className="flex items-center justify-between p-4 border rounded">
                        <div>
                          <h4 className="font-medium">{template.name}</h4>
                          {template.description && (
                            <p className="text-sm text-gray-500 mt-1">{template.description}</p>
                          )}
                          <div className="flex items-center space-x-4 mt-2">
                            <Badge variant="outline">
                              {template.items.length} items
                            </Badge>
                            <span className="text-sm text-gray-500">
                              Created: {new Date(template.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                        <div className="flex space-x-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => loadTemplate(template)}
                          >
                            <Upload className="mr-2 h-4 w-4" />
                            Load
                          </Button>
                        </div>
                      </div>
                    ))}
                    {exportTemplates.length === 0 && (
                      <p className="text-gray-500 text-center py-8">
                        No templates saved yet
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  )
}