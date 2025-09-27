'use client'

import React, { useState, useEffect } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Badge } from '@/components/ui/Badge'
import { Select } from '@/components/ui/Select'
import { Textarea } from '@/components/ui/Textarea'
import { Checkbox } from '@/components/ui/Checkbox'
import { APIAdapter, PlaceholderDisplayInfo, AnalysisProgressInfo, ErrorDisplayInfo } from '@/services/apiAdapter'
import { subscribeToTask, PipelineTaskUpdate, PipelineTaskStatus } from '@/services/websocketAdapter'
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
  data?: {
    items: PlaceholderDisplayInfo[]
    stats: {
      total: number
      need_reanalysis: number
      by_kind: Record<string, number>
    }
    task_id?: string
  }
  progress?: AnalysisProgressInfo
  error?: ErrorDisplayInfo
  message: string
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
  const [realTimeProgress, setRealTimeProgress] = useState<PipelineTaskUpdate | null>(null)
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const { showToast } = useToast()

  useEffect(() => {
    loadDataSources()
  }, [])

  const loadDataSources = async () => {
    try {
      // 使用原有的api调用，因为数据源API可能没有变化
      const response = await fetch('/api/v1/data-sources?size=100', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
          'Content-Type': 'application/json'
        }
      })
      const data = await response.json()

      if (data.success) {
        const activeSources = data.data?.filter(ds => ds.is_active) || []
        setDataSources(activeSources)

        // 自动选择第一个数据源
        if (activeSources.length > 0) {
          setSelectedDataSource(activeSources[0].id)
        }
      }
    } catch (error) {
      console.error('Failed to load data sources:', error)
      showToast('无法加载数据源列表', 'error')
    }
  }

  const analyzeTemplate = async () => {
    if (!selectedDataSource) {
      showToast('需要选择一个数据源来进行模板分析', 'error')
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

      const result = await APIAdapter.analyzeTemplatePlaceholders(
        templateId,
        selectedDataSource,
        options
      )

      if (result.success) {
        const initialResult = {
          success: true,
          data: result.data,
          progress: result.progress,
          message: '分析完成'
        }

        setAnalysisResult(initialResult)

        // 如果有任务ID，订阅WebSocket更新
        if (result.data?.task_id) {
          setCurrentTaskId(result.data.task_id)
          await subscribeToTask(
            result.data.task_id,
            // 任务更新监听器
            (update: PipelineTaskUpdate) => {
              setRealTimeProgress(update)

              // 更新分析结果的进度信息
              if (update.status !== PipelineTaskStatus.COMPLETED && update.status !== PipelineTaskStatus.FAILED) {
                setAnalysisResult(prev => prev ? {
                  ...prev,
                  progress: {
                    current_step: Math.ceil(update.progress * 4), // 假设4个步骤
                    total_steps: 4,
                    step_name: update.message,
                    progress_percent: update.progress * 100,
                    status: 'running',
                    steps: []
                  }
                } : prev)
              }
            },
            // 任务完成监听器
            (taskId: string, taskResult: any) => {
              console.log('任务完成:', taskId, taskResult)
              setRealTimeProgress(null)
              setCurrentTaskId(null)

              // 更新结果数据
              if (taskResult) {
                setAnalysisResult(prev => prev ? {
                  ...prev,
                  data: taskResult.total_placeholders ? {
                    ...prev.data,
                    stats: {
                      total: taskResult.total_placeholders,
                      need_reanalysis: taskResult.needs_reanalysis || 0,
                      by_kind: taskResult.placeholders_by_kind || {}
                    }
                  } : prev.data
                } : prev)
              }

              showToast('模板分析完成！', 'success')
            },
            // 任务错误监听器
            (taskId: string, error: string) => {
              console.error('任务失败:', taskId, error)
              setRealTimeProgress(null)
              setCurrentTaskId(null)
              showToast(`分析任务失败: ${error}`, 'error')
            }
          )
        } else {
          // 没有任务ID的情况
          showToast('模板占位符分析已完成', 'success')
        }

        onAnalysisComplete?.(result.data)
      } else {
        throw new Error(result.error?.user_friendly_message || '分析失败')
      }

    } catch (error: any) {
      console.error('Template analysis failed:', error)

      const errorResult: AnalysisResult = {
        success: false,
        message: '分析失败',
        error: {
          error_code: 'template_analysis_failed',
          error_message: error.message || '未知错误',
          user_friendly_message: error.message || 'React Agent 分析过程中出现错误，请稍后重试',
          error_type: 'system',
          severity: 'error',
          suggestions: ['检查数据源连接', '确认模板格式正确', '联系技术支持']
        }
      }

      setAnalysisResult(errorResult)

      // 使用API适配器的错误处理
      if (errorResult.error) {
        APIAdapter.handleError(errorResult.error)
      }
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
            <div className="flex items-center space-x-3">
              <h3 className="text-lg font-semibold">React Agent 模板分析</h3>
              {currentTaskId && (
                <Badge variant="outline" className="animate-pulse">
                  实时分析中
                </Badge>
              )}
            </div>
            <Badge variant="outline">智能分析</Badge>
          </div>

          <div className="space-y-4">
            {/* 数据源选择 */}
            <div>
              <label className="block text-sm font-medium mb-2">数据源</label>
              <Select
                value={selectedDataSource}
                onChange={(value) => setSelectedDataSource(String(value))}
                disabled={loading}
                placeholder="请选择数据源"
                options={[
                  { value: '', label: '请选择数据源' },
                  ...dataSources.map((ds) => ({
                    value: ds.id,
                    label: `${ds.name} (${ds.source_type})`
                  }))
                ]}
              />
            </div>

            {/* 优化级别 */}
            <div>
              <label className="block text-sm font-medium mb-2">优化级别</label>
              <Select
                value={optimizationLevel}
                onChange={(value) => setOptimizationLevel(String(value))}
                disabled={loading}
                options={optimizationLevels.map((level) => ({
                  value: level.value,
                  label: level.label
                }))}
              />
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
                onChange={(e) => setForceReanalyze(e.target.checked)}
                disabled={loading}
              />
              <label htmlFor="force-reanalyze" className="text-sm">
                强制重新分析（忽略缓存）
              </label>
            </div>

            {/* 实时进度显示 */}
            {realTimeProgress && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-blue-600 font-medium">{realTimeProgress.message}</span>
                  <span className="text-gray-500">{(realTimeProgress.progress * 100).toFixed(0)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
                    style={{ width: `${realTimeProgress.progress * 100}%` }}
                  />
                </div>
                <div className="text-xs text-gray-500 text-center">
                  任务ID: {realTimeProgress.task_id}
                </div>
              </div>
            )}

            {/* 分析按钮 */}
            <Button
              onClick={analyzeTemplate}
              disabled={loading || !selectedDataSource || !!currentTaskId}
              className="w-full"
            >
              {loading || currentTaskId ? (
                <>
                  <LoadingSpinner size="sm" />
                  {realTimeProgress ? realTimeProgress.message : 'React Agent 分析中...'}
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

                {/* 分析统计信息 */}
                {analysisResult.data?.stats && (
                  <div className="grid grid-cols-3 gap-4 p-4 bg-blue-50 rounded-lg">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600">
                        {analysisResult.data.stats.total}
                      </div>
                      <div className="text-sm text-gray-600">发现占位符</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-orange-600">
                        {analysisResult.data.stats.need_reanalysis}
                      </div>
                      <div className="text-sm text-gray-600">需重新分析</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">
                        {analysisResult.data.stats.total - analysisResult.data.stats.need_reanalysis}
                      </div>
                      <div className="text-sm text-gray-600">已完成</div>
                    </div>
                  </div>
                )}

                {/* 占位符类型分布 */}
                {analysisResult.data?.stats?.by_kind && (
                  <div>
                    <h5 className="font-medium mb-2">占位符类型分布:</h5>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(analysisResult.data.stats.by_kind).map(([kind, count]) => (
                        <div key={kind} className="px-3 py-1 bg-gray-100 rounded-full text-sm">
                          {kind}: {count}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 占位符列表 */}
                {analysisResult.data?.items && analysisResult.data.items.length > 0 && (
                  <div>
                    <h5 className="font-medium mb-2">发现的占位符:</h5>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {analysisResult.data.items.map((item, index) => (
                        <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                          <div className="flex items-center space-x-3">
                            <div className={`w-3 h-3 rounded-full ${
                              item.status === 'completed' ? 'bg-green-500' :
                              item.status === 'pending' ? 'bg-yellow-500' : 'bg-red-500'
                            }`} />
                            <div>
                              <div className="font-medium text-sm">{item.display_name}</div>
                              <div className="text-xs text-gray-500">{item.text}</div>
                              {item.description && (
                                <div className="text-xs text-gray-400 mt-1">{item.description}</div>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className={`px-2 py-1 text-xs rounded-full ${
                              item.badge_color === 'success' ? 'bg-green-100 text-green-800' :
                              item.badge_color === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                              item.badge_color === 'info' ? 'bg-blue-100 text-blue-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {item.kind}
                            </span>
                            {item.confidence && (
                              <span className="text-xs text-gray-500">
                                {(item.confidence * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 进度信息 */}
                {analysisResult.progress && (
                  <div>
                    <h5 className="font-medium mb-2">分析进度:</h5>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>{analysisResult.progress.step_name}</span>
                        <span>{analysisResult.progress.progress_percent.toFixed(0)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${analysisResult.progress.progress_percent}%` }}
                        />
                      </div>
                      <div className="text-xs text-gray-500">
                        第 {analysisResult.progress.current_step} / {analysisResult.progress.total_steps} 步
                      </div>
                    </div>
                  </div>
                )}

                {/* 任务ID（用于WebSocket连接） */}
                {analysisResult.data?.task_id && (
                  <div className="text-xs text-gray-500 font-mono bg-gray-100 p-2 rounded">
                    Task ID: {analysisResult.data.task_id}
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <p className="text-red-600 font-medium">{analysisResult.message}</p>
                  {analysisResult.error && (
                    <div className="mt-2">
                      <p className="text-sm font-medium text-red-700">
                        {analysisResult.error.user_friendly_message}
                      </p>
                      {process.env.NODE_ENV === 'development' && (
                        <p className="text-xs text-gray-500 mt-1 font-mono">
                          错误代码: {analysisResult.error.error_code}
                        </p>
                      )}
                    </div>
                  )}
                </div>

                <div className="bg-red-50 border border-red-200 rounded p-4">
                  <h5 className="font-medium text-red-800 mb-2">解决建议:</h5>
                  <ul className="text-sm text-red-700 list-disc list-inside space-y-1">
                    {analysisResult.error?.suggestions?.map((suggestion, index) => (
                      <li key={index}>{suggestion}</li>
                    )) || [
                      '检查数据源连接是否正常',
                      '确认模板格式正确',
                      '验证React Agent服务状态',
                      '查看系统洞察页面了解更多信息'
                    ].map((suggestion, index) => (
                      <li key={index}>{suggestion}</li>
                    ))}
                  </ul>

                  {/* 支持信息 */}
                  {analysisResult.error?.support_info && (
                    <div className="mt-3 pt-3 border-t border-red-200">
                      <h6 className="font-medium text-red-800 text-xs mb-1">获取帮助:</h6>
                      <div className="text-xs text-red-600 space-y-1">
                        <div>技术支持: {analysisResult.error.support_info.contact}</div>
                        <div>文档中心: {analysisResult.error.support_info.documentation}</div>
                        <div>系统状态: {analysisResult.error.support_info.status_page}</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}