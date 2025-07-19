'use client'

import React, { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger,
  DialogFooter 
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { 
  Brain, 
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Zap
} from 'lucide-react'

// Import modular components
import { PlaceholderAnalyzer } from './PlaceholderAnalyzer'
import { FieldMatcher } from './FieldMatcher'
import { AIAssistant } from './AIAssistant'
import { ErrorBoundary } from './ErrorBoundary'

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
  validation_result: Record<string, any>
  processing_errors: Array<Record<string, any>>
  estimated_processing_time: number
}

interface FieldMatchingResponse {
  success: boolean
  placeholder_understanding: Record<string, any>
  field_suggestions: any[]
  best_match?: any
  confidence_score: number
  processing_metadata: Record<string, any>
}

interface IntelligentPlaceholderManagerProps {
  templateId?: string
  dataSourceId?: number
  onPlaceholderUpdate?: (placeholders: PlaceholderInfo[]) => void
}

export function IntelligentPlaceholderManager({ 
  templateId, 
  dataSourceId, 
  onPlaceholderUpdate 
}: IntelligentPlaceholderManagerProps) {
  // State management
  const [analysisResult, setAnalysisResult] = useState<PlaceholderAnalysisResponse | null>(null)
  const [selectedPlaceholder, setSelectedPlaceholder] = useState<PlaceholderInfo | null>(null)
  const [fieldMatchingResult, setFieldMatchingResult] = useState<FieldMatchingResponse | null>(null)
  
  // UI state
  const [activeTab, setActiveTab] = useState('analysis')
  const [feedbackDialog, setFeedbackDialog] = useState(false)
  const [feedback, setFeedback] = useState({ type: '', message: '', placeholder: '' })

  // Handle analysis completion
  const handleAnalysisComplete = (result: PlaceholderAnalysisResponse) => {
    setAnalysisResult(result)
    if (onPlaceholderUpdate) {
      onPlaceholderUpdate(result.placeholders)
    }
  }

  // Handle placeholder selection
  const handlePlaceholderSelect = (placeholder: PlaceholderInfo) => {
    setSelectedPlaceholder(placeholder)
    setActiveTab('field-mapping')
  }

  // Handle field matching completion
  const handleFieldMatchingComplete = (result: FieldMatchingResponse) => {
    setFieldMatchingResult(result)
    setActiveTab('llm-understanding')
  }

  // Handle AI assistant suggestions
  const handleSuggestionApply = (suggestion: string) => {
    console.log('Applying suggestion:', suggestion)
    // This could trigger specific actions based on the suggestion
  }

  // Submit user feedback
  const submitFeedback = async () => {
    if (!feedback.message.trim()) {
      alert('请输入反馈内容')
      return
    }

    try {
      // This would be implemented when the feedback API is available
      console.log('Submitting feedback:', feedback)
      alert('反馈已提交，谢谢您的建议！')
      setFeedbackDialog(false)
      setFeedback({ type: '', message: '', placeholder: '' })
    } catch (error) {
      console.error('Failed to submit feedback:', error)
      alert('反馈提交失败')
    }
  }

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center">
              <Brain className="w-8 h-8 mr-3 text-blue-600" />
              智能占位符管理
            </h1>
            <p className="text-gray-600 mt-2">
              使用AI技术分析和处理模板中的智能占位符
            </p>
          </div>
        </div>

        {/* Main Content Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="analysis">占位符分析</TabsTrigger>
            <TabsTrigger value="field-mapping">字段映射</TabsTrigger>
            <TabsTrigger value="llm-understanding">AI理解</TabsTrigger>
            <TabsTrigger value="assistant">AI助手</TabsTrigger>
          </TabsList>

          {/* Placeholder Analysis Tab */}
          <TabsContent value="analysis">
            <ErrorBoundary>
              <PlaceholderAnalyzer
                templateId={templateId}
                dataSourceId={dataSourceId}
                onAnalysisComplete={handleAnalysisComplete}
                onPlaceholderSelect={handlePlaceholderSelect}
              />
            </ErrorBoundary>
          </TabsContent>

          {/* Field Mapping Tab */}
          <TabsContent value="field-mapping">
            <ErrorBoundary>
              <FieldMatcher
                placeholder={selectedPlaceholder}
                dataSourceId={dataSourceId}
                onMatchingComplete={handleFieldMatchingComplete}
              />
            </ErrorBoundary>
          </TabsContent>

          {/* LLM Understanding Tab */}
          <TabsContent value="llm-understanding">
            <ErrorBoundary>
              <div className="space-y-6">
                {fieldMatchingResult?.placeholder_understanding ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <div className="p-4 bg-blue-50 border border-blue-200 rounded">
                        <h3 className="font-semibold mb-2">语义理解</h3>
                        <p className="text-sm text-gray-700">
                          {fieldMatchingResult.placeholder_understanding.semantic_meaning}
                        </p>
                      </div>
                      
                      <div className="p-4 bg-green-50 border border-green-200 rounded">
                        <h3 className="font-semibold mb-2">数据类型</h3>
                        <Badge variant="outline">
                          {fieldMatchingResult.placeholder_understanding.data_type}
                        </Badge>
                      </div>
                    </div>
                    
                    <div className="space-y-4">
                      <div className="p-4 bg-purple-50 border border-purple-200 rounded">
                        <h3 className="font-semibold mb-2">计算需求</h3>
                        <Badge variant={fieldMatchingResult.placeholder_understanding.calculation_needed ? "default" : "secondary"}>
                          {fieldMatchingResult.placeholder_understanding.calculation_needed ? "需要计算" : "直接取值"}
                        </Badge>
                      </div>
                      
                      {fieldMatchingResult.placeholder_understanding.aggregation_type && (
                        <div className="p-4 bg-orange-50 border border-orange-200 rounded">
                          <h3 className="font-semibold mb-2">聚合类型</h3>
                          <Badge className="bg-orange-100 text-orange-800">
                            {fieldMatchingResult.placeholder_understanding.aggregation_type}
                          </Badge>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <Brain className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <h3 className="text-lg font-medium mb-2">等待AI理解结果</h3>
                    <p>请先完成占位符分析和字段匹配</p>
                  </div>
                )}
              </div>
            </ErrorBoundary>
          </TabsContent>

          {/* AI Assistant Tab */}
          <TabsContent value="assistant">
            <ErrorBoundary>
              <AIAssistant
                context={{
                  templateId,
                  dataSourceId,
                  placeholders: analysisResult?.placeholders,
                  currentTask: selectedPlaceholder ? '字段匹配分析' : '占位符分析'
                }}
                onSuggestionApply={handleSuggestionApply}
              />
            </ErrorBoundary>
          </TabsContent>
        </Tabs>

        {/* Feedback Dialog */}
        <Dialog open={feedbackDialog} onOpenChange={setFeedbackDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center">
                <MessageSquare className="w-5 h-5 mr-2" />
                用户反馈
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="feedback-type">反馈类型</Label>
                <select
                  id="feedback-type"
                  value={feedback.type}
                  onChange={(e) => setFeedback({ ...feedback, type: e.target.value })}
                  className="w-full p-2 border rounded"
                >
                  <option value="">选择反馈类型</option>
                  <option value="positive">正面反馈</option>
                  <option value="negative">问题反馈</option>
                  <option value="suggestion">改进建议</option>
                </select>
              </div>
              
              <div>
                <Label htmlFor="feedback-message">反馈内容</Label>
                <Textarea
                  id="feedback-message"
                  value={feedback.message}
                  onChange={(e) => setFeedback({ ...feedback, message: e.target.value })}
                  placeholder="请详细描述您的反馈..."
                  className="min-h-[100px]"
                />
              </div>
              
              {feedback.placeholder && (
                <div>
                  <Label>相关占位符</Label>
                  <div className="p-2 bg-gray-100 rounded font-mono text-sm">
                    {feedback.placeholder}
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setFeedbackDialog(false)}>
                取消
              </Button>
              <Button onClick={submitFeedback}>
                提交反馈
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Quick Feedback Actions */}
        {analysisResult && (
          <div className="fixed bottom-4 right-4 space-y-2">
            <Button
              size="sm"
              className="bg-green-600 hover:bg-green-700"
              onClick={() => {
                setFeedback({ type: 'positive', message: '分析结果准确', placeholder: '' })
                setFeedbackDialog(true)
              }}
            >
              <ThumbsUp className="w-4 h-4 mr-1" />
              准确
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="border-red-200 text-red-600 hover:bg-red-50"
              onClick={() => {
                setFeedback({ type: 'negative', message: '', placeholder: '' })
                setFeedbackDialog(true)
              }}
            >
              <ThumbsDown className="w-4 h-4 mr-1" />
              有误
            </Button>
          </div>
        )}
      </div>
    </ErrorBoundary>
  )
}