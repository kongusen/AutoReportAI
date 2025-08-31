'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  PlusIcon,
  MagnifyingGlassIcon,
  DocumentTextIcon,
  EyeIcon,
  PencilIcon,
  TrashIcon,
  DocumentDuplicateIcon,
} from '@heroicons/react/24/outline'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { Empty } from '@/components/ui/Empty'
import { useEnhancedTemplates } from '@/hooks/useEnhancedTemplates'
import { formatRelativeTime } from '@/utils'
import { Template } from '@/types'

export default function TemplatesPage() {
  const router = useRouter()
  const { 
    templates, 
    loading,
    operations,
    fetchTemplates, 
    deleteTemplate 
  } = useEnhancedTemplates()
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedType, setSelectedType] = useState<string>('all')
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)

  useEffect(() => {
    fetchTemplates()
  }, [fetchTemplates])

  // 过滤模板
  const filteredTemplates = (templates || []).filter(template => {
    const matchesSearch = template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         template.description?.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesType = selectedType === 'all' || template.template_type === selectedType
    return matchesSearch && matchesType
  })

  // 获取模板类型列表
  const templateTypes = [...new Set((templates || []).map(t => t.template_type))]

  const handleDeleteConfirm = async () => {
    if (!selectedTemplate) return
    
    try {
      await deleteTemplate(selectedTemplate.id)
      setDeleteModalOpen(false)
      setSelectedTemplate(null)
    } catch (error) {
      // 错误处理已在store中处理
    }
  }

  const handleDuplicate = (template: Template) => {
    router.push(`/templates/create?duplicate=${template.id}`)
  }

  const getTemplateTypeInfo = (type: string) => {
    const typeMap: Record<string, { label: string; color: string }> = {
      'docx': { label: 'DOCX 模板', color: 'blue' },
      'report': { label: '报告模板', color: 'blue' },
      'email': { label: '邮件模板', color: 'green' },
      'dashboard': { label: '仪表板', color: 'purple' },
      'export': { label: '导出模板', color: 'orange' },
    }
    return typeMap[type] || { label: type, color: 'gray' }
  }

  const getVariableCount = (template: Template) => {
    if (!template.variables) return 0
    return Object.keys(template.variables).length
  }

  return (
    <>
      <PageHeader
        title="模板管理"
        description="创建和管理报告模板，支持Markdown语法和变量占位符"
        actions={
          <Button onClick={() => router.push('/templates/create')}>
            <PlusIcon className="w-4 h-4 mr-2" />
            创建模板
          </Button>
        }
      />

      {/* 搜索和筛选 */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <Input
            placeholder="搜索模板..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            leftIcon={<MagnifyingGlassIcon className="w-4 h-4 text-gray-400" />}
          />
        </div>
        <div className="sm:w-48">
          <select
            className="w-full rounded-md border border-gray-300 bg-white py-2 pl-3 pr-10 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
          >
            <option value="all">全部类型</option>
            {templateTypes.map(type => (
              <option key={type} value={type}>
                {getTemplateTypeInfo(type).label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 操作状态提示 */}
      {operations.delete.loading && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-blue-800 text-sm">正在删除模板...</p>
        </div>
      )}
      
      {operations.delete.error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800 text-sm">{operations.delete.error}</p>
        </div>
      )}

      {/* 模板列表 */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="space-y-3">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                  <div className="flex space-x-2">
                    <div className="h-6 bg-gray-200 rounded w-16"></div>
                    <div className="h-6 bg-gray-200 rounded w-12"></div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredTemplates.length === 0 ? (
        <Empty
          title={searchTerm || selectedType !== 'all' ? '未找到匹配的模板' : '还没有模板'}
          description={searchTerm || selectedType !== 'all' ? '尝试调整搜索条件或筛选器' : '创建您的第一个报告模板'}
          action={
            <Button onClick={() => router.push('/templates/create')}>
              <PlusIcon className="w-4 h-4 mr-2" />
              创建模板
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTemplates.map((template) => (
            <Card key={template.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center">
                    <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center mr-3">
                      <DocumentTextIcon className="w-5 h-5 text-gray-600" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="text-sm font-medium text-gray-900 truncate">
                        {template.name}
                      </h3>
                      <p className="text-xs text-gray-500">
                        {getTemplateTypeInfo(template.template_type).label}
                      </p>
                    </div>
                  </div>
                  {template.template_type !== 'docx' && (
                    <Badge 
                      variant="secondary"
                      className="ml-2 shrink-0"
                    >
                      {getVariableCount(template)} 变量
                    </Badge>
                  )}
                </div>

                {template.description && (
                  <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                    {template.description}
                  </p>
                )}

                <div className="space-y-2 mb-4">
                  <p className="text-xs text-gray-500">
                    创建时间: {formatRelativeTime(template.created_at)}
                  </p>
                  {template.updated_at && (
                    <p className="text-xs text-gray-500">
                      更新时间: {formatRelativeTime(template.updated_at)}
                    </p>
                  )}
                  {template.template_type !== 'docx' ? (
                    <p className="text-xs text-gray-500">
                      内容长度: {template.content.length} 字符
                    </p>
                  ) : template.file_size ? (
                    <p className="text-xs text-gray-500">
                      文件大小: {(template.file_size / 1024).toFixed(2)} KB
                    </p>
                  ) : null}
                </div>

                <div className="flex items-center gap-1">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => router.push(`/templates/${template.id}`)}
                  >
                    <EyeIcon className="w-3 h-3 mr-1" />
                    查看
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => router.push(`/templates/${template.id}/edit`)}
                  >
                    <PencilIcon className="w-3 h-3 mr-1" />
                    编辑
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleDuplicate(template)}
                  >
                    <DocumentDuplicateIcon className="w-3 h-3 mr-1" />
                    复制
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedTemplate(template)
                      setDeleteModalOpen(true)
                    }}
                  >
                    <TrashIcon className="w-3 h-3 mr-1" />
                    删除
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 删除确认对话框 */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        title="删除模板"
        description={`确定要删除模板"${selectedTemplate?.name}"吗？此操作无法撤销。`}
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
            onClick={handleDeleteConfirm}
          >
            删除
          </Button>
        </div>
      </Modal>

    </>
  )
}