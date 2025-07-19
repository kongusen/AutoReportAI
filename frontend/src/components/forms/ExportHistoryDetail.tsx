'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { 
  Download, 
  Eye, 
  Clock,
  Database,
  FileText,
  User,
  Calendar,
  AlertCircle,
  CheckCircle,
  Info,
  Settings,
  Filter,
  Columns,
  Hash
} from 'lucide-react'
import { formatFileSize, getStatusColor, getStatusIcon } from '@/lib/export-config'
import api from '@/lib/api'

interface ExportHistoryItem {
  id: string
  name: string
  type: 'single' | 'bulk' | 'scheduled'
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
  format: string
  file_size?: number
  row_count?: number
  created_at: string
  started_at?: string
  completed_at?: string
  download_url?: string
  error_message?: string
  metadata?: {
    source_name?: string
    source_type?: string
    columns?: string[]
    filters?: Record<string, any>
    limit?: number
    user_id?: string
    user_name?: string
    processing_time?: number
    compression?: boolean
    file_path?: string
  }
}

interface ExportHistoryDetailProps {
  exportId: string
  trigger?: React.ReactNode
  onDownload?: (exportId: string) => void
}

export function ExportHistoryDetail({
  exportId,
  trigger,
  onDownload
}: ExportHistoryDetailProps) {
  const [open, setOpen] = useState(false)
  const [exportDetail, setExportDetail] = useState<ExportHistoryItem | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open && exportId) {
      fetchExportDetail()
    }
  }, [open, exportId])

  const fetchExportDetail = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await api.get(`/data-export/history/${exportId}`)
      setExportDetail(response.data.export)
    } catch (err: any) {
      console.error('Failed to fetch export detail:', err)
      setError(err.response?.data?.detail || 'Failed to fetch export details')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async () => {
    if (!exportDetail?.download_url) return

    try {
      const response = await api.get(`/data-export/download/${exportDetail.id}`, {
        responseType: 'blob'
      })
      
      const blob = new Blob([response.data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${exportDetail.name}.${exportDetail.format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      onDownload?.(exportDetail.id)
    } catch (err: any) {
      console.error('Download failed:', err)
      alert('Download failed')
    }
  }

  const formatDuration = (start?: string, end?: string) => {
    if (!start || !end) return 'N/A'
    const duration = new Date(end).getTime() - new Date(start).getTime()
    const seconds = Math.floor(duration / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    
    if (hours > 0) return `${hours}h ${minutes % 60}m ${seconds % 60}s`
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`
    return `${seconds}s`
  }

  const renderMetadataSection = (title: string, icon: React.ReactNode, children: React.ReactNode) => (
    <div className="space-y-3">
      <div className="flex items-center space-x-2">
        {icon}
        <h4 className="font-medium">{title}</h4>
      </div>
      <div className="pl-6 space-y-2">
        {children}
      </div>
    </div>
  )

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm">
            <Eye className="h-4 w-4" />
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <FileText className="h-5 w-5" />
            <span>Export Details</span>
          </DialogTitle>
        </DialogHeader>

        {loading && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <span className="ml-2">Loading export details...</span>
          </div>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {exportDetail && !loading && (
          <div className="space-y-6">
            {/* 基本信息 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>{exportDetail.name}</span>
                  <div className="flex items-center space-x-2">
                    <Badge variant="outline" className="capitalize">
                      {exportDetail.type}
                    </Badge>
                    <Badge className={getStatusColor(exportDetail.status)}>
                      {getStatusIcon(exportDetail.status)} {exportDetail.status}
                    </Badge>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div className="flex items-center space-x-2">
                    <FileText className="h-4 w-4 text-gray-500" />
                    <div>
                      <p className="text-sm text-gray-500">Format</p>
                      <p className="font-medium">{exportDetail.format.toUpperCase()}</p>
                    </div>
                  </div>
                  
                  {exportDetail.file_size && (
                    <div className="flex items-center space-x-2">
                      <Database className="h-4 w-4 text-gray-500" />
                      <div>
                        <p className="text-sm text-gray-500">File Size</p>
                        <p className="font-medium">{formatFileSize(exportDetail.file_size)}</p>
                      </div>
                    </div>
                  )}
                  
                  {exportDetail.row_count && (
                    <div className="flex items-center space-x-2">
                      <Hash className="h-4 w-4 text-gray-500" />
                      <div>
                        <p className="text-sm text-gray-500">Rows</p>
                        <p className="font-medium">{exportDetail.row_count.toLocaleString()}</p>
                      </div>
                    </div>
                  )}
                </div>

                {exportDetail.status === 'completed' && exportDetail.download_url && (
                  <Button onClick={handleDownload} className="w-full">
                    <Download className="mr-2 h-4 w-4" />
                    Download Export
                  </Button>
                )}
              </CardContent>
            </Card>

            {/* 时间信息 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Clock className="h-5 w-5" />
                  <span>Timeline</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">Created</p>
                    <p className="font-medium">{new Date(exportDetail.created_at).toLocaleString()}</p>
                  </div>
                  
                  {exportDetail.started_at && (
                    <div>
                      <p className="text-sm text-gray-500">Started</p>
                      <p className="font-medium">{new Date(exportDetail.started_at).toLocaleString()}</p>
                    </div>
                  )}
                  
                  {exportDetail.completed_at && (
                    <div>
                      <p className="text-sm text-gray-500">Completed</p>
                      <p className="font-medium">{new Date(exportDetail.completed_at).toLocaleString()}</p>
                    </div>
                  )}
                  
                  <div>
                    <p className="text-sm text-gray-500">Processing Time</p>
                    <p className="font-medium">
                      {exportDetail.metadata?.processing_time 
                        ? `${exportDetail.metadata.processing_time}s`
                        : formatDuration(exportDetail.started_at, exportDetail.completed_at)
                      }
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 元数据 */}
            {exportDetail.metadata && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Info className="h-5 w-5" />
                    <span>Export Configuration</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* 数据源信息 */}
                  {exportDetail.metadata.source_name && (
                    <>
                      {renderMetadataSection(
                        'Data Source',
                        <Database className="h-4 w-4 text-blue-500" />,
                        <div className="space-y-1">
                          <p><strong>Name:</strong> {exportDetail.metadata.source_name}</p>
                          {exportDetail.metadata.source_type && (
                            <p><strong>Type:</strong> {exportDetail.metadata.source_type}</p>
                          )}
                        </div>
                      )}
                      <Separator />
                    </>
                  )}

                  {/* 导出设置 */}
                  {renderMetadataSection(
                    'Export Settings',
                    <Settings className="h-4 w-4 text-gray-500" />,
                    <div className="space-y-1">
                      {exportDetail.metadata.limit && (
                        <p><strong>Row Limit:</strong> {exportDetail.metadata.limit.toLocaleString()}</p>
                      )}
                      {exportDetail.metadata.compression !== undefined && (
                        <p><strong>Compression:</strong> {exportDetail.metadata.compression ? 'Enabled' : 'Disabled'}</p>
                      )}
                    </div>
                  )}

                  {/* 列信息 */}
                  {exportDetail.metadata.columns && exportDetail.metadata.columns.length > 0 && (
                    <>
                      <Separator />
                      {renderMetadataSection(
                        `Selected Columns (${exportDetail.metadata.columns.length})`,
                        <Columns className="h-4 w-4 text-green-500" />,
                        <div className="flex flex-wrap gap-2">
                          {exportDetail.metadata.columns.map((column, index) => (
                            <Badge key={index} variant="outline">
                              {column}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </>
                  )}

                  {/* 过滤器 */}
                  {exportDetail.metadata.filters && Object.keys(exportDetail.metadata.filters).length > 0 && (
                    <>
                      <Separator />
                      {renderMetadataSection(
                        'Applied Filters',
                        <Filter className="h-4 w-4 text-orange-500" />,
                        <div className="space-y-2">
                          {Object.entries(exportDetail.metadata.filters).map(([column, filter]: [string, any]) => (
                            <div key={column} className="flex items-center space-x-2">
                              <Badge variant="outline">{column}</Badge>
                              <span className="text-sm">
                                {filter.operator} "{filter.value}"
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}

                  {/* 用户信息 */}
                  {exportDetail.metadata.user_name && (
                    <>
                      <Separator />
                      {renderMetadataSection(
                        'Created By',
                        <User className="h-4 w-4 text-purple-500" />,
                        <p>{exportDetail.metadata.user_name}</p>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>
            )}

            {/* 错误信息 */}
            {exportDetail.status === 'failed' && exportDetail.error_message && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <strong>Export Failed:</strong> {exportDetail.error_message}
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}