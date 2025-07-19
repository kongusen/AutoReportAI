'use client'

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { 
  Download, 
  FileText, 
  Database, 
  Package,
  Loader2,
  ChevronDown
} from 'lucide-react'
import { EnhancedDataExportDialog } from './EnhancedDataExportDialog'
import api from '@/lib/api'

interface QuickExportButtonProps {
  sourceId?: number
  sourceName?: string
  sourceType?: 'data_source' | 'task' | 'history'
  variant?: 'default' | 'outline' | 'ghost'
  size?: 'default' | 'sm' | 'lg'
  className?: string
}

export function QuickExportButton({
  sourceId,
  sourceName,
  sourceType = 'data_source',
  variant = 'outline',
  size = 'default',
  className
}: QuickExportButtonProps) {
  const [exporting, setExporting] = useState(false)
  const [showDialog, setShowDialog] = useState(false)

  const quickExport = async (format: string) => {
    if (!sourceId) {
      setShowDialog(true)
      return
    }

    setExporting(true)
    try {
      const exportData = {
        [`${sourceType}_id`]: sourceId,
        export_format: format,
        limit: 1000
      }

      const response = await api.post('/data-export/export-data', exportData, {
        responseType: 'blob'
      })

      // 创建下载链接
      const blob = new Blob([response.data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      
      const contentDisposition = response.headers['content-disposition']
      let filename = `${sourceName || 'export'}.${format}`
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
    } catch (error: any) {
      console.error('Quick export failed:', error)
      alert(error.response?.data?.detail || 'Export failed')
    } finally {
      setExporting(false)
    }
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button 
            variant={variant} 
            size={size} 
            className={className}
            disabled={exporting}
          >
            {exporting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                Export
                <ChevronDown className="ml-2 h-4 w-4" />
              </>
            )}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuLabel>Quick Export</DropdownMenuLabel>
          <DropdownMenuSeparator />
          
          <DropdownMenuItem onClick={() => quickExport('csv')}>
            <FileText className="mr-2 h-4 w-4" />
            Export as CSV
          </DropdownMenuItem>
          
          <DropdownMenuItem onClick={() => quickExport('json')}>
            <Database className="mr-2 h-4 w-4" />
            Export as JSON
          </DropdownMenuItem>
          
          <DropdownMenuItem onClick={() => quickExport('xlsx')}>
            <Package className="mr-2 h-4 w-4" />
            Export as Excel
          </DropdownMenuItem>
          
          <DropdownMenuSeparator />
          
          <DropdownMenuItem onClick={() => setShowDialog(true)}>
            <Download className="mr-2 h-4 w-4" />
            Advanced Export...
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <EnhancedDataExportDialog
        trigger={null}
        defaultType={sourceType}
        defaultSourceId={sourceId}
        defaultSourceName={sourceName}
      />
    </>
  )
}