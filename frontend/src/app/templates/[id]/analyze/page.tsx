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
import type { Template } from '@/types/api'

// 占位符类型检测
function detectPlaceholderType(placeholder: string): string {
  const name = placeholder.toLowerCase()
  
  // 统计类型关键词
  if (name.includes('统计') || name.includes('数量') || name.includes('总数') || 
      name.includes('计算') || name.includes('count') || name.includes('sum') ||
      name.includes('avg') || name.includes('平均')) {
    return 'statistic'
  }
  
  // 图表类型关键词  
  if (name.includes('图表') || name.includes('chart') || name.includes('图') ||
      name.includes('柱状图') || name.includes('饼图') || name.includes('折线图') ||
      name.includes('bar') || name.includes('pie') || name.includes('line')) {
    return 'chart'
  }
  
  // 分析类型关键词
  if (name.includes('分析') || name.includes('洞察') || name.includes('趋势') ||
      name.includes('analysis') || name.includes('insight') || name.includes('trend')) {
    return 'analysis'
  }
  
  // 表格类型关键词
  if (name.includes('表格') || name.includes('table') || name.includes('列表') ||
      name.includes('list') || name.includes('明细')) {
    return 'table'
  }
  
  // 日期时间类型
  if (name.includes('时间') || name.includes('日期') || name.includes('date') ||
      name.includes('time') || name.includes('datetime')) {
    return 'datetime'
  }
  
  return 'text'
}

// 获取占位符样式
function getPlaceholderStyle(type: string): string {
  const styles = {
    statistic: 'bg-blue-100 text-blue-800 border-blue-200',
    chart: 'bg-green-100 text-green-800 border-green-200', 
    analysis: 'bg-purple-100 text-purple-800 border-purple-200',
    table: 'bg-orange-100 text-orange-800 border-orange-200',
    datetime: 'bg-indigo-100 text-indigo-800 border-indigo-200',
    text: 'bg-yellow-100 text-yellow-800 border-yellow-200'
  }
  return styles[type as keyof typeof styles] || styles.text
}

// 获取占位符图标
function getPlaceholderIcon(type: string): string {
  const icons = {
    statistic: '📊',
    chart: '📈', 
    analysis: '🔍',
    table: '📋',
    datetime: '🕒',
    text: '📝'
  }
  return icons[type as keyof typeof icons] || icons.text
}

// 基于后端解析数据的占位符高亮函数
function highlightPlaceholdersWithBackendData(content: string, backendPlaceholders: any[]) {
  if (!content) return content
  
  let result = content
  let placeholderStats: Record<string, number> = {}
  
  // 使用后端解析的占位符数据进行高亮
  if (backendPlaceholders && backendPlaceholders.length > 0) {
    // 按位置排序，从后往前替换（避免位置偏移）
    const sortedPlaceholders = [...backendPlaceholders].sort((a, b) => (b.start || 0) - (a.start || 0))
    
    sortedPlaceholders.forEach((placeholder) => {
      const placeholderText = placeholder.text || `{{${placeholder.name}}}`
      const placeholderName = placeholder.name || ''
      const type = detectPlaceholderType(placeholderName)
      const style = getPlaceholderStyle(type)
      const icon = getPlaceholderIcon(type)
      
      placeholderStats[type] = (placeholderStats[type] || 0) + 1
      
      const highlightedSpan = `<span class="${style} px-2 py-1 rounded text-xs font-semibold border inline-flex items-center gap-1" title="${placeholderName} (${type})">
        <span class="text-xs">${icon}</span>
        ${placeholderText}
      </span>`
      
      // 使用文本匹配替换
      result = result.replace(placeholderText, highlightedSpan)
    })
  } else {
    // 如果没有后端数据，回退到前端正则匹配
    result = highlightPlaceholdersWithRegex(content, placeholderStats)
  }
  
  // 存储统计信息
  ;(window as any).placeholderStats = placeholderStats
  
  return result
}

