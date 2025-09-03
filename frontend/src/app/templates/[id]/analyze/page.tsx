'use client'

import React, { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import AppLayout from '@/components/layout/AppLayout'
import PageHeader from '@/components/layout/PageHeader'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import ReactAgentTemplateAnalyzer from '@/components/templates/ReactAgentTemplateAnalyzer'
import { apiClient } from '@/lib/api-client'
import { useToast } from '@/hooks/useToast'
import { formatDateTime } from '@/utils'
import { ArrowLeftIcon } from '@heroicons/react/24/outline'

interface Template {
  id: string
  name: string
  description?: string
  content: string
  template_type: string
  is_active: boolean
  created_at: string
  updated_at?: string
}

export default function TemplateAnalyzePage() {
  const params = useParams()
  const router = useRouter()
  const [template, setTemplate] = useState<Template | null>(null)
  const [loading, setLoading] = useState(true)
  const { showToast } = useToast()

  const templateId = Array.isArray(params.id) ? params.id[0] : params.id

  useEffect(() => {
    if (templateId) {
      loadTemplate()
    }
  }, [templateId])

  const loadTemplate = async () => {
    try {
      const templateData = await apiClient.getTemplate(templateId)
      setTemplate(templateData)
    } catch (error) {
      console.error('Failed to load template:', error)
      showToast('无法加载模板信息', 'error')
      router.push('/templates')
    } finally {
      setLoading(false)
    }
  }

  const handleAnalysisComplete = (result: any) => {
    showToast('React Agent 已完成模板分析', 'success')
  }

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      </AppLayout>
    )
  }

  if (!template) {
    return (
      <AppLayout>
        <div className="text-center py-12">
          <h3 className="text-lg font-medium text-gray-900 mb-2">模板未找到</h3>
          <p className="text-gray-600 mb-4">请检查模板ID是否正确</p>
          <Button onClick={() => router.push('/templates')}>
            返回模板列表
          </Button>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        <PageHeader
          title="React Agent 模板分析"
          description={`使用智能代理分析模板: ${template.name}`}
          actions={
            <Button
              variant="outline"
              onClick={() => router.push(`/templates/${templateId}`)}
            >
              <ArrowLeftIcon className="w-4 h-4 mr-2" />
              返回模板详情
            </Button>
          }
        />

        {/* 模板信息概览 */}
        <Card>
          <div className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold">{template.name}</h3>
                {template.description && (
                  <p className="text-gray-600 mt-1">{template.description}</p>
                )}
              </div>
              <div className="flex gap-2">
                <Badge variant={template.is_active ? 'default' : 'secondary'}>
                  {template.is_active ? '活跃' : '未激活'}
                </Badge>
                <Badge variant="outline">
                  {template.template_type}
                </Badge>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">创建时间:</span>
                <span className="ml-2">{formatDateTime(template.created_at)}</span>
              </div>
              {template.updated_at && (
                <div>
                  <span className="text-gray-600">更新时间:</span>
                  <span className="ml-2">{formatDateTime(template.updated_at)}</span>
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* React Agent 分析器 */}
        <ReactAgentTemplateAnalyzer 
          templateId={templateId}
          onAnalysisComplete={handleAnalysisComplete}
        />

        {/* 帮助信息 */}
        <Card>
          <div className="p-6">
            <h4 className="font-medium mb-3">关于 React Agent 分析</h4>
            <div className="space-y-2 text-sm text-gray-600">
              <p>• React Agent 使用先进的AI技术分析模板中的占位符和数据需求</p>
              <p>• 智能识别数据源字段映射和关联关系</p>
              <p>• 提供优化建议和潜在的数据质量问题预警</p>
              <p>• 支持多种优化级别，从基础分析到深度学习优化</p>
              <p>• 可以设置目标期望来指导分析过程</p>
            </div>
          </div>
        </Card>
      </div>
    </AppLayout>
  )
}