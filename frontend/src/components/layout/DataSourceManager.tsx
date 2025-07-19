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
import { 
  Database, 
  Plus, 
  TestTube, 
  Eye, 
  Edit, 
  Trash2, 
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  Settings
} from 'lucide-react'
import api from '@/lib/api'

interface DataSource {
  id: number
  name: string
  source_type: 'sql' | 'csv' | 'api'
  connection_string?: string
  file_path?: string
  api_url?: string
  is_active: boolean
  last_sync_time?: string
  created_at: string
}

interface ConnectionTest {
  success: boolean
  message: string
  timestamp: string
  error?: string
}

interface DataPreview {
  columns: string[]
  data: any[]
  row_count: number
  total_columns: number
  data_types: Record<string, string>
}

export function DataSourceManager() {
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedSource, setSelectedSource] = useState<DataSource | null>(null)
  const [testResults, setTestResults] = useState<Record<number, ConnectionTest>>({})
  const [previewData, setPreviewData] = useState<DataPreview | null>(null)
  const [isPreviewOpen, setIsPreviewOpen] = useState(false)
  const [testingConnections, setTestingConnections] = useState<Set<number>>(new Set())
  const [previewingData, setPreviewingData] = useState<Set<number>>(new Set())

  useEffect(() => {
    fetchDataSources()
  }, [])

  const fetchDataSources = async () => {
    try {
      setLoading(true)
      const response = await api.get('/enhanced-data-sources')
      setDataSources(Array.isArray(response.data) ? response.data : (response.data.items || []))
    } catch (error) {
      console.error('Failed to fetch data sources:', error)
    } finally {
      setLoading(false)
    }
  }

  const testConnection = async (sourceId: number) => {
    setTestingConnections(prev => new Set(prev).add(sourceId))
    
    try {
      const response = await api.post(`/enhanced-data-sources/${sourceId}/test`)
      setTestResults(prev => ({
        ...prev,
        [sourceId]: response.data
      }))
    } catch (error: any) {
      setTestResults(prev => ({
        ...prev,
        [sourceId]: {
          success: false,
          message: 'Connection test failed',
          timestamp: new Date().toISOString(),
          error: error.response?.data?.detail || error.message
        }
      }))
    } finally {
      setTestingConnections(prev => {
        const newSet = new Set(prev)
        newSet.delete(sourceId)
        return newSet
      })
    }
  }

  const previewSourceData = async (sourceId: number) => {
    setPreviewingData(prev => new Set(prev).add(sourceId))
    
    try {
      const response = await api.get(`/enhanced-data-sources/${sourceId}/preview?limit=10`)
      setPreviewData(response.data)
      setIsPreviewOpen(true)
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to preview data')
    } finally {
      setPreviewingData(prev => {
        const newSet = new Set(prev)
        newSet.delete(sourceId)
        return newSet
      })
    }
  }

  const deleteDataSource = async (sourceId: number) => {
    if (!confirm('Are you sure you want to delete this data source?')) return
    
    try {
      await api.delete(`/enhanced-data-sources/${sourceId}`)
      setDataSources(prev => prev.filter(source => source.id !== sourceId))
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to delete data source')
    }
  }

  const getSourceTypeColor = (type: string) => {
    switch (type) {
      case 'sql': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'csv': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'api': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    }
  }

  const getConnectionStatus = (sourceId: number) => {
    const result = testResults[sourceId]
    if (!result) return null

    if (result.success) {
      return (
        <div className="flex items-center space-x-1 text-green-600">
          <CheckCircle className="h-4 w-4" />
          <span className="text-xs">Connected</span>
        </div>
      )
    } else {
      return (
        <div className="flex items-center space-x-1 text-red-600">
          <AlertCircle className="h-4 w-4" />
          <span className="text-xs">Failed</span>
        </div>
      )
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading data sources...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Data Source Manager</h2>
          <p className="text-gray-600">Manage and monitor your data connections</p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Add Data Source
        </Button>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">
            <Database className="w-4 h-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="monitoring">
            <Settings className="w-4 h-4 mr-2" />
            Monitoring
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Sources</CardTitle>
                <Database className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{dataSources.length}</div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Active Sources</CardTitle>
                <CheckCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {dataSources.filter(s => s.is_active).length}
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Connected</CardTitle>
                <TestTube className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {Object.values(testResults).filter(r => r.success).length}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Data Sources</CardTitle>
              <CardDescription>
                Manage your data source connections and configurations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Connection</TableHead>
                    <TableHead>Last Sync</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dataSources.map((source) => (
                    <TableRow key={source.id}>
                      <TableCell className="font-medium">{source.name}</TableCell>
                      <TableCell>
                        <Badge className={getSourceTypeColor(source.source_type)}>
                          {source.source_type.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={source.is_active ? 'default' : 'secondary'}>
                          {source.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {testingConnections.has(source.id) ? (
                          <div className="flex items-center space-x-1">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span className="text-xs">Testing...</span>
                          </div>
                        ) : (
                          getConnectionStatus(source.id) || (
                            <span className="text-xs text-gray-500">Not tested</span>
                          )
                        )}
                      </TableCell>
                      <TableCell>
                        {source.last_sync_time ? (
                          <span className="text-xs text-gray-500">
                            {new Date(source.last_sync_time).toLocaleString()}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400">Never</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => testConnection(source.id)}
                            disabled={testingConnections.has(source.id)}
                          >
                            <TestTube className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => previewSourceData(source.id)}
                            disabled={previewingData.has(source.id)}
                          >
                            {previewingData.has(source.id) ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => deleteDataSource(source.id)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="monitoring">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Connection Health</CardTitle>
                <CardDescription>
                  Real-time connection status for all data sources
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {dataSources.map((source) => {
                    const result = testResults[source.id]
                    return (
                      <div key={source.id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center space-x-3">
                          <Badge className={getSourceTypeColor(source.source_type)}>
                            {source.source_type}
                          </Badge>
                          <span className="font-medium">{source.name}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          {result ? (
                            result.success ? (
                              <CheckCircle className="h-5 w-5 text-green-500" />
                            ) : (
                              <AlertCircle className="h-5 w-5 text-red-500" />
                            )
                          ) : (
                            <Clock className="h-5 w-5 text-gray-400" />
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => testConnection(source.id)}
                            disabled={testingConnections.has(source.id)}
                          >
                            {testingConnections.has(source.id) ? 'Testing...' : 'Test'}
                          </Button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
                <CardDescription>
                  Latest data source operations and sync activities
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(testResults).map(([sourceId, result]) => {
                    const source = dataSources.find(s => s.id === parseInt(sourceId))
                    if (!source) return null

                    return (
                      <div key={sourceId} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                        <div className="flex-shrink-0 mt-1">
                          {result.success ? (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          ) : (
                            <AlertCircle className="h-4 w-4 text-red-500" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium">{source.name}</p>
                          <p className="text-xs text-gray-500">{result.message}</p>
                          <p className="text-xs text-gray-400">
                            {new Date(result.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Data Preview Dialog */}
      <Dialog open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
        <DialogContent className="sm:max-w-[800px]">
          <DialogHeader>
            <DialogTitle>Data Preview</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            {previewData && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="font-medium">Rows:</span> {previewData.row_count}
                  </div>
                  <div>
                    <span className="font-medium">Columns:</span> {previewData.total_columns}
                  </div>
                </div>
                
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {previewData.columns.map((column) => (
                          <TableHead key={column}>
                            <div>
                              <div className="font-medium">{column}</div>
                              <div className="text-xs text-gray-500">
                                {previewData.data_types[column] || 'unknown'}
                              </div>
                            </div>
                          </TableHead>
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