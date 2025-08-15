'use client'

import { useState } from 'react'
import { Task, ProcessingMode, AgentWorkflowType } from '@/types'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Switch } from '@/components/ui/Switch'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { getProcessingModeInfo, getWorkflowTypeInfo } from '@/utils'
import {
  InformationCircleIcon,
  Cog6ToothIcon,
  SparklesIcon,
  CpuChipIcon
} from '@heroicons/react/24/outline'

interface TaskConfigFormProps {
  task?: Partial<Task>
  onChange: (config: Partial<Task>) => void
  showAdvanced?: boolean
}

export function TaskConfigForm({ task, onChange, showAdvanced = false }: TaskConfigFormProps) {
  const [showAdvancedConfig, setShowAdvancedConfig] = useState(showAdvanced)

  const handleChange = (field: keyof Task, value: any) => {
    onChange({
      ...task,
      [field]: value
    })
  }

  const processingModes: { value: ProcessingMode; label: string; description: string }[] = [
    {
      value: 'simple',
      label: '简单模式',
      description: '传统报告生成，快速简单'
    },
    {
      value: 'intelligent',
      label: '智能模式',
      description: 'AI智能编排，功能强大'
    },
    {
      value: 'hybrid',
      label: '混合模式',
      description: '智能与传统结合，平衡性能'
    }
  ]

  const workflowTypes: { value: AgentWorkflowType; label: string; description: string }[] = [
    {
      value: 'simple_report',
      label: '简单报告',
      description: '基础报告生成，适合简单数据展示'
    },
    {
      value: 'statistical_analysis',
      label: '统计分析',
      description: '深度数据统计分析，包含趋势和洞察'
    },
    {
      value: 'chart_generation',
      label: '图表生成',
      description: '重点生成可视化图表和图形'
    },
    {
      value: 'comprehensive_analysis',
      label: '综合分析',
      description: '全面的数据分析报告，包含多种分析维度'
    },
    {
      value: 'custom_workflow',
      label: '自定义流程',
      description: '定制化工作流，高度可配置'
    }
  ]

  return (
    <div className="space-y-6">
      {/* AI配置标题 */}
      <div className="flex items-center gap-2">
        <SparklesIcon className="w-5 h-5 text-purple-600" />
        <h3 className="text-lg font-medium text-gray-900">AI智能配置</h3>
        <Badge variant="default" className="ml-2">智能增强</Badge>
      </div>

      {/* 处理模式选择 */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <CpuChipIcon className="w-4 h-4 text-blue-600" />
          <label className="text-sm font-medium text-gray-700">处理模式</label>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {processingModes.map((mode) => {
            const isSelected = (task?.processing_mode || 'intelligent') === mode.value
            const modeInfo = getProcessingModeInfo(mode.value)
            
            return (
              <div
                key={mode.value}
                className={`
                  p-3 border rounded-lg cursor-pointer transition-all
                  ${isSelected 
                    ? `border-${modeInfo.color}-300 bg-${modeInfo.color}-50` 
                    : 'border-gray-200 hover:border-gray-300'
                  }
                `}
                onClick={() => handleChange('processing_mode', mode.value)}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-sm">{mode.label}</span>
                  {isSelected && (
                    <div className={`w-2 h-2 rounded-full bg-${modeInfo.color}-500`} />
                  )}
                </div>
                <p className="text-xs text-gray-600">{mode.description}</p>
              </div>
            )
          })}
        </div>
      </Card>

      {/* 工作流类型选择 */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <Cog6ToothIcon className="w-4 h-4 text-green-600" />
          <label className="text-sm font-medium text-gray-700">AI工作流类型</label>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {workflowTypes.map((workflow) => {
            const isSelected = (task?.workflow_type || 'simple_report') === workflow.value
            const workflowInfo = getWorkflowTypeInfo(workflow.value)
            
            return (
              <div
                key={workflow.value}
                className={`
                  p-3 border rounded-lg cursor-pointer transition-all
                  ${isSelected 
                    ? `border-${workflowInfo.color}-300 bg-${workflowInfo.color}-50` 
                    : 'border-gray-200 hover:border-gray-300'
                  }
                `}
                onClick={() => handleChange('workflow_type', workflow.value)}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-sm">{workflow.label}</span>
                  {isSelected && (
                    <div className={`w-2 h-2 rounded-full bg-${workflowInfo.color}-500`} />
                  )}
                </div>
                <p className="text-xs text-gray-600">{workflow.description}</p>
              </div>
            )
          })}
        </div>
      </Card>

      {/* 高级配置切换 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <InformationCircleIcon className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-600">高级配置</span>
        </div>
        <Switch
          checked={showAdvancedConfig}
          onChange={setShowAdvancedConfig}
          label=""
        />
      </div>

      {/* 高级配置选项 */}
      {showAdvancedConfig && (
        <Card className="p-4 bg-gray-50">
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-gray-700 mb-3">高级选项</h4>
            
            {/* 最大上下文长度 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                最大上下文长度
              </label>
              <Input
                type="number"
                value={task?.max_context_tokens || 32000}
                onChange={(e) => handleChange('max_context_tokens', parseInt(e.target.value) || 32000)}
                placeholder="32000"
                min={1000}
                max={128000}
                step={1000}
              />
              <p className="text-xs text-gray-500 mt-1">
                AI处理的最大文本长度，影响处理复杂度和成本
              </p>
            </div>

            {/* 启用压缩 */}
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  启用智能压缩
                </label>
                <p className="text-xs text-gray-500">
                  自动压缩长文本以提高处理效率
                </p>
              </div>
              <Switch
                checked={task?.enable_compression ?? true}
                onChange={(checked) => handleChange('enable_compression', checked)}
                label=""
              />
            </div>
          </div>
        </Card>
      )}

      {/* 配置预览 */}
      <Card className="p-4 bg-blue-50 border-blue-200">
        <div className="flex items-center gap-2 mb-2">
          <InformationCircleIcon className="w-4 h-4 text-blue-600" />
          <span className="text-sm font-medium text-blue-800">配置预览</span>
        </div>
        <div className="text-sm text-blue-700 space-y-1">
          <div>
            <span className="font-medium">处理模式:</span> {getProcessingModeInfo(task?.processing_mode || 'intelligent').label}
          </div>
          <div>
            <span className="font-medium">工作流类型:</span> {getWorkflowTypeInfo(task?.workflow_type || 'simple_report').label}
          </div>
          <div>
            <span className="font-medium">上下文长度:</span> {(task?.max_context_tokens || 32000).toLocaleString()} tokens
          </div>
          <div>
            <span className="font-medium">智能压缩:</span> {(task?.enable_compression ?? true) ? '已启用' : '已禁用'}
          </div>
        </div>
      </Card>
    </div>
  )
}