'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { 
  PencilIcon, 
  DocumentDuplicateIcon, 
  TrashIcon,
  EyeIcon,
  EyeSlashIcon,
  CogIcon,
  TableCellsIcon,
} from '@heroicons/react/24/outline'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { useTemplateStore } from '@/features/templates/templateStore'
import { formatRelativeTime } from '@/utils'
import { Template } from '@/types'

interface TemplateDetailPageProps {
  params: {
    id: string
  }
}

export default function TemplateDetailPage({ params }: TemplateDetailPageProps) {
  const router = useRouter()
  const { currentTemplate, loading, getTemplate, deleteTemplate, previewTemplate, previewContent, fetchPlaceholderPreview, placeholderPreview, previewLoading } = useTemplateStore()
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [previewVariables, setPreviewVariables] = useState<Record<string, any>>({})

  useEffect(() => {
    getTemplate(params.id)
  }, [params.id, getTemplate])

  useEffect(() => {
    if (currentTemplate?.variables) {
      setPreviewVariables(currentTemplate.variables)
    }
  }, [currentTemplate])

  // Fetch placeholder preview when template loads
  useEffect(() => {
    if (currentTemplate) {
      fetchPlaceholderPreview(params.id)
    }
  }, [currentTemplate, params.id, fetchPlaceholderPreview])

  const handleDelete = async () => {
    if (!currentTemplate) return
    
    try {
      await deleteTemplate(currentTemplate.id)
      setDeleteModalOpen(false)
      router.push('/templates')
    } catch (error) {
      // 错误处理在store中已处理
    }
  }

  const handlePreview = async () => {
    if (!currentTemplate) return
    
    try {
      await previewTemplate(currentTemplate.content, previewVariables)
      setShowPreview(true)
    } catch (error) {
      // 错误处理在store中已处理
    }
  }

  const handleDuplicate = () => {
    if (currentTemplate) {
      router.push(`/templates/create?duplicate=${currentTemplate.id}`)
    }
  }

  const getTemplateTypeInfo = (type: string) => {
    const typeMap: Record<string, { label: string; variant: any }> = {
      'docx': { label: 'DOCX 模板', variant: 'info' },
      'report': { label: '报告模板', variant: 'info' },
      'email': { label: '邮件模板', variant: 'success' },
      'dashboard': { label: '仪表板', variant: 'warning' },
    }
    return typeMap[type] || { label: type, variant: 'secondary' }
  }

  if (loading || !currentTemplate) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-gray-200 rounded w-48"></div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <div className="bg-white p-6 rounded-lg shadow space-y-4">
              <div className="h-6 bg-gray-200 rounded w-32"></div>
              <div className="space-y-2">
                {[...Array(10)].map((_, i) => (
                  <div key={i} className="h-4 bg-gray-200 rounded"></div>
                ))}
              </div>
            </div>
          </div>
          <div className="lg:col-span-1">
            <div className="bg-white p-6 rounded-lg shadow space-y-4">
              <div className="h-6 bg-gray-200 rounded w-24"></div>
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-4 bg-gray-200 rounded"></div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const typeInfo = getTemplateTypeInfo(currentTemplate.template_type)

  return (
    <>
      <PageHeader
        title={currentTemplate.name}
        description={currentTemplate.description || '模板详情'}
        breadcrumbs={[
          { label: '模板管理', href: '/templates' },
          { label: currentTemplate.name },
        ]}
        actions={
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={showPreview ? () => setShowPreview(false) : handlePreview}
            >
              {showPreview ? (
                <>
                  <EyeSlashIcon className="w-4 h-4 mr-2" />
                  隐藏预览
                </>
              ) : (
                <>
                  <EyeIcon className="w-4 h-4 mr-2" />
                  预览
                </>
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(`/templates/${currentTemplate.id}/placeholders`)}
            >
              <TableCellsIcon className="w-4 h-4 mr-2" />
              占位符管理
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDuplicate}
            >
              <DocumentDuplicateIcon className="w-4 h-4 mr-2" />
              复制
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(`/templates/${currentTemplate.id}/edit`)}
            >
              <PencilIcon className="w-4 h-4 mr-2" />
              编辑
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDeleteModalOpen(true)}
            >
              <TrashIcon className="w-4 h-4 mr-2" />
              删除
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 主内容区域 */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{showPreview ? '模板预览' : '模板内容'}</span>
                <Badge variant={typeInfo.variant}>
                  {typeInfo.label}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {showPreview ? (
                <div 
                  className="prose prose-sm max-w-none bg-gray-50 p-4 rounded-lg min-h-[400px]"
                  dangerouslySetInnerHTML={{ __html: previewContent }}
                />
              ) : currentTemplate.template_type === 'docx' ? (
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600">
                    这是一个 DOCX 模板文件。文件信息：
                  </p>
                  <div className="mt-2 space-y-1">
                    {false && (
                      <p className="text-sm">
                        <span className="font-medium">文件名:</span> {}
                      </p>
                    )}
                    {false && (
                      <p className="text-sm">
                        <span className="font-medium">文件大小:</span> {} KB
                      </p>
                    )}
                    <p className="text-sm">
                      <span className="font-medium">创建时间:</span> {formatRelativeTime(currentTemplate.created_at)}
                    </p>
                    {currentTemplate.updated_at && (
                      <p className="text-sm">
                        <span className="font-medium">更新时间:</span> {formatRelativeTime(currentTemplate.updated_at)}
                      </p>
                    )}
                  </div>
                </div>
              ) : (
                <div className="bg-gray-50 p-4 rounded-lg">
                  <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono">
                    {currentTemplate.content}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* 侧边栏 */}
        <div className="lg:col-span-1 space-y-6">
          {/* 基本信息 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">基本信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <dt className="text-sm font-medium text-gray-500">模板类型</dt>
                <dd className="mt-1">
                  <Badge variant={typeInfo.variant}>
                    {typeInfo.label}
                  </Badge>
                </dd>
              </div>
              
              <div>
                <dt className="text-sm font-medium text-gray-500">创建时间</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {formatRelativeTime(currentTemplate.created_at)}
                </dd>
              </div>
              
              {currentTemplate.updated_at && (
                <div>
                  <dt className="text-sm font-medium text-gray-500">更新时间</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {formatRelativeTime(currentTemplate.updated_at)}
                  </dd>
                </div>
              )}
              
              {currentTemplate.template_type !== 'docx' && (
                <>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">内容长度</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {currentTemplate.content.length} 字符
                    </dd>
                  </div>
                  
                  <div>
                    <dt className="text-sm font-medium text-gray-500">变量数量</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {currentTemplate.variables ? Object.keys(currentTemplate.variables).length : 0} 个
                    </dd>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* DOCX模板占位符预览 */}
          {currentTemplate.template_type === 'docx' && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">占位符预览</CardTitle>
              </CardHeader>
              <CardContent>
                {previewLoading ? (
                  <div className="animate-pulse space-y-2">
                    <div className="h-4 bg-gray-200 rounded"></div>
                    <div className="h-4 bg-gray-200 rounded"></div>
                    <div className="h-4 bg-gray-200 rounded"></div>
                  </div>
                ) : placeholderPreview ? (
                  <div className="space-y-4">
                    {/* 总计和错误状态 */}
                    <div className="grid grid-cols-2 gap-2 text-center">
                      <div className="bg-blue-50 p-2 rounded">
                        <div className="text-lg font-bold text-blue-600">{placeholderPreview.total_count}</div>
                        <div className="text-xs text-gray-600">总计</div>
                      </div>
                      {placeholderPreview.has_errors && (
                        <div className="bg-red-50 p-2 rounded">
                          <div className="text-lg font-bold text-red-600">{placeholderPreview.error_count || 0}</div>
                          <div className="text-xs text-gray-600">错误</div>
                        </div>
                      )}
                    </div>
                    
                    {/* 业务类型统计 */}
                    <div className="grid grid-cols-2 gap-2 text-center">
                      <div className="bg-green-50 p-2 rounded">
                        <div className="text-lg font-bold text-green-600">{placeholderPreview.stats_count || 0}</div>
                        <div className="text-xs text-gray-600">统计</div>
                      </div>
                      <div className="bg-purple-50 p-2 rounded">
                        <div className="text-lg font-bold text-purple-600">{placeholderPreview.chart_count || 0}</div>
                        <div className="text-xs text-gray-600">图表</div>
                      </div>
                    </div>
                    
                    {/* 其他类型统计 */}
                    {((placeholderPreview.table_count || 0) > 0 || (placeholderPreview.analysis_count || 0) > 0) && (
                      <div className="grid grid-cols-2 gap-2 text-center">
                        {(placeholderPreview.table_count || 0) > 0 && (
                          <div className="bg-indigo-50 p-2 rounded">
                            <div className="text-lg font-bold text-indigo-600">{placeholderPreview.table_count}</div>
                            <div className="text-xs text-gray-600">表格</div>
                          </div>
                        )}
                        {(placeholderPreview.analysis_count || 0) > 0 && (
                          <div className="bg-orange-50 p-2 rounded">
                            <div className="text-lg font-bold text-orange-600">{placeholderPreview.analysis_count}</div>
                            <div className="text-xs text-gray-600">分析</div>
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* 配置类型统计 */}
                    {((placeholderPreview.datetime_count || 0) > 0 || (placeholderPreview.variable_count || 0) > 0) && (
                      <div className="grid grid-cols-2 gap-2 text-center">
                        {(placeholderPreview.datetime_count || 0) > 0 && (
                          <div className="bg-yellow-50 p-2 rounded">
                            <div className="text-lg font-bold text-yellow-600">{placeholderPreview.datetime_count}</div>
                            <div className="text-xs text-gray-600">时间</div>
                          </div>
                        )}
                        {(placeholderPreview.variable_count || 0) > 0 && (
                          <div className="bg-gray-50 p-2 rounded">
                            <div className="text-lg font-bold text-gray-600">{placeholderPreview.variable_count}</div>
                            <div className="text-xs text-gray-600">变量</div>
                          </div>
                        )}
                      </div>
                    )}
                    
                    {placeholderPreview.placeholders.length > 0 ? (
                      <div className="space-y-3 max-h-96 overflow-y-auto">
                        {placeholderPreview.placeholders.map((placeholder: any, index: number) => {
                          // 定义类型样式映射
                          const getTypeStyle = (type: string) => {
                            const styleMap: Record<string, { variant: any; bgColor: string; textColor: string }> = {
                              '统计': { variant: 'success', bgColor: 'bg-green-50', textColor: 'text-green-700' },
                              '图表': { variant: 'info', bgColor: 'bg-blue-50', textColor: 'text-blue-700' },
                              '表格': { variant: 'info', bgColor: 'bg-indigo-50', textColor: 'text-indigo-700' },
                              '分析': { variant: 'warning', bgColor: 'bg-orange-50', textColor: 'text-orange-700' },
                              '日期时间': { variant: 'warning', bgColor: 'bg-yellow-50', textColor: 'text-yellow-700' },
                              '标题': { variant: 'info', bgColor: 'bg-cyan-50', textColor: 'text-cyan-700' },
                              '摘要': { variant: 'secondary', bgColor: 'bg-gray-50', textColor: 'text-gray-700' },
                              '作者': { variant: 'secondary', bgColor: 'bg-slate-50', textColor: 'text-slate-700' },
                              '变量': { variant: 'secondary', bgColor: 'bg-gray-50', textColor: 'text-gray-600' },
                              '中文': { variant: 'secondary', bgColor: 'bg-pink-50', textColor: 'text-pink-700' },
                              '文本': { variant: 'secondary', bgColor: 'bg-gray-50', textColor: 'text-gray-600' },
                              '错误': { variant: 'destructive', bgColor: 'bg-red-50', textColor: 'text-red-700' },
                              '系统错误': { variant: 'destructive', bgColor: 'bg-red-100', textColor: 'text-red-800' }
                            }
                            return styleMap[type] || { variant: 'secondary', bgColor: 'bg-gray-50', textColor: 'text-gray-600' }
                          }
                          
                          const typeStyle = getTypeStyle(placeholder.type)
                          const hasError = placeholder.type === '错误' || placeholder.type === '系统错误'
                          
                          return (
                            <div key={index} className={`border-l-4 ${hasError ? 'border-red-300' : 'border-gray-200'} pl-3 pb-2`}>
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <div className="flex items-center mb-1">
                                    <Badge 
                                      variant={typeStyle.variant}
                                      className="mr-2"
                                    >
                                      {placeholder.type}
                                    </Badge>
                                    {placeholder.requirements?.content_type && (
                                      <span className="text-xs text-gray-400 bg-gray-100 px-1 py-0.5 rounded">
                                        {placeholder.requirements.content_type}
                                      </span>
                                    )}
                                  </div>
                                  <div className="text-sm font-medium text-gray-900 mb-1">
                                    {placeholder.description}
                                  </div>
                                  <div className="text-xs text-gray-500 font-mono bg-gray-50 px-2 py-1 rounded">
                                    {placeholder.placeholder_text}
                                  </div>
                                  {hasError && placeholder.requirements?.error && (
                                    <div className="text-xs text-red-600 mt-1 bg-red-50 px-2 py-1 rounded">
                                      错误: {placeholder.requirements.error}
                                    </div>
                                  )}
                                  {placeholder.requirements?.fallback_mode && (
                                    <div className="text-xs text-amber-600 mt-1">
                                      ⚠️ 使用备用解析模式
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500 text-center py-4">
                        未检测到占位符
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 text-center py-4">
                    无法加载占位符信息
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {/* 模板变量 */}
          {currentTemplate.variables && Object.keys(currentTemplate.variables).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">模板变量</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(currentTemplate.variables).map(([key, value]) => (
                    <div key={key} className="border-b border-gray-100 pb-2 last:border-b-0">
                      <dt className="text-sm font-medium text-gray-700">{key}</dt>
                      <dd className="mt-1 text-sm text-gray-600 break-all">
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </dd>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 使用统计 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">使用统计</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div>
                  <dt className="text-sm font-medium text-gray-500">关联任务数</dt>
                  <dd className="mt-1 text-sm text-gray-900">0 个</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">生成报告数</dt>
                  <dd className="mt-1 text-sm text-gray-900">0 个</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">最后使用时间</dt>
                  <dd className="mt-1 text-sm text-gray-900">暂未使用</dd>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 删除确认对话框 */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        title="删除模板"
        description={`确定要删除模板"${currentTemplate.name}"吗？此操作无法撤销。`}
      >
        <div className="flex justify-end space-x-3">
          <Button
            variant="outline"
            onClick={() => setDeleteModalOpen(false)}
          >
            取消
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
          >
            删除
          </Button>
        </div>
      </Modal>
    </>
  )
}