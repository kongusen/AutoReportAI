'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger,
  DialogFooter 
} from '@/components/ui/dialog'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import { 
  Edit, 
  Eye, 
  Save, 
  Plus, 
  Trash2, 
  FileText, 
  Code, 
  Search,
  BarChart3,
  Calendar,
  Hash,
  Brain,
  Lightbulb,
  CheckCircle,
  AlertCircle,
  XCircle,
  Loader2,
  Database,
  MapPin,
  PlayCircle
} from 'lucide-react'
import apiClient from '@/lib/api-client'

interface Placeholder {
  id?: string
  name: string
  type: 'text' | 'number' | 'date' | 'table' | 'chart' | 'image'
  description?: string
  default_value?: string
  required: boolean
  format?: string
}

interface Template {
  id: string
  name: string
  description?: string
  content: string
  template_type: string
  placeholders: Placeholder[]
  is_public: boolean
  created_at: string
  updated_at?: string
}

// Intelligent placeholder types
interface IntelligentPlaceholder {
  placeholder_text: string
  placeholder_type: string
  description: string
  position: number
  context_before: string
  context_after: string
  confidence: number
}

interface PlaceholderSuggestion {
  type: string
  description: string
  example: string
  confidence: number
}

interface ValidationError {
  position: number
  message: string
  suggestion?: string
  severity: 'error' | 'warning' | 'info'
}

interface DataSource {
  id: number
  name: string
  source_type: string
}

interface TemplateEditorProps {
  templateId?: string
  onSave?: (template: Template) => void
  onCancel?: () => void
}

