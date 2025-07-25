'use client'

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { 
  FileText, 
  Plus, 
  Download, 
  RefreshCw, 
  Trash2, 
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  Play
} from 'lucide-react'
import { useApiCall } from '@/lib/hooks/useApiCall'
import { useErrorNotification } from '@/components/providers/ErrorNotificationProvider'
import { reportApiService } from '@/lib/api/services/report-service'
import { TemplateApiService } from '@/lib/api/services/template-service'
import { enhancedDataSourceApiService } from '@/lib/api/services/enhanced-data-source-service'
import type { ReportHistory, Template, DataSource } from '@/types/api'
import { LoadingSpinner } from '@/components/ui/loading'
import { ErrorSeverity } from '@/lib/error-handler'

interface ReportGenerateFormProps {
  templates: Template[]
  dataSources: DataSource[]
  onGenerate: (templateId: string, dataSourceId: string) => void
  onCancel: () => void
  isLoading?: boolean
}

function ReportGenerateForm({ 
  templates, 
  dataSources, 
  onGenerate, 
  onCancel, 
  isLoading 
}: ReportGenerateFormProps) {
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [selectedDataSource, setSelectedDataSource] = useState<string>('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (selectedTemplate && selectedDataSource) {
      onGenerate(selectedTemplate, selectedDataSource)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Select Template</label>
          <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
            <SelectTrigger>
              <SelectValue placeholder="Choose a template" />
            </SelectTrigger>
            <SelectContent>
              {templates.map((template) => (
                <SelectItem key={template.id} value={template.id}>
                  {template.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Select Data Source</label>
          <Select value={selectedDataSource} onValueChange={setSelectedDataSource}>
            <SelectTrigger>
              <SelectValue placeholder="Choose a data source" />
            </SelectTrigger>
            <SelectContent>
              {dataSources.map((dataSource) => (
                <SelectItem key={dataSource.id} value={dataSource.id}>
                  {dataSource.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex justify-end space-x-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button 
          type="submit" 
          disabled={!selectedTemplate || !selectedDataSource || isLoading}
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Play className="mr-2 h-4 w-4" />
              Generate Report
            </>
          )}
        </Button>
      </div>
    </form>
  )
}

export function ReportManager() {
  const [reports, setReports] = useState<ReportHistory[]>([])
  const [templates, setTemplates] = useState<Template[]>([])
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [isGenerateOpen, setIsGenerateOpen] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const { showToast, showError } = useErrorNotification()

  const templateApi = new TemplateApiService()

  // Load reports
  const loadReportsApi = useApiCall(
    () => reportApiService.getReports(1, 50, statusFilter !== 'all' ? { status: statusFilter } : {}),
    {
      loadingMessage: 'Loading reports...',
      errorContext: 'fetch reports',
      onSuccess: (data) => {
        setReports(data)
      }
    }
  )

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

  // Load data sources
  const loadDataSourcesApi = useApiCall(
    () => enhancedDataSourceApiService.getDataSources(1, 50),
    {
      loadingMessage: 'Loading data sources...',
      errorContext: 'fetch data sources',
      onSuccess: (data) => {
        setDataSources(data)
      }
    }
  )

  // Generate report
  const generateReportApi = useApiCall(
    (data: { templateId: string; dataSourceId: string }) => 
      reportApiService.generateReport({
        template_id: data.templateId,
        data_source_id: data.dataSourceId
      }),
    {
      loadingMessage: 'Generating report...',
      errorContext: 'generate report',
      onSuccess: (result) => {
        showToast({ severity: ErrorSeverity.LOW, title: 'Success', message: 'Report generation started successfully' })
        setIsGenerateOpen(false)
        loadReportsApi.execute()
      }
    }
  )

  // Delete report
  const deleteReportApi = useApiCall(
    (reportId: number) => reportApiService.deleteReport(reportId),
    {
      loadingMessage: 'Deleting report...',
      errorContext: 'delete report',
      onSuccess: () => {
        showToast({ severity: ErrorSeverity.LOW, title: 'Success', message: 'Report deleted successfully' })
        loadReportsApi.execute()
      }
    }
  )

  // Regenerate report
  const regenerateReportApi = useApiCall(
    (reportId: number) => reportApiService.regenerateReport(reportId),
    {
      loadingMessage: 'Regenerating report...',
      errorContext: 'regenerate report',
      onSuccess: () => {
        showToast({ severity: ErrorSeverity.LOW, title: 'Success', message: 'Report regeneration started' })
        loadReportsApi.execute()
      }
    }
  )

  // Download report
  const downloadReportApi = useApiCall(
    (reportId: number) => reportApiService.downloadReport(reportId),
    {
      loadingMessage: 'Preparing download...',
      errorContext: 'download report',
      onSuccess: (result) => {
        // Open download URL in new tab
        window.open(result.download_url, '_blank')
      }
    }
  )

  useEffect(() => {
    loadReportsApi.execute()
    loadTemplatesApi.execute()
    loadDataSourcesApi.execute()
  }, [])

  useEffect(() => {
    loadReportsApi.execute()
  }, [statusFilter])

  const handleGenerateReport = async (templateId: string, dataSourceId: string) => {
    await generateReportApi.execute({ templateId, dataSourceId })
  }

  const handleDeleteReport = async (reportId: number) => {
    if (!confirm('Are you sure you want to delete this report?')) return
    await deleteReportApi.execute(reportId)
  }

  const handleRegenerateReport = async (reportId: number) => {
    if (!confirm('Are you sure you want to regenerate this report?')) return
    await regenerateReportApi.execute(reportId)
  }

  const handleDownloadReport = async (reportId: number) => {
    await downloadReportApi.execute(reportId)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      case 'regenerating': return 'bg-blue-100 text-blue-800'
      case 'failed': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-4 w-4" />
      case 'pending': return <Clock className="h-4 w-4" />
      case 'regenerating': return <RefreshCw className="h-4 w-4 animate-spin" />
      case 'failed': return <AlertCircle className="h-4 w-4" />
      default: return <Clock className="h-4 w-4" />
    }
  }

  // Show loading state
  if (loadReportsApi.isLoading && !loadReportsApi.data) {
    return <LoadingSpinner />
  }

  // Show error state
  if (loadReportsApi.isError && !loadReportsApi.data) {
    return (
      <div className="text-destructive p-4 text-center">
        Failed to load reports
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Report Manager</h2>
          <p className="text-gray-600">Generate and manage your reports</p>
        </div>
        <Button onClick={() => setIsGenerateOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Generate Report
        </Button>
      </div>

      <Tabs defaultValue="reports" className="space-y-4">
        <TabsList>
          <TabsTrigger value="reports">
            <FileText className="w-4 h-4 mr-2" />
            Reports
          </TabsTrigger>
        </TabsList>

        <TabsContent value="reports">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Reports</CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{reports.length}</div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Completed</CardTitle>
                <CheckCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {reports.filter(r => r.status === 'completed').length}
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Pending</CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {reports.filter(r => r.status === 'pending').length}
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Failed</CardTitle>
                <AlertCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {reports.filter(r => r.status === 'failed').length}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Filter */}
          <div className="flex items-center space-x-4 mb-4">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="regenerating">Regenerating</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Report History</CardTitle>
              <CardDescription>
                View and manage your generated reports
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Generated At</TableHead>
                    <TableHead>File Path</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reports.map((report) => (
                    <TableRow key={report.id}>
                      <TableCell className="font-medium">#{report.id}</TableCell>
                      <TableCell>
                        <Badge className={getStatusColor(report.status)}>
                          <div className="flex items-center space-x-1">
                            {getStatusIcon(report.status)}
                            <span>{report.status.toUpperCase()}</span>
                          </div>
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {new Date(report.generated_at).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        {report.file_path ? (
                          <span className="text-sm text-gray-600">{report.file_path}</span>
                        ) : (
                          <span className="text-sm text-gray-400">No file</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          {report.status === 'completed' && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDownloadReport(report.id)}
                              disabled={downloadReportApi.isLoading}
                            >
                              {downloadReportApi.isLoading ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Download className="h-4 w-4" />
                              )}
                            </Button>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleRegenerateReport(report.id)}
                            disabled={regenerateReportApi.isLoading}
                          >
                            {regenerateReportApi.isLoading ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <RefreshCw className="h-4 w-4" />
                            )}
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDeleteReport(report.id)}
                            disabled={deleteReportApi.isLoading}
                            className="text-red-600 hover:text-red-700"
                          >
                            {deleteReportApi.isLoading ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {reports.length === 0 && (
                <div className="text-center py-12">
                  <FileText className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No reports found</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Get started by generating your first report.
                  </p>
                  <div className="mt-6">
                    <Button onClick={() => setIsGenerateOpen(true)}>
                      <Plus className="mr-2 h-4 w-4" />
                      Generate Report
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Generate Report Dialog */}
      <Dialog open={isGenerateOpen} onOpenChange={setIsGenerateOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Generate New Report</DialogTitle>
          </DialogHeader>
          <ReportGenerateForm
            templates={templates}
            dataSources={dataSources}
            onGenerate={handleGenerateReport}
            onCancel={() => setIsGenerateOpen(false)}
            isLoading={generateReportApi.isLoading}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}