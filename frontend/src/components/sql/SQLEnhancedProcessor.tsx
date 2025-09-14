'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Badge } from '@/components/ui/Badge'
import { Textarea } from '@/components/ui/Textarea'
import { Select } from '@/components/ui/Select'
import { Switch } from '@/components/ui/Switch'
import { Tabs } from '@/components/ui/Tabs'
import { Table } from '@/components/ui/Table'
import { useToast } from '@/hooks/useToast'

interface SQLEnhancedProcessorProps {
  onSqlGenerated?: (sql: string) => void
  onQueryExecuted?: (results: any) => void
  initialTaskDescription?: string
}

interface DataSource {
  id: string
  name: string
  source_type: string
  is_active: boolean
}

interface SQLExecutionResult {
  success: boolean
  data?: any[]
  columns?: string[]
  row_count?: number
  execution_time?: number
  execution_plan?: any
  error?: string
  warnings?: string[]
}

interface SQLAnalysisResult {
  success: boolean
  syntax_valid: boolean
  complexity_score?: number
  performance_issues?: string[]
  security_issues?: string[]
  optimization_suggestions?: string[]
  query_type?: string
  tables_accessed?: string[]
  estimated_cost?: number
  error?: string
}

export default function SQLEnhancedProcessor({ 
  onSqlGenerated,
  onQueryExecuted,
  initialTaskDescription = ""
}: SQLEnhancedProcessorProps) {
  // 基础状态
  const [taskDescription, setTaskDescription] = useState(initialTaskDescription)
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [selectedDataSource, setSelectedDataSource] = useState('')
  const [optimizationLevel, setOptimizationLevel] = useState('standard')
  const [includeComments, setIncludeComments] = useState(true)
  const [formatSql, setFormatSql] = useState(true)
  const [enableStreaming, setEnableStreaming] = useState(true)

  // SQL相关状态
  const [generatedSql, setGeneratedSql] = useState('')
  const [formattedSql, setFormattedSql] = useState('')
  const [sqlExplanation, setSqlExplanation] = useState('')
  const [executionResults, setExecutionResults] = useState<SQLExecutionResult | null>(null)
  const [analysisResults, setAnalysisResults] = useState<SQLAnalysisResult | null>(null)

  // 执行状态
  const [isGenerating, setIsGenerating] = useState(false)
  const [isExecuting, setIsExecuting] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [streamingLogs, setStreamingLogs] = useState<string[]>([])

  // 引用和工具
  const { showToast } = useToast()
  const streamingLogsRef = useRef<HTMLDivElement>(null)

  // 加载数据源
  useEffect(() => {
    loadDataSources()
  }, [])

  // 自动滚动流式日志
  useEffect(() => {
    if (streamingLogsRef.current) {
      streamingLogsRef.current.scrollTop = streamingLogsRef.current.scrollHeight
    }
  }, [streamingLogs])

  const loadDataSources = async () => {
    try {
      const response = await fetch('/api/v1/data-sources', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setDataSources(data)
        if (data.length > 0 && !selectedDataSource) {
          setSelectedDataSource(data[0].id)
        }
      }
    } catch (error) {
      console.error('加载数据源失败:', error)
      showToast('加载数据源失败', 'error')
    }
  }

  const addStreamingLog = (message: string) => {
    setStreamingLogs(prev => [...prev, `${new Date().toLocaleTimeString()}: ${message}`])
  }

  const generateSQL = async () => {
    if (!taskDescription.trim()) {
      showToast('请输入任务描述', 'error')
      return
    }

    if (!selectedDataSource) {
      showToast('请选择数据源', 'error')
      return
    }

    setIsGenerating(true)
    setStreamingLogs([])
    setGeneratedSql('')
    setFormattedSql('')
    setSqlExplanation('')

    try {
      if (enableStreaming) {
        // 流式生成
        const response = await fetch('/api/v1/sql/generate-stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify({
            task_description: taskDescription,
            data_source_id: selectedDataSource,
            optimization_level: optimizationLevel,
            include_comments: includeComments,
            format_sql: formatSql,
            enable_streaming: true
          })
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const reader = response.body?.getReader()
        const decoder = new TextDecoder()

        if (reader) {
          while (true) {
            const { done, value } = await reader.read()
            if (done) break

            const chunk = decoder.decode(value)
            const lines = chunk.split('\n')

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const eventData = JSON.parse(line.substring(6))
                  handleSQLStreamEvent(eventData)
                } catch (e) {
                  console.warn('解析流式数据失败:', e, line)
                }
              }
            }
          }
        }
      } else {
        // 标准生成
        const response = await fetch('/api/v1/sql/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify({
            task_description: taskDescription,
            data_source_id: selectedDataSource,
            optimization_level: optimizationLevel,
            include_comments: includeComments,
            format_sql: formatSql
          })
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const result = await response.json()
        if (result.success) {
          setGeneratedSql(result.sql_query)
          setFormattedSql(result.formatted_sql || result.sql_query)
          setSqlExplanation(result.explanation || '')
          
          if (onSqlGenerated) {
            onSqlGenerated(result.sql_query)
          }
          showToast('SQL生成成功', 'success')
        } else {
          throw new Error(result.error || 'SQL生成失败')
        }
      }

    } catch (error) {
      console.error('SQL生成失败:', error)
      showToast(`SQL生成失败: ${error}`, 'error')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleSQLStreamEvent = (event: any) => {
    switch (event.event_type) {
      case 'sql_generation_start':
        addStreamingLog('开始生成SQL查询...')
        break
      
      case 'data_source_loaded':
        addStreamingLog(`已连接数据源: ${event.data.source_name}`)
        break
      
      case 'agent_analysis_start':
        addStreamingLog('Agent开始智能分析任务需求...')
        break
      
      case 'sql_generated':
        setGeneratedSql(event.data.sql_query)
        setSqlExplanation(event.data.query_explanation || '')
        addStreamingLog(`SQL生成完成，复杂度: ${event.data.complexity}`)
        if (onSqlGenerated) {
          onSqlGenerated(event.data.sql_query)
        }
        break
      
      case 'sql_formatted':
        setFormattedSql(event.data.formatted_sql)
        addStreamingLog('SQL格式化完成')
        break
      
      case 'sql_generation_complete':
        addStreamingLog(`SQL生成流程完成，耗时: ${event.data.execution_time.toFixed(2)}秒`)
        showToast('SQL生成成功', 'success')
        break
      
      case 'error':
        addStreamingLog(`错误: ${event.data.error}`)
        showToast('SQL生成失败', 'error')
        break
      
      default:
        addStreamingLog(`收到事件: ${event.event_type}`)
    }
  }

  const executeSQL = async (dryRun = false) => {
    if (!generatedSql.trim()) {
      showToast('没有可执行的SQL查询', 'error')
      return
    }

    if (!selectedDataSource) {
      showToast('请选择数据源', 'error')
      return
    }

    setIsExecuting(true)
    setExecutionResults(null)

    try {
      const response = await fetch('/api/v1/sql/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          sql_query: generatedSql,
          data_source_id: selectedDataSource,
          limit_rows: 100,
          timeout_seconds: 30,
          explain_plan: false,
          dry_run: dryRun
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      setExecutionResults(result)

      if (result.success) {
        if (onQueryExecuted) {
          onQueryExecuted(result)
        }
        showToast(
          dryRun ? 'SQL语法验证通过' : `查询执行成功，返回 ${result.row_count} 行`, 
          'success'
        )
      } else {
        throw new Error(result.error || '查询执行失败')
      }

    } catch (error) {
      console.error('SQL执行失败:', error)
      showToast(`SQL执行失败: ${error}`, 'error')
      setExecutionResults({
        success: false,
        error: error.toString()
      })
    } finally {
      setIsExecuting(false)
    }
  }

  const analyzeSQL = async () => {
    if (!generatedSql.trim()) {
      showToast('没有可分析的SQL查询', 'error')
      return
    }

    setIsAnalyzing(true)
    setAnalysisResults(null)

    try {
      const response = await fetch('/api/v1/sql/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          sql_query: generatedSql,
          analysis_type: 'full'
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      setAnalysisResults(result)

      if (result.success) {
        showToast('SQL分析完成', 'success')
      } else {
        throw new Error(result.error || 'SQL分析失败')
      }

    } catch (error) {
      console.error('SQL分析失败:', error)
      showToast(`SQL分析失败: ${error}`, 'error')
      setAnalysisResults({
        success: false,
        syntax_valid: false,
        error: error.toString()
      })
    } finally {
      setIsAnalyzing(false)
    }
  }

  const formatSQLQuery = async () => {
    if (!generatedSql.trim()) {
      showToast('没有可格式化的SQL查询', 'error')
      return
    }

    try {
      const response = await fetch(`/api/v1/sql/format?sql=${encodeURIComponent(generatedSql)}&style=standard`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      
      if (result.success) {
        setFormattedSql(result.formatted_sql)
        showToast('SQL格式化成功', 'success')
      } else {
        throw new Error(result.error || 'SQL格式化失败')
      }

    } catch (error) {
      console.error('SQL格式化失败:', error)
      showToast(`SQL格式化失败: ${error}`, 'error')
    }
  }

  return (
    <div className="space-y-6">
      {/* SQL生成配置 */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">智能SQL生成</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">任务描述</label>
            <Textarea
              value={taskDescription}
              onChange={(e) => setTaskDescription(e.target.value)}
              placeholder="请描述您的数据查询需求，例如：查询2025年9月14日创建的用户信息"
              rows={3}
              disabled={isGenerating}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">数据源</label>
              <Select
                value={selectedDataSource}
                onChange={setSelectedDataSource}
                disabled={isGenerating}
              >
                <option value="">选择数据源</option>
                {dataSources.map(ds => (
                  <option key={ds.id} value={ds.id}>
                    {ds.name} ({ds.source_type})
                  </option>
                ))}
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">优化级别</label>
              <Select
                value={optimizationLevel}
                onChange={setOptimizationLevel}
                disabled={isGenerating}
              >
                <option value="basic">基础</option>
                <option value="standard">标准</option>
                <option value="advanced">高级</option>
                <option value="expert">专家</option>
              </Select>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                checked={includeComments}
                onCheckedChange={setIncludeComments}
                disabled={isGenerating}
              />
              <label className="text-sm font-medium">包含注释</label>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                checked={enableStreaming}
                onCheckedChange={setEnableStreaming}
                disabled={isGenerating}
              />
              <label className="text-sm font-medium">流式反馈</label>
            </div>
          </div>

          <div className="flex space-x-3">
            <Button
              onClick={generateSQL}
              disabled={isGenerating || !taskDescription.trim()}
              className="flex items-center space-x-2"
            >
              {isGenerating && <LoadingSpinner size="sm" />}
              <span>{isGenerating ? '生成中...' : '生成SQL'}</span>
            </Button>

            <Button
              onClick={formatSQLQuery}
              variant="outline"
              disabled={!generatedSql.trim()}
            >
              格式化
            </Button>

            <Button
              onClick={analyzeSQL}
              variant="outline"
              disabled={isAnalyzing || !generatedSql.trim()}
              className="flex items-center space-x-2"
            >
              {isAnalyzing && <LoadingSpinner size="sm" />}
              <span>{isAnalyzing ? '分析中...' : '分析SQL'}</span>
            </Button>
          </div>
        </div>
      </Card>

      {/* 流式日志 */}
      {enableStreaming && streamingLogs.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">生成日志</h3>
          <div 
            ref={streamingLogsRef}
            className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 h-32 overflow-y-auto font-mono text-sm"
          >
            {streamingLogs.map((log, index) => (
              <div key={index} className="text-green-600 dark:text-green-400">
                {log}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* SQL展示和操作 */}
      {generatedSql && (
        <Card className="p-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">生成的SQL查询</h3>
              <div className="flex space-x-2">
                <Button
                  onClick={() => executeSQL(true)}
                  variant="outline"
                  size="sm"
                  disabled={isExecuting}
                >
                  验证语法
                </Button>
                <Button
                  onClick={() => executeSQL(false)}
                  disabled={isExecuting || !selectedDataSource}
                  size="sm"
                  className="flex items-center space-x-2"
                >
                  {isExecuting && <LoadingSpinner size="sm" />}
                  <span>{isExecuting ? '执行中...' : '执行查询'}</span>
                </Button>
              </div>
            </div>

            <Tabs defaultValue="formatted">
              <div className="mb-4">
                <div className="flex space-x-1">
                  <button 
                    className="px-3 py-1 text-sm rounded-md bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
                    onClick={() => {/* Switch to formatted */}}
                  >
                    格式化SQL
                  </button>
                  <button 
                    className="px-3 py-1 text-sm rounded-md text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800"
                    onClick={() => {/* Switch to original */}}
                  >
                    原始SQL
                  </button>
                </div>
              </div>

              <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4">
                <pre className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap overflow-x-auto">
                  {formattedSql || generatedSql}
                </pre>
              </div>
            </Tabs>

            {sqlExplanation && (
              <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">查询说明</h4>
                <p className="text-blue-700 dark:text-blue-300 text-sm">{sqlExplanation}</p>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* SQL分析结果 */}
      {analysisResults && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">SQL分析结果</h3>
          
          <div className="space-y-4">
            <div className="flex items-center space-x-4">
              <Badge variant={analysisResults.syntax_valid ? 'success' : 'destructive'}>
                {analysisResults.syntax_valid ? '语法正确' : '语法错误'}
              </Badge>
              
              {analysisResults.complexity_score !== undefined && (
                <div className="text-sm">
                  <span className="font-medium">复杂度分数:</span>
                  <span className="ml-2">{analysisResults.complexity_score.toFixed(2)}</span>
                </div>
              )}

              {analysisResults.query_type && (
                <Badge variant="outline">{analysisResults.query_type}</Badge>
              )}
            </div>

            {analysisResults.performance_issues && analysisResults.performance_issues.length > 0 && (
              <div>
                <h4 className="font-medium text-yellow-700 dark:text-yellow-300 mb-2">性能问题</h4>
                <ul className="text-sm text-yellow-600 dark:text-yellow-400 space-y-1">
                  {analysisResults.performance_issues.map((issue, index) => (
                    <li key={index}>• {issue}</li>
                  ))}
                </ul>
              </div>
            )}

            {analysisResults.optimization_suggestions && analysisResults.optimization_suggestions.length > 0 && (
              <div>
                <h4 className="font-medium text-green-700 dark:text-green-300 mb-2">优化建议</h4>
                <ul className="text-sm text-green-600 dark:text-green-400 space-y-1">
                  {analysisResults.optimization_suggestions.map((suggestion, index) => (
                    <li key={index}>• {suggestion}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* 查询结果 */}
      {executionResults && (
        <Card className="p-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">查询结果</h3>
              <Badge variant={executionResults.success ? 'success' : 'destructive'}>
                {executionResults.success ? '执行成功' : '执行失败'}
              </Badge>
            </div>

            {executionResults.success && executionResults.data ? (
              <div className="space-y-4">
                <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                  <span>返回行数: {executionResults.row_count}</span>
                  {executionResults.execution_time && (
                    <span>执行时间: {executionResults.execution_time.toFixed(3)}秒</span>
                  )}
                </div>

                <div className="overflow-x-auto">
                  <Table>
                    <thead>
                      <tr>
                        {executionResults.columns?.map((column, index) => (
                          <th key={index} className="text-left">{column}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {executionResults.data.slice(0, 10).map((row, rowIndex) => (
                        <tr key={rowIndex}>
                          {executionResults.columns?.map((column, colIndex) => (
                            <td key={colIndex} className="py-2">
                              {row[column] !== null ? String(row[column]) : '(null)'}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </div>

                {(executionResults.row_count || 0) > 10 && (
                  <div className="text-sm text-gray-500 text-center">
                    显示前10行，共{executionResults.row_count}行
                  </div>
                )}
              </div>
            ) : executionResults.error && (
              <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <h4 className="font-medium text-red-900 dark:text-red-100 mb-2">执行错误</h4>
                <p className="text-red-700 dark:text-red-300 text-sm">{executionResults.error}</p>
              </div>
            )}

            {executionResults.warnings && executionResults.warnings.length > 0 && (
              <div className="bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                <h4 className="font-medium text-yellow-900 dark:text-yellow-100 mb-2">警告信息</h4>
                <ul className="text-yellow-700 dark:text-yellow-300 text-sm space-y-1">
                  {executionResults.warnings.map((warning, index) => (
                    <li key={index}>• {warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}