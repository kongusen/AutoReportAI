'use client'

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { 
  Search, 
  Settings,
  CheckCircle,
  AlertCircle,
  XCircle,
  Database,
  FileText,
  BarChart3,
  Calendar,
  MapPin,
  Hash,
  Loader2
} from 'lucide-react'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { httpClient } from '@/lib/api/client'
import axios from 'axios';

// Types
interface PlaceholderInfo {
  placeholder_text: string
  placeholder_type: string
  description: string
  position: number
  context_before: string
  context_after: string
  confidence: number
}

interface PlaceholderAnalysisResponse {
  success: boolean
  placeholders: PlaceholderInfo[]
  total_count: number
  type_distribution: Record<string, number>
  validation_result: Record<string, unknown>
  processing_errors: Array<Record<string, unknown>>
  estimated_processing_time: number
}

interface DataSource {
  id: number
  name: string
  source_type: string
}

interface Template {
  id: string
  name: string
  content: string
}

interface PlaceholderAnalyzerProps {
  templateId?: string
  dataSourceId?: number
  onAnalysisComplete?: (result: PlaceholderAnalysisResponse) => void
  onPlaceholderSelect?: (placeholder: PlaceholderInfo) => void
}

export function PlaceholderAnalyzer({ 
  templateId, 
  dataSourceId, 
  onAnalysisComplete,
  onPlaceholderSelect
}: PlaceholderAnalyzerProps) {
  // State management
  const [template, setTemplate] = useState<Template | null>(null)
  const [templateContent, setTemplateContent] = useState('')
  const [selectedDataSource, setSelectedDataSource] = useState<number | null>(dataSourceId || null)
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  
  // Analysis state
  const [analysisResult, setAnalysisResult] = useState<PlaceholderAnalysisResponse | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  
  // Analysis options
  const [includeContext, setIncludeContext] = useState(true)
  const [enableCaching, setEnableCaching] = useState(true)
  const [qualityCheck, setQualityCheck] = useState(true)
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.7)

  // Load initial data
  React.useEffect(() => {
    loadDataSources()
    if (templateId) {
      loadTemplate(templateId)
    }
  }, [templateId])

  const loadDataSources = async () => {
    try {
      const response = await httpClient.get('/enhanced-data-sources/')
      setDataSources(response.data)
    } catch (error) {
      console.error('Failed to load data sources:', error)
    }
  }

  const loadTemplate = async (id: string) => {
    try {
      const response = await httpClient.get(`/templates/${id}`)
      const templateData = response.data
      setTemplate(templateData)
      setTemplateContent(templateData.content || '')
    } catch (error) {
      console.error('Failed to load template:', error)
    }
  }

  // Placeholder analysis
  const analyzePlaceholders = async () => {
    if (!templateContent.trim()) {
      alert('请输入模板内容')
      return
    }

    setAnalyzing(true)
    try {
      const response = await httpClient.post('/intelligent-placeholders/analyze', {
        template_content: templateContent,
        template_id: templateId,
        data_source_id: selectedDataSource,
        analysis_options: {
          include_context: includeContext,
          confidence_threshold: confidenceThreshold,
          enable_caching: enableCaching,
          quality_check: qualityCheck
        }
      })
      
      setAnalysisResult(response.data)
      if (onAnalysisComplete) {
        onAnalysisComplete(response.data)
      }
    } catch (error: unknown) {
      console.error('Placeholder analysis failed:', error)
      if (axios.isAxiosError(error)) {
        alert(error.response?.data?.detail || '占位符分析失败')
      } else if (error instanceof Error) {
        alert(error.message || '占位符分析失败')
      } else {
        alert('占位符分析失败')
      }
    } finally {
      setAnalyzing(false)
    }
  }

  // Helper functions
  const getPlaceholderTypeIcon = (type: string) => {
    switch (type) {
      case '统计': return <Hash className="w-4 h-4" />
      case '周期': return <Calendar className="w-4 h-4" />
      case '区域': return <MapPin className="w-4 h-4" />
      case '图表': return <BarChart3 className="w-4 h-4" />
      default: return <FileText className="w-4 h-4" />
    }
  }

  const getPlaceholderTypeColor = (type: string) => {
    const colors = {
      '统计': 'bg-blue-100 text-blue-800',
      '周期': 'bg-purple-100 text-purple-800',
      '区域': 'bg-green-100 text-green-800',
      '图表': 'bg-orange-100 text-orange-800'
    }
    return colors[type as keyof typeof colors] || 'bg-gray-100 text-gray-800'
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600'
    if (confidence >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 0.8) return <CheckCircle className="w-4 h-4 text-green-600" />
    if (confidence >= 0.6) return <AlertCircle className="w-4 h-4 text-yellow-600" />
    return <XCircle className="w-4 h-4 text-red-600" />
  }

  return (
    <div className="space-y-6">
      {/* Configuration Panel */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Settings className="w-5 h-5 mr-2" />
            分析配置
          </CardTitle>
          <CardDescription>
            配置模板内容和数据源以进行智能分析
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Template Content */}
            <div className="space-y-4">
              <div>
                <Label htmlFor="template-content">模板内容</Label>
                <Textarea
                  id="template-content"
                  value={templateContent}
                  onChange={(e) => setTemplateContent(e.target.value)}
                  placeholder="输入包含{{类型:描述}}格式占位符的模板内容..."
                  className="min-h-[200px] font-mono text-sm"
                />
              </div>
              {template && (
                <div className="text-sm text-gray-600">
                  <p>模板: {template.name}</p>
                  <p>ID: {template.id}</p>
                </div>
              )}
            </div>

            {/* Data Source Selection */}
            <div className="space-y-4">
              <div>
                <Label htmlFor="data-source">数据源</Label>
                <Select 
                  value={selectedDataSource?.toString() || ''} 
                  onValueChange={(value) => setSelectedDataSource(parseInt(value))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择数据源" />
                  </SelectTrigger>
                  <SelectContent>
                    {dataSources.map((ds) => (
                      <SelectItem key={ds.id} value={ds.id.toString()}>
                        <div className="flex items-center">
                          <Database className="w-4 h-4 mr-2" />
                          {ds.name} ({ds.source_type})
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Analysis Options */}
              <div className="space-y-3">
                <Label>分析选项</Label>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">包含上下文分析</span>
                    <Switch 
                      checked={includeContext}
                      onCheckedChange={setIncludeContext}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">启用字段缓存</span>
                    <Switch 
                      checked={enableCaching}
                      onCheckedChange={setEnableCaching}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">质量检查</span>
                    <Switch 
                      checked={qualityCheck}
                      onCheckedChange={setQualityCheck}
                    />
                  </div>
                </div>
                
                <div>
                  <Label htmlFor="confidence-threshold">
                    置信度阈值: {confidenceThreshold}
                  </Label>
                  <input
                    type="range"
                    min="0.5"
                    max="1.0"
                    step="0.1"
                    value={confidenceThreshold}
                    onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>
              </div>
            </div>
          </div>
          
          <div className="mt-6 flex justify-end">
            <Button 
              onClick={analyzePlaceholders} 
              disabled={analyzing || !templateContent.trim()}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {analyzing ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Search className="w-4 h-4 mr-2" />
              )}
              {analyzing ? '分析中...' : '分析占位符'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Analysis Results */}
      {analysisResult && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>分析结果</CardTitle>
                <CardDescription>
                  识别的占位符列表和分析结果
                </CardDescription>
              </div>
              <div className="flex items-center space-x-4 text-sm">
                <span>总计: {analysisResult.total_count}</span>
                <span>预估时间: {analysisResult.estimated_processing_time}秒</span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* Type Distribution */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold mb-3">类型分布</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(analysisResult.type_distribution).map(([type, count]) => (
                  <Badge key={type} className={getPlaceholderTypeColor(type)}>
                    {getPlaceholderTypeIcon(type)}
                    <span className="ml-1">{type}: {count}</span>
                  </Badge>
                ))}
              </div>
            </div>

            {/* Placeholders List */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">占位符详情</h3>
              {analysisResult.placeholders.map((placeholder, index) => (
                <Card 
                  key={index} 
                  className="border-l-4 border-l-blue-500 cursor-pointer hover:bg-gray-50"
                  onClick={() => onPlaceholderSelect?.(placeholder)}
                >
                  <CardContent className="pt-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <Badge className={getPlaceholderTypeColor(placeholder.placeholder_type)}>
                            {getPlaceholderTypeIcon(placeholder.placeholder_type)}
                            <span className="ml-1">{placeholder.placeholder_type}</span>
                          </Badge>
                          <div className="flex items-center space-x-1">
                            {getConfidenceIcon(placeholder.confidence)}
                            <span className={`text-sm font-medium ${getConfidenceColor(placeholder.confidence)}`}>
                              {(placeholder.confidence * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                        
                        <div className="space-y-2">
                          <p className="font-mono text-sm bg-gray-100 p-2 rounded">
                            {placeholder.placeholder_text}
                          </p>
                          <p className="text-sm text-gray-600">
                            <strong>描述:</strong> {placeholder.description}
                          </p>
                          <p className="text-sm text-gray-600">
                            <strong>位置:</strong> 第 {placeholder.position} 个字符
                          </p>
                          
                          {/* Context */}
                          <div className="text-sm">
                            <strong>上下文:</strong>
                            <div className="mt-1 p-2 bg-gray-50 rounded text-xs">
                              <span className="text-gray-500">{placeholder.context_before}</span>
                              <span className="bg-yellow-200 px-1 rounded">{placeholder.placeholder_text}</span>
                              <span className="text-gray-500">{placeholder.context_after}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Processing Errors */}
            {analysisResult.processing_errors.length > 0 && (
              <div className="mt-6">
                <h3 className="text-lg font-semibold mb-3 text-red-600">处理错误</h3>
                <div className="space-y-2">
                  {analysisResult.processing_errors.map((error, index) => (
                    <div key={index} className="p-3 bg-red-50 border border-red-200 rounded">
                      <p className="text-sm text-red-800">
                        <strong>{String(error.error_type)}:</strong> {String(error.message)}
                      </p>
                      {typeof error.suggestion === 'string' && error.suggestion && (
                        <p className="text-sm text-red-600 mt-1">
                          <strong>建议:</strong> {String(error.suggestion)}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}