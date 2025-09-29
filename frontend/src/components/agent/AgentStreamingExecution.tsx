'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { Textarea } from '@/components/ui/Textarea'
import { Select } from '@/components/ui/Select'
import { Switch } from '@/components/ui/Switch'
import { useToast } from '@/hooks/useToast'
import AgentService, { AgentTaskRequest, AgentRunRequest } from '@/services/agentService'

interface AgentExecutionEvent {
  event_type: string
  timestamp: string
  data: any
  phase?: string
  progress?: number
}

interface AgentStreamingExecutionProps {
  onExecutionComplete?: (result: any) => void
  onSqlGenerated?: (sql: string, metadata: any) => void
  initialTaskDescription?: string
}

interface ExecutionLog {
  id: string
  timestamp: string
  type: 'info' | 'success' | 'warning' | 'error'
  phase?: string
  message: string
  data?: any
}

export default function AgentStreamingExecution({ 
  onExecutionComplete,
  onSqlGenerated,
  initialTaskDescription = ""
}: AgentStreamingExecutionProps) {
  const [taskDescription, setTaskDescription] = useState(initialTaskDescription)
  const [coordinationMode, setCoordinationMode] = useState('intelligent')
  const [enableStreaming, setEnableStreaming] = useState(true)
  const [sqlPreview, setSqlPreview] = useState(true)
  
  // 执行状态
  const [isExecuting, setIsExecuting] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentPhase, setCurrentPhase] = useState<string | null>(null)
  const [executionLogs, setExecutionLogs] = useState<ExecutionLog[]>([])
  
  // 结果状态
  const [executionResult, setExecutionResult] = useState<any>(null)
  const [generatedSql, setGeneratedSql] = useState<string | null>(null)
  const [sqlMetadata, setSqlMetadata] = useState<any>(null)
  
  // 引用
  const eventSourceRef = useRef<EventSource | null>(null)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const { showToast } = useToast()

  // 自动滚动到日志底部
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [executionLogs])

  // 清理EventSource
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
    }
  }, [])

  const addLog = (type: ExecutionLog['type'], message: string, phase?: string, data?: any) => {
    const newLog: ExecutionLog = {
      id: `${Date.now()}-${Math.random()}`,
      timestamp: new Date().toISOString(),
      type,
      phase,
      message,
      data
    }
    setExecutionLogs(prev => [...prev, newLog])
  }

  const handleAgentEvent = (event: AgentExecutionEvent) => {
    console.log('收到Agent事件:', event)

    switch (event.event_type) {
      case 'task_start':
        setCurrentPhase('任务开始')
        setProgress(0)
        addLog('info', `开始执行任务: ${event.data.task_description}`, '任务开始', event.data)
        break

      case 'stage_start':
        setCurrentPhase(event.phase || '未知阶段')
        addLog('info', `开始阶段: ${event.phase}`, event.phase, event.data)
        if (event.progress) {
          setProgress(event.progress)
        }
        break

      case 'stage_complete':
        addLog('success', `完成阶段: ${event.phase}`, event.phase, event.data)
        if (event.progress) {
          setProgress(event.progress)
        }
        break

      case 'context_building':
        setCurrentPhase('智能上下文构建')
        addLog('info', '正在分析任务上下文...', '上下文构建')
        break

      case 'strategy_generation':
        setCurrentPhase('执行策略生成')
        addLog('info', '正在生成最优执行策略...', '策略生成')
        break

      case 'tool_selection':
        setCurrentPhase('工具选择')
        addLog('info', '正在选择最适合的工具...', '工具选择')
        break

      case 'tt_execution':
        setCurrentPhase('TT控制循环执行')
        addLog('info', '正在执行TT控制循环...', 'TT执行')
        break

      case 'sql_generated':
        setGeneratedSql(event.data.sql_query)
        setSqlMetadata(event.data)
        addLog('success', 'SQL查询生成成功', 'SQL生成', event.data)
        if (onSqlGenerated) {
          onSqlGenerated(event.data.sql_query, event.data)
        }
        break

      case 'task_complete':
        setCurrentPhase('任务完成')
        setProgress(100)
        setExecutionResult(event.data)
        addLog('success', '任务执行完成', '任务完成', event.data)
        if (onExecutionComplete) {
          onExecutionComplete(event.data)
        }
        setIsExecuting(false)
        break

      case 'error':
        addLog('error', `执行错误: ${event.data.error}`, currentPhase || '错误', event.data)
        setIsExecuting(false)
        showToast('Agent执行失败', 'error')
        break

      case 'progress':
        if (event.progress) {
          setProgress(event.progress)
        }
        addLog('info', event.data.message || '进度更新', currentPhase || '进度', event.data)
        break

      default:
        addLog('info', `收到事件: ${event.event_type}`, currentPhase || '未知', event.data)
    }
  }

  const executeAgent = async () => {
    if (!taskDescription.trim()) {
      showToast('请输入任务描述', 'error')
      return
    }

    setIsExecuting(true)
    setProgress(0)
    setCurrentPhase(null)
    setExecutionLogs([])
    setExecutionResult(null)
    setGeneratedSql(null)
    setSqlMetadata(null)

    try {
      if (enableStreaming) {
        // 使用新的异步流式执行架构
        addLog('info', '正在启动异步Agent任务...', '初始化')

        const agentRequest: AgentTaskRequest = {
          task_description: taskDescription,
          context_data: {},
          coordination_mode: coordinationMode as any,
          enable_streaming: true,
          sql_preview: sqlPreview
        }

        // 使用兼容方法启动异步任务
        const taskResponse = await AgentService.executeStreamCompat(agentRequest)

        if (taskResponse.success && taskResponse.task_id) {
          addLog('success', `任务已启动: ${taskResponse.task_id}`, '任务启动')

          // 创建EventSource连接
          const token = localStorage.getItem('authToken') || localStorage.getItem('token') || ''
          const eventSource = AgentService.createAsyncTaskStream(taskResponse.task_id, token)
          eventSourceRef.current = eventSource

          eventSource.onmessage = (event) => {
            try {
              const eventData = JSON.parse(event.data)
              handleAgentEvent(eventData)
            } catch (e) {
              console.warn('解析事件数据失败:', e, event.data)
            }
          }

          eventSource.onerror = (error) => {
            console.error('EventSource error:', error)
            addLog('error', 'SSE连接发生错误', currentPhase || '连接错误')
            eventSource.close()
            setIsExecuting(false)
          }

          // 监控任务状态
          const statusInterval = setInterval(async () => {
            try {
              const status = await AgentService.getAsyncTaskStatus(taskResponse.task_id!)
              if (status.status === 'completed' || status.status === 'failed') {
                clearInterval(statusInterval)
                if (eventSource) {
                  eventSource.close()
                }
                setIsExecuting(false)
              }
            } catch (e) {
              // 忽略状态查询错误，继续等待流式事件
            }
          }, 2000)

          // 清理定时器
          setTimeout(() => clearInterval(statusInterval), 300000) // 5分钟超时
        } else {
          throw new Error(taskResponse.error || '启动异步任务失败')
        }
      } else {
        // 非流式执行 - 使用兼容的同步接口
        addLog('info', '正在执行同步Agent任务...', '同步执行')

        const agentRequest: AgentTaskRequest = {
          task_description: taskDescription,
          context_data: {},
          coordination_mode: coordinationMode as any,
          enable_streaming: false,
          sql_preview: sqlPreview
        }

        const result = await AgentService.executeCompat(agentRequest)

        setExecutionResult(result)
        setProgress(100)
        setCurrentPhase('任务完成')
        addLog('success', '任务执行完成', '任务完成', result)

        if (onExecutionComplete) {
          onExecutionComplete(result)
        }
      }

    } catch (error: any) {
      console.error('Agent执行失败:', error)
      const errorMsg = error?.message || error?.toString() || 'Unknown error'
      addLog('error', `执行失败: ${errorMsg}`, currentPhase || '错误')
      showToast(`Agent执行失败: ${errorMsg}`, 'error')
    } finally {
      if (!enableStreaming) {
        setIsExecuting(false)
      }
    }
  }

  const stopExecution = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setIsExecuting(false)
    addLog('warning', '执行已被用户取消', currentPhase || '取消')
    showToast('执行已取消', 'warning')
  }

  const clearLogs = () => {
    setExecutionLogs([])
    setProgress(0)
    setCurrentPhase(null)
    setExecutionResult(null)
    setGeneratedSql(null)
    setSqlMetadata(null)
  }

  const getLogIcon = (type: ExecutionLog['type']) => {
    switch (type) {
      case 'success': return '✅'
      case 'error': return '❌'
      case 'warning': return '⚠️'
      default: return 'ℹ️'
    }
  }

  const getLogColorClass = (type: ExecutionLog['type']) => {
    switch (type) {
      case 'success': return 'text-green-600 dark:text-green-400'
      case 'error': return 'text-red-600 dark:text-red-400'
      case 'warning': return 'text-yellow-600 dark:text-yellow-400'
      default: return 'text-blue-600 dark:text-blue-400'
    }
  }

  return (
    <div className="space-y-6">
      {/* API升级提示 */}
      <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="text-blue-600 border-blue-600">
            API v2.0
          </Badge>
          <span className="text-sm text-blue-700 dark:text-blue-300">
            现在使用稳定的无版本别名路由 (/api/agent/*) 和新的异步+流式架构
          </span>
        </div>
      </Card>

      {/* 任务配置 */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Agent任务配置</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">任务描述</label>
            <Textarea
              value={taskDescription}
              onChange={(e) => setTaskDescription(e.target.value)}
              placeholder="请描述您希望Agent执行的任务，例如：分析占位符 {{用户统计日期}} 的含义"
              rows={3}
              disabled={isExecuting}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">协调模式</label>
              <Select
                options={[
                  { label: '智能模式', value: 'intelligent' },
                  { label: '标准模式', value: 'standard' },
                  { label: '简单模式', value: 'simple' }
                ]}
                value={coordinationMode}
                onChange={(value) => setCoordinationMode(value as string)}
                disabled={isExecuting}
              />
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                checked={enableStreaming}
                onChange={setEnableStreaming}
                disabled={isExecuting}
              />
              <label className="text-sm font-medium">启用流式反馈</label>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                checked={sqlPreview}
                onChange={setSqlPreview}
                disabled={isExecuting}
              />
              <label className="text-sm font-medium">SQL预览</label>
            </div>
          </div>

          <div className="flex space-x-3">
            <Button
              onClick={executeAgent}
              disabled={isExecuting || !taskDescription.trim()}
              className="flex items-center space-x-2"
            >
              {isExecuting && <LoadingSpinner size="sm" />}
              <span>{isExecuting ? '执行中...' : '执行Agent'}</span>
            </Button>

            {isExecuting && (
              <Button 
                onClick={stopExecution}
                variant="outline"
                className="text-red-600"
              >
                停止执行
              </Button>
            )}

            <Button 
              onClick={clearLogs}
              variant="outline"
              disabled={isExecuting}
            >
              清空日志
            </Button>
          </div>
        </div>
      </Card>

      {/* 执行进度 */}
      {(isExecuting || currentPhase) && (
        <Card className="p-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">执行进度</h3>
              <Badge variant="default">
                {coordinationMode === 'intelligent' ? '智能模式' : 
                 coordinationMode === 'standard' ? '标准模式' : '简单模式'}
              </Badge>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>当前阶段: {currentPhase || '准备中...'}</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <Progress value={progress} className="w-full" />
            </div>

            {isExecuting && enableStreaming && (
              <div className="text-sm text-gray-600 dark:text-gray-400">
                正在接收实时执行反馈...
              </div>
            )}
          </div>
        </Card>
      )}

      {/* 生成的SQL预览 */}
      {generatedSql && (
        <Card className="p-6">
          <div className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center space-x-2">
              <span>生成的SQL查询</span>
              <Badge variant="success">成功生成</Badge>
            </h3>

            <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4">
              <pre className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                {generatedSql}
              </pre>
            </div>

            {sqlMetadata && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                {sqlMetadata.complexity && (
                  <div>
                    <span className="font-medium">复杂度:</span>
                    <Badge variant={sqlMetadata.complexity === 'low' ? 'success' : 'warning'} className="ml-2">
                      {sqlMetadata.complexity}
                    </Badge>
                  </div>
                )}
                {sqlMetadata.estimated_rows && (
                  <div>
                    <span className="font-medium">预计行数:</span>
                    <span className="ml-2">{sqlMetadata.estimated_rows}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </Card>
      )}

      {/* 执行日志 */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">执行日志</h3>
            <Badge variant="outline">{executionLogs.length} 条记录</Badge>
          </div>

          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 h-64 overflow-y-auto">
            {executionLogs.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-500">
                暂无执行日志
              </div>
            ) : (
              <div className="space-y-2">
                {executionLogs.map((log) => (
                  <div key={log.id} className="flex items-start space-x-3 text-sm">
                    <span className="flex-shrink-0 mt-0.5">
                      {getLogIcon(log.type)}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <span className={getLogColorClass(log.type)}>
                          {log.message}
                        </span>
                        {log.phase && (
                          <Badge variant="outline" className="text-xs">
                            {log.phase}
                          </Badge>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* 执行结果 */}
      {executionResult && (
        <Card className="p-6">
          <div className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center space-x-2">
              <span>执行结果</span>
              <Badge variant={executionResult.success ? 'success' : 'destructive'}>
                {executionResult.success ? '成功' : '失败'}
              </Badge>
            </h3>

            <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4">
              <pre className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                {JSON.stringify(executionResult, null, 2)}
              </pre>
            </div>

            {executionResult.execution_time && (
              <div className="text-sm text-gray-600 dark:text-gray-400">
                执行时间: {executionResult.execution_time.toFixed(2)}秒
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}