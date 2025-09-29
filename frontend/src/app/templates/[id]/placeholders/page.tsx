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
  ClipboardDocumentIcon,
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
import { InlineAnalysisProgress } from '@/components/ui/InlineAnalysisProgress'
import { InlineTestProgress } from '@/components/ui/InlineTestProgress'
import toast from 'react-hot-toast'

export default function TemplatePlaceholdersPage() {
  const params = useParams()
  const router = useRouter()
  const templateId = params.id as string
  
  const { currentTemplate, getTemplate } = useTemplateStore()
  const [placeholders, setPlaceholders] = useState<NormalizedPlaceholder[]>([])
  const [analytics, setAnalytics] = useState<PlaceholderAnalytics | null>(null)
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [selectedDataSource, setSelectedDataSource] = useState<string>(() => {
    // 从localStorage恢复数据源选择
    if (typeof window !== 'undefined') {
      return localStorage.getItem(`selectedDataSource_${templateId}`) || ''
    }
    return ''
  })
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzingSingle, setAnalyzingSingle] = useState<{[key: string]: boolean}>({})
  const [validating, setValidating] = useState<{[key: string]: boolean}>({})
  const [testResults, setTestResults] = useState<{[key: string]: any}>({})
  
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
    description: ''
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
      const [templateResult, placeholdersResult, savedPlaceholdersResult, dataSourcesResult] = await Promise.allSettled([
        getTemplate(templateId),
        api.get(`/templates/${templateId}/preview`), // 使用预览API获取占位符
        api.get(`/placeholders/?template_id=${templateId}`), // 获取已保存的占位符配置
        api.get('/data-sources')
      ])

      // 处理占位符数据 - 合并预览API和已保存的配置
      if (placeholdersResult.status === 'fulfilled') {
        const placeholderData = placeholdersResult.value.data?.data || placeholdersResult.value.data || {}
        const rawPlaceholders = placeholderData.placeholders || []
        
        // 使用工具函数规范化占位符数据
        let normalizedPlaceholdersData = normalizePlaceholders(rawPlaceholders)
        
        // 合并已保存的占位符配置
        if (savedPlaceholdersResult.status === 'fulfilled') {
          const savedData = savedPlaceholdersResult.value.data?.data || []

          // 🔧 添加调试日志
          console.log('🔧 [Debug] 从数据库加载的占位符数据:', savedData)
          console.log('🔧 [Debug] 当前规范化的占位符:', normalizedPlaceholdersData.map(p => ({ name: p.name, generated_sql: p.generated_sql })))

          const savedPlaceholdersMap = new Map(
            savedData.map((p: any) => [p.placeholder_name || p.name, p])
          )

          // 🔧 调试映射关系
          console.log('🔧 [Debug] 占位符映射关系:')
          savedPlaceholdersMap.forEach((value, key) => {
            console.log(`  "${key}" -> generated_sql: "${(value as any).generated_sql}"`)
          })

          // 将保存的分析结果合并到规范化数据中
          normalizedPlaceholdersData = normalizedPlaceholdersData.map(placeholder => {
            const savedPlaceholder = savedPlaceholdersMap.get(placeholder.name) as any
            if (savedPlaceholder) {
              console.log(`🔧 [Debug] 合并占位符 "${placeholder.name}":`, {
                原始: placeholder.generated_sql,
                数据库: savedPlaceholder.generated_sql,
                最终: savedPlaceholder.generated_sql || ''
              })
              return {
                ...placeholder,
                id: savedPlaceholder.id, // 添加数据库ID
                generated_sql: savedPlaceholder.generated_sql || '',
                suggested_sql: savedPlaceholder.generated_sql || '',
                analysis: savedPlaceholder.description || savedPlaceholder.analysis || '',
                confidence_score: savedPlaceholder.confidence_score || 0,
                sql_validated: savedPlaceholder.sql_validated || false,
                agent_analyzed: true,
                status: 'analyzed'
              } as any
            }
            return placeholder
          })

          // 🔧 最终结果调试
          console.log('🔧 [Debug] 合并后的占位符数据:', normalizedPlaceholdersData.map(p => ({
            name: p.name,
            generated_sql: (p as any).generated_sql,
            id: (p as any).id
          })))
        }
        
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

  // 单个占位符分析 - 增加超时时间和进度指示器
  const handleAnalyzeSinglePlaceholder = async (placeholder: NormalizedPlaceholder) => {
    if (!selectedDataSource) {
      toast.error('请先选择数据源')
      return
    }

    const placeholderKey = placeholder.name
    try {
      setAnalyzingSingle(prev => ({ ...prev, [placeholderKey]: true }))

      // 使用更长的超时时间（90秒）和显示进度
      const response = await api.post('/placeholders/analyze', {
        placeholder_name: placeholder.name,
        placeholder_text: placeholder.text,
        template_id: templateId,
        data_source_id: selectedDataSource,
        template_context: currentTemplate?.content || ''
      }, {
        timeout: 90000 // 90秒超时
      })

      // 检查响应结构，API可能直接返回数据而不是包装的格式
      const result = response.data?.data || response.data
      const isSuccess = response.data?.success !== undefined ? response.data.success : (result && result.generated_sql)

      // 🔧 添加调试信息
      console.log('🔧 [Debug] API响应结构:', response.data)
      console.log('🔧 [Debug] 提取的result:', result)
      console.log('🔧 [Debug] isSuccess:', isSuccess)
      console.log('🔧 [Debug] generated_sql:', result?.generated_sql)
      
      if (isSuccess && result) {
        // 检查是否有验证结果（周期性占位符会直接包含验证结果）
        if (result.test_result) {
          setTestResults(prev => ({
            ...prev,
            [placeholderKey]: result.test_result
          }))
        } else {
          // 清除该占位符的验证结果，因为SQL可能已经改变
          setTestResults(prev => {
            const updated = { ...prev }
            delete updated[placeholderKey]
            return updated
          })
        }

        // 使用callback形式的setState来确保获取最新状态
        setPlaceholders(currentPlaceholders => {
          // 寻找匹配的占位符
          let targetIndex = -1
          let matchedPlaceholder = null

          for (let i = 0; i < currentPlaceholders.length; i++) {
            const p = currentPlaceholders[i]
            if (p.name === placeholder.name && p.text === placeholder.text) {
              targetIndex = i
              matchedPlaceholder = p
              break
            }
          }

          if (targetIndex === -1) {
            return currentPlaceholders
          }

          // 创建新的数组，更新指定索引的占位符
          const updatedPlaceholders = [...currentPlaceholders]
          updatedPlaceholders[targetIndex] = {
            ...matchedPlaceholder,
            id: result.placeholder_id || matchedPlaceholder?.id, // 保存数据库ID
            generated_sql: typeof result.generated_sql === 'object' ? result.generated_sql.sql || result.generated_sql[placeholder.name] : result.generated_sql,
            suggested_sql: typeof result.generated_sql === 'object' ? result.generated_sql.sql || result.generated_sql[placeholder.name] : result.generated_sql,
            analysis: result.analysis || result.analysis_result?.description,
            agent_analyzed: true,
            sql_validated: result.sql_validated,
            confidence_score: result.confidence_score,
            status: result.test_result ? 'tested' : 'analyzed',
            // 设置验证结果
            last_test_result: result.test_result,
            // 数据库保存状态
            db_saved: result.placeholder_db_saved
          } as any

          return updatedPlaceholders
        })

        // 根据是否是周期性占位符显示不同的成功消息
        if (result.test_result && result.test_result.result_type === 'period_value') {
          toast.success(`周期性占位符分析完成：${result.test_result.computed_value}`)
        } else {
          toast.success('占位符分析完成，SQL已自动保存')
        }

        // 💾 可选：重新加载数据以确保数据一致性（可以注释掉以提高性能）
        // setTimeout(() => loadData(), 1000)
      } else {
        toast.error(response.data?.message || '分析失败')
      }
    } catch (error: any) {
      console.error('Failed to analyze placeholder:', error)
      toast.error(error.response?.data?.detail || '分析失败')
    } finally {
      setAnalyzingSingle(prev => ({ ...prev, [placeholderKey]: false }))
    }
  }

  // SQL验证
  const handleValidateSQL = async (placeholder: NormalizedPlaceholder) => {
    const sql = typeof (placeholder as any).generated_sql === 'object' ? 
      (placeholder as any).generated_sql.sql || (placeholder as any).generated_sql[(placeholder as any).name] : 
      (placeholder as any).generated_sql
    if (!sql) {
      toast.error('请先分析占位符生成SQL')
      return
    }

    if (!selectedDataSource) {
      toast.error('请先选择数据源')
      return
    }

    const validationKey = placeholder.name
    try {
      setValidating(prev => ({ ...prev, [validationKey]: true }))
      toast.loading('正在验证SQL...', { duration: 1000 })
      
      const response = await api.post('/placeholders/validate-sql', {
        sql_template: sql,
        data_source_id: selectedDataSource,
        placeholder_name: placeholder.name,
        execution_mode: 'test',
        days_offset: -1
      })
      
      if (response.data?.success) {
        const validationResult = response.data.data
        const testResult = {
          success: validationResult.execution_success || false,
          error: validationResult.error_message || '',
          data: validationResult.result_data || [],
          columns: validationResult.columns || [],
          row_count: validationResult.row_count || 0,
          execution_time_ms: validationResult.execution_time_ms || 0,
          sql_after_substitution: validationResult.sql_after_substitution || sql
        }
        setTestResults(prev => ({ ...prev, [validationKey]: testResult }))
        
        // 更新占位符状态
        setPlaceholders(prev => 
          prev.map(p => 
            p.name === placeholder.name 
              ? { 
                  ...p, 
                  last_test_result: testResult,
                  status: testResult.success ? 'tested' : 'error'
                } as any
              : p
          )
        )
        
        toast.success('SQL验证完成')
      } else {
        toast.error(response.data?.message || 'SQL验证失败')
      }
    } catch (error: any) {
      console.error('Failed to validate SQL:', error)
      toast.error(error.response?.data?.detail || 'SQL验证失败')
    } finally {
      setValidating(prev => ({ ...prev, [validationKey]: false }))
    }
  }

  // 复制SQL到剪贴板
  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast.success('SQL已复制到剪贴板')
    } catch (error) {
      toast.error('复制失败')
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
      generated_sql: (placeholder as any).generated_sql || '',
      description: placeholder.description || ''
    })
    setEditModalOpen(true)
  }

  // 保存编辑 - 连接到后端API
  const handleSaveEdit = async () => {
    if (!selectedPlaceholder) return

    try {
      // 准备更新数据
      const updateData = {
        generated_sql: editForm.generated_sql,
        execution_order: editForm.execution_order,
        cache_ttl_hours: editForm.cache_ttl_hours,
        is_active: editForm.is_active,
        placeholder_type: editForm.placeholder_type,
        description: editForm.description
      }

      // 如果有placeholder ID，调用更新API
      if (selectedPlaceholder.id) {
        const response = await api.put(`/placeholders/${selectedPlaceholder.id}/sql`, updateData)

        if (response.data.success) {
          toast.success('占位符配置已保存')

          // 更新本地状态
          setPlaceholders(currentPlaceholders =>
            currentPlaceholders.map(p =>
              p.name === selectedPlaceholder.name && p.text === selectedPlaceholder.text
                ? { ...p, ...updateData }
                : p
            )
          )
        } else {
          toast.error(response.data.message || '保存失败')
        }
      } else {
        // 没有ID的占位符，提示用户先分析
        toast.error('请先分析占位符生成数据库记录')
      }

      setEditModalOpen(false)

    } catch (error: any) {
      console.error('Failed to update placeholder:', error)
      toast.error(error.response?.data?.detail || '占位符更新失败')
    }
  }

  // 获取占位符状态颜色
  const getPlaceholderStatusBadge = (placeholder: NormalizedPlaceholder) => {
    const hasGeneratedSql = (placeholder as any).generated_sql
    const hasSuggestedSql = (placeholder as any).suggested_sql
    const hasWorkflowData = (placeholder as any).workflow_data
    const status = (placeholder as any).status
    const testResult = testResults[placeholder.name]
    
    // 检查SQL验证状态
    if (testResult) {
      if (testResult.success) {
        return <Badge variant="success">已验证</Badge>
      } else {
        return <Badge variant="destructive">验证失败</Badge>
      }
    }
    
    // 检查是否有SQL生成
    if (hasGeneratedSql || hasSuggestedSql) {
      return <Badge variant="success">已解析</Badge>
    } else if (hasWorkflowData) {
      return <Badge variant="warning">部分分析</Badge>
    } else {
      return <Badge variant="secondary">未解析</Badge>
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
        description={`模板"${currentTemplate?.name}"的占位符配置，生成和验证SQL查询`}
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
          </div>
        }
      />

      {/* 数据源选择区域 */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">数据源配置</h3>
              <p className="text-sm text-gray-600">选择数据源用于占位符分析和SQL验证</p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="min-w-[300px]">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  选择数据源:
                </label>
                <Select
                  options={dataSources.map(ds => ({
                    label: `${ds.name} (${ds.source_type})`,
                    value: ds.id
                  }))}
                  placeholder="请选择数据源..."
                  value={selectedDataSource}
                  onChange={(value) => {
                    setSelectedDataSource(value as string)
                    // 保存到localStorage
                    if (typeof window !== 'undefined') {
                      localStorage.setItem(`selectedDataSource_${templateId}`, value as string)
                    }
                  }}
                  className="w-full"
                />
              </div>
              {selectedDataSource && (
                <div className="flex flex-col items-center">
                  <div className="text-xs text-green-600 mb-1">✅ 已选择</div>
                  <div className="text-xs text-gray-500">
                    {dataSources.find(ds => ds.id === selectedDataSource)?.name}
                  </div>
                </div>
              )}
            </div>
          </div>
          
          {selectedDataSource && (
            <div className="mt-4 p-3 bg-blue-50 rounded-md">
              <p className="text-sm text-blue-800">
                现在可以对占位符进行分析和SQL验证了
              </p>
            </div>
          )}
        </CardContent>
      </Card>

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
          placeholders.map((placeholder, index) => {
            const hasGeneratedSql = typeof (placeholder as any).generated_sql === 'object' ? 
              (placeholder as any).generated_sql.sql || (placeholder as any).generated_sql[(placeholder as any).name] : 
              (placeholder as any).generated_sql || (placeholder as any).suggested_sql
            const testResult = testResults[placeholder.name]
            const isValidatingThis = validating[placeholder.name]
            const isAnalyzingThis = analyzingSingle[placeholder.name]
            
            
            return (
              <Card key={`${placeholder.name}-${index}`} className="border border-gray-200 bg-white">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 p-4 relative">
                  {/* 左半部分：基本信息+配置 */}
                  <div className="space-y-3">
                    <div>
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="text-sm font-medium text-gray-900 mb-1">
                            {placeholder.name}
                          </h3>
                          <code className="text-xs text-gray-600 bg-gray-50 px-2 py-1 rounded">
                            {placeholder.text}
                          </code>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-gray-500">{placeholder.type || '变量'}</span>
                          {getPlaceholderStatusBadge(placeholder)}
                        </div>
                      </div>
                    </div>

                    {/* 操作按钮 */}
                    <div className="flex gap-2">
                      {!hasGeneratedSql ? (
                        <Button
                          size="sm"
                          onClick={() => handleAnalyzeSinglePlaceholder(placeholder)}
                          disabled={isAnalyzingThis || !selectedDataSource}
                          className="flex-1 text-xs bg-black text-white hover:bg-gray-800 disabled:bg-gray-300 disabled:text-gray-500"
                        >
                          {isAnalyzingThis ? '分析中' : '分析'}
                        </Button>
                      ) : (
                        <>
                          <Button
                            size="sm"
                            onClick={() => handleValidateSQL(placeholder)}
                            disabled={isValidatingThis || !selectedDataSource}
                            className="flex-1 text-xs bg-gray-800 text-white hover:bg-black disabled:bg-gray-300 disabled:text-gray-500"
                          >
                            {isValidatingThis ? '验证中' : '验证'}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleAnalyzeSinglePlaceholder(placeholder)}
                            disabled={isAnalyzingThis || !selectedDataSource}
                            className="text-xs border-gray-300 text-gray-600 hover:bg-gray-50 disabled:text-gray-400"
                          >
                            重新分析
                          </Button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* 右半部分：SQL+验证结果 */}
                  <div className="space-y-3">
                    {/* SQL区域 */}
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-gray-500">SQL</span>
                        {hasGeneratedSql && (
                          <button
                            onClick={() => copyToClipboard(
                              typeof hasGeneratedSql === 'object' ?
                                hasGeneratedSql.sql || hasGeneratedSql[placeholder.name] :
                                hasGeneratedSql
                            )}
                            className="text-xs text-gray-400 hover:text-gray-600"
                          >
                            复制
                          </button>
                        )}
                      </div>

                      {isAnalyzingThis ? (
                        <InlineAnalysisProgress
                          isAnalyzing={true}
                          placeholderName={placeholder.name}
                        />
                      ) : hasGeneratedSql ? (
                        <div className="bg-black rounded p-2 max-h-32 overflow-y-auto">
                          <pre className="text-xs text-gray-100 font-mono whitespace-pre-wrap">
                            {typeof hasGeneratedSql === 'object' ?
                              hasGeneratedSql.sql || hasGeneratedSql[placeholder.name] :
                              hasGeneratedSql}
                          </pre>
                        </div>
                      ) : (
                        <div className="bg-gray-50 rounded p-2 text-center">
                          <p className="text-xs text-gray-400">未生成</p>
                        </div>
                      )}
                    </div>

                    {/* 验证结果区域 */}
                    <div>
                      <span className="text-xs text-gray-500 mb-1 block">验证结果</span>

                      {isValidatingThis ? (
                        <InlineTestProgress
                          isTesting={true}
                          placeholderName={placeholder.name}
                        />
                      ) : testResult ? (
                        <div className={`p-2 rounded ${testResult.success ? 'bg-gray-50' : 'bg-gray-50'}`}>
                          {testResult.success ? (
                            <div className="space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="text-xs text-gray-800 font-medium">
                                  成功
                                </span>
                                <span className="text-xs text-gray-500">
                                  {testResult.execution_time_ms}ms
                                </span>
                              </div>

                              {/* 周期性占位符 */}
                              {testResult.result_type === 'period_value' ? (
                                <div className="bg-white border border-gray-200 rounded p-2 text-center">
                                  <div className="text-sm font-medium text-gray-900">
                                    {testResult.computed_value || testResult.data?.[0]?.[0] || '-'}
                                  </div>
                                  {testResult.period_info && (
                                    <div className="text-xs text-gray-500 mt-1">
                                      {testResult.period_info.start_date} ~ {testResult.period_info.end_date}
                                    </div>
                                  )}
                                </div>
                              ) : (
                                /* 常规SQL结果 */
                                <div>
                                  <span className="text-xs text-gray-500">{testResult.row_count} 行</span>
                                  {testResult.data && testResult.data.length > 0 && (
                                    <div className="mt-1 bg-white border border-gray-200 rounded overflow-hidden">
                                      <table className="w-full text-xs">
                                        <thead className="bg-gray-50">
                                          <tr>
                                            {testResult.columns?.slice(0, 3).map((col: string) => (
                                              <th key={col} className="px-2 py-1 text-left text-gray-600 font-normal">
                                                {col}
                                              </th>
                                            ))}
                                          </tr>
                                        </thead>
                                        <tbody>
                                          {testResult.data.slice(0, 2).map((row: any, i: number) => (
                                            <tr key={i} className="border-t border-gray-100">
                                              {Object.values(row).slice(0, 3).map((val: any, j: number) => (
                                                <td key={j} className="px-2 py-1 text-gray-700">
                                                  {String(val).substring(0, 15)}{String(val).length > 15 ? '...' : ''}
                                                </td>
                                              ))}
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          ) : (
                            <div>
                              <span className="text-xs text-gray-800 font-medium">失败</span>
                              <p className="text-xs text-gray-600 mt-1 bg-gray-50 p-1 rounded">
                                {testResult.error}
                              </p>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="bg-gray-50 rounded p-2 text-center">
                          <p className="text-xs text-gray-400">未验证</p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 右上角编辑按钮 */}
                  <button
                    onClick={() => handleEditPlaceholder(placeholder)}
                    className="absolute top-3 right-3 text-gray-400 hover:text-gray-600"
                  >
                    <PencilIcon className="w-4 h-4" />
                  </button>
                </div>
              </Card>
            )
          })
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