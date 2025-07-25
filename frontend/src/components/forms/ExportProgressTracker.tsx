'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  Download, 
  CheckCircle, 
  AlertCircle, 
  Clock,
  Loader2,
  X,
  RefreshCw
} from 'lucide-react'
import api from '@/lib/api'

interface ExportJob {
  id: string
  name: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  created_at: string
  updated_at: string
  file_size?: number
  download_url?: string
  error_message?: string
  metadata?: {
    total_rows?: number
    processed_rows?: number
    estimated_time?: number
  }
}

interface ExportProgressTrackerProps {
  className?: string
  autoRefresh?: boolean
  refreshInterval?: number
  maxItems?: number
}

export function ExportProgressTracker({
  className,
  autoRefresh = true,
  refreshInterval = 2000,
  maxItems = 5
}: ExportProgressTrackerProps) {
  const [exportJobs, setExportJobs] = useState<ExportJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchExportJobs()
    
    if (autoRefresh) {
      const interval = setInterval(fetchExportJobs, refreshInterval)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, refreshInterval])

  const fetchExportJobs = async () => {
    try {
      const response = await api.get('/v1/data-export/active-jobs')
      setExportJobs(response.data?.jobs || [])
      setError(null)
    } catch (err: unknown) {
      console.error('Failed to fetch export jobs:', err)
      setExportJobs([])
      setError(null)
    } finally {
      setLoading(false)
    }
  }

  const cancelExport = async (jobId: string) => {
    try {
      await api.post(`/v1/data-export/cancel/${jobId}`)
      await fetchExportJobs()
    } catch (err: unknown) {
      console.error('Failed to cancel export:', err)
      alert('Failed to cancel export')
    }
  }

  const downloadExport = async (job: ExportJob) => {
    if (!job.download_url) return

    try {
      const response = await api.get(`/v1/data-export/download/${job.id}`, {
        responseType: 'blob'
      })
      const blob = new Blob([response.data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${job.name}.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (err: unknown) {
      console.error('Download failed:', err)
      alert('Download failed')
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      case 'processing':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    const variants = {
      completed: 'default',
      failed: 'destructive',
      processing: 'secondary',
      pending: 'outline'
    } as const
    
    return (
      <Badge variant={variants[status as keyof typeof variants] || 'outline'}>
        {status}
      </Badge>
    )
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A'
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatTimeRemaining = (estimatedTime?: number) => {
    if (!estimatedTime) return 'N/A'
    const minutes = Math.floor(estimatedTime / 60)
    const seconds = estimatedTime % 60
    return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`
  }

  const activeJobs = exportJobs.filter(job => 
    job.status === 'pending' || job.status === 'processing'
  )
  
  const recentJobs = exportJobs
    .filter(job => job.status === 'completed' || job.status === 'failed')
    .slice(0, maxItems - activeJobs.length)

  const displayJobs = [...activeJobs, ...recentJobs].slice(0, maxItems)

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="ml-2">Loading export jobs...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  if (displayJobs.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-lg">Export Progress</CardTitle>
          <CardDescription>Track your data export jobs</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6">
            <Download className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">No active or recent exports</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Export Progress</CardTitle>
            <CardDescription>
              {activeJobs.length > 0 
                ? `${activeJobs.length} active export${activeJobs.length > 1 ? 's' : ''}`
                : 'Recent export jobs'
              }
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchExportJobs}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {displayJobs.map((job) => (
          <div key={job.id} className="border rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {getStatusIcon(job.status)}
                <span className="font-medium">{job.name}</span>
                {getStatusBadge(job.status)}
              </div>
              <div className="flex items-center space-x-2">
                {job.status === 'completed' && job.download_url && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => downloadExport(job)}
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                )}
                {(job.status === 'pending' || job.status === 'processing') && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => cancelExport(job.id)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>

            {job.status === 'processing' && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>Progress: {job.progress}%</span>
                  {job.metadata?.processed_rows && job.metadata?.total_rows && (
                    <span>
                      {job.metadata.processed_rows.toLocaleString()} / {job.metadata.total_rows.toLocaleString()} rows
                    </span>
                  )}
                </div>
                <Progress value={job.progress} className="h-2" />
                {job.metadata?.estimated_time && (
                  <div className="text-sm text-gray-500">
                    Estimated time remaining: {formatTimeRemaining(job.metadata.estimated_time)}
                  </div>
                )}
              </div>
            )}

            {job.status === 'completed' && (
              <div className="flex items-center justify-between text-sm text-gray-600">
                <span>Completed: {new Date(job.updated_at).toLocaleString()}</span>
                <span>Size: {formatFileSize(job.file_size)}</span>
              </div>
            )}

            {job.status === 'failed' && job.error_message && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="text-sm">
                  {job.error_message}
                </AlertDescription>
              </Alert>
            )}

            <div className="text-xs text-gray-500">
              Created: {new Date(job.created_at).toLocaleString()}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}