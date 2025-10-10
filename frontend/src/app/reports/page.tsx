'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  MagnifyingGlassIcon,
  DocumentArrowDownIcon,
  EyeIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  FunnelIcon,
  CalendarDaysIcon,
} from '@heroicons/react/24/outline'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Table } from '@/components/ui/Table'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { Checkbox } from '@/components/ui/Checkbox'
import { Empty } from '@/components/ui/Empty'
import { useReportStore } from '@/features/reports/reportStore'
import { formatRelativeTime, formatFileSize } from '@/utils'
import { Report } from '@/types'

export default function ReportsPage() {
  const router = useRouter()
  const { 
    reports, 
    loading, 
    fetchReports, 
    deleteReport, 
    downloadReport,
    batchDeleteReports,
    batchDownloadReports
  } = useReportStore()
  
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'generating' | 'completed' | 'failed'>('all')
  const [dateFilter, setDateFilter] = useState<'all' | 'today' | 'week' | 'month'>('all')
  const [selectedReports, setSelectedReports] = useState<string[]>([])
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [selectedReport, setSelectedReport] = useState<Report | null>(null)
  const [batchDeleteModalOpen, setBatchDeleteModalOpen] = useState(false)

  useEffect(() => {
    fetchReports()
  }, [fetchReports])

  // 过滤报告
  const filteredReports = reports.filter(report => {
    const matchesSearch = report.name.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = statusFilter === 'all' || report.status === statusFilter
    
    let matchesDate = true
    if (dateFilter !== 'all') {
      const reportDate = new Date(report.created_at)
      const now = new Date()
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
      
      switch (dateFilter) {
        case 'today':
          matchesDate = reportDate >= today
          break
        case 'week':
          const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)
          matchesDate = reportDate >= weekAgo
          break
        case 'month':
          const monthAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000)
          matchesDate = reportDate >= monthAgo
          break
      }
    }
    
    return matchesSearch && matchesStatus && matchesDate
  })

  const handleSelectReport = (reportId: string, checked: boolean) => {
    if (checked) {
      setSelectedReports([...selectedReports, reportId])
    } else {
      setSelectedReports(selectedReports.filter(id => id !== reportId))
    }
  }

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement> | boolean) => {
    const checked = typeof e === 'boolean' ? e : e.target.checked;
    if (checked) {
      setSelectedReports(filteredReports.map(report => report.id))
    } else {
      setSelectedReports([])
    }
  }

  const handleDeleteConfirm = async () => {
    if (!selectedReport) return
    
    try {
      await deleteReport(selectedReport.id)
      setDeleteModalOpen(false)
      setSelectedReport(null)
    } catch (error) {
      // 错误处理已在store中处理
    }
  }

  const handleBatchDelete = async () => {
    if (selectedReports.length === 0) return
    try {
      await batchDeleteReports(selectedReports)
      setBatchDeleteModalOpen(false)
      setSelectedReports([])
    } catch (error) {
      // 错误处理已在store中处理
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

  const getReportStats = () => {
    const total = reports.length
    const generating = reports.filter(r => r.status === 'generating').length
    const completed = reports.filter(r => r.status === 'completed').length
    const failed = reports.filter(r => r.status === 'failed').length
    return { total, generating, completed, failed }
  }

  const stats = getReportStats()

  const columns: any[] = [
    {
      key: 'selection',
      title: (
        <Checkbox
          checked={selectedReports.length === filteredReports.length && filteredReports.length > 0}
          indeterminate={selectedReports.length > 0 && selectedReports.length < filteredReports.length}
          onChange={handleSelectAll as any}
        />
      ),
      width: 50,
      render: (_: any, record: Report) => (
        <Checkbox
          checked={selectedReports.includes(record.id)}
          onChange={(e: any) => handleSelectReport(record.id, typeof e === 'boolean' ? e : e.target.checked)}
        />
      ),
    },
    {
      key: 'name',
      title: '报告名称',
      dataIndex: 'name',
      render: (name: string, record: Report) => (
        <div className="flex items-center">
          <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
            <DocumentArrowDownIcon className="w-4 h-4 text-blue-600" />
          </div>
          <div>
            <div className="font-medium text-gray-900">{name}</div>
            <div className="text-sm text-gray-500">
              {formatFileSize(record.file_size)}
            </div>
          </div>
        </div>
      ),
    },
    {
      key: 'status',
      title: '状态',
      dataIndex: 'status',
      render: (status: Report['status']) => getStatusBadge(status),
    },
    {
      key: 'created_at',
      title: '创建时间',
      dataIndex: 'created_at',
      render: (createdAt: string) => (
        <div className="flex items-center text-sm text-gray-500">
          <CalendarDaysIcon className="w-4 h-4 mr-1" />
          {formatRelativeTime(createdAt)}
        </div>
      ),
    },
    {
      key: 'file_path',
      title: '文件路径',
      dataIndex: 'file_path',
      render: (filePath: string) => (
        <span className="text-sm text-gray-500 font-mono truncate max-w-xs">
          {filePath}
        </span>
      ),
    },
    {
      key: 'actions',
      title: '操作',
      width: 150,
      render: (_: any, record: Report) => (
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => router.push(`/reports/${record.id}`)}
            disabled={record.status !== 'completed'}
          >
            <EyeIcon className="w-3 h-3" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => downloadReport(record.id)}
            disabled={record.status !== 'completed'}
          >
            <ArrowDownTrayIcon className="w-3 h-3" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setSelectedReport(record)
              setDeleteModalOpen(true)
            }}
          >
            <TrashIcon className="w-3 h-3" />
          </Button>
        </div>
      ),
    },
  ]

  return (
    <>
      <PageHeader
        title="报告中心"
        description="查看和管理生成的报告文件"
      >
        {/* 统计卡片 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-2xl font-bold text-gray-900">{stats.total}</div>
            <div className="text-sm text-gray-500">总报告数</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-2xl font-bold text-blue-600">{stats.generating}</div>
            <div className="text-sm text-gray-500">生成中</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
            <div className="text-sm text-gray-500">已完成</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-2xl font-bold text-red-600">{stats.failed}</div>
            <div className="text-sm text-gray-500">生成失败</div>
          </div>
        </div>
      </PageHeader>

      {/* 搜索和筛选 */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <Input
            placeholder="搜索报告..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            leftIcon={<MagnifyingGlassIcon className="w-4 h-4 text-gray-400" />}
          />
        </div>
        <div className="flex gap-2">
          <select
            className="rounded-md border border-gray-300 bg-white py-2 pl-3 pr-10 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
          >
            <option value="all">全部状态</option>
            <option value="generating">生成中</option>
            <option value="completed">已完成</option>
            <option value="failed">生成失败</option>
          </select>
          <select
            className="rounded-md border border-gray-300 bg-white py-2 pl-3 pr-10 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value as any)}
          >
            <option value="all">全部时间</option>
            <option value="today">今天</option>
            <option value="week">最近一周</option>
            <option value="month">最近一月</option>
          </select>
        </div>
      </div>

      {/* 批量操作工具栏 */}
      {selectedReports.length > 0 && (
        <div className="mb-4 p-4 bg-gray-50 rounded-lg flex items-center justify-between">
          <span className="text-sm text-gray-600">
            已选择 {selectedReports.length} 个报告
          </span>
          <div className="flex items-center gap-2">
            <Button 
              size="sm"
              variant="outline"
              onClick={() => batchDownloadReports(selectedReports)}
            >
              <ArrowDownTrayIcon className="w-3 h-3 mr-1" />
              批量下载
            </Button>
            <Button 
              size="sm" 
              variant="destructive" 
              onClick={() => setBatchDeleteModalOpen(true)}
            >
              <TrashIcon className="w-3 h-3 mr-1" />
              批量删除
            </Button>
          </div>
        </div>
      )}

      {/* 报告表格 */}
      {loading ? (
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded mb-4"></div>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-100 rounded"></div>
            ))}
          </div>
        </div>
      ) : filteredReports.length === 0 ? (
        <Empty
          title={searchTerm || statusFilter !== 'all' || dateFilter !== 'all' ? '未找到匹配的报告' : '还没有报告'}
          description={searchTerm || statusFilter !== 'all' || dateFilter !== 'all' ? '尝试调整搜索条件或筛选器' : '创建任务后将在这里显示生成的报告'}
          action={
            <Button onClick={() => router.push('/tasks/create')}>
              创建任务
            </Button>
          }
        />
      ) : (
        <Table
          columns={columns}
          dataSource={filteredReports}
          rowKey="id"
        />
      )}

      {/* 删除确认对话框 */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        title="删除报告"
        description={`确定要删除报告"${selectedReport?.name}"吗？此操作无法撤销。`}
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

      {/* 批量删除确认对话框 */}
      <Modal
        isOpen={batchDeleteModalOpen}
        onClose={() => setBatchDeleteModalOpen(false)}
        title="批量删除报告"
        description={`确定要删除选中的 ${selectedReports.length} 个报告吗？此操作无法撤销。`}
      >
        <div className="flex justify-end space-x-3">
          <Button
            variant="outline"
            onClick={() => setBatchDeleteModalOpen(false)}
          >
            取消
          </Button>
          <Button
            variant="destructive"
            onClick={handleBatchDelete}
          >
            批量删除
          </Button>
        </div>
      </Modal>
    </>
  )
}
