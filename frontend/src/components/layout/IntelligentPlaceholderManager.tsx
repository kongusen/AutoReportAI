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
  Brain, 
  Search, 
  Zap, 
  Target,
  TrendingUp,
  FileText,
  Database,
  CheckCircle,
  AlertCircle,
  Clock
} from 'lucide-react'
import { useApiCall } from '@/lib/hooks/useApiCall'
import { useErrorNotification } from '@/components/providers/ErrorNotificationProvider'
import { PlaceholderApiService } from '@/lib/api/services/placeholder-service'
import { TemplateApiService } from '@/lib/api/services/template-service'
import { enhancedDataSourceApiService } from '@/lib/api/services/enhanced-data-source-service'
import type { Template, DataSource, PlaceholderInfo, FieldSuggestion } from '@/types/api'
import { LoadingSpinner } from '@/components/ui/loading'
import { ErrorSeverity } from '@/lib/error-handler'

interface PlaceholderAnalysisProps {
  templates: Template[]
  dataSources: DataSource[]
  onAnalyze: (templateId: string) => void
  onFieldMatch: (templateId: string, dataSourceId: string, placeholderName: string) => void
  isLoading?: boolean
}

function PlaceholderAnalysisForm({ 
  templates, 
  dataSources, 
  onAnalyze, 
  onFieldMatch, 
  isLoading 
}: PlaceholderAnalysisProps) {
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [selectedDataSource, setSelectedDataSource] = useState<string>('')
  const [selectedPlaceholder, setSelectedPlaceholder] = useState<string>('')

  const handleAnalyze = () => {
    if (selectedTemplate) {
      onAnalyze(selectedTemplate)
    }
  }

  const handleFieldMatch = () => {
    if (selectedTemplate && selectedDataSource && selectedPlaceholder) {
      onFieldMatch(selectedTemplate, selectedDataSource, selectedPlaceholder)
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Select Template</label>
          <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
            <SelectTrigger>
              <SelectValue placeholder="Choose a template to analyze" />
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

        <Button 
          onClick={handleAnalyze}
          disabled={!selectedTemplate || isLoading}
          className="w-full"
        >
          <Search className="mr-2 h-4 w-4" />
          Analyze Placeholders
        </Button>
      </div>

      <div className="border-t pt-6">
        <h3 className="text-lg font-medium mb-4">Field Matching</h3>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Data Source</label>
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

          <div className="space-y-2">
            <label className="text-sm font-medium">Placeholder Name</label>
            <input
              type="text"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="Enter placeholder name (e.g., customer_name)"
              value={selectedPlaceholder}
              onChange={(e) => setSelectedPlaceholder(e.target.value)}
            />
          </div>

          <Button 
            onClick={handleFieldMatch}
            disabled={!selectedTemplate || !selectedDataSource || !selectedPlaceholder || isLoading}
            className="w-full"
          >
            <Target className="mr-2 h-4 w-4" />
            Match Fields
          </Button>
        </div>
      </div>
    </div>
  )
}

export function IntelligentPlaceholderManager() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [analysisResults, setAnalysisResults] = useState<PlaceholderInfo[]>([])
  const [fieldSuggestions, setFieldSuggestions] = useState<FieldSuggestion[]>([])
  const [statistics, setStatistics] = useState<any>(null)
  const [isAnalysisOpen, setIsAnalysisOpen] = useState(false)
  const { showToast, showError } = useErrorNotification()

  const placeholderApi = new PlaceholderApiService()
  const templateApi = new TemplateApiService()

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

  // Load statistics
  const loadStatisticsApi = useApiCall(
    () => placeholderApi.getStatistics(),
    {
      loadingMessage: 'Loading statistics...',
      errorContext: 'fetch statistics',
      onSuccess: (data) => {
        setStatistics(data)
      }
    }
  )

  // Analyze template
  const analyzeTemplateApi = useApiCall(
    (templateId: string) => placeholderApi.analyzeTemplate(templateId),
    {
      loadingMessage: 'Analyzing template...',
      errorContext: 'analyze template',
      onSuccess: (data) => {
        setAnalysisResults(data.placeholders)
        showToast({ severity: 'low' as ErrorSeverity, title: 'Success', message: `Found ${data.placeholders.length} placeholders` })
      }
    }
  )

  // Match fields
  const matchFieldsApi = useApiCall(
    (data: { templateId: string; dataSourceId: string; placeholderName: string }) => 
      placeholderApi.matchPlaceholderFields(data.templateId, data.dataSourceId, data.placeholderName),
    {
      loadingMessage: 'Matching fields...',
      errorContext: 'match fields',
      onSuccess: (data) => {
        setFieldSuggestions(data.field_suggestions)
        showToast({ severity: 'low' as ErrorSeverity, title: 'Success', message: `Found ${data.field_suggestions.length} field suggestions` })
      }
    }
  )

  useEffect(() => {
    loadTemplatesApi.execute()
    loadDataSourcesApi.execute()
    loadStatisticsApi.execute()
  }, [])

  const handleAnalyzeTemplate = async (templateId: string) => {
    await analyzeTemplateApi.execute(templateId)
  }

  const handleFieldMatch = async (templateId: string, dataSourceId: string, placeholderName: string) => {
    await matchFieldsApi.execute({ templateId, dataSourceId, placeholderName })
  }

  const getPlaceholderTypeColor = (type: string) => {
    switch (type) {
      case 'text': return 'bg-blue-100 text-blue-800'
      case 'number': return 'bg-green-100 text-green-800'
      case 'date': return 'bg-purple-100 text-purple-800'
      case 'image': return 'bg-orange-100 text-orange-800'
      case 'table': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600'
    if (confidence >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  // Show loading state
  if (loadTemplatesApi.isLoading && !loadTemplatesApi.data) {
    return <LoadingSpinner />
  }

  // Show error state
  if (loadTemplatesApi.isError && !loadTemplatesApi.data) {
    return (
      <div className="text-destructive p-4 text-center">
        Failed to load templates
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Intelligent Placeholders</h2>
          <p className="text-gray-600">Analyze and match template placeholders with data sources</p>
        </div>
        <Button onClick={() => setIsAnalysisOpen(true)}>
          <Brain className="mr-2 h-4 w-4" />
          Analyze Template
        </Button>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">
            <TrendingUp className="w-4 h-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="analysis">
            <Search className="w-4 h-4 mr-2" />
            Analysis Results
          </TabsTrigger>
          <TabsTrigger value="matching">
            <Target className="w-4 h-4 mr-2" />
            Field Matching
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          {statistics && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Templates Analyzed</CardTitle>
                  <FileText className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{statistics.total_templates_analyzed}</div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Placeholders Found</CardTitle>
                  <Zap className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{statistics.total_placeholders_found}</div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Accuracy Rate</CardTitle>
                  <Target className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{(statistics.accuracy_rate * 100).toFixed(1)}%</div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Avg Processing Time</CardTitle>
                  <Clock className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{statistics.processing_time_avg}s</div>
                </CardContent>
              </Card>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Placeholder Types Distribution</CardTitle>
                <CardDescription>
                  Most common placeholder types found in templates
                </CardDescription>
              </CardHeader>
              <CardContent>
                {statistics && (
                  <div className="space-y-3">
                    {Object.entries(statistics.most_common_types).map(([type, count]) => (
                      <div key={type} className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <Badge className={getPlaceholderTypeColor(type)}>
                            {type.toUpperCase()}
                          </Badge>
                          <span className="text-sm">{type}</span>
                        </div>
                        <span className="font-medium">{String(count)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
                <CardDescription>
                  Latest template analysis activities
                </CardDescription>
              </CardHeader>
              <CardContent>
                {statistics && (
                  <div className="space-y-3">
                    {statistics.recent_activity.map((activity: any, index: number) => (
                      <div key={index} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                        <div className="flex-shrink-0 mt-1">
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium">{activity.template_name}</p>
                          <p className="text-xs text-gray-500">
                            {activity.placeholders_count} placeholders found
                          </p>
                          <p className="text-xs text-gray-400">
                            {new Date(activity.processed_at).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="analysis">
          <Card>
            <CardHeader>
              <CardTitle>Placeholder Analysis Results</CardTitle>
              <CardDescription>
                Detailed analysis of placeholders found in templates
              </CardDescription>
            </CardHeader>
            <CardContent>
              {analysisResults.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Placeholder</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Confidence</TableHead>
                      <TableHead>Context</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {analysisResults.map((placeholder, index) => (
                      <TableRow key={index}>
                        <TableCell className="font-mono">
                          {placeholder.placeholder_text}
                        </TableCell>
                        <TableCell>
                          <Badge className={getPlaceholderTypeColor(placeholder.placeholder_type)}>
                            {placeholder.placeholder_type.toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-xs">
                          <div className="truncate" title={placeholder.description}>
                            {placeholder.description}
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className={getConfidenceColor(placeholder.confidence)}>
                            {(placeholder.confidence * 100).toFixed(0)}%
                          </span>
                        </TableCell>
                        <TableCell className="max-w-xs">
                          <div className="text-xs text-gray-500 truncate">
                            ...{placeholder.context_before}
                            <span className="font-bold">{placeholder.placeholder_text}</span>
                            {placeholder.context_after}...
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-12">
                  <Search className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No analysis results</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Analyze a template to see placeholder results here.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="matching">
          <Card>
            <CardHeader>
              <CardTitle>Field Matching Results</CardTitle>
              <CardDescription>
                Suggested field mappings for placeholders
              </CardDescription>
            </CardHeader>
            <CardContent>
              {fieldSuggestions.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Field Name</TableHead>
                      <TableHead>Match Score</TableHead>
                      <TableHead>Reason</TableHead>
                      <TableHead>Validation Rules</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {fieldSuggestions.map((suggestion, index) => (
                      <TableRow key={index}>
                        <TableCell className="font-medium">
                          {suggestion.field_name}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            <div className="w-16 bg-gray-200 rounded-full h-2">
                              <div 
                                className="bg-blue-600 h-2 rounded-full" 
                                style={{ width: `${suggestion.match_score * 100}%` }}
                              ></div>
                            </div>
                            <span className="text-sm">
                              {(suggestion.match_score * 100).toFixed(0)}%
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="max-w-xs">
                          <div className="truncate" title={suggestion.match_reason}>
                            {suggestion.match_reason}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            {suggestion.validation_rules.map((rule, ruleIndex) => (
                              <Badge key={ruleIndex} variant="outline" className="text-xs">
                                {rule}
                              </Badge>
                            ))}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-12">
                  <Target className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No field matching results</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Use the field matching feature to see suggestions here.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Analysis Dialog */}
      <Dialog open={isAnalysisOpen} onOpenChange={setIsAnalysisOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Intelligent Placeholder Analysis</DialogTitle>
          </DialogHeader>
          <PlaceholderAnalysisForm
            templates={templates}
            dataSources={dataSources}
            onAnalyze={handleAnalyzeTemplate}
            onFieldMatch={handleFieldMatch}
            isLoading={analyzeTemplateApi.isLoading || matchFieldsApi.isLoading}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}