export function TemplateEditor({ templateId, onSave, onCancel }: TemplateEditorProps) {
  const [template, setTemplate] = useState<Template>({
    id: '',
    name: '',
    description: '',
    content: '',
    template_type: 'docx',
    placeholders: [],
    is_public: false,
    created_at: new Date().toISOString()
  })
  
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [previewMode, setPreviewMode] = useState(false)
  const [newPlaceholder, setNewPlaceholder] = useState<Placeholder>({
    name: '',
    type: 'text',
    description: '',
    required: false
  })
  const [placeholderDialogOpen, setPlaceholderDialogOpen] = useState(false)
  const [editingPlaceholder, setEditingPlaceholder] = useState<Placeholder | null>(null)

  // Intelligent placeholder state
  const [intelligentMode, setIntelligentMode] = useState(false)
  const [intelligentPlaceholders, setIntelligentPlaceholders] = useState<IntelligentPlaceholder[]>([])
  const [placeholderSuggestions, setPlaceholderSuggestions] = useState<PlaceholderSuggestion[]>([])
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([])
  const [analyzing, setAnalyzing] = useState(false)
  const [validating, setValidating] = useState(false)
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [selectedDataSource, setSelectedDataSource] = useState<number | null>(null)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [cursorPosition, setCursorPosition] = useState(0)
  const [testingTemplate, setTestingTemplate] = useState(false)
  const [testResults, setTestResults] = useState<any>(null)
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(0)
  const [showTypeHelper, setShowTypeHelper] = useState(false)
  const [previewData, setPreviewData] = useState<any>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)
  
  // Refs for intelligent features
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const suggestionTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (templateId) {
      fetchTemplate()
    }
    loadDataSources()
  }, [templateId])

  // Load data sources for intelligent placeholder features
  const loadDataSources = async () => {
    try {
      const response = await apiClient.get('/enhanced-data-sources/')
      setDataSources(response.data)
    } catch (error) {
      console.error('Failed to load data sources:', error)
    }
  }

  // Intelligent placeholder analysis
  const analyzeIntelligentPlaceholders = async () => {
    if (!template.content.trim()) {
      alert('请输入模板内容')
      return
    }

    setAnalyzing(true)
    try {
      const response = await apiClient.post('/intelligent-placeholders/analyze', {
        template_content: template.content,
        template_id: templateId,
        data_source_id: selectedDataSource,
        analysis_options: {
          include_context: true,
          confidence_threshold: 0.7
        }
      })
      
      setIntelligentPlaceholders(response.data.placeholders || [])
      setValidationErrors([])
      
      // Validate placeholders in real-time
      await validatePlaceholders()
    } catch (error: any) {
      console.error('Placeholder analysis failed:', error)
      alert(error.response?.data?.detail || '占位符分析失败')
    } finally {
      setAnalyzing(false)
    }
  }

  // Real-time placeholder validation
  const validatePlaceholders = async () => {
    if (!template.content.trim()) return

    setValidating(true)
    const errors: ValidationError[] = []
    
    try {
      // Check for malformed placeholders
      const placeholderRegex = /\{\{([^}]*)\}\}/g
      let match
      
      while ((match = placeholderRegex.exec(template.content)) !== null) {
        const placeholderText = match[1]
        const position = match.index
        
        // Check if it follows the {{类型:描述}} format
        if (!placeholderText.includes(':')) {
          errors.push({
            position,
            message: '占位符格式不正确，应使用 {{类型:描述}} 格式',
            suggestion: '例如: {{统计:投诉总数}}',
            severity: 'warning'
          })
        } else {
          const [type, description] = placeholderText.split(':')
          if (!type.trim() || !description.trim()) {
            errors.push({
              position,
              message: '占位符类型或描述不能为空',
              suggestion: '请确保类型和描述都有内容',
              severity: 'error'
            })
          }
        }
      }
      
      setValidationErrors(errors)
    } catch (error) {
      console.error('Validation failed:', error)
    } finally {
      setValidating(false)
    }
  }

  // Handle content change with intelligent features
  const handleContentChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value
    setTemplate(prev => ({ ...prev, content: newContent }))
    setCursorPosition(e.target.selectionStart)
    
    // Clear previous timeout
    if (suggestionTimeoutRef.current) {
      clearTimeout(suggestionTimeoutRef.current)
    }
    
    // Check if user is typing a placeholder
    const beforeCursor = newContent.substring(0, e.target.selectionStart)
    const isTypingPlaceholder = beforeCursor.endsWith('{{') || 
                               (beforeCursor.includes('{{') && !beforeCursor.includes('}}'))
    
    if (intelligentMode && isTypingPlaceholder) {
      // Show type helper immediately when typing {{
      setShowTypeHelper(true)
      setShowSuggestions(false)
    } else {
      setShowTypeHelper(false)
    }
    
    // Debounced validation and suggestions
    suggestionTimeoutRef.current = setTimeout(() => {
      if (intelligentMode) {
        validatePlaceholders()
        if (!isTypingPlaceholder) {
          generatePlaceholderSuggestions(newContent, e.target.selectionStart)
        }
      }
    }, 500)
  }, [intelligentMode])

  // Handle keyboard navigation for suggestions
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (!intelligentMode || (!showSuggestions && !showTypeHelper)) return

    if (showSuggestions && placeholderSuggestions.length > 0) {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedSuggestionIndex(prev => 
            prev < placeholderSuggestions.length - 1 ? prev + 1 : 0
          )
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedSuggestionIndex(prev => 
            prev > 0 ? prev - 1 : placeholderSuggestions.length - 1
          )
          break
        case 'Enter':
        case 'Tab':
          e.preventDefault()
          insertIntelligentPlaceholder(placeholderSuggestions[selectedSuggestionIndex])
          break
        case 'Escape':
          e.preventDefault()
          setShowSuggestions(false)
          setSelectedSuggestionIndex(0)
          break
      }
    }

    if (showTypeHelper) {
      const placeholderTypes = ['统计', '周期', '区域', '图表']
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedSuggestionIndex(prev => 
            prev < placeholderTypes.length - 1 ? prev + 1 : 0
          )
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedSuggestionIndex(prev => 
            prev > 0 ? prev - 1 : placeholderTypes.length - 1
          )
          break
        case 'Enter':
        case 'Tab':
          e.preventDefault()
          insertPlaceholderType(placeholderTypes[selectedSuggestionIndex])
          break
        case 'Escape':
          e.preventDefault()
          setShowTypeHelper(false)
          setSelectedSuggestionIndex(0)
          break
      }
    }
  }, [intelligentMode, showSuggestions, showTypeHelper, placeholderSuggestions, selectedSuggestionIndex])

  // Insert placeholder type helper
  const insertPlaceholderType = (type: string) => {
    const textarea = textareaRef.current
    if (!textarea) return

    const content = template.content
    const cursorPos = textarea.selectionStart
    
    // Find the {{ before cursor
    const beforeCursor = content.substring(0, cursorPos)
    const lastBraceIndex = beforeCursor.lastIndexOf('{{')
    
    if (lastBraceIndex !== -1) {
      const placeholder = `{{${type}:`
      const newContent = content.substring(0, lastBraceIndex) + placeholder + content.substring(cursorPos)
      
      setTemplate(prev => ({ ...prev, content: newContent }))
      setShowTypeHelper(false)
      setSelectedSuggestionIndex(0)
      
      // Set cursor after the colon
      setTimeout(() => {
        textarea.focus()
        const newCursorPos = lastBraceIndex + placeholder.length
        textarea.setSelectionRange(newCursorPos, newCursorPos)
      }, 0)
    }
  }

  // Generate intelligent placeholder suggestions
  const generatePlaceholderSuggestions = async (content: string, position: number) => {
    if (!intelligentMode || !selectedDataSource) return

    try {
      // Get context around cursor
      const beforeCursor = content.substring(Math.max(0, position - 100), position)
      const afterCursor = content.substring(position, Math.min(content.length, position + 100))
      
      const response = await apiClient.post('/intelligent-placeholders/suggestions', {
        context_before: beforeCursor,
        context_after: afterCursor,
        data_source_id: selectedDataSource,
        cursor_position: position
      })
      
      if (response.data.suggestions && response.data.suggestions.length > 0) {
        setPlaceholderSuggestions(response.data.suggestions)
        setShowSuggestions(true)
      }
    } catch (error) {
      console.error('Failed to generate suggestions:', error)
    }
  }

  // Insert intelligent placeholder suggestion
  const insertIntelligentPlaceholder = (suggestion: PlaceholderSuggestion) => {
    const placeholder = `{{${suggestion.type}:${suggestion.description}}}`
    const textarea = textareaRef.current
    
    if (textarea) {
      const start = cursorPosition
      const content = template.content
      const newContent = content.substring(0, start) + placeholder + content.substring(start)
      
      setTemplate(prev => ({ ...prev, content: newContent }))
      setShowSuggestions(false)
      
      // Set cursor position after placeholder
      setTimeout(() => {
        textarea.focus()
        textarea.setSelectionRange(start + placeholder.length, start + placeholder.length)
      }, 0)
    }
  }

  // Test template with sample data
  const testTemplate = async () => {
    if (!template.content.trim() || !selectedDataSource) {
      alert('请选择数据源并输入模板内容')
      return
    }

    setTestingTemplate(true)
    try {
      const response = await apiClient.post('/intelligent-placeholders/test', {
        template_content: template.content,
        data_source_id: selectedDataSource,
        test_options: {
          sample_size: 10,
          include_preview: true
        }
      })
      
      setTestResults(response.data)
    } catch (error: any) {
      console.error('Template test failed:', error)
      alert(error.response?.data?.detail || '模板测试失败')
    } finally {
      setTestingTemplate(false)
    }
  }

  // Generate live preview with real data
  const generateLivePreview = async () => {
    if (!template.content.trim() || !selectedDataSource || !intelligentMode) {
      return generatePreview()
    }

    setLoadingPreview(true)
    try {
      const response = await apiClient.post('/intelligent-placeholders/preview', {
        template_content: template.content,
        data_source_id: selectedDataSource,
        preview_options: {
          sample_data: true,
          format_output: true
        }
      })
      
      setPreviewData(response.data)
      return response.data.preview_content || template.content
    } catch (error) {
      console.error('Failed to generate live preview:', error)
      return generatePreview()
    } finally {
      setLoadingPreview(false)
    }
  }

  // Enhanced preview generation
  const getPreviewContent = () => {
    if (intelligentMode && previewData) {
      return previewData.preview_content || generatePreview()
    }
    return testResults ? testResults.preview : generatePreview()
  }

  // Helper functions for intelligent placeholders
  const getIntelligentPlaceholderTypeIcon = (type: string) => {
    switch (type) {
      case '统计': return <Hash className="w-4 h-4" />
      case '周期': return <Calendar className="w-4 h-4" />
      case '区域': return <MapPin className="w-4 h-4" />
      case '图表': return <BarChart3 className="w-4 h-4" />
      default: return <FileText className="w-4 h-4" />
    }
  }

  const getIntelligentPlaceholderTypeColor = (type: string) => {
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

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error': return 'text-red-600 bg-red-50 border-red-200'
      case 'warning': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'info': return 'text-blue-600 bg-blue-50 border-blue-200'
      default: return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const fetchTemplate = async () => {
    if (!templateId) return
    
    setLoading(true)
    try {
      const response = await apiClient.get(`/templates/${templateId}`)
      setTemplate(response.data)
    } catch (error) {
      console.error('Error fetching template:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      let response
      if (templateId) {
        response = await apiClient.put(`/templates/${templateId}`, template)
      } else {
        response = await apiClient.post('/templates', template)
      }
      
      if (onSave) {
        onSave(response.data)
      }
      alert('Template saved successfully!')
    } catch (error: any) {
      console.error('Error saving template:', error)
      alert(error.response?.data?.detail || 'Failed to save template')
    } finally {
      setSaving(false)
    }
  }

  const handleAddPlaceholder = () => {
    if (!newPlaceholder.name.trim()) return
    
    const placeholder: Placeholder = {
      ...newPlaceholder,
      id: Date.now().toString()
    }
    
    setTemplate(prev => ({
      ...prev,
      placeholders: [...prev.placeholders, placeholder]
    }))
    
    setNewPlaceholder({
      name: '',
      type: 'text',
      description: '',
      required: false
    })
    setPlaceholderDialogOpen(false)
  }

  const handleEditPlaceholder = (placeholder: Placeholder) => {
    setEditingPlaceholder(placeholder)
    setNewPlaceholder({ ...placeholder })
    setPlaceholderDialogOpen(true)
  }

  const handleUpdatePlaceholder = () => {
    if (!editingPlaceholder || !newPlaceholder.name.trim()) return
    
    setTemplate(prev => ({
      ...prev,
      placeholders: prev.placeholders.map(p => 
        p.id === editingPlaceholder.id ? { ...newPlaceholder } : p
      )
    }))
    
    setEditingPlaceholder(null)
    setNewPlaceholder({
      name: '',
      type: 'text',
      description: '',
      required: false
    })
    setPlaceholderDialogOpen(false)
  }

  const handleDeletePlaceholder = (placeholderId: string) => {
    if (!confirm('Are you sure you want to delete this placeholder?')) return
    
    setTemplate(prev => ({
      ...prev,
      placeholders: prev.placeholders.filter(p => p.id !== placeholderId)
    }))
  }

  const insertPlaceholder = (placeholderName: string) => {
    const placeholder = `{{${placeholderName}}}`
    const textarea = document.getElementById('template-content') as HTMLTextAreaElement
    if (textarea) {
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const content = template.content
      const newContent = content.substring(0, start) + placeholder + content.substring(end)
      
      setTemplate(prev => ({ ...prev, content: newContent }))
      
      // 重新设置光标位置
      setTimeout(() => {
        textarea.focus()
        textarea.setSelectionRange(start + placeholder.length, start + placeholder.length)
      }, 0)
    }
  }

  const generatePreview = () => {
    let preview = template.content
    template.placeholders.forEach(placeholder => {
      const regex = new RegExp(`{{${placeholder.name}}}`, 'g')
      const sampleValue = getSampleValue(placeholder)
      preview = preview.replace(regex, sampleValue)
    })
    return preview
  }

  const getSampleValue = (placeholder: Placeholder): string => {
    switch (placeholder.type) {
      case 'text':
        return placeholder.default_value || `[Sample ${placeholder.name}]`
      case 'number':
        return placeholder.default_value || '123'
      case 'date':
        return placeholder.default_value || new Date().toLocaleDateString()
      case 'table':
        return '[Sample Table Data]'
      case 'chart':
        return '[Sample Chart]'
      case 'image':
        return '[Sample Image]'
      default:
        return `[${placeholder.name}]`
    }
  }

  const getPlaceholderTypeColor = (type: string) => {
    const colors = {
      text: 'bg-blue-100 text-blue-800',
      number: 'bg-green-100 text-green-800',
      date: 'bg-purple-100 text-purple-800',
      table: 'bg-orange-100 text-orange-800',
      chart: 'bg-pink-100 text-pink-800',
      image: 'bg-gray-100 text-gray-800'
    }
    return colors[type as keyof typeof colors] || 'bg-gray-100 text-gray-800'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Loading template...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">
            {templateId ? 'Edit Template' : 'Create Template'}
          </h1>
          <p className="text-gray-600">
            Design and configure your document template with dynamic placeholders
          </p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" onClick={() => setPreviewMode(!previewMode)}>
            <Eye className="w-4 h-4 mr-2" />
            {previewMode ? 'Edit Mode' : 'Preview'}
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Saving...' : 'Save Template'}
          </Button>
          {onCancel && (
            <Button variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Intelligent Mode Toggle */}
      <Card className="border-blue-200 bg-blue-50">
        <CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Brain className="w-6 h-6 text-blue-600" />
              <div>
                <h3 className="font-semibold text-blue-900">智能占位符模式</h3>
                <p className="text-sm text-blue-700">启用AI驱动的占位符智能提示和验证</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {intelligentMode && (
                <Select 
                  value={selectedDataSource?.toString() || ''} 
                  onValueChange={(value) => setSelectedDataSource(parseInt(value))}
                >
                  <SelectTrigger className="w-48">
                    <SelectValue placeholder="选择数据源" />
                  </SelectTrigger>
                  <SelectContent>
                    {dataSources.map((ds) => (
                      <SelectItem key={ds.id} value={ds.id.toString()}>
                        <div className="flex items-center">
                          <Database className="w-4 h-4 mr-2" />
                          {ds.name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <Switch
                checked={intelligentMode}
                onCheckedChange={setIntelligentMode}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Template Content Editor */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center">
                    <FileText className="w-5 h-5 mr-2" />
                    Template Content
                    {intelligentMode && (
                      <Badge className="ml-2 bg-blue-100 text-blue-800">
                        <Brain className="w-3 h-3 mr-1" />
                        智能模式
                      </Badge>
                    )}
                  </CardTitle>
                  <CardDescription>
                    {intelligentMode 
                      ? '使用 {{类型:描述}} 格式创建智能占位符，例如 {{统计:投诉总数}}'
                      : '编写模板内容并使用 {{placeholder_name}} 格式的占位符'
                    }
                  </CardDescription>
                </div>
                {intelligentMode && (
                  <div className="flex space-x-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={analyzeIntelligentPlaceholders}
                      disabled={analyzing || !template.content.trim()}
                    >
                      {analyzing ? (
                        <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                      ) : (
                        <Search className="w-4 h-4 mr-1" />
                      )}
                      分析占位符
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={testTemplate}
                      disabled={testingTemplate || !selectedDataSource}
                    >
                      {testingTemplate ? (
                        <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                      ) : (
                        <PlayCircle className="w-4 h-4 mr-1" />
                      )}
                      测试模板
                    </Button>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="template-name">Template Name</Label>
                    <Input
                      id="template-name"
                      value={template.name}
                      onChange={(e) => setTemplate(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="Enter template name"
                    />
                  </div>
                  <div>
                    <Label htmlFor="template-type">Template Type</Label>
                    <Select 
                      value={template.template_type} 
                      onValueChange={(value) => setTemplate(prev => ({ ...prev, template_type: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select template type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="docx">Word Document (.docx)</SelectItem>
                        <SelectItem value="html">HTML Document</SelectItem>
                        <SelectItem value="markdown">Markdown</SelectItem>
                        <SelectItem value="text">Plain Text</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                <div>
                  <Label htmlFor="template-description">Description</Label>
                  <Input
                    id="template-description"
                    value={template.description}
                    onChange={(e) => setTemplate(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Brief description of the template"
                  />
                </div>

                {/* Validation Errors Display */}
                {intelligentMode && validationErrors.length > 0 && (
                  <div className="space-y-2">
                    <Label className="text-red-600">验证错误</Label>
                    {validationErrors.map((error, index) => (
                      <div key={index} className={`p-3 rounded border ${getSeverityColor(error.severity)}`}>
                        <div className="flex items-start space-x-2">
                          {error.severity === 'error' && <XCircle className="w-4 h-4 mt-0.5" />}
                          {error.severity === 'warning' && <AlertCircle className="w-4 h-4 mt-0.5" />}
                          {error.severity === 'info' && <CheckCircle className="w-4 h-4 mt-0.5" />}
                          <div className="flex-1">
                            <p className="text-sm font-medium">{error.message}</p>
                            {error.suggestion && (
                              <p className="text-xs mt-1 opacity-80">{error.suggestion}</p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="relative">
                  <Label htmlFor="template-content">Template Content</Label>
                  {previewMode ? (
                    <div className="min-h-[400px] p-4 border rounded-md bg-gray-50">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold">Preview</h3>
                        {intelligentMode && (
                          <div className="flex items-center space-x-2">
                            {loadingPreview && <Loader2 className="w-4 h-4 animate-spin" />}
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={generateLivePreview}
                              disabled={loadingPreview || !selectedDataSource}
                            >
                              <Eye className="w-3 h-3 mr-1" />
                              实时预览
                            </Button>
                          </div>
                        )}
                      </div>
                      <div className="whitespace-pre-wrap">
                        {getPreviewContent()}
                      </div>
                      {intelligentMode && previewData && (
                        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
                          <p className="text-sm text-blue-700">
                            <CheckCircle className="w-4 h-4 inline mr-1" />
                            使用智能占位符处理生成预览，处理了 {previewData.processed_placeholders || 0} 个占位符
                          </p>
                        </div>
                      )}
                    </div>
                      </div>
                      {intelligentMode && previewData && (
                        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
                          <p className="text-sm text-blue-700">
                            <CheckCircle className="w-4 h-4 inline mr-1" />
                            使用智能占位符处理生成预览，处理了 {previewData.processed_placeholders || 0} 个占位符
                          </p>
                        </div>
                      )}
                    </div>
                      </div>
                      {intelligentMode && previewData && (
                        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
                          <p className="text-sm text-blue-700">
                            <CheckCircle className="w-4 h-4 inline mr-1" />
                            使用智能占位符处理生成预览，处理了 {previewData.processed_placeholders || 0} 个占位符
                          </p>
                        </div>
                      )}
                    </div>
                      </div>
                      {intelligentMode && previewData && (
                        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
                          <p className="text-sm text-blue-700">
                            <CheckCircle className="w-4 h-4 inline mr-1" />
                            使用智能占位符处理生成预览，处理了 {previewData.processed_placeholders || 0} 个占位符
                          </p>
                        </div>
                      )}
                    </div>
                      </div>
                      {intelligentMode && previewData && (
                        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
                          <p className="text-sm text-blue-700">
                            <CheckCircle className="w-4 h-4 inline mr-1" />
                            使用智能占位符处理生成预览，处理了 {previewData.processed_placeholders || 0} 个占位符
                          </p>
                        </div>
                      )}
                    </div>
                      </div>
                      {intelligentMode && previewData && (
                        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
                          <p className="text-sm text-blue-700">
                            <CheckCircle className="w-4 h-4 inline mr-1" />
                            使用智能占位符处理生成预览，处理了 {previewData.processed_placeholders || 0} 个占位符
                          </p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="relative">
                      <Textarea
                        ref={textareaRef}
                        id="template-content"
                        value={template.content}
                        onChange={intelligentMode ? handleContentChange : (e) => setTemplate(prev => ({ ...prev, content: e.target.value }))}
                        onKeyDown={intelligentMode ? handleKeyDown : undefined}
                        placeholder={intelligentMode 
                          ? "输入模板内容，使用 {{类型:描述}} 格式创建智能占位符。例如：{{统计:投诉总数}}、{{周期:报告时间段}}、{{区域:统计区域}}\n\n快捷键：\n- 输入 {{ 显示类型选择器\n- ↑↓ 导航建议\n- Tab/Enter 选择建议\n- Esc 关闭建议"
                          : "Enter your template content here. Use {{placeholder_name}} for dynamic content."
                        }
                        className="min-h-[400px] font-mono"
                        onFocus={() => intelligentMode && setShowSuggestions(false)}
                      />
                      
                      {/* Intelligent Suggestions Dropdown */}
                      {intelligentMode && showSuggestions && placeholderSuggestions.length > 0 && (
                        <div className="absolute top-full left-0 right-0 z-10 mt-1 bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto">
                          <div className="p-2 border-b bg-gray-50">
                            <p className="text-xs text-gray-600 flex items-center">
                              <Lightbulb className="w-3 h-3 mr-1" />
                              智能占位符建议
                            </p>
                          </div>
                          {placeholderSuggestions.map((suggestion, index) => (
                            <div
                              key={index}
                              className={`p-3 cursor-pointer border-b last:border-b-0 ${
                                index === selectedSuggestionIndex ? 'bg-blue-100' : 'hover:bg-blue-50'
                              }`}
                              onClick={() => insertIntelligentPlaceholder(suggestion)}
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-2">
                                  {getIntelligentPlaceholderTypeIcon(suggestion.type)}
                                  <span className="font-medium text-sm">{`{{${suggestion.type}:${suggestion.description}}}`}</span>
                                </div>
                                <div className="flex items-center space-x-1">
                                  {getConfidenceIcon(suggestion.confidence)}
                                  <span className={`text-xs ${getConfidenceColor(suggestion.confidence)}`}>
                                    {(suggestion.confidence * 100).toFixed(0)}%
                                  </span>
                                </div>
                              </div>
                              <p className="text-xs text-gray-500 mt-1">{suggestion.example}</p>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Type Helper Dropdown */}
                      {intelligentMode && showTypeHelper && (
                        <div className="absolute top-full left-0 right-0 z-10 mt-1 bg-white border rounded-md shadow-lg max-h-64 overflow-y-auto">
                          <div className="p-2 border-b bg-gray-50">
                            <p className="text-xs text-gray-600 flex items-center">
                              <Brain className="w-3 h-3 mr-1" />
                              选择占位符类型
                            </p>
                          </div>
                          {[
                            { 
                              type: '统计', 
                              icon: Hash, 
                              desc: '数值统计和计算', 
                              examples: ['投诉总数', '平均处理时长', '同比增长率'],
                              color: 'text-blue-600'
                            },
                            { 
                              type: '周期', 
                              icon: Calendar, 
                              desc: '时间周期和日期', 
                              examples: ['报告时间段', '统计月份', '截止日期'],
                              color: 'text-purple-600'
                            },
                            { 
                              type: '区域', 
                              icon: MapPin, 
                              desc: '地理区域和位置', 
                              examples: ['统计区域', '投诉最多城市', '覆盖范围'],
                              color: 'text-green-600'
                            },
                            { 
                              type: '图表', 
                              icon: BarChart3, 
                              desc: '图表和可视化', 
                              examples: ['趋势图表', '分布饼图', '对比柱状图'],
                              color: 'text-orange-600'
                            }
                          ].map(({ type, icon: Icon, desc, examples, color }, index) => (
                            <div
                              key={type}
                              className={`p-3 cursor-pointer border-b last:border-b-0 ${
                                index === selectedSuggestionIndex ? 'bg-blue-100' : 'hover:bg-blue-50'
                              }`}
                              onClick={() => insertPlaceholderType(type)}
                            >
                              <div className="flex items-start space-x-3">
                                <Icon className={`w-5 h-5 mt-0.5 ${color}`} />
                                <div className="flex-1">
                                  <div className="flex items-center space-x-2 mb-1">
                                    <span className="font-medium text-sm">{type}</span>
                                    <Badge variant="outline" className={`text-xs ${color}`}>
                                      类型
                                    </Badge>
                                  </div>
                                  <p className="text-xs text-gray-600 mb-2">{desc}</p>
                                  <div className="flex flex-wrap gap-1">
                                    {examples.map((example, idx) => (
                                      <span key={idx} className="text-xs bg-gray-100 px-2 py-1 rounded">
                                        {example}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                          <div className="p-2 bg-gray-50 text-xs text-gray-500">
                            <p>💡 提示：选择类型后输入冒号和描述，例如 {{统计:投诉总数}}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Validation Status */}
                  {intelligentMode && (
                    <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                      <div className="flex items-center space-x-2">
                        {validating ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : validationErrors.length === 0 ? (
                          <CheckCircle className="w-3 h-3 text-green-600" />
                        ) : (
                          <AlertCircle className="w-3 h-3 text-yellow-600" />
                        )}
                        <span>
                          {validating ? '验证中...' : 
                           validationErrors.length === 0 ? '格式正确' : 
                           `${validationErrors.length} 个问题`}
                        </span>
                      </div>
                      <div>
                        智能占位符: {intelligentPlaceholders.length}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Test Results */}
          {testResults && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <PlayCircle className="w-5 h-5 mr-2 text-green-600" />
                  模板测试结果
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-3 bg-green-50 rounded">
                      <p className="text-2xl font-bold text-green-600">{testResults.success_count || 0}</p>
                      <p className="text-sm text-gray-600">成功处理</p>
                    </div>
                    <div className="text-center p-3 bg-red-50 rounded">
                      <p className="text-2xl font-bold text-red-600">{testResults.error_count || 0}</p>
                      <p className="text-sm text-gray-600">处理错误</p>
                    </div>
                    <div className="text-center p-3 bg-blue-50 rounded">
                      <p className="text-2xl font-bold text-blue-600">{testResults.processing_time || 0}s</p>
                      <p className="text-sm text-gray-600">处理时间</p>
                    </div>
                  </div>
                  
                  {testResults.errors && testResults.errors.length > 0 && (
                    <div>
                      <h4 className="font-semibold text-red-600 mb-2">处理错误</h4>
                      <div className="space-y-2">
                        {testResults.errors.map((error: any, index: number) => (
                          <div key={index} className="p-2 bg-red-50 border border-red-200 rounded text-sm">
                            <p className="font-medium">{error.placeholder}</p>
                            <p className="text-red-600">{error.message}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Placeholders Panel */}
        <div>
          {intelligentMode ? (
            /* Intelligent Placeholders Panel */
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center">
                      <Brain className="w-5 h-5 mr-2 text-blue-600" />
                      智能占位符
                    </CardTitle>
                    <CardDescription>
                      AI分析的智能占位符和类型选择器
                    </CardDescription>
                  </div>
                  <Badge variant="outline" className="text-blue-600">
                    {intelligentPlaceholders.length} 个
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Placeholder Type Selector */}
                  <div>
                    <Label className="text-sm font-medium mb-2 block">占位符类型助手</Label>
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { type: '统计', icon: Hash, desc: '数值统计', example: '投诉总数' },
                        { type: '周期', icon: Calendar, desc: '时间周期', example: '报告时间段' },
                        { type: '区域', icon: MapPin, desc: '地理区域', example: '统计区域' },
                        { type: '图表', icon: BarChart3, desc: '图表展示', example: '趋势图表' }
                      ].map(({ type, icon: Icon, desc, example }) => (
                        <Button
                          key={type}
                          variant="outline"
                          size="sm"
                          className="h-auto p-3 flex flex-col items-start"
                          onClick={() => {
                            const placeholder = `{{${type}:${example}}}`
                            const textarea = textareaRef.current
                            if (textarea) {
                              const start = textarea.selectionStart
                              const content = template.content
                              const newContent = content.substring(0, start) + placeholder + content.substring(start)
                              setTemplate(prev => ({ ...prev, content: newContent }))
                              setTimeout(() => {
                                textarea.focus()
                                textarea.setSelectionRange(start + placeholder.length, start + placeholder.length)
                              }, 0)
                            }
                          }}
                        >
                          <div className="flex items-center space-x-2 mb-1">
                            <Icon className="w-4 h-4" />
                            <span className="font-medium">{type}</span>
                          </div>
                          <span className="text-xs text-gray-500">{desc}</span>
                        </Button>
                      ))}
                    </div>
                  </div>

                  {/* Analyzed Intelligent Placeholders */}
                  {intelligentPlaceholders.length > 0 && (
                    <div>
                      <Label className="text-sm font-medium mb-2 block">已识别的智能占位符</Label>
                      <ScrollArea className="h-64">
                        <div className="space-y-3">
                          {intelligentPlaceholders.map((placeholder, index) => (
                            <div key={index} className="p-3 border rounded-lg bg-gray-50">
                              <div className="flex items-center justify-between mb-2">
                                <Badge className={getIntelligentPlaceholderTypeColor(placeholder.placeholder_type)}>
                                  {getIntelligentPlaceholderTypeIcon(placeholder.placeholder_type)}
                                  <span className="ml-1">{placeholder.placeholder_type}</span>
                                </Badge>
                                <div className="flex items-center space-x-1">
                                  {getConfidenceIcon(placeholder.confidence)}
                                  <span className={`text-xs font-medium ${getConfidenceColor(placeholder.confidence)}`}>
                                    {(placeholder.confidence * 100).toFixed(1)}%
                                  </span>
                                </div>
                              </div>
                              
                              <div className="space-y-2">
                                <p className="font-mono text-xs bg-white p-2 rounded border">
                                  {placeholder.placeholder_text}
                                </p>
                                <p className="text-xs text-gray-600">
                                  <strong>描述:</strong> {placeholder.description}
                                </p>
                                <p className="text-xs text-gray-500">
                                  <strong>位置:</strong> 第 {placeholder.position} 个字符
                                </p>
                                
                                {/* Context Preview */}
                                <div className="text-xs">
                                  <strong>上下文:</strong>
                                  <div className="mt-1 p-2 bg-white rounded text-xs border">
                                    <span className="text-gray-400">{placeholder.context_before.slice(-30)}</span>
                                    <span className="bg-yellow-200 px-1 rounded font-medium">{placeholder.placeholder_text}</span>
                                    <span className="text-gray-400">{placeholder.context_after.slice(0, 30)}</span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </ScrollArea>
                    </div>
                  )}

                  {/* Quick Actions */}
                  <div className="pt-4 border-t">
                    <div className="flex space-x-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          const sampleTemplate = `# 投诉数据分析报告

## 基本统计
本月共收到投诉 {{统计:投诉总数}} 件，较上月{{统计:同比变化}}。

## 时间分析
报告周期：{{周期:统计时间段}}
处理时效：平均 {{统计:平均处理时长}} 天

## 区域分布
主要投诉区域：{{区域:投诉最多区域}}
区域统计：{{图表:区域分布图}}

## 趋势分析
{{图表:投诉趋势图}}`
                          setTemplate(prev => ({ ...prev, content: sampleTemplate }))
                        }}
                        className="flex-1"
                      >
                        <FileText className="w-3 h-3 mr-1" />
                        示例模板
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setTemplate(prev => ({ ...prev, content: '' }))}
                        className="flex-1"
                      >
                        <Trash2 className="w-3 h-3 mr-1" />
                        清空内容
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
            /* Traditional Placeholders Panel */
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center">
                      <Code className="w-5 h-5 mr-2" />
                      Placeholders
                    </CardTitle>
                    <CardDescription>
                      Manage dynamic content placeholders
                    </CardDescription>
                  </div>
                  <Dialog open={placeholderDialogOpen} onOpenChange={setPlaceholderDialogOpen}>
                    <DialogTrigger asChild>
                      <Button size="sm">
                        <Plus className="w-4 h-4 mr-1" />
                        Add
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>
                          {editingPlaceholder ? 'Edit Placeholder' : 'Add New Placeholder'}
                        </DialogTitle>
                      </DialogHeader>
                      <div className="space-y-4">
                        <div>
                          <Label htmlFor="placeholder-name">Placeholder Name</Label>
                          <Input
                            id="placeholder-name"
                            value={newPlaceholder.name}
                            onChange={(e) => setNewPlaceholder(prev => ({ ...prev, name: e.target.value }))}
                            placeholder="e.g., company_name, report_date"
                          />
                        </div>
                        <div>
                          <Label htmlFor="placeholder-type">Type</Label>
                          <Select 
                            value={newPlaceholder.type} 
                            onValueChange={(value: any) => setNewPlaceholder(prev => ({ ...prev, type: value }))}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select type" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="text">Text</SelectItem>
                              <SelectItem value="number">Number</SelectItem>
                              <SelectItem value="date">Date</SelectItem>
                              <SelectItem value="table">Table</SelectItem>
                              <SelectItem value="chart">Chart</SelectItem>
                              <SelectItem value="image">Image</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label htmlFor="placeholder-description">Description</Label>
                          <Input
                            id="placeholder-description"
                            value={newPlaceholder.description}
                            onChange={(e) => setNewPlaceholder(prev => ({ ...prev, description: e.target.value }))}
                            placeholder="Brief description of this placeholder"
                          />
                        </div>
                        <div>
                          <Label htmlFor="placeholder-default">Default Value</Label>
                          <Input
                            id="placeholder-default"
                            value={newPlaceholder.default_value || ''}
                            onChange={(e) => setNewPlaceholder(prev => ({ ...prev, default_value: e.target.value }))}
                            placeholder="Default value (optional)"
                          />
                        </div>
                        <div className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            id="placeholder-required"
                            checked={newPlaceholder.required}
                            onChange={(e) => setNewPlaceholder(prev => ({ ...prev, required: e.target.checked }))}
                          />
                          <Label htmlFor="placeholder-required">Required field</Label>
                        </div>
                      </div>
                      <DialogFooter>
                        <Button variant="outline" onClick={() => setPlaceholderDialogOpen(false)}>
                          Cancel
                        </Button>
                        <Button onClick={editingPlaceholder ? handleUpdatePlaceholder : handleAddPlaceholder}>
                          {editingPlaceholder ? 'Update' : 'Add'} Placeholder
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {template.placeholders.length === 0 ? (
                    <p className="text-gray-500 text-sm">No placeholders defined</p>
                  ) : (
                    template.placeholders.map((placeholder) => (
                      <div key={placeholder.id} className="p-3 border rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            <Badge className={getPlaceholderTypeColor(placeholder.type)}>
                              {placeholder.type}
                            </Badge>
                            {placeholder.required && (
                              <Badge variant="outline" className="text-red-600">
                                Required
                              </Badge>
                            )}
                          </div>
                          <div className="flex space-x-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleEditPlaceholder(placeholder)}
                            >
                              <Edit className="w-3 h-3" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleDeletePlaceholder(placeholder.id!)}
                              className="text-red-600"
                            >
                              <Trash2 className="w-3 h-3" />
                            </Button>
                          </div>
                        </div>
                        <div>
                          <p className="font-medium text-sm">{`{{${placeholder.name}}}`}</p>
                          {placeholder.description && (
                            <p className="text-xs text-gray-500 mt-1">{placeholder.description}</p>
                          )}
                          <Button
                            size="sm"
                            variant="outline"
                            className="mt-2 text-xs"
                            onClick={() => insertPlaceholder(placeholder.name)}
                          >
                            Insert
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}