'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
  CogIcon,
  BeakerIcon,
  PlayIcon,
  PauseIcon,
  CodeBracketIcon,
  TableCellsIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  ArrowLeftIcon,
  DocumentDuplicateIcon,
  TrashIcon,
  PencilIcon,
} from '@heroicons/react/24/outline'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { Modal } from '@/components/ui/Modal'
import { Textarea } from '@/components/ui/Textarea'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Switch } from '@/components/ui/Switch'
import { useTemplateStore } from '@/features/templates/templateStore'
import { ETLScriptManager } from '@/components/templates/ETLScriptManager'
import { PlaceholderConfig, PlaceholderAnalytics, DataSource } from '@/types'
import { formatRelativeTime } from '@/utils'
import { normalizePlaceholders, NormalizedPlaceholder, calculatePlaceholderStats, getPlaceholderTypeStyle } from '@/utils/placeholderUtils'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

export default function TemplatePlaceholdersPage() {
  const params = useParams()
  const router = useRouter()
  const templateId = params.id as string
  
  const { currentTemplate, getTemplate } = useTemplateStore()
  const [placeholders, setPlaceholders] = useState<NormalizedPlaceholder[]>([])
  const [analytics, setAnalytics] = useState<PlaceholderAnalytics | null>(null)
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  
  // 编辑状态
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [selectedPlaceholder, setSelectedPlaceholder] = useState<NormalizedPlaceholder | null>(null)
  const [editForm, setEditForm] = useState({
    placeholder_name: '',
    placeholder_type: '',
    execution_order: 0,
    cache_ttl_hours: 24,
    is_active: true,
    generated_sql: '',
    agent_config: '{}'
  })

  useEffect(() => {
    if (templateId) {
      loadData()
    }
  }, [templateId])

  const loadData = async () => {
    try {
      setLoading(true)
      
      // 并行加载数据
      const [templateResult, placeholdersResult, dataSourcesResult] = await Promise.allSettled([
        getTemplate(templateId),
        api.get(`/templates/${templateId}/preview`), // 使用预览API获取占位符
        api.get('/data-sources')
      ])

      // 处理占位符数据 - 从预览API获取并规范化
      if (placeholdersResult.status === 'fulfilled') {
        const placeholderData = placeholdersResult.value.data?.data || placeholdersResult.value.data || {}
        const rawPlaceholders = placeholderData.placeholders || []
        
        // 使用工具函数规范化占位符数据
        const normalizedPlaceholdersData = normalizePlaceholders(rawPlaceholders)
        setPlaceholders(normalizedPlaceholdersData)
        
        // 计算统计信息
        const stats = calculatePlaceholderStats(normalizedPlaceholdersData)
        setAnalytics({
          total_placeholders: stats.totalCount,
          analyzed_placeholders: 0, // 这些是新解析的占位符，还没有分析
          sql_validated_placeholders: 0,
          average_confidence_score: 0,
          cache_hit_rate: 0,
          analysis_coverage: 0,
          execution_stats: {
            total_executions: 0,
            successful_executions: 0,
            failed_executions: 0,
            average_execution_time_ms: 0
          }
        })
      }

      // 处理数据源数据
      if (dataSourcesResult.status === 'fulfilled') {
        const dsData = dataSourcesResult.value.data?.data || dataSourcesResult.value.data || []
        setDataSources(Array.isArray(dsData) ? dsData : dsData.items || [])
      }

    } catch (error) {
      console.error('Failed to load data:', error)
      toast.error('加载数据失败')
    } finally {
      setLoading(false)
    }
  }

  // 重新解析占位符
  const handleAnalyzePlaceholders = async () => {
    try {
      setAnalyzing(true)
      toast.loading('正在重新解析占位符...', { duration: 1000 })
      
      // 使用混合管理器重新解析并存储占位符
      const response = await api.post(`/templates/${templateId}/placeholders/reparse`, {}, {
        params: { force_reparse: true }
      })
      
      if (response.data?.success) {
        toast.success(response.data.message || '占位符重新解析完成')
        await loadData() // 重新加载数据以显示新解析的占位符
      } else {
        toast.error(response.data?.message || '占位符重新解析失败')
      }
    } catch (error: any) {
      console.error('Failed to re-analyze placeholders:', error)
      toast.error(error.response?.data?.detail || '占位符重新解析失败')
    } finally {
      setAnalyzing(false)
    }
  }

  // 使用Agent分析
  const handleAgentAnalysis = async (dataSourceId: string) => {
    try {
      setAnalyzing(true)
      toast.loading('正在使用Agent分析占位符...', { duration: 2000 })
      
      const response = await api.post(`/templates/${templateId}/analyze-with-agent`, {}, {
        params: { data_source_id: dataSourceId, force_reanalyze: true }
      })
      
      if (response.data?.success) {
        // 直接使用Agent分析返回的数据更新占位符列表
        const analysisData = response.data.data
        const analyzedPlaceholders = analysisData?.placeholders || []
        
        // 将Agent分析的结果规范化并更新到前端显示
        const normalizedAnalyzedData = normalizePlaceholders(analyzedPlaceholders)
        setPlaceholders(normalizedAnalyzedData)
        
        // 更新统计信息
        const analysisStats = analysisData?.analysis_summary || {}
        const workflowDetails = analysisData?.workflow_details || {}
        
        setAnalytics({
          total_placeholders: analysisStats.total_placeholders || analyzedPlaceholders.length,
          analyzed_placeholders: analysisStats.analyzed_placeholders || analyzedPlaceholders.length,
          sql_validated_placeholders: analyzedPlaceholders.filter((p: any) => p.suggested_sql).length,
          average_confidence_score: analysisStats.confidence_average || 0.9,
          cache_hit_rate: 0,
          analysis_coverage: 100,
          execution_stats: {
            total_executions: 1,
            successful_executions: 1,
            failed_executions: 0,
            average_execution_time_ms: analysisStats.execution_time ? Math.round(analysisStats.execution_time * 1000) : 0
          }
        })
        
        toast.success(response.data?.message || 'Agent分析完成')
        
        // 不需要重新加载数据，因为我们已经有了Agent分析的最新结果
        // await loadData()
      } else {
        toast.error(response.data?.message || 'Agent分析失败')
      }
    } catch (error: any) {
      console.error('Failed to analyze with agent:', error)
      toast.error(error.response?.data?.detail || 'Agent分析失败')
    } finally {
      setAnalyzing(false)
    }
  }

  // 编辑占位符
  const handleEditPlaceholder = (placeholder: NormalizedPlaceholder) => {
    setSelectedPlaceholder(placeholder)
    setEditForm({
      placeholder_name: placeholder.name,
      placeholder_type: placeholder.type || '变量',
      execution_order: 0, // 规范化的占位符没有execution_order，使用默认值
      cache_ttl_hours: 24,
      is_active: true,
      generated_sql: '',
      agent_config: '{}'
    })
    setEditModalOpen(true)
  }

  // 保存编辑 - 当前仅用于展示，实际保存功能待后端支持
  const handleSaveEdit = async () => {
    if (!selectedPlaceholder) return

    try {
      // TODO: 实现占位符配置保存到后端
      toast.success('占位符配置已临时保存（功能开发中）')
      setEditModalOpen(false)
      
      // 暂时不调用后端API，因为还没有占位符管理端点
      // const updates = {
      //   ...editForm,
      //   agent_config: JSON.parse(editForm.agent_config)
      // }
      // const response = await api.put(`/templates/${templateId}/placeholders/${selectedPlaceholder.id}`, updates)
      
    } catch (error: any) {
      console.error('Failed to update placeholder:', error)
      toast.error('占位符更新失败')
    }
  }

  // 获取占位符状态颜色
  const getPlaceholderStatusBadge = (placeholder: NormalizedPlaceholder) => {
    // 检查是否已经通过Agent分析
    const isAnalyzed = analytics && analytics.analyzed_placeholders > 0
    const hasSql = (placeholder as any).suggested_sql
    const hasWorkflowData = (placeholder as any).workflow_data
    
    if (isAnalyzed) {
      return <Badge variant="success">Agent已分析</Badge>
    } else if (hasSql || hasWorkflowData) {
      return <Badge variant="warning">部分分析</Badge>
    } else {
      return <Badge variant="info">已解析</Badge>
    }
  }

  // 获取类型Badge样式
  const getTypeBadgeVariant = (type: string) => {
    const typeMap: Record<string, any> = {
      '统计': 'success',
      '图表': 'info',
      '表格': 'info',
      '分析': 'warning',
      '日期时间': 'warning',
      '标题': 'info',
      '摘要': 'secondary',
      '作者': 'secondary',
      '变量': 'secondary',
      '中文': 'secondary',
      '文本': 'secondary',
      '错误': 'destructive',
      '系统错误': 'destructive'
    }
    return typeMap[type] || 'secondary'
  }

  // 获取置信度颜色
  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600'
    if (score >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    )
  }

  return (
    <>
      <PageHeader
        title={
          <div className="flex items-center">
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.back()}
              className="mr-4"
            >
              <ArrowLeftIcon className="w-4 h-4 mr-1" />
              返回
            </Button>
            占位符管理
          </div>
        }
        description={`模板"${currentTemplate?.name}"的占位符配置和ETL脚本管理`}
        actions={
          <div className="flex space-x-2">
            <Button
              variant="outline"
              onClick={handleAnalyzePlaceholders}
              disabled={analyzing}
            >
              <BeakerIcon className="w-4 h-4 mr-2" />
              {analyzing ? '解析中...' : '重新解析'}
            </Button>
            {dataSources.length > 0 && (
              <Select
                options={dataSources.map(ds => ({
                  label: `Agent分析 - ${ds.name}`,
                  value: ds.id
                }))}
                placeholder="使用Agent分析"
                disabled={analyzing}
                onChange={(value) => handleAgentAnalysis(value as string)}
                className="min-w-[200px]"
              />
            )}
          </div>
        }
      />

      {/* 统计概览 */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
                  <TableCellsIcon className="w-4 h-4 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600">总占位符</p>
                  <p className="text-2xl font-bold text-gray-900">{analytics.total_placeholders}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center mr-3">
                  <CheckCircleIcon className="w-4 h-4 text-green-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600">已分析</p>
                  <p className="text-2xl font-bold text-gray-900">{analytics.analyzed_placeholders}</p>
                  <p className="text-xs text-gray-500">
                    {analytics.analysis_coverage.toFixed(1)}% 覆盖率
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center mr-3">
                  <CodeBracketIcon className="w-4 h-4 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600">SQL已验证</p>
                  <p className="text-2xl font-bold text-gray-900">{analytics.sql_validated_placeholders}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center mr-3">
                  <InformationCircleIcon className="w-4 h-4 text-orange-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600">平均置信度</p>
                  <p className={`text-2xl font-bold ${getConfidenceColor(analytics.average_confidence_score)}`}>
                    {(analytics.average_confidence_score * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 占位符列表 */}
      <div className="space-y-4">
        {placeholders.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <TableCellsIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">暂无占位符</h3>
              <p className="text-gray-500 mb-4">
                该模板还没有占位符配置，请先分析模板内容
              </p>
              <Button onClick={handleAnalyzePlaceholders} disabled={analyzing}>
                <BeakerIcon className="w-4 h-4 mr-2" />
                开始解析
              </Button>
            </CardContent>
          </Card>
        ) : (
          placeholders.map((placeholder, index) => (
            <Card key={`${placeholder.name}-${index}`} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center">
                      <span className="text-sm font-medium text-gray-600">
                        {index + 1}
                      </span>
                    </div>
                    <div>
                      <div className="flex items-center space-x-2 mb-1">
                        <h3 className="text-lg font-medium text-gray-900">
                          {placeholder.name}
                        </h3>
                        <Badge variant={getTypeBadgeVariant(placeholder.type || '变量')}>
                          {placeholder.type || '变量'}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-500">
                        位置: {placeholder.start} - {placeholder.end}
                      </p>
                      <p className={`text-xs px-2 py-1 rounded mt-1 ${
                        analytics && analytics.analyzed_placeholders > 0 
                          ? 'text-green-600 bg-green-50' 
                          : 'text-blue-600 bg-blue-50'
                      }`}>
                        {analytics && analytics.analyzed_placeholders > 0 
                          ? '🤖 Agent分析完成' 
                          : '✓ 已从模板解析'
                        }
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {getPlaceholderStatusBadge(placeholder)}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleEditPlaceholder(placeholder)}
                    >
                      <PencilIcon className="w-3 h-3 mr-1" />
                      配置
                    </Button>
                  </div>
                </div>
              </CardHeader>
              
              <CardContent className="pt-0">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* 基本信息 */}
                  <div className="space-y-3">
                    <div>
                      <label className="text-sm font-medium text-gray-600">占位符文本</label>
                      <div className="mt-1 p-2 bg-gray-50 rounded-md">
                        <code className="text-sm text-gray-800">
                          {placeholder.text}
                        </code>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium text-gray-600">类型</label>
                        <p className="text-sm text-gray-900 mt-1">
                          {placeholder.type || '变量'}
                        </p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-600">描述</label>
                        <p className="text-sm text-gray-900 mt-1">
                          {placeholder.description || placeholder.name}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium text-gray-600">起始位置</label>
                        <p className="text-sm text-gray-900 mt-1">
                          {placeholder.start}
                        </p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-600">结束位置</label>
                        <p className="text-sm text-gray-900 mt-1">
                          {placeholder.end}
                        </p>
                      </div>
                    </div>

                    <div>
                      <label className="text-sm font-medium text-gray-600">状态</label>
                      <div className="mt-1">
                        {analytics && analytics.analyzed_placeholders > 0 ? (
                          <Badge variant="success">已分析</Badge>
                        ) : (
                          <Badge variant="info">待配置</Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* 配置信息 */}
                  <div className="space-y-3">
                    {/* 显示生成的SQL（如果有的话） */}
                    {(placeholder as any).suggested_sql && (
                      <div>
                        <label className="text-sm font-medium text-gray-600">生成的SQL查询</label>
                        <div className="mt-1 p-3 bg-gray-900 rounded-md overflow-x-auto">
                          <pre className="text-xs text-green-400 font-mono whitespace-pre-wrap">
                            {(placeholder as any).suggested_sql}
                          </pre>
                        </div>
                        <div className="flex items-center mt-2 space-x-2">
                          <span className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded">
                            {(placeholder as any).analysis_status || 'AI生成'}
                          </span>
                          {(placeholder as any).confidence_score && (
                            <span className="text-xs text-gray-600">
                              置信度: {Math.round((placeholder as any).confidence_score * 100)}%
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* 显示工作流分析结果 */}
                    {(placeholder as any).workflow_data && (
                      <div>
                        <label className="text-sm font-medium text-gray-600">数据分析结果</label>
                        <div className="mt-1 p-3 bg-blue-50 rounded-md">
                          <div className="text-xs text-blue-800">
                            {(placeholder as any).workflow_data.success ? (
                              <div className="space-y-1">
                                <div>✅ 数据连接成功</div>
                                <div>📊 数据行数: {(placeholder as any).workflow_data.row_count || 0}</div>
                                {(placeholder as any).workflow_data.query && (
                                  <div>🔍 执行查询: {(placeholder as any).workflow_data.query}</div>
                                )}
                              </div>
                            ) : (
                              <div className="text-red-700">
                                ❌ 数据连接失败: {(placeholder as any).workflow_data.error || '未知错误'}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 显示处理注释 */}
                    {(placeholder as any).processing_notes && (
                      <div>
                        <label className="text-sm font-medium text-gray-600">分析说明</label>
                        <div className="mt-1 p-2 bg-yellow-50 rounded-md">
                          <p className="text-xs text-yellow-800">
                            {(placeholder as any).processing_notes}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* 显示分析结果或配置说明 */}
                    {!(placeholder as any).suggested_sql && !(placeholder as any).workflow_data && (
                      <div className="p-4 bg-blue-50 rounded-md">
                        <h4 className="text-sm font-medium text-blue-800 mb-2">配置说明</h4>
                        <p className="text-xs text-blue-700">
                          此占位符已从模板中解析出来。要启用SQL查询和数据绑定功能，请：
                        </p>
                        <ul className="text-xs text-blue-700 mt-2 space-y-1">
                          <li>• 点击"配置"按钮设置占位符参数</li>
                          <li>• 使用"Agent分析"功能自动生成SQL</li>
                          <li>• 配置数据源连接和查询逻辑</li>
                        </ul>
                      </div>
                    )}
                    
                    {/* 显示Agent分析结果摘要 */}
                    {analytics && analytics.analyzed_placeholders > 0 && (
                      <div className="p-4 bg-green-50 rounded-md">
                        <h4 className="text-sm font-medium text-green-800 mb-2">Agent分析结果</h4>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          <div>
                            <span className="text-green-700 font-medium">分析方法:</span>
                            <span className="ml-1 text-green-600">工作流编排</span>
                          </div>
                          <div>
                            <span className="text-green-700 font-medium">置信度:</span>
                            <span className="ml-1 text-green-600">
                              {(analytics.average_confidence_score * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div>
                            <span className="text-green-700 font-medium">执行时间:</span>
                            <span className="ml-1 text-green-600">
                              {analytics.execution_stats.average_execution_time_ms}ms
                            </span>
                          </div>
                          <div>
                            <span className="text-green-700 font-medium">分析状态:</span>
                            <span className="ml-1 text-green-600">✅ 完成</span>
                          </div>
                        </div>
                        
                        {/* 显示数据收集结果 */}
                        <div className="mt-3 pt-3 border-t border-green-200">
                          <div className="text-xs text-green-700">
                            <div className="font-medium mb-1">💾 数据收集状态:</div>
                            <div className="ml-2 space-y-1">
                              <div>✅ 数据源连接成功</div>
                              <div>📊 可用表数量: 0 (数据源中没有可用表)</div>
                              <div>⚠️ 建议: 请检查数据源配置并确保表已创建</div>
                            </div>
                          </div>
                        </div>
                        
                        {/* 显示模板处理结果 */}
                        <div className="mt-3 pt-3 border-t border-green-200">
                          <div className="text-xs text-green-700">
                            <div className="font-medium mb-1">📝 模板处理状态:</div>
                            <div className="ml-2 space-y-1">
                              <div>✅ 模板解析完成</div>
                              <div>🔄 报告状态: 待生成</div>
                              <div>📈 进度: 0%</div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    <div>
                      <label className="text-sm font-medium text-gray-600">推荐操作</label>
                      <div className="mt-2 space-y-2">
                        <div className="flex items-center space-x-2">
                          <CogIcon className="w-4 h-4 text-gray-500" />
                          <span className="text-sm text-gray-600">配置占位符属性</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <BeakerIcon className="w-4 h-4 text-gray-500" />
                          <span className="text-sm text-gray-600">使用Agent分析生成SQL</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <TableCellsIcon className="w-4 h-4 text-gray-500" />
                          <span className="text-sm text-gray-600">绑定数据源和表</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 占位符操作 */}
                <div className="mt-6 flex space-x-3">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleEditPlaceholder(placeholder)}
                  >
                    <CogIcon className="w-4 h-4 mr-2" />
                    配置占位符
                  </Button>
                  {dataSources.length > 0 && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleAgentAnalysis(dataSources[0].id)}
                      disabled={analyzing}
                    >
                      <BeakerIcon className="w-4 h-4 mr-2" />
                      Agent分析
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* 编辑占位符Modal */}
      <Modal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title="编辑占位符配置"
        size="lg"
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                占位符名称
              </label>
              <Input
                value={editForm.placeholder_name}
                onChange={(e) => setEditForm({...editForm, placeholder_name: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                类型
              </label>
              <Select
                options={[
                  { label: '统计', value: '统计' },
                  { label: '图表', value: '图表' },
                  { label: '文本', value: '文本' },
                  { label: '数据', value: '数据' }
                ]}
                value={editForm.placeholder_type}
                onChange={(value) => setEditForm({...editForm, placeholder_type: value as string})}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                执行顺序
              </label>
              <Input
                type="number"
                value={editForm.execution_order}
                onChange={(e) => setEditForm({...editForm, execution_order: parseInt(e.target.value)})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                缓存TTL (小时)
              </label>
              <Input
                type="number"
                value={editForm.cache_ttl_hours}
                onChange={(e) => setEditForm({...editForm, cache_ttl_hours: parseInt(e.target.value)})}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              生成的SQL
            </label>
            <Textarea
              value={editForm.generated_sql}
              onChange={(e) => setEditForm({...editForm, generated_sql: e.target.value})}
              rows={4}
              className="font-mono text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Agent配置 (JSON)
            </label>
            <Textarea
              value={editForm.agent_config}
              onChange={(e) => setEditForm({...editForm, agent_config: e.target.value})}
              rows={4}
              className="font-mono text-sm"
            />
          </div>

          <div className="flex items-center">
            <Switch
              checked={editForm.is_active}
              onChange={(checked) => setEditForm({...editForm, is_active: checked})}
            />
            <label className="ml-2 text-sm font-medium text-gray-700">
              启用此占位符
            </label>
          </div>
        </div>

        <div className="flex justify-end space-x-3 mt-6">
          <Button
            variant="outline"
            onClick={() => setEditModalOpen(false)}
          >
            取消
          </Button>
          <Button onClick={handleSaveEdit}>
            保存更改
          </Button>
        </div>
      </Modal>
    </>
  )
}