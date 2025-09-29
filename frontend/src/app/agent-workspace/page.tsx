'use client'

import React, { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Tabs } from '@/components/ui/Tabs'
import { Switch } from '@/components/ui/Switch'
import AgentStreamingExecution from '@/components/agent/AgentStreamingExecution'
import SQLEnhancedProcessor from '@/components/sql/SQLEnhancedProcessor'

interface AgentWorkspaceState {
  activeTab: 'agent' | 'sql' | 'integrated'
  integratedMode: boolean
  sharedContext: {
    taskDescription: string
    generatedSql: string
    executionResults: any
    agentMetadata: any
  }
}

export default function AgentWorkspacePage() {
  const [workspaceState, setWorkspaceState] = useState<AgentWorkspaceState>({
    activeTab: 'integrated',
    integratedMode: true,
    sharedContext: {
      taskDescription: '',
      generatedSql: '',
      executionResults: null,
      agentMetadata: null
    }
  })

  const [stats, setStats] = useState({
    totalExecutions: 0,
    successfulExecutions: 0,
    sqlQueriesGenerated: 0,
    averageExecutionTime: 0
  })

  const updateSharedContext = (updates: Partial<typeof workspaceState.sharedContext>) => {
    setWorkspaceState(prev => ({
      ...prev,
      sharedContext: {
        ...prev.sharedContext,
        ...updates
      }
    }))
  }

  const handleAgentExecutionComplete = (result: any) => {
    updateSharedContext({
      agentMetadata: result.metadata,
      executionResults: result
    })

    setStats(prev => ({
      ...prev,
      totalExecutions: prev.totalExecutions + 1,
      successfulExecutions: result.success ? prev.successfulExecutions + 1 : prev.successfulExecutions,
      averageExecutionTime: result.execution_time ? 
        (prev.averageExecutionTime * prev.totalExecutions + result.execution_time) / (prev.totalExecutions + 1) :
        prev.averageExecutionTime
    }))

    // 如果Agent识别为SQL相关任务，自动切换到SQL标签页
    if (result.metadata?.scenario === 'sql_generation' && workspaceState.integratedMode) {
      setWorkspaceState(prev => ({ ...prev, activeTab: 'sql' }))
    }
  }

  const handleSqlGenerated = (sql: string, metadata?: any) => {
    updateSharedContext({
      generatedSql: sql
    })

    setStats(prev => ({
      ...prev,
      sqlQueriesGenerated: prev.sqlQueriesGenerated + 1
    }))
  }

  const handleQueryExecuted = (results: any) => {
    updateSharedContext({
      executionResults: results
    })
  }

  const TabButton = ({ tabId, label, active, onClick }: {
    tabId: string
    label: string
    active: boolean
    onClick: () => void
  }) => (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
        active
          ? 'bg-blue-600 text-white'
          : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-100 dark:hover:bg-gray-800'
      }`}
    >
      {label}
    </button>
  )

  return (
    <div className="container mx-auto px-4 py-8">
      {/* 页面头部 */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              Agent智能工作台
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-2">
              基于新架构的Agent系统，支持智能任务执行和SQL处理
            </p>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Switch
                checked={workspaceState.integratedMode}
                onChange={(checked) =>
                  setWorkspaceState(prev => ({ ...prev, integratedMode: checked }))
                }
              />
              <span className="text-sm font-medium">集成模式</span>
            </div>
            <Badge variant="outline" className="text-xs">
              v2.0 - 新架构
            </Badge>
          </div>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="text-2xl font-bold text-blue-600">{stats.totalExecutions}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">总执行次数</div>
          </Card>
          <Card className="p-4">
            <div className="text-2xl font-bold text-green-600">
              {stats.totalExecutions > 0 ? Math.round((stats.successfulExecutions / stats.totalExecutions) * 100) : 0}%
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">成功率</div>
          </Card>
          <Card className="p-4">
            <div className="text-2xl font-bold text-purple-600">{stats.sqlQueriesGenerated}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">生成SQL查询</div>
          </Card>
          <Card className="p-4">
            <div className="text-2xl font-bold text-orange-600">
              {stats.averageExecutionTime.toFixed(2)}s
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">平均执行时间</div>
          </Card>
        </div>
      </div>

      {/* 主要功能区域 */}
      {workspaceState.integratedMode ? (
        /* 集成模式：统一界面 */
        <div className="space-y-6">
          {/* 导航标签 */}
          <div className="flex space-x-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg w-fit">
            <TabButton
              tabId="agent"
              label="Agent执行"
              active={workspaceState.activeTab === 'agent'}
              onClick={() => setWorkspaceState(prev => ({ ...prev, activeTab: 'agent' }))}
            />
            <TabButton
              tabId="sql"
              label="SQL处理"
              active={workspaceState.activeTab === 'sql'}
              onClick={() => setWorkspaceState(prev => ({ ...prev, activeTab: 'sql' }))}
            />
            <TabButton
              tabId="integrated"
              label="智能识别"
              active={workspaceState.activeTab === 'integrated'}
              onClick={() => setWorkspaceState(prev => ({ ...prev, activeTab: 'integrated' }))}
            />
          </div>

          {/* 内容区域 */}
          {workspaceState.activeTab === 'agent' && (
            <AgentStreamingExecution
              onExecutionComplete={handleAgentExecutionComplete}
              onSqlGenerated={handleSqlGenerated}
              initialTaskDescription={workspaceState.sharedContext.taskDescription}
            />
          )}

          {workspaceState.activeTab === 'sql' && (
            <SQLEnhancedProcessor
              onSqlGenerated={handleSqlGenerated}
              onQueryExecuted={handleQueryExecuted}
              initialTaskDescription={workspaceState.sharedContext.taskDescription}
            />
          )}

          {workspaceState.activeTab === 'integrated' && (
            <div className="space-y-6">
              {/* 智能识别说明 */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
                  <span>🤖</span>
                  <span>智能任务识别</span>
                </h3>
                
                <div className="space-y-4">
                  <p className="text-gray-600 dark:text-gray-400">
                    在智能识别模式下，Agent会自动分析您的任务描述，智能判断任务类型并选择最合适的处理方式：
                  </p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-lg">
                      <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">
                        占位符分析任务
                      </h4>
                      <p className="text-blue-700 dark:text-blue-300 text-sm">
                        自动识别模板占位符，智能解析含义，避免不必要的数据库查询
                      </p>
                    </div>
                    
                    <div className="bg-green-50 dark:bg-green-950 p-4 rounded-lg">
                      <h4 className="font-medium text-green-900 dark:text-green-100 mb-2">
                        SQL生成任务
                      </h4>
                      <p className="text-green-700 dark:text-green-300 text-sm">
                        智能生成优化的SQL查询，提供执行计划和性能建议
                      </p>
                    </div>
                    
                    <div className="bg-purple-50 dark:bg-purple-950 p-4 rounded-lg">
                      <h4 className="font-medium text-purple-900 dark:text-purple-100 mb-2">
                        数据分析任务
                      </h4>
                      <p className="text-purple-700 dark:text-purple-300 text-sm">
                        综合数据处理和统计分析，生成可视化报表
                      </p>
                    </div>
                    
                    <div className="bg-orange-50 dark:bg-orange-950 p-4 rounded-lg">
                      <h4 className="font-medium text-orange-900 dark:text-orange-100 mb-2">
                        系统维护任务
                      </h4>
                      <p className="text-orange-700 dark:text-orange-300 text-sm">
                        安全的系统操作和维护管理
                      </p>
                    </div>
                  </div>

                  <div className="bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                    <h4 className="font-medium text-yellow-900 dark:text-yellow-100 mb-2">
                      💡 使用建议
                    </h4>
                    <ul className="text-yellow-700 dark:text-yellow-300 text-sm space-y-1">
                      <li>• 描述越详细，Agent识别越准确</li>
                      <li>• 可以直接输入自然语言描述，无需特定格式</li>
                      <li>• Agent会根据上下文智能选择最优工具组合</li>
                      <li>• 支持多轮对话和渐进式优化</li>
                    </ul>
                  </div>
                </div>
              </Card>

              {/* Agent执行组件 */}
              <AgentStreamingExecution
                onExecutionComplete={handleAgentExecutionComplete}
                onSqlGenerated={handleSqlGenerated}
              />
            </div>
          )}

          {/* 共享上下文显示 */}
          {(workspaceState.sharedContext.generatedSql || workspaceState.sharedContext.agentMetadata) && (
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">共享上下文</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {workspaceState.sharedContext.agentMetadata && (
                  <div>
                    <h4 className="font-medium mb-2">Agent分析结果</h4>
                    <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-3 text-sm">
                      <div className="space-y-1">
                        <div>场景: <Badge variant="outline">{workspaceState.sharedContext.agentMetadata.scenario}</Badge></div>
                        <div>复杂度: <Badge variant="outline">{workspaceState.sharedContext.agentMetadata.complexity}</Badge></div>
                        <div>Agent类型: <Badge variant="outline">{workspaceState.sharedContext.agentMetadata.agent_type}</Badge></div>
                      </div>
                    </div>
                  </div>
                )}

                {workspaceState.sharedContext.generatedSql && (
                  <div>
                    <h4 className="font-medium mb-2">生成的SQL</h4>
                    <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-3 text-sm font-mono">
                      {workspaceState.sharedContext.generatedSql.slice(0, 100)}
                      {workspaceState.sharedContext.generatedSql.length > 100 && '...'}
                    </div>
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>
      ) : (
        /* 分离模式：独立标签 */
        <Tabs
          items={[
            { key: 'agent', label: 'Agent执行' },
            { key: 'sql', label: 'SQL处理' }
          ]}
          defaultActiveKey="agent"
        >
          <div className="mb-6">
            <div className="flex space-x-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg w-fit">
              <TabButton
                tabId="agent"
                label="Agent执行"
                active={workspaceState.activeTab === 'agent'}
                onClick={() => setWorkspaceState(prev => ({ ...prev, activeTab: 'agent' }))}
              />
              <TabButton
                tabId="sql"
                label="SQL处理"
                active={workspaceState.activeTab === 'sql'}
                onClick={() => setWorkspaceState(prev => ({ ...prev, activeTab: 'sql' }))}
              />
            </div>
          </div>

          <div className="space-y-6">
            {workspaceState.activeTab === 'agent' && (
              <AgentStreamingExecution
                onExecutionComplete={handleAgentExecutionComplete}
                onSqlGenerated={handleSqlGenerated}
              />
            )}

            {workspaceState.activeTab === 'sql' && (
              <SQLEnhancedProcessor
                onSqlGenerated={handleSqlGenerated}
                onQueryExecuted={handleQueryExecuted}
              />
            )}
          </div>
        </Tabs>
      )}
    </div>
  )
}