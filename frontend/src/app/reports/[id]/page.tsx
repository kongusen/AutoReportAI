'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  ArrowDownTrayIcon,
  ShareIcon,
  TrashIcon,
  DocumentTextIcon,
  CalendarDaysIcon,
  FolderIcon,
  ScaleIcon,
} from '@heroicons/react/24/outline'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { useReportStore } from '@/features/reports/reportStore'
import { formatRelativeTime, formatFileSize, copyToClipboard } from '@/utils'
import { Report } from '@/types'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

interface ReportDetailPageProps {
  params: {
    id: string
  }
}

export default function ReportDetailPage({ params }: ReportDetailPageProps) {
  const router = useRouter()
  const { currentReport, loading, getReport, deleteReport, downloadReport } = useReportStore()
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [shareModalOpen, setShareModalOpen] = useState(false)
  const [reportContent, setReportContent] = useState<string>('')
  const [contentLoading, setContentLoading] = useState(false)

  useEffect(() => {
    getReport(params.id)
  }, [params.id, getReport])

  useEffect(() => {
    if (currentReport && currentReport.status === 'completed') {
      // Use content directly from the report data if available
      if (currentReport.content) {
        setReportContent(currentReport.content)
      } else {
        // Fallback to loading content separately if not included
        loadReportContent()
      }
    }
  }, [currentReport])

  const loadReportContent = async () => {
    if (!currentReport) return
    
    try {
      setContentLoading(true)
      const response = await api.get(`/reports/${currentReport.id}/content`)
      setReportContent(response.data.content || '<p>报告内容为空。</p>')
    } catch (error) {
      console.error('Failed to load report content:', error)
      toast.error('加载报告内容失败')
      setReportContent('<p class="text-red-500">加载报告内容失败。</p>')
    } finally {
      setContentLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!currentReport) return
    
    try {
      await deleteReport(currentReport.id)
      setDeleteModalOpen(false)
      router.push('/reports')
    } catch (error) {
      // 错误处理在store中已处理
    }
  }

  const handleShare = async () => {
    if (!currentReport) return
    
    const shareUrl = `${window.location.origin}/reports/${currentReport.id}`
    try {
      await copyToClipboard(shareUrl)
      setShareModalOpen(false)
    } catch (error) {
      console.error('Failed to copy share link:', error)
    }
  }

  const getStatusBadge = (status: Report['status']) => {
    switch (status) {
      case 'generating':
        return <Badge variant="warning">生成中</Badge>
      case 'completed':
        return <Badge variant="success">已完成</Badge>
      case 'failed':
        return <Badge variant="destructive">生成失败</Badge>
      default:
        return <Badge variant="secondary">{status}</Badge>
    }
  }

  if (loading || !currentReport) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-gray-200 rounded w-48"></div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="h-6 bg-gray-200 rounded w-32 mb-4"></div>
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

  return (
    <>
      <PageHeader
        title={currentReport.name}
        description="报告详情和内容预览"
        breadcrumbs={[
          { label: '报告中心', href: '/reports' },
          { label: currentReport.name },
        ]}
        actions={
          <div className="flex items-center space-x-2">
            {getStatusBadge(currentReport.status)}
            {currentReport.status === 'completed' && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => downloadReport(currentReport.id)}
                >
                  <ArrowDownTrayIcon className="w-4 h-4 mr-2" />
                  下载
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShareModalOpen(true)}
                >
                  <ShareIcon className="w-4 h-4 mr-2" />
                  分享
                </Button>
              </>
            )}
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
              <CardTitle className="flex items-center">
                <DocumentTextIcon className="w-5 h-5 mr-2" />
                报告内容
              </CardTitle>
            </CardHeader>
            <CardContent>
              {currentReport.status === 'generating' ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-2 text-sm text-gray-500">报告生成中，请稍候...</p>
                  </div>
                </div>
              ) : currentReport.status === 'failed' ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto">
                      <TrashIcon className="w-6 h-6 text-red-600" />
                    </div>
                    <p className="mt-2 text-sm text-red-600">报告生成失败</p>
                    <p className="text-sm text-gray-500">请重新运行任务生成报告</p>
                  </div>
                </div>
              ) : contentLoading ? (
                <div className="animate-pulse space-y-4">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                  <div className="h-4 bg-gray-200 rounded w-5/6"></div>
                  <div className="h-4 bg-gray-200 rounded w-2/3"></div>
                </div>
              ) : (
                <div 
                  className="prose prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: reportContent }}
                />
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
              <div className="flex items-center">
                <CalendarDaysIcon className="w-4 h-4 text-gray-400 mr-2" />
                <div>
                  <dt className="text-sm font-medium text-gray-500">创建时间</dt>
                  <dd className="text-sm text-gray-900">
                    {formatRelativeTime(currentReport.created_at)}
                  </dd>
                </div>
              </div>
              
              <div className="flex items-center">
                <FolderIcon className="w-4 h-4 text-gray-400 mr-2" />
                <div>
                  <dt className="text-sm font-medium text-gray-500">文件路径</dt>
                  <dd className="text-sm text-gray-900 font-mono break-all">
                    {currentReport.file_path}
                  </dd>
                </div>
              </div>
              
              <div className="flex items-center">
                <ScaleIcon className="w-4 h-4 text-gray-400 mr-2" />
                <div>
                  <dt className="text-sm font-medium text-gray-500">文件大小</dt>
                  <dd className="text-sm text-gray-900">
                    {formatFileSize(currentReport.file_size)}
                  </dd>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 操作历史 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">操作历史</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                  <div>
                    <p className="text-sm text-gray-900">报告创建</p>
                    <p className="text-xs text-gray-500">
                      {formatRelativeTime(currentReport.created_at)}
                    </p>
                  </div>
                </div>
                
                {currentReport.status === 'completed' && (
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full mt-2"></div>
                    <div>
                      <p className="text-sm text-gray-900">生成完成</p>
                      <p className="text-xs text-gray-500">
                        {formatRelativeTime(currentReport.created_at)}
                      </p>
                    </div>
                  </div>
                )}
                
                {currentReport.status === 'failed' && (
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-red-500 rounded-full mt-2"></div>
                    <div>
                      <p className="text-sm text-gray-900">生成失败</p>
                      <p className="text-xs text-gray-500">
                        {formatRelativeTime(currentReport.created_at)}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* 相关任务 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">相关任务</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm font-medium text-gray-900">任务 #{currentReport.task_id}</p>
                  <p className="text-xs text-gray-500">定时任务</p>
                  <Button
                    size="sm"
                    variant="outline"
                    className="mt-2"
                    onClick={() => router.push(`/tasks/${currentReport.task_id}`)}
                  >
                    查看任务
                  </Button>
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
        title="删除报告"
        description={`确定要删除报告"${currentReport.name}"吗？此操作无法撤销。`}
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

      {/* 分享对话框 */}
      <Modal
        isOpen={shareModalOpen}
        onClose={() => setShareModalOpen(false)}
        title="分享报告"
        description="复制链接分享此报告"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              分享链接
            </label>
            <div className="flex">
              <input
                type="text"
                readOnly
                value={`${window.location.origin}/reports/${currentReport.id}`}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-l-md bg-gray-50 text-sm"
              />
              <Button
                type="button"
                className="rounded-l-none"
                onClick={handleShare}
              >
                复制
              </Button>
            </div>
          </div>
          
          <div className="flex justify-end space-x-3">
            <Button
              variant="outline"
              onClick={() => setShareModalOpen(false)}
            >
              关闭
            </Button>
          </div>
        </div>
      </Modal>
    </>
  )
}