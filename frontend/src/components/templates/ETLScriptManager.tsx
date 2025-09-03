'use client'

import { useState, useEffect } from 'react'
import {
  CodeBracketIcon,
  PlayIcon,
  PauseIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  ClockIcon,
  TableCellsIcon,
  ArrowPathIcon,
  CloudArrowDownIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { Textarea } from '@/components/ui/Textarea'
import { Select } from '@/components/ui/Select'
import { Switch } from '@/components/ui/Switch'
import { Modal } from '@/components/ui/Modal'
import { ChartPreview } from '@/components/ui/ChartPreview'
import { PlaceholderConfig, PlaceholderValue, DataSource } from '@/types'
import { api } from '@/lib/api'
import { formatDateTime } from '@/utils'
import toast from 'react-hot-toast'

interface ETLScriptManagerProps {
  placeholder: PlaceholderConfig
  dataSources: DataSource[]
  onUpdate?: () => void
}

export function ETLScriptManager({ placeholder, dataSources, onUpdate }: ETLScriptManagerProps) {
  const [executing, setExecuting] = useState(false)
  const [testResult, setTestResult] = useState<PlaceholderValue | null>(null)
  const [isChartPlaceholder, setIsChartPlaceholder] = useState(false)
  const [selectedDataSource, setSelectedDataSource] = useState<string>('')
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [sqlQuery, setSqlQuery] = useState(placeholder.generated_sql || '')
  const [executionHistory, setExecutionHistory] = useState<PlaceholderValue[]>([])

  useEffect(() => {
    if (dataSources.length > 0 && !selectedDataSource) {
      setSelectedDataSource(dataSources[0].id)
    }
  }, [dataSources, selectedDataSource])

  // 检查是否为图表类占位符
  useEffect(() => {
    const isChart = placeholder.content_type === 'chart' || 
                   placeholder.content_type === 'image' ||
                   placeholder.placeholder_type === 'chart' ||
                   placeholder.placeholder_type === 'visualization'
    setIsChartPlaceholder(isChart)
  }, [placeholder])

  useEffect(() => {
    // 加载执行历史
    if (placeholder.id) {
      loadExecutionHistory()
    }
  }, [placeholder.id])

  // 加载执行历史
  const loadExecutionHistory = async () => {
    try {
      const res = await api.get(`/placeholders/${placeholder.id}/execution-history`)
      const payload = res?.data ?? res
      // 后端可能返回 {history: [...]} 或直接返回数组，做兼容处理
      const history: any[] = Array.isArray(payload)
        ? payload
        : (payload?.history ?? [])
      setExecutionHistory(history as any)
    } catch (error) {
      console.error('Failed to load execution history:', error)
      setExecutionHistory([])
    }
  }

  // 测试SQL查询并生成图表
  const handleTestQuery = async () => {
    if (!selectedDataSource || !placeholder.generated_sql) {
      toast.error('请选择数据源并确保有SQL查询')
      return
    }

    try {
      setExecuting(true)
      
      // 使用新的图表测试接口
      const res = await api.post(`/chart-test/placeholders/${placeholder.id}/test-chart`, {
        data_source_id: selectedDataSource,
        execution_mode: 'test_with_chart'  // 完整测试模式，生成图表
      })

      if (res?.success) {
        const d = res.data || res || {}
        
        // 兼容旧格式的同时支持新的图表功能
        const normalized: any = {
          ...d,
          success: Boolean(d.success),
          execution_time_ms: Number(d.execution_time_ms ?? d.execution_time ?? 0),
          row_count: Number(d.row_count ?? (Array.isArray(d.raw_data) ? d.raw_data.length : 0)),
          formatted_text: d.formatted_text ?? '',
          error_message: d.error_message ?? d.error ?? null,
          data: d.raw_data || d.data || [],
          sql_executed: d.sql_executed || '',
          
          // 新增图表相关字段
          chart_config: d.chart_config,
          chart_type: d.chart_type,
          echarts_config: d.echarts_config,
          chart_ready: Boolean(d.chart_ready),
          test_summary: d.test_summary,
          
          // 占位符类型信息
          is_chart_placeholder: d.is_chart_placeholder,
          placeholder_type_info: d.placeholder_type_info,
          
          full_result: d.full_result
        }
        
        setTestResult(normalized)
        
        // 根据占位符类型和结果显示不同的成功消息
        if (normalized.is_chart_placeholder === false) {
          toast.success('SQL查询测试成功')
        } else if (normalized.chart_ready) {
          toast.success(`图表生成成功！类型：${normalized.chart_type}，数据点：${normalized.row_count}`)
        } else {
          toast.success('SQL查询测试成功')
        }
        
        loadExecutionHistory() // 重新加载历史
      } else {
        // 根据占位符类型提供更友好的错误提示
        const baseMessage = res?.message || '测试失败'
        const errorMessage = isChartPlaceholder ? `图表生成失败: ${baseMessage}` : `SQL查询测试失败: ${baseMessage}`
        toast.error(errorMessage)
      }
    } catch (error: any) {
      console.error('Failed to test query:', error)
      const errorDetail = error.response?.data?.detail || '网络错误或服务异常'
      const errorMessage = isChartPlaceholder ? `图表生成异常: ${errorDetail}` : `SQL查询测试异常: ${errorDetail}`
      toast.error(errorMessage)
    } finally {
      setExecuting(false)
    }
  }

  // 更新SQL查询
  const handleUpdateSQL = async () => {
    try {
      const response = await api.put(`/templates/${placeholder.template_id}/placeholders/${placeholder.id}`, {
        generated_sql: sqlQuery
      })

      if (response.data?.success) {
        toast.success('SQL查询更新成功')
        setEditModalOpen(false)
        onUpdate?.()
      } else {
        toast.error(response.data?.message || 'SQL查询更新失败')
      }
    } catch (error: any) {
      console.error('Failed to update SQL:', error)
      toast.error(error.response?.data?.detail || 'SQL查询更新失败')
    }
  }

  // 验证SQL查询
  const handleValidateSQL = async () => {
    if (!selectedDataSource || !placeholder.generated_sql) {
      toast.error('请选择数据源并确保有SQL查询')
      return
    }

    try {
      const response = await api.post(`/placeholders/${placeholder.id}/validate-sql`, {
        data_source_id: selectedDataSource
      })

      if (response.data?.success) {
        toast.success('SQL查询验证成功')
        onUpdate?.()
      } else {
        toast.error(response.data?.message || 'SQL查询验证失败')
      }
    } catch (error: any) {
      console.error('Failed to validate SQL:', error)
      toast.error(error.response?.data?.detail || 'SQL查询验证失败')
    }
  }

  // 获取状态颜色
  const getStatusColor = () => {
    if (!placeholder.is_active) return 'text-gray-400'
    if (placeholder.sql_validated) return 'text-green-600'
    if (placeholder.agent_analyzed) return 'text-yellow-600'
    return 'text-red-600'
  }

  // 获取状态图标
  const getStatusIcon = () => {
    if (!placeholder.is_active) return <PauseIcon className="w-4 h-4" />
    if (placeholder.sql_validated) return <CheckCircleIcon className="w-4 h-4" />
    if (placeholder.agent_analyzed) return <ExclamationTriangleIcon className="w-4 h-4" />
    return <InformationCircleIcon className="w-4 h-4" />
  }

  // 格式化执行时间
  const formatExecutionTime = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  return (
    <div className="space-y-4">
      {/* ETL脚本信息 */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center bg-gray-100 ${getStatusColor()}`}>
                {getStatusIcon()}
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-900">ETL脚本状态</h3>
                <p className="text-xs text-gray-500">
                  {placeholder.sql_validated ? '已验证' : placeholder.agent_analyzed ? '需验证' : '待分析'}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant={placeholder.sql_validated ? 'success' : 'warning'}>
                置信度: {(placeholder.confidence_score * 100).toFixed(1)}%
              </Badge>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setSqlQuery(placeholder.generated_sql || '')
                  setEditModalOpen(true)
                }}
                disabled={!placeholder.generated_sql}
              >
                <CodeBracketIcon className="w-3 h-3 mr-1" />
                编辑SQL
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-0">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* SQL查询 */}
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium text-gray-600">生成的SQL查询</label>
                {placeholder.generated_sql ? (
                  <div className="mt-1 p-3 bg-gray-900 rounded-md">
                    <pre className="text-sm text-green-400 whitespace-pre-wrap overflow-x-auto">
                      {placeholder.generated_sql}
                    </pre>
                  </div>
                ) : (
                  <div className="mt-1 p-3 bg-gray-50 rounded-md text-center">
                    <p className="text-sm text-gray-500">暂无SQL查询</p>
                  </div>
                )}
              </div>

              {/* 测试区域 */}
              <div className="flex items-center space-x-2">
                <Select
                  options={dataSources.map(ds => ({
                    label: `${ds.name} (${ds.source_type})`,
                    value: ds.id
                  }))}
                  value={selectedDataSource}
                  onChange={(value) => setSelectedDataSource(value as string)}
                  placeholder="选择数据源"
                  className="flex-1"
                />
                <Button
                  size="sm"
                  onClick={handleTestQuery}
                  disabled={executing || !placeholder.generated_sql || !selectedDataSource}
                >
                  <PlayIcon className="w-3 h-3 mr-1" />
                  {executing ? '生成中...' : isChartPlaceholder ? '测试并生成图表' : '测试SQL查询'}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleValidateSQL}
                  disabled={!placeholder.generated_sql || !selectedDataSource}
                >
                  <CheckCircleIcon className="w-3 h-3 mr-1" />
                  验证SQL
                </Button>
              </div>
            </div>

            {/* 执行结果 */}
            <div className="space-y-3">
              {testResult ? (
                <div className="space-y-4">
                  <label className="text-sm font-medium text-gray-600">最新测试结果</label>
                  
                  {/* 基础执行信息 */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <span className="text-xs text-gray-600">执行状态</span>
                      <Badge variant={testResult.success ? 'success' : 'destructive'}>
                        {testResult.success ? '成功' : '失败'}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <span className="text-xs text-gray-600">执行时间</span>
                      <span className="text-xs font-mono">
                        {formatExecutionTime(testResult.execution_time_ms)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <span className="text-xs text-gray-600">返回行数</span>
                      <span className="text-xs font-mono">{testResult.row_count}</span>
                    </div>
                    
                    {/* 显示实际查询结果值 */}
                    {testResult.actual_result_value && (
                      <div className="flex items-center justify-between p-2 bg-blue-50 rounded">
                        <span className="text-xs text-gray-600">查询结果</span>
                        <span className="text-xs font-mono font-semibold text-blue-700">
                          {testResult.actual_result_value}
                        </span>
                      </div>
                    )}
                    
                    {/* 图表类型信息 */}
                    {testResult.chart_ready && testResult.chart_type && (
                      <div className="flex items-center justify-between p-2 bg-blue-50 rounded">
                        <span className="text-xs text-gray-600">图表类型</span>
                        <Badge variant="outline" className="text-xs">
                          {testResult.chart_type}
                        </Badge>
                      </div>
                    )}
                  </div>
                  
                  {/* 图表预览（仅图表类占位符显示） */}
                  {testResult.success && testResult.chart_ready && testResult.echarts_config && isChartPlaceholder && (
                    <div>
                      <ChartPreview
                        echartsConfig={testResult.echarts_config}
                        chartType={testResult.chart_type || 'bar_chart'}
                        chartData={testResult.data || []}
                        metadata={{
                          data_points: testResult.row_count,
                          generation_time: new Date().toISOString(),
                          data_source: {
                            sql_query: testResult.sql_executed,
                            execution_time_ms: testResult.execution_time_ms,
                            row_count: testResult.row_count,
                            data_quality_score: 0.8
                          }
                        }}
                        title={`${placeholder.placeholder_name} - 测试图表`}
                        className="mt-4"
                      />
                    </div>
                  )}

                  {/* 占位符类型说明（非图表类占位符） */}
                  {testResult.success && testResult.placeholder_type_info && !isChartPlaceholder && (
                    <div>
                      <label className="text-xs font-medium text-gray-600">占位符类型说明</label>
                      <div className="mt-1 p-2 bg-yellow-50 rounded text-xs text-yellow-700 border border-yellow-200">
                        <div className="flex items-start space-x-2">
                          <InformationCircleIcon className="w-4 h-4 flex-shrink-0 mt-0.5" />
                          <div>
                            <div className="font-medium">非图表类占位符</div>
                            <div className="mt-1">
                              类型: {testResult.placeholder_type_info.content_type} / {testResult.placeholder_type_info.placeholder_type}
                            </div>
                            <div className="mt-1 text-yellow-600">
                              {testResult.placeholder_type_info.message}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* 格式化文本结果（非图表模式） */}
                  {testResult.success && testResult.formatted_text && !testResult.chart_ready && (
                    <div>
                      <label className="text-xs font-medium text-gray-600">格式化结果</label>
                      <div className="mt-1 p-2 bg-blue-50 rounded text-xs">
                        {testResult.formatted_text}
                      </div>
                    </div>
                  )}
                  
                  {/* 错误信息 */}
                  {!testResult.success && testResult.error_message && (
                    <div>
                      <label className="text-xs font-medium text-gray-600">错误信息</label>
                      <div className="mt-1 p-2 bg-red-50 rounded text-xs text-red-700">
                        {testResult.error_message}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-6">
                  <TableCellsIcon className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">暂无测试结果</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {isChartPlaceholder ? '运行SQL查询测试以生成图表结果' : '运行SQL查询测试以查看结果'}
                  </p>
                </div>
              )}

              {/* 配置信息 */}
              <div className="space-y-2">
                <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <span className="text-xs text-gray-600">目标数据库</span>
                  <span className="text-xs font-mono">
                    {testResult?.target_database || placeholder.target_database || '未设置'}
                  </span>
                </div>
                <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <span className="text-xs text-gray-600">目标表</span>
                  <span className="text-xs font-mono">
                    {testResult?.target_table || placeholder.target_table || '未设置'}
                  </span>
                </div>
                <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <span className="text-xs text-gray-600">缓存TTL</span>
                  <span className="text-xs font-mono">{placeholder.cache_ttl_hours}小时</span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 执行历史 */}
      {executionHistory.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-900">执行历史</h3>
              <Button
                size="sm"
                variant="outline"
                onClick={loadExecutionHistory}
              >
                <ArrowPathIcon className="w-3 h-3 mr-1" />
                刷新
              </Button>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {executionHistory.slice(0, 10).map((execution, index) => (
                <div key={execution.id} className="flex items-center justify-between p-2 bg-gray-50 rounded text-xs">
                  <div className="flex items-center space-x-2">
                    <Badge variant={execution.success ? 'success' : 'destructive'} className="text-xs">
                      {execution.success ? '成功' : '失败'}
                    </Badge>
                    <span className="text-gray-600">
                      {formatExecutionTime(execution.execution_time_ms)}
                    </span>
                    <span className="text-gray-600">
                      {execution.row_count} 行
                    </span>
                  </div>
                  <div className="text-gray-500">
                    {formatDateTime(execution.created_at)}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 编辑SQL Modal */}
      <Modal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title="编辑SQL查询"
        size="lg"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              SQL查询语句
            </label>
            <Textarea
              value={sqlQuery}
              onChange={(e) => setSqlQuery(e.target.value)}
              rows={8}
              className="font-mono text-sm"
              placeholder="SELECT * FROM table WHERE condition"
            />
          </div>

          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <InformationCircleIcon className="w-4 h-4" />
            <span>请确保SQL语句符合目标数据库的语法规范</span>
          </div>
        </div>

        <div className="flex justify-end space-x-3 mt-6">
          <Button
            variant="outline"
            onClick={() => setEditModalOpen(false)}
          >
            取消
          </Button>
          <Button onClick={handleUpdateSQL}>
            保存SQL
          </Button>
        </div>
      </Modal>
    </div>
  )
}