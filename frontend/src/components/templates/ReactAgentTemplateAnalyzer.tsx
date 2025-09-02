'use client'

import React, { useState, useEffect } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Badge } from '@/components/ui/Badge'
import { Select } from '@/components/ui/Select'
import { Textarea } from '@/components/ui/Textarea'
import { Checkbox } from '@/components/ui/Checkbox'
import { apiClient } from '@/lib/api-client'
import { useToast } from '@/hooks/useToast'

interface ReactAgentTemplateAnalyzerProps {
  templateId: string
  onAnalysisComplete?: (result: any) => void
}

interface DataSource {
  id: string
  name: string
  source_type: string
  is_active: boolean
}

interface AnalysisResult {
  success: boolean
  data: any
  message: string
  error?: string
}

export default function ReactAgentTemplateAnalyzer({ 
  templateId, 
  onAnalysisComplete 
}: ReactAgentTemplateAnalyzerProps) {
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [selectedDataSource, setSelectedDataSource] = useState('')
  const [optimizationLevel, setOptimizationLevel] = useState('enhanced')
  const [forceReanalyze, setForceReanalyze] = useState(false)
  const [targetExpectations, setTargetExpectations] = useState('')
  const [loading, setLoading] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const { toast } = useToast()

  useEffect(() => {
    loadDataSources()
  }, [])

  const loadDataSources = async () => {
    try {
      const response = await apiClient.getDataSources({ size: 100 })
      setDataSources(response.items?.filter(ds => ds.is_active) || [])
      
      // 自动选择第一个数据源
      if (response.items?.length > 0) {
        setSelectedDataSource(response.items[0].id)
      }
    } catch (error) {
      console.error('Failed to load data sources:', error)
      toast({
        title: '加载失败',
        description: '无法加载数据源列表',
        variant: 'destructive'
      })
    }
  }

  const analyzeTemplate = async () => {
    if (!selectedDataSource) {
      toast({
        title: '请选择数据源',
        description: '需要选择一个数据源来进行模板分析',
        variant: 'destructive'
      })
      return
    }

    setLoading(true)
    setAnalysisResult(null)

    try {
      const options: any = {
        forceReanalyze,
        optimizationLevel
      }

      // 解析目标期望（如果提供）
      if (targetExpectations.trim()) {
        try {
          options.targetExpectations = JSON.parse(targetExpectations)
        } catch (e) {
          // 如果不是JSON，作为普通文本处理
          options.targetExpectations = { description: targetExpectations.trim() }
        }
      }

      const result = await apiClient.analyzeTemplatePlaceholders(
        templateId,
        selectedDataSource,
        options
      )

      setAnalysisResult({
        success: true,
        data: result,
        message: '分析完成'
      })

      toast({
        title: 'React Agent 分析完成',
        description: '模板占位符分析已完成',
        variant: 'default'
      })

      onAnalysisComplete?.(result)

    } catch (error: any) {
      console.error('Template analysis failed:', error)
      
      const errorResult: AnalysisResult = {
        success: false,
        data: null,
        message: '分析失败',
        error: error.message || '未知错误'
      }
      
      setAnalysisResult(errorResult)
      
      toast({
        title: 'React Agent 分析失败',
        description: errorResult.error,
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const optimizationLevels = [
    { value: 'basic', label: '基础优化', description: '基本的上下文补全和错误修正' },
    { value: 'enhanced', label: '增强优化', description: '智能推理和上下文增强' },
    { value: 'iterative', label: '迭代优化', description: '多轮迭代改进，直到达到满意效果' },
    { value: 'intelligent', label: '智能优化', description: '基于学习的自适应优化' }
  ]

  const formatAnalysisData = (data: any) => {
    if (typeof data === 'string') {
      return data
    }
    
    if (typeof data === 'object') {
      return JSON.stringify(data, null, 2)
    }
    
    return String(data)
  }

  return (
    <div className="space-y-6">
      <Card>
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold">React Agent 模板分析</h3>
            <Badge variant="outline">智能分析</Badge>
          </div>

          <div className="space-y-4">
            {/* 数据源选择 */}
            <div>
              <label className="block text-sm font-medium mb-2">数据源</label>
              <Select
                value={selectedDataSource}
                onValueChange={setSelectedDataSource}
                disabled={loading}
              >
                <option value="">请选择数据源</option>
                {dataSources.map((ds) => (
                  <option key={ds.id} value={ds.id}>
                    {ds.name} ({ds.source_type})
                  </option>
                ))}
              </Select>
            </div>

            {/* 优化级别 */}
            <div>
              <label className="block text-sm font-medium mb-2">优化级别</label>
              <Select
                value={optimizationLevel}
                onValueChange={setOptimizationLevel}
                disabled={loading}
              >
                {optimizationLevels.map((level) => (
                  <option key={level.value} value={level.value}>
                    {level.label}
                  </option>
                ))}
              </Select>
              <p className="text-xs text-gray-500 mt-1">
                {optimizationLevels.find(l => l.value === optimizationLevel)?.description}
              </p>
            </div>

            {/* 目标期望 */}
            <div>
              <label className="block text-sm font-medium mb-2">目标期望 (可选)</label>
              <Textarea
                value={targetExpectations}
                onChange={(e) => setTargetExpectations(e.target.value)}
                placeholder="描述您对分析结果的期望，可以是JSON格式或自然语言描述..."
                rows={3}
                disabled={loading}
              />
              <p className="text-xs text-gray-500 mt-1">
                可以输入JSON配置或自然语言描述来指导React Agent的分析过程
              </p>
            </div>

            {/* 选项 */}
            <div className="flex items-center space-x-2">
              <Checkbox
                id="force-reanalyze"
                checked={forceReanalyze}
                onCheckedChange={(checked) => setForceReanalyze(!!checked)}
                disabled={loading}
              />
              <label htmlFor="force-reanalyze" className="text-sm">
                强制重新分析（忽略缓存）
              </label>
            </div>

            {/* 分析按钮 */}
            <Button
              onClick={analyzeTemplate}
              disabled={loading || !selectedDataSource}
              className="w-full"
            >
              {loading ? (
                <>
                  <LoadingSpinner size="sm" />
                  React Agent 分析中...
                </>
              ) : (
                '开始 React Agent 分析'
              )}
            </Button>
          </div>
        </div>
      </Card>

      {/* 分析结果 */}
      {analysisResult && (
        <Card>
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-lg font-semibold">分析结果</h4>
              <Badge variant={analysisResult.success ? 'default' : 'destructive'}>
                {analysisResult.success ? '成功' : '失败'}
              </Badge>
            </div>

            {analysisResult.success ? (
              <div className="space-y-4">
                <div>
                  <p className="text-green-600 font-medium">{analysisResult.message}</p>
                </div>

                {analysisResult.data && (
                  <div>
                    <h5 className="font-medium mb-2">分析详情:</h5>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <pre className="text-sm whitespace-pre-wrap overflow-x-auto">
                        {formatAnalysisData(analysisResult.data)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <p className="text-red-600 font-medium">{analysisResult.message}</p>
                  {analysisResult.error && (
                    <p className="text-sm text-gray-600 mt-1">{analysisResult.error}</p>
                  )}
                </div>

                <div className="bg-red-50 border border-red-200 rounded p-4">
                  <h5 className="font-medium text-red-800 mb-2">错误排查建议:</h5>
                  <ul className="text-sm text-red-700 list-disc list-inside space-y-1">
                    <li>检查数据源连接是否正常</li>
                    <li>确认模板格式正确</li>
                    <li>验证React Agent服务状态</li>
                    <li>查看系统洞察页面了解更多信息</li>
                  </ul>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}