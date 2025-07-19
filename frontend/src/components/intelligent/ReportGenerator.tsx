'use client'

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { 
  Play, 
  Square,
  Settings,
  Database,
  FileText,
  Loader2,
  Zap,
  Mail
} from 'lucide-react'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import apiClient from '@/lib/api-client'

// Types
interface Template {
  id: string
  name: string
  content: string
  template_type: string
}

interface DataSource {
  id: number
  name: string
  source_type: string
}

interface IntelligentProcessingConfig {
  llm_provider: string
  llm_model: string
  enable_caching: boolean
  quality_check: boolean
  auto_optimization: boolean
  confidence_threshold: number
  processing_timeout: number
}

interface ReportOutputConfig {
  format: string
  include_charts: boolean
  include_metadata: boolean
  email_recipients: string[]
  auto_send: boolean
}

interface GeneratedReport {
  id: string
  file_path: string
  file_size: number
  generation_time: number
  quality_score: number
  metadata: Record<string, any>
  preview_content?: string
}

interface ReportGeneratorProps {
  templateId?: string
  dataSourceId?: number
  onReportGenerated?: (report: GeneratedReport) => void
}

export function ReportGenerator({ 
  templateId, 
  dataSourceId, 
  onReportGenerated 
}: ReportGeneratorProps) {
  // State management
  const [templates, setTemplates] = useState<Template[]>([])
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<string>(templateId || '')
  const [selectedDataSource, setSelectedDataSource] = useState<number>(dataSourceId || 0)
  
  // Processing configuration
  const [processingConfig, setProcessingConfig] = useState<IntelligentProcessingConfig>({
    llm_provider: 'openai',
    llm_model: 'gpt-4',
    enable_caching: true,
    quality_check: true,
    auto_optimization: false,
    confidence_threshold: 0.8,
    processing_timeout: 300
  })
  
  const [outputConfig, setOutputConfig] = useState<ReportOutputConfig>({
    format: 'docx',
    include_charts: true,
    include_metadata: true,
    email_recipients: [],
    auto_send: false
  })
  
  // Processing state
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationProgress, setGenerationProgress] = useState(0)
  const [currentStage, setCurrentStage] = useState('')
  const [generatedReport, setGeneratedReport] = useState<GeneratedReport | null>(null)
  
  // Email configuration
  const [emailRecipient, setEmailRecipient] = useState('')

  // Load initial data
  useEffect(() => {
    loadTemplates()
    loadDataSources()
  }, [])

  const loadTemplates = async () => {
    try {
      const response = await apiClient.get('/templates/')
      setTemplates(response.data)
    } catch (error) {
      console.error('Failed to load templates:', error)
    }
  }

  const loadDataSources = async () => {
    try {
      const response = await apiClient.get('/enhanced-data-sources/')
      setDataSources(response.data)
    } catch (error) {
      console.error('Failed to load data sources:', error)
    }
  }

  // Generate intelligent report
  const generateReport = async () => {
    if (!selectedTemplate || !selectedDataSource) {
      alert('请选择模板和数据源')
      return
    }

    setIsGenerating(true)
    setGenerationProgress(0)
    setCurrentStage('初始化...')

    try {
      // Start the intelligent report generation
      const response = await apiClient.post('/intelligent-placeholders/generate-report', {
        template_id: selectedTemplate,
        data_source_id: selectedDataSource,
        processing_config: processingConfig,
        output_config: outputConfig,
        email_config: outputConfig.auto_send ? {
          recipients: outputConfig.email_recipients,
          subject: '智能生成报告',
          include_summary: true
        } : null
      })

      const taskId = response.data.task_id
      
      // Poll for progress updates
      await pollGenerationProgress(taskId)
      
    } catch (error: any) {
      console.error('Report generation failed:', error)
      alert(error.response?.data?.detail || '报告生成失败')
      setIsGenerating(false)
    }
  }

  // Poll generation progress
  const pollGenerationProgress = async (taskId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await apiClient.get(`/intelligent-placeholders/task/${taskId}/status`)
        const status = response.data
        
        setGenerationProgress(status.progress || 0)
        setCurrentStage(status.message || '')
        
        if (status.status === 'completed') {
          clearInterval(pollInterval)
          setIsGenerating(false)
          setGenerationProgress(100)
          setCurrentStage('完成')
          
          // Mock generated report data
          const mockReport: GeneratedReport = {
            id: taskId,
            file_path: '/reports/generated_report.docx',
            file_size: 1024 * 1024, // 1MB
            generation_time: 120, // 2 minutes
            quality_score: 0.92,
            metadata: {
              placeholders_processed: 15,
              llm_provider: processingConfig.llm_provider,
              generation_timestamp: new Date().toISOString()
            }
          }
          
          setGeneratedReport(mockReport)
          
          if (onReportGenerated) {
            onReportGenerated(mockReport)
          }
        } else if (status.status === 'failed') {
          clearInterval(pollInterval)
          setIsGenerating(false)
          alert('报告生成失败')
        }
      } catch (error) {
        console.error('Failed to get progress:', error)
        clearInterval(pollInterval)
        setIsGenerating(false)
      }
    }, 2000)
  }

  // Cancel report generation
  const cancelGeneration = () => {
    setIsGenerating(false)
    setGenerationProgress(0)
    setCurrentStage('')
  }

  // Add email recipient
  const addEmailRecipient = () => {
    if (!emailRecipient.trim() || outputConfig.email_recipients.includes(emailRecipient)) return
    
    setOutputConfig(prev => ({
      ...prev,
      email_recipients: [...prev.email_recipients, emailRecipient.trim()]
    }))
    setEmailRecipient('')
  }

  // Remove email recipient
  const removeEmailRecipient = (email: string) => {
    setOutputConfig(prev => ({
      ...prev,
      email_recipients: prev.email_recipients.filter(e => e !== email)
    }))
  }

  // Download report
  const downloadReport = async () => {
    if (!generatedReport) return
    
    try {
      // Mock download functionality
      alert(`下载报告: ${generatedReport.file_path}`)
    } catch (error) {
      console.error('Failed to download report:', error)
      alert('下载失败')
    }
  }

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Settings className="w-5 h-5 mr-2" />
            报告生成配置
          </CardTitle>
          <CardDescription>
            配置智能报告生成的参数和选项
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Basic Configuration */}
            <div className="space-y-4">
              <div>
                <Label htmlFor="template-select">模板选择</Label>
                <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择报告模板" />
                  </SelectTrigger>
                  <SelectContent>
                    {templates.map((template) => (
                      <SelectItem key={template.id} value={template.id}>
                        <div className="flex items-center">
                          <FileText className="w-4 h-4 mr-2" />
                          {template.name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="datasource-select">数据源选择</Label>
                <Select 
                  value={selectedDataSource.toString()} 
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

              <div>
                <Label htmlFor="output-format">输出格式</Label>
                <Select 
                  value={outputConfig.format} 
                  onValueChange={(value) => setOutputConfig(prev => ({ ...prev, format: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="docx">Word文档 (.docx)</SelectItem>
                    <SelectItem value="pdf">PDF文档 (.pdf)</SelectItem>
                    <SelectItem value="html">HTML网页 (.html)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Advanced Configuration */}
            <div className="space-y-4">
              <div>
                <Label htmlFor="llm-provider">AI提供商</Label>
                <Select 
                  value={processingConfig.llm_provider} 
                  onValueChange={(value) => 
                    setProcessingConfig(prev => ({ ...prev, llm_provider: value }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="openai">OpenAI</SelectItem>
                    <SelectItem value="claude">Claude</SelectItem>
                    <SelectItem value="azure_openai">Azure OpenAI</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="llm-model">模型选择</Label>
                <Select 
                  value={processingConfig.llm_model} 
                  onValueChange={(value) => 
                    setProcessingConfig(prev => ({ ...prev, llm_model: value }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="gpt-4">GPT-4</SelectItem>
                    <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                    <SelectItem value="claude-3-opus">Claude 3 Opus</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-3">
                <Label>处理选项</Label>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">启用缓存</span>
                    <Switch 
                      checked={processingConfig.enable_caching}
                      onCheckedChange={(checked) => 
                        setProcessingConfig(prev => ({ ...prev, enable_caching: checked }))
                      }
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">质量检查</span>
                    <Switch 
                      checked={processingConfig.quality_check}
                      onCheckedChange={(checked) => 
                        setProcessingConfig(prev => ({ ...prev, quality_check: checked }))
                      }
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">包含图表</span>
                    <Switch 
                      checked={outputConfig.include_charts}
                      onCheckedChange={(checked) => 
                        setOutputConfig(prev => ({ ...prev, include_charts: checked }))
                      }
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">自动发送邮件</span>
                    <Switch 
                      checked={outputConfig.auto_send}
                      onCheckedChange={(checked) => 
                        setOutputConfig(prev => ({ ...prev, auto_send: checked }))
                      }
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Email Recipients */}
          {outputConfig.auto_send && (
            <div className="mt-6 pt-6 border-t">
              <Label className="text-base font-medium">邮件接收者</Label>
              <div className="flex space-x-2 mt-2">
                <Input
                  placeholder="输入邮箱地址"
                  value={emailRecipient}
                  onChange={(e) => setEmailRecipient(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && addEmailRecipient()}
                />
                <Button onClick={addEmailRecipient} disabled={!emailRecipient.trim()}>
                  添加
                </Button>
              </div>
              
              <div className="flex flex-wrap gap-2 mt-3">
                {outputConfig.email_recipients.map((email, index) => (
                  <Badge key={index} variant="secondary" className="flex items-center">
                    <Mail className="w-3 h-3 mr-1" />
                    {email}
                    <button
                      onClick={() => removeEmailRecipient(email)}
                      className="ml-2 text-red-500 hover:text-red-700"
                    >
                      ×
                    </button>
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="mt-6 flex justify-end space-x-2">
            {!isGenerating ? (
              <Button 
                onClick={generateReport} 
                disabled={!selectedTemplate || !selectedDataSource}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <Play className="w-4 h-4 mr-2" />
                生成报告
              </Button>
            ) : (
              <Button 
                onClick={cancelGeneration}
                variant="destructive"
              >
                <Square className="w-4 h-4 mr-2" />
                取消生成
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Generation Progress */}
      {isGenerating && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Zap className="w-5 h-5 mr-2" />
              生成进度
            </CardTitle>
            <CardDescription>
              智能报告生成进度和状态
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">总体进度</span>
                  <span className="text-sm text-gray-600">{generationProgress}%</span>
                </div>
                <Progress value={generationProgress} className="h-3" />
              </div>
              
              <div className="flex items-center space-x-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm">{currentStage}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Generated Report */}
      {generatedReport && (
        <Card>
          <CardHeader>
            <CardTitle>生成结果</CardTitle>
            <CardDescription>
              报告生成完成，可以下载或查看详情
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-3 bg-green-50 rounded">
                  <p className="text-2xl font-bold text-green-600">
                    {(generatedReport.quality_score * 100).toFixed(0)}%
                  </p>
                  <p className="text-sm text-gray-600">质量评分</p>
                </div>
                <div className="text-center p-3 bg-blue-50 rounded">
                  <p className="text-2xl font-bold text-blue-600">
                    {Math.round(generatedReport.file_size / 1024)}KB
                  </p>
                  <p className="text-sm text-gray-600">文件大小</p>
                </div>
                <div className="text-center p-3 bg-purple-50 rounded">
                  <p className="text-2xl font-bold text-purple-600">
                    {generatedReport.generation_time}s
                  </p>
                  <p className="text-sm text-gray-600">生成时间</p>
                </div>
                <div className="text-center p-3 bg-orange-50 rounded">
                  <p className="text-2xl font-bold text-orange-600">
                    {generatedReport.metadata.placeholders_processed}
                  </p>
                  <p className="text-sm text-gray-600">处理占位符</p>
                </div>
              </div>
              
              <Button onClick={downloadReport} className="w-full">
                下载报告
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}