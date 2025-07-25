'use client'

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { 
  Database,
  Loader2,
  CheckCircle,
  AlertCircle,
  XCircle
} from 'lucide-react'
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

interface FieldSuggestion {
  field_name: string
  match_score: number
  match_reason: string
  data_transformation?: string
  validation_rules: string[]
}

interface FieldMatchingResponse {
  success: boolean
  placeholder_understanding: Record<string, unknown>
  field_suggestions: FieldSuggestion[]
  best_match?: FieldSuggestion
  confidence_score: number
  processing_metadata: Record<string, unknown>
}

interface FieldMatcherProps {
  placeholder: PlaceholderInfo | null
  dataSourceId: number | null
  onMatchingComplete?: (result: FieldMatchingResponse) => void
}

export function FieldMatcher({ 
  placeholder, 
  dataSourceId, 
  onMatchingComplete 
}: FieldMatcherProps) {
  const [fieldMatchingResult, setFieldMatchingResult] = useState<FieldMatchingResponse | null>(null)
  const [matchingField, setMatchingField] = useState(false)

  // Field matching validation
  const validateFieldMatching = async () => {
    if (!placeholder || !dataSourceId) {
      alert('请选择占位符和数据源')
      return
    }

    setMatchingField(true)
    
    try {
      const response = await httpClient.post('/intelligent-placeholders/field-matching', {
        placeholder_text: placeholder.placeholder_text,
        placeholder_type: placeholder.placeholder_type,
        description: placeholder.description,
        data_source_id: dataSourceId,
        context: `${placeholder.context_before} ${placeholder.context_after}`,
        matching_options: {
          confidence_threshold: 0.8,
          max_suggestions: 5
        }
      })
      
      setFieldMatchingResult(response.data)
      if (onMatchingComplete) {
        onMatchingComplete(response.data)
      }
    } catch (error: unknown) {
      console.error('Field matching failed:', error)
      if (axios.isAxiosError(error)) {
        alert(error.response?.data?.detail || '字段匹配失败')
      } else if (error instanceof Error) {
        alert(error.message || '字段匹配失败')
      } else {
        alert('字段匹配失败')
      }
    } finally {
      setMatchingField(false)
    }
  }

  // Helper functions
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

  if (!placeholder) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Database className="w-5 h-5 mr-2" />
            字段映射
          </CardTitle>
          <CardDescription>
            请先选择一个占位符进行字段匹配分析
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-gray-500">
            <Database className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>等待选择占位符...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Selected Placeholder */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Database className="w-5 h-5 mr-2" />
            字段映射分析
          </CardTitle>
          <CardDescription>
            分析占位符与数据源字段的匹配关系
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="p-4 bg-blue-50 border border-blue-200 rounded mb-4">
            <h3 className="font-semibold mb-2">当前分析的占位符</h3>
            <p className="font-mono text-sm">{placeholder.placeholder_text}</p>
            <p className="text-sm text-gray-600 mt-1">{placeholder.description}</p>
          </div>
          
          <Button
            onClick={validateFieldMatching}
            disabled={!dataSourceId || matchingField}
            className="w-full"
          >
            {matchingField ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Database className="w-4 h-4 mr-2" />
            )}
            {matchingField ? '分析中...' : '开始字段匹配'}
          </Button>
        </CardContent>
      </Card>

      {/* Field Matching Results */}
      {fieldMatchingResult && (
        <Card>
          <CardHeader>
            <CardTitle>匹配结果</CardTitle>
            <CardDescription>
              字段匹配建议和置信度评估
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Overall Confidence */}
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded">
                <span className="font-semibold">整体匹配置信度</span>
                <div className="flex items-center space-x-2">
                  <Progress value={fieldMatchingResult.confidence_score * 100} className="w-32" />
                  <span className={`font-semibold ${getConfidenceColor(fieldMatchingResult.confidence_score)}`}>
                    {(fieldMatchingResult.confidence_score * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Best Match */}
              {fieldMatchingResult.best_match && (
                <div className="p-4 bg-green-50 border border-green-200 rounded">
                  <h3 className="font-semibold mb-2 text-green-800">最佳匹配</h3>
                  <div className="space-y-2">
                    <p><strong>字段名:</strong> {fieldMatchingResult.best_match.field_name}</p>
                    <p><strong>匹配分数:</strong> {(fieldMatchingResult.best_match.match_score * 100).toFixed(1)}%</p>
                    <p><strong>匹配原因:</strong> {fieldMatchingResult.best_match.match_reason}</p>
                    {fieldMatchingResult.best_match.data_transformation && (
                      <p><strong>数据转换:</strong> {fieldMatchingResult.best_match.data_transformation}</p>
                    )}
                    {fieldMatchingResult.best_match.validation_rules.length > 0 && (
                      <div>
                        <p className="font-medium">验证规则:</p>
                        <ul className="text-sm text-gray-600 list-disc list-inside">
                          {fieldMatchingResult.best_match.validation_rules.map((rule, index) => (
                            <li key={index}>{rule}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* All Suggestions */}
              <div>
                <h3 className="font-semibold mb-3">所有匹配建议</h3>
                <div className="space-y-3">
                  {fieldMatchingResult.field_suggestions.map((suggestion, index) => (
                    <div key={index} className="p-3 border rounded">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">{suggestion.field_name}</span>
                        <div className="flex items-center space-x-2">
                          {getConfidenceIcon(suggestion.match_score)}
                          <Progress value={suggestion.match_score * 100} className="w-20" />
                          <span className="text-sm font-medium">
                            {(suggestion.match_score * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600">{suggestion.match_reason}</p>
                      {suggestion.data_transformation && (
                        <p className="text-sm text-blue-600 mt-1">
                          <strong>转换:</strong> {suggestion.data_transformation}
                        </p>
                      )}
                      {suggestion.validation_rules.length > 0 && (
                        <div className="mt-2">
                          <p className="text-sm font-medium">验证规则:</p>
                          <ul className="text-sm text-gray-600 list-disc list-inside">
                            {suggestion.validation_rules.map((rule, ruleIndex) => (
                              <li key={ruleIndex}>{rule}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* LLM Understanding */}
              {fieldMatchingResult.placeholder_understanding && (
                <div className="p-4 bg-purple-50 border border-purple-200 rounded">
                  <h3 className="font-semibold mb-3 text-purple-800">AI理解结果</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm font-medium">语义理解:</p>
                      <p className="text-sm text-gray-700">
                        {String(fieldMatchingResult.placeholder_understanding.semantic_meaning)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium">数据类型:</p>
                      <Badge variant="outline">
                        {String(fieldMatchingResult.placeholder_understanding.data_type)}
                      </Badge>
                    </div>
                    <div>
                      <p className="text-sm font-medium">需要计算:</p>
                      <Badge variant={fieldMatchingResult.placeholder_understanding.calculation_needed ? "default" : "secondary"}>
                        {String(fieldMatchingResult.placeholder_understanding.calculation_needed)}
                      </Badge>
                    </div>
                    {typeof fieldMatchingResult.placeholder_understanding.aggregation_type === 'string' && fieldMatchingResult.placeholder_understanding.aggregation_type && (
                      <div>
                        <p className="text-sm font-medium">聚合类型:</p>
                        <Badge className="bg-purple-100 text-purple-800">
                          {String(fieldMatchingResult.placeholder_understanding.aggregation_type)}
                        </Badge>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Processing Metadata */}
              <div className="p-4 bg-gray-50 rounded">
                <h3 className="font-semibold mb-2">处理信息</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <strong>LLM提供商:</strong> {String(fieldMatchingResult.processing_metadata.llm_provider)}
                  </div>
                  <div>
                    <strong>处理时间:</strong> {String(fieldMatchingResult.processing_metadata.processing_time)}ms
                  </div>
                  <div>
                    <strong>数据源字段数:</strong> {String(fieldMatchingResult.processing_metadata.data_source_fields)}
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}