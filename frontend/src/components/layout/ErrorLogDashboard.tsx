'use client'

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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
  AlertTriangle, 
  Activity, 
  TrendingUp, 
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Info,
  Trash2,
  Download,
  RefreshCw
} from 'lucide-react'
import { errorHandler, ErrorSeverity, ErrorCategory, ErrorReport } from '@/lib/error-handler'
import { apiLogger, LogLevel, ApiLogEntry, ApiMetrics } from '@/lib/api-logger'

export function ErrorLogDashboard() {
  const [errors, setErrors] = useState<ErrorReport[]>([])
  const [apiLogs, setApiLogs] = useState<ApiLogEntry[]>([])
  const [errorStats, setErrorStats] = useState<any>(null)
  const [apiMetrics, setApiMetrics] = useState<ApiMetrics | null>(null)
  const [errorFilter, setErrorFilter] = useState<string>('all')
  const [logFilter, setLogFilter] = useState<string>('all')
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null)

  // Load data
  const loadData = () => {
    setErrors(errorHandler.getErrors())
    setApiLogs(apiLogger.getLogs())
    setErrorStats(errorHandler.getErrorStatistics())
    setApiMetrics(apiLogger.getMetrics())
  }

  useEffect(() => {
    loadData()
    
    // Set up auto-refresh
    const interval = setInterval(loadData, 5000) // Refresh every 5 seconds
    setRefreshInterval(interval)

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [])

  const handleClearErrors = () => {
    if (confirm('Are you sure you want to clear all errors?')) {
      errorHandler.clearErrors()
      loadData()
    }
  }

  const handleClearLogs = () => {
    if (confirm('Are you sure you want to clear all API logs?')) {
      apiLogger.clearLogs()
      loadData()
    }
  }

  const handleResolveError = (errorId: string) => {
    errorHandler.resolveError(errorId)
    loadData()
  }

  const handleExportLogs = () => {
    const data = {
      errors,
      apiLogs,
      errorStats,
      apiMetrics,
      exportedAt: new Date().toISOString()
    }
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `error-logs-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const getSeverityColor = (severity: ErrorSeverity) => {
    switch (severity) {
      case ErrorSeverity.CRITICAL:
        return 'bg-red-100 text-red-800'
      case ErrorSeverity.HIGH:
        return 'bg-orange-100 text-orange-800'
      case ErrorSeverity.MEDIUM:
        return 'bg-yellow-100 text-yellow-800'
      case ErrorSeverity.LOW:
        return 'bg-blue-100 text-blue-800'
    }
  }

  const getCategoryColor = (category: ErrorCategory) => {
    switch (category) {
      case ErrorCategory.NETWORK:
        return 'bg-purple-100 text-purple-800'
      case ErrorCategory.AUTHENTICATION:
        return 'bg-red-100 text-red-800'
      case ErrorCategory.VALIDATION:
        return 'bg-yellow-100 text-yellow-800'
      case ErrorCategory.BUSINESS_LOGIC:
        return 'bg-blue-100 text-blue-800'
      case ErrorCategory.UI:
        return 'bg-green-100 text-green-800'
      case ErrorCategory.SYSTEM:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return 'text-green-600'
    if (status >= 300 && status < 400) return 'text-blue-600'
    if (status >= 400 && status < 500) return 'text-yellow-600'
    if (status >= 500) return 'text-red-600'
    return 'text-gray-600'
  }

  const filteredErrors = errors.filter(error => {
    if (errorFilter === 'all') return true
    if (errorFilter === 'unresolved') return !error.resolved
    if (errorFilter === 'resolved') return error.resolved
    return error.severity === errorFilter || error.category === errorFilter
  })

  const filteredLogs = apiLogs.filter(log => {
    if (logFilter === 'all') return true
    if (logFilter === 'errors') return log.error || (log.responseStatus && log.responseStatus >= 400)
    if (logFilter === 'slow') return log.duration > 2000
    return log.method === logFilter
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Error & Log Dashboard</h2>
          <p className="text-gray-600">Monitor application errors and API performance</p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" onClick={loadData}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button variant="outline" onClick={handleExportLogs}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">
            <TrendingUp className="w-4 h-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="errors">
            <AlertTriangle className="w-4 h-4 mr-2" />
            Errors
          </TabsTrigger>
          <TabsTrigger value="api-logs">
            <Activity className="w-4 h-4 mr-2" />
            API Logs
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Errors</CardTitle>
                <AlertTriangle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{errorStats?.total || 0}</div>
                <p className="text-xs text-muted-foreground">
                  {errorStats?.unresolved || 0} unresolved
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">API Requests</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{apiMetrics?.totalRequests || 0}</div>
                <p className="text-xs text-muted-foreground">
                  {((apiMetrics?.errorRate || 0) * 100).toFixed(1)}% error rate
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {apiMetrics?.averageResponseTime ? `${apiMetrics.averageResponseTime.toFixed(0)}ms` : '0ms'}
                </div>
                <p className="text-xs text-muted-foreground">
                  Last 24 hours
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
                <CheckCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {apiMetrics ? `${((1 - apiMetrics.errorRate) * 100).toFixed(1)}%` : '100%'}
                </div>
                <p className="text-xs text-muted-foreground">
                  {apiMetrics?.successfulRequests || 0} successful
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Error Distribution</CardTitle>
                <CardDescription>Errors by severity and category</CardDescription>
              </CardHeader>
              <CardContent>
                {errorStats && (
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-sm font-medium mb-2">By Severity</h4>
                      <div className="space-y-2">
                        {Object.entries(errorStats.bySeverity).map(([severity, count]) => (
                          <div key={severity} className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <Badge className={getSeverityColor(severity as ErrorSeverity)}>
                                {severity.toUpperCase()}
                              </Badge>
                            </div>
                            <span className="font-medium">{String(count)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="text-sm font-medium mb-2">By Category</h4>
                      <div className="space-y-2">
                        {Object.entries(errorStats.byCategory).map(([category, count]) => (
                          <div key={category} className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <Badge className={getCategoryColor(category as ErrorCategory)}>
                                {category.replace('_', ' ').toUpperCase()}
                              </Badge>
                            </div>
                            <span className="font-medium">{String(count)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>API Performance</CardTitle>
                <CardDescription>Request statistics and performance metrics</CardDescription>
              </CardHeader>
              <CardContent>
                {apiMetrics && (
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-sm font-medium mb-2">By Method</h4>
                      <div className="space-y-2">
                        {Object.entries(apiMetrics.requestsByMethod).map(([method, count]) => (
                          <div key={method} className="flex items-center justify-between">
                            <Badge variant="outline">{method}</Badge>
                            <span className="font-medium">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="text-sm font-medium mb-2">Response Times</h4>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Fastest</span>
                          <span className="font-medium">
                            {apiMetrics.fastestRequest ? `${apiMetrics.fastestRequest.duration}ms` : 'N/A'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Slowest</span>
                          <span className="font-medium">
                            {apiMetrics.slowestRequest ? `${apiMetrics.slowestRequest.duration}ms` : 'N/A'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="errors">
          <div className="flex items-center justify-between mb-4">
            <Select value={errorFilter} onValueChange={setErrorFilter}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Errors</SelectItem>
                <SelectItem value="unresolved">Unresolved</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
                <SelectItem value={ErrorSeverity.CRITICAL}>Critical</SelectItem>
                <SelectItem value={ErrorSeverity.HIGH}>High</SelectItem>
                <SelectItem value={ErrorSeverity.MEDIUM}>Medium</SelectItem>
                <SelectItem value={ErrorSeverity.LOW}>Low</SelectItem>
              </SelectContent>
            </Select>
            
            <Button variant="outline" onClick={handleClearErrors}>
              <Trash2 className="mr-2 h-4 w-4" />
              Clear All
            </Button>
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Message</TableHead>
                    <TableHead>Component</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredErrors.map((error) => (
                    <TableRow key={error.id}>
                      <TableCell className="text-sm">
                        {new Date(error.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Badge className={getSeverityColor(error.severity)}>
                          {error.severity.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={getCategoryColor(error.category)}>
                          {error.category.replace('_', ' ').toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-xs">
                        <div className="truncate" title={error.message}>
                          {error.message}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm">
                        {error.context.component || 'Unknown'}
                      </TableCell>
                      <TableCell>
                        {error.resolved ? (
                          <CheckCircle className="h-4 w-4 text-green-600" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-600" />
                        )}
                      </TableCell>
                      <TableCell>
                        {!error.resolved && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleResolveError(error.id)}
                          >
                            Resolve
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {filteredErrors.length === 0 && (
                <div className="text-center py-12">
                  <CheckCircle className="mx-auto h-12 w-12 text-green-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No errors found</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    {errorFilter === 'all' ? 'Great! No errors to display.' : 'No errors match the current filter.'}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="api-logs">
          <div className="flex items-center justify-between mb-4">
            <Select value={logFilter} onValueChange={setLogFilter}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Requests</SelectItem>
                <SelectItem value="errors">Errors Only</SelectItem>
                <SelectItem value="slow">Slow Requests</SelectItem>
                <SelectItem value="GET">GET Requests</SelectItem>
                <SelectItem value="POST">POST Requests</SelectItem>
                <SelectItem value="PUT">PUT Requests</SelectItem>
                <SelectItem value="DELETE">DELETE Requests</SelectItem>
              </SelectContent>
            </Select>
            
            <Button variant="outline" onClick={handleClearLogs}>
              <Trash2 className="mr-2 h-4 w-4" />
              Clear All
            </Button>
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Method</TableHead>
                    <TableHead>URL</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Error</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredLogs.slice(0, 100).map((log) => (
                    <TableRow key={log.id}>
                      <TableCell className="text-sm">
                        {new Date(log.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{log.method}</Badge>
                      </TableCell>
                      <TableCell className="max-w-xs">
                        <div className="truncate" title={log.url}>
                          {log.url}
                        </div>
                      </TableCell>
                      <TableCell>
                        {log.responseStatus ? (
                          <span className={getStatusColor(log.responseStatus)}>
                            {log.responseStatus}
                          </span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className={log.duration > 2000 ? 'text-red-600' : log.duration > 1000 ? 'text-yellow-600' : 'text-green-600'}>
                          {log.duration}ms
                        </span>
                      </TableCell>
                      <TableCell>
                        {log.error ? (
                          <div className="flex items-center space-x-1">
                            <AlertCircle className="h-4 w-4 text-red-600" />
                            <span className="text-sm text-red-600 truncate max-w-xs" title={log.error}>
                              {log.error}
                            </span>
                          </div>
                        ) : (
                          <CheckCircle className="h-4 w-4 text-green-600" />
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {filteredLogs.length === 0 && (
                <div className="text-center py-12">
                  <Activity className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No API logs found</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    {logFilter === 'all' ? 'No API requests have been made yet.' : 'No requests match the current filter.'}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}