// 前端正则匹配高亮函数（回退方案）
function highlightPlaceholdersWithRegex(content: string, stats: Record<string, number>) {
  const patterns = [
    /\{\{([^:}]+):([^}]+)\}\}/g,  // {{type:description}} 格式
    /\{\{@(\w+)\s*=\s*([^}]+)\}\}/g,  // {{@var=value}} 格式
    /\{\{\s*([^#/{}]+?)\s*\}\}/g,  // {{variable}} 格式
    /【([^】]+)】/g,  // 【中文占位符】格式
    /\[([^\[\]{}【】]+)\]/g  // [variable] 格式
  ]
  
  let result = content
  
  patterns.forEach((pattern, index) => {
    result = result.replace(pattern, (match, ...groups) => {
      let placeholderName = ''
      let placeholderDescription = ''
      
      if (index === 0 && groups.length >= 2) {
        placeholderName = groups[1].trim()
        placeholderDescription = `${groups[0].trim()}: ${groups[1].trim()}`
      } else if (index === 1 && groups.length >= 2) {
        placeholderName = groups[0].trim()
        placeholderDescription = `变量: ${groups[0].trim()}`
      } else {
        placeholderName = groups[0].trim()
        placeholderDescription = placeholderName
      }
      
      const type = detectPlaceholderType(placeholderName)
      const style = getPlaceholderStyle(type)
      const icon = getPlaceholderIcon(type)
      
      stats[type] = (stats[type] || 0) + 1
      
      return `<span class="${style} px-2 py-1 rounded text-xs font-semibold border inline-flex items-center gap-1" title="${placeholderDescription} (${type})">
        <span class="text-xs">${icon}</span>
        ${match}
      </span>`
    })
  })
  
  return result
}

// 格式化内容显示
function formatContentByType(content: string, templateType: string) {
  if (!content) return { displayContent: '', isStructured: false }
  
  const type = templateType?.toLowerCase() || 'txt'
  
  switch (type) {
    case 'html':
      return {
        displayContent: content,
        isStructured: true,
        language: 'html'
      }
    case 'md':
    case 'markdown':
      return {
        displayContent: content,
        isStructured: true,
        language: 'markdown'
      }
    case 'json':
      try {
        const parsed = JSON.parse(content)
        return {
          displayContent: JSON.stringify(parsed, null, 2),
          isStructured: true,
          language: 'json'
        }
      } catch {
        return { displayContent: content, isStructured: false }
      }
    default:
      return { displayContent: content, isStructured: false }
  }
}

export default function TemplateAnalyzePage() {
  const params = useParams()
  const router = useRouter()
  const [template, setTemplate] = useState<Template | null>(null)
  const [templatePreview, setTemplatePreview] = useState<any>(null)
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
      // 同时获取模板基本信息和预览信息
      const [templateData, previewData] = await Promise.all([
        apiClient.getTemplate(templateId),
        apiClient.previewTemplate(templateId)
      ])
      
      setTemplate(templateData)
      setTemplatePreview(previewData)
      
      // 将解析后的占位符数据存储到全局变量
      if (previewData?.placeholders) {
        const stats: Record<string, number> = {}
        previewData.placeholders.forEach((placeholder: any) => {
          const type = detectPlaceholderType(placeholder.name || placeholder.text || '')
          stats[type] = (stats[type] || 0) + 1
        })
        ;(window as any).placeholderStats = stats
      }
      
    } catch (error) {
      console.error('Failed to load template:', error)
      showToast('无法加载模板信息', 'error')
      router.push('/templates')
    } finally {
      setLoading(false)
    }
  }

  const handleAnalysisComplete = () => {
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

        {/* 模板文档预览 */}
        <Card>
          <div className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-lg font-semibold">{template.name}</h3>
                  <Badge variant="outline" className="text-xs">
                    {template.template_type?.toUpperCase() || 'TXT'}
                  </Badge>
                  {template.file_size && (
                    <span className="text-xs text-gray-500">
                      {(template.file_size / 1024).toFixed(1)}KB
                    </span>
                  )}
                </div>
                {template.description && (
                  <p className="text-gray-600 text-sm">{template.description}</p>
                )}
              </div>
              <div className="flex gap-2">
                <Badge variant={template.is_active ? 'default' : 'secondary'}>
                  {template.is_active ? '活跃' : '未激活'}
                </Badge>
              </div>
            </div>

            {/* 模板内容预览 */}
            {(() => {
              const content = template.content || ''
              const { displayContent, isStructured, language } = formatContentByType(
                content, 
                template.template_type || 'txt'
              )
              const highlightedContent = highlightPlaceholdersWithBackendData(
                displayContent, 
                templatePreview?.placeholders || []
              )
              
              if (!content.trim()) {
                return (
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <p className="text-gray-500 text-sm">暂无模板内容</p>
                  </div>
                )
              }
              
              return (
                <div className="bg-gray-50 rounded-lg p-4 overflow-auto max-h-64">
                  <div className="relative">
                    {/* 内容类型指示器 */}
                    {isStructured && (
                      <div className="absolute top-2 right-2 z-10">
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                          {language}
                        </span>
                      </div>
                    )}
                    
                    {/* 模板内容显示 */}
                    {isStructured ? (
                      <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono pr-16">
                        <div 
                          dangerouslySetInnerHTML={{ 
                            __html: highlightedContent 
                          }}
                        />
                      </pre>
                    ) : (
                      <div className="text-sm text-gray-800 whitespace-pre-wrap font-mono">
                        <div 
                          dangerouslySetInnerHTML={{ 
                            __html: highlightedContent 
                          }}
                        />
                      </div>
                    )}
                    
                    {/* 占位符统计 */}
                    {(() => {
                      const stats: Record<string, number> = (window as any).placeholderStats || {}
                      const totalCount = Object.values(stats).reduce((sum: number, count: number) => sum + count, 0)
                      
                      return totalCount > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-medium text-gray-700">
                              占位符统计 (共 {totalCount} 个)
                            </span>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(stats).map(([type, count]) => {
                              const icon = getPlaceholderIcon(type)
                              const style = getPlaceholderStyle(type)
                              const typeNames = {
                                statistic: '统计',
                                chart: '图表',
                                analysis: '分析', 
                                table: '表格',
                                datetime: '时间',
                                text: '文本'
                              }
                              const typeName = typeNames[type as keyof typeof typeNames] || type
                              
                              return (
                                <div key={type} className={`${style} px-2 py-1 rounded text-xs inline-flex items-center gap-1`}>
                                  <span>{icon}</span>
                                  <span>{typeName}: {count}</span>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )
                    })()} 
                  </div>
                </div>
              )
            })()}

            {/* 文件信息 */}
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-gray-600">
                <div>
                  <span>创建时间:</span>
                  <span className="ml-1">{formatDateTime(template.created_at)}</span>
                </div>
                {template.updated_at && (
                  <div>
                    <span>更新时间:</span>
                    <span className="ml-1">{formatDateTime(template.updated_at)}</span>
                  </div>
                )}
                {template.original_filename && (
                  <div>
                    <span>原始文件:</span>
                    <span className="ml-1" title={template.original_filename}>
                      {template.original_filename.length > 20 
                        ? template.original_filename.substring(0, 20) + '...' 
                        : template.original_filename}
                    </span>
                  </div>
                )}
              </div>
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
            <div className="space-y-3">
              <div className="space-y-2 text-sm text-gray-600">
                <p>• React Agent 使用先进的AI技术分析模板中的占位符和数据需求</p>
                <p>• 智能识别数据源字段映射和关联关系</p>
                <p>• 提供优化建议和潜在的数据质量问题预警</p>
                <p>• 支持多种优化级别，从基础分析到深度学习优化</p>
                <p>• 可以设置目标期望来指导分析过程</p>
              </div>
              
              <div className="pt-3 border-t border-gray-200">
                <h5 className="text-xs font-medium text-gray-700 mb-2">支持的模板格式</h5>
                <div className="flex flex-wrap gap-1">
                  {['DOCX', 'DOC', 'HTML', 'MD', 'TXT'].map((format) => (
                    <span 
                      key={format}
                      className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded"
                    >
                      {format}
                    </span>
                  ))}
                </div>
              </div>
              
              <div className="pt-2">
                <h5 className="text-xs font-medium text-gray-700 mb-2">占位符语法</h5>
                <div className="space-y-1 text-xs">
                  <code className="bg-gray-100 text-gray-700 px-2 py-1 rounded block">
                    {"{{ placeholder_name }}"}
                  </code>
                  <code className="bg-gray-100 text-gray-700 px-2 py-1 rounded block">
                    {"{{ type:description }}"}
                  </code>
                  <code className="bg-gray-100 text-gray-700 px-2 py-1 rounded block">
                    {"【中文占位符】"}
                  </code>
                </div>
              </div>
              
              <div className="pt-3 border-t border-gray-200">
                <h5 className="text-xs font-medium text-gray-700 mb-2">占位符类型图例</h5>
                <div className="grid grid-cols-2 gap-1 text-xs">
                  {[
                    { type: 'statistic', name: '统计', icon: '📊' },
                    { type: 'chart', name: '图表', icon: '📈' },
                    { type: 'analysis', name: '分析', icon: '🔍' },
                    { type: 'table', name: '表格', icon: '📋' },
                    { type: 'datetime', name: '时间', icon: '🕒' },
                    { type: 'text', name: '文本', icon: '📝' }
                  ].map(({ type, name, icon }) => (
                    <div key={type} className="flex items-center gap-1 p-1 rounded hover:bg-gray-50">
                      <span className="text-xs">{icon}</span>
                      <span className={`${getPlaceholderStyle(type)} px-1 py-0.5 rounded text-xs`}>
                        {name}
                      </span>
                    </div>
                  ))}
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  💡 系统会根据占位符名称自动识别类型并应用相应的颜色标识
                </p>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </AppLayout>
  )
}