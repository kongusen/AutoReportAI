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
import { AppLayout } from '@/components/layout/AppLayout'
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
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

export default function TemplatePlaceholdersPage() {
  const params = useParams()
  const router = useRouter()
  const templateId = params.id as string
  
  const { currentTemplate, getTemplate } = useTemplateStore()
  const [placeholders, setPlaceholders] = useState<PlaceholderConfig[]>([])
  const [analytics, setAnalytics] = useState<PlaceholderAnalytics | null>(null)
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  
  // 编辑状态
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [selectedPlaceholder, setSelectedPlaceholder] = useState<PlaceholderConfig | null>(null)
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
        api.get(`/templates/${templateId}/placeholders`),
        api.get('/data-sources')
      ])

      // 处理占位符数据
      if (placeholdersResult.status === 'fulfilled') {
        const placeholderData = placeholdersResult.value.data?.data || placeholdersResult.value.data || []
        setPlaceholders(placeholderData.placeholders || [])
        
        // 计算分析统计
        const totalPlaceholders = placeholderData.total_placeholders || 0
        const analyzedPlaceholders = placeholderData.placeholders?.filter((p: PlaceholderConfig) => p.agent_analyzed).length || 0
        const sqlValidatedPlaceholders = placeholderData.placeholders?.filter((p: PlaceholderConfig) => p.sql_validated).length || 0
        const avgConfidence = placeholderData.placeholders?.reduce((sum: number, p: PlaceholderConfig) => sum + p.confidence_score, 0) / totalPlaceholders || 0
        
        setAnalytics({
          total_placeholders: totalPlaceholders,
          analyzed_placeholders: analyzedPlaceholders,
          sql_validated_placeholders: sqlValidatedPlaceholders,
          average_confidence_score: avgConfidence,
          cache_hit_rate: 0, // 暂时设为0，后续从缓存统计API获取
          analysis_coverage: totalPlaceholders > 0 ? (analyzedPlaceholders / totalPlaceholders) * 100 : 0,
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

  // 分析占位符
  const handleAnalyzePlaceholders = async () => {
    try {
      setAnalyzing(true)
      const response = await api.post(`/templates/${templateId}/analyze-placeholders`, {
        force_reparse: true
      })
      
      if (response.data?.success) {
        toast.success('占位符分析完成')
        await loadData() // 重新加载数据
      } else {
        toast.error(response.data?.message || '占位符分析失败')
      }
    } catch (error: any) {
      console.error('Failed to analyze placeholders:', error)
      toast.error(error.response?.data?.detail || '占位符分析失败')
    } finally {
      setAnalyzing(false)
    }
  }

  // 使用Agent分析
  const handleAgentAnalysis = async (dataSourceId: string) => {
    try {
      setAnalyzing(true)
      const response = await api.post(`/templates/${templateId}/analyze-with-agent`, {}, {
        params: { data_source_id: dataSourceId, force_reanalyze: true }
      })
      
      if (response.data?.success) {
        toast.success('Agent分析完成')
        await loadData()
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
  const handleEditPlaceholder = (placeholder: PlaceholderConfig) => {
    setSelectedPlaceholder(placeholder)
    setEditForm({
      placeholder_name: placeholder.placeholder_name,
      placeholder_type: placeholder.placeholder_type,
      execution_order: placeholder.execution_order,
      cache_ttl_hours: placeholder.cache_ttl_hours,
      is_active: placeholder.is_active,
      generated_sql: placeholder.generated_sql || '',
      agent_config: JSON.stringify(placeholder.agent_config || {}, null, 2)
    })
    setEditModalOpen(true)
  }

  // 保存编辑
  const handleSaveEdit = async () => {
    if (!selectedPlaceholder) return

    try {
      const updates = {
        ...editForm,
        agent_config: JSON.parse(editForm.agent_config)
      }
      
      const response = await api.put(`/templates/${templateId}/placeholders/${selectedPlaceholder.id}`, updates)
      
      if (response.data?.success) {
        toast.success('占位符更新成功')
        setEditModalOpen(false)
        await loadData()
      } else {
        toast.error(response.data?.message || '占位符更新失败')
      }
    } catch (error: any) {
      console.error('Failed to update placeholder:', error)
      toast.error(error.response?.data?.detail || '占位符更新失败')
    }
  }

  // 获取占位符状态颜色
  const getPlaceholderStatusBadge = (placeholder: PlaceholderConfig) => {
    if (!placeholder.is_active) {
      return <Badge variant="secondary">已禁用</Badge>
    }
    if (placeholder.agent_analyzed && placeholder.sql_validated) {
      return <Badge variant="success">已就绪</Badge>
    }
    if (placeholder.agent_analyzed) {
      return <Badge variant="warning">需验证</Badge>
    }
    return <Badge variant="destructive">待分析</Badge>
  }

  // 获取置信度颜色
  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600'
    if (score >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
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
              {analyzing ? '分析中...' : '重新分析'}
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
                开始分析
              </Button>
            </CardContent>
          </Card>
        ) : (
          placeholders.map((placeholder, index) => (
            <Card key={placeholder.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center">
                      <span className="text-sm font-medium text-gray-600">
                        {placeholder.execution_order}
                      </span>
                    </div>
                    <div>
                      <h3 className="text-lg font-medium text-gray-900">
                        {placeholder.placeholder_name}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {placeholder.placeholder_type} • {placeholder.content_type}
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
                      编辑
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
                          {placeholder.placeholder_text}
                        </code>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium text-gray-600">目标数据库</label>
                        <p className="text-sm text-gray-900 mt-1">
                          {placeholder.target_database || '未设置'}
                        </p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-600">目标表</label>
                        <p className="text-sm text-gray-900 mt-1">
                          {placeholder.target_table || '未设置'}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium text-gray-600">缓存TTL</label>
                        <p className="text-sm text-gray-900 mt-1">
                          {placeholder.cache_ttl_hours} 小时
                        </p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-600">置信度</label>
                        <p className={`text-sm font-medium mt-1 ${getConfidenceColor(placeholder.confidence_score)}`}>
                          {(placeholder.confidence_score * 100).toFixed(1)}%
                        </p>
                      </div>
                    </div>

                    {placeholder.analyzed_at && (
                      <div>
                        <label className="text-sm font-medium text-gray-600">分析时间</label>
                        <p className="text-sm text-gray-900 mt-1">
                          {formatRelativeTime(placeholder.analyzed_at)}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* SQL和配置 */}
                  <div className="space-y-3">
                    {placeholder.required_fields && Object.keys(placeholder.required_fields).length > 0 && (
                      <div>
                        <label className="text-sm font-medium text-gray-600">所需字段</label>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {Object.keys(placeholder.required_fields).map(field => (
                            <Badge key={field} variant="secondary" className="text-xs">
                              {field}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {placeholder.agent_config && (
                      <div>
                        <label className="text-sm font-medium text-gray-600">Agent配置</label>
                        <div className="mt-1 p-2 bg-gray-50 rounded-md">
                          <pre className="text-xs text-gray-700 whitespace-pre-wrap">
                            {JSON.stringify(placeholder.agent_config, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* ETL脚本管理 */}
                <div className="mt-6">
                  <ETLScriptManager 
                    placeholder={placeholder}
                    dataSources={dataSources}
                    onUpdate={loadData}
                  />
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
    </AppLayout>
  )
}