'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { 
  History, 
  FileText, 
  Download, 
  Search,
  Filter,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  Calendar,
  Eye
} from 'lucide-react'
import { httpClient } from '@/lib/api/client'
import { ReportHistory } from '@/types/api'

const StatusBadge = ({ status }: { status: string }) => {
  switch (status) {
    case 'success':
      return (
        <Badge className="bg-green-100 text-green-800">
          <CheckCircle2 className="w-3 h-3 mr-1" />
          成功
        </Badge>
      )
    case 'failed':
    case 'failure':
      return (
        <Badge variant="destructive">
          <AlertCircle className="w-3 h-3 mr-1" />
          失败
        </Badge>
      )
    case 'running':
    case 'in_progress':
      return (
        <Badge className="bg-blue-100 text-blue-800">
          <Clock className="w-3 h-3 mr-1" />
          进行中
        </Badge>
      )
    default:
      return <Badge variant="secondary">{status}</Badge>
  }
}

export default function HistoryPage() {
  const router = useRouter()
  const params = useParams()
  const locale = params.locale as string
  
  const [history, setHistory] = useState<ReportHistory[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchHistory()
  }, [])

  const fetchHistory = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await httpClient.get('/v1/history?limit=100')
      if (response.data && response.data.success) {
        setHistory(response.data.data?.items || [])
      } else {
        setHistory([])
      }
    } catch (err) {
      setError('获取历史记录失败，请稍后重试')
      setHistory([])
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async (reportId: number) => {
    try {
      const response = await httpClient.get(`/v1/reports/${reportId}/download`, {
        responseType: 'blob'
      })
      
      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `report_${reportId}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      alert('下载失败，请稍后重试')
    }
  }

  const handleViewReport = (reportId: number) => {
    router.push(`/${locale}/reports/${reportId}`)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN')
  }

  const filteredHistory = history.filter(item => {
    const matchesSearch = item.id.toString().includes(searchTerm) || 
                         item.task_id?.toString().includes(searchTerm)
    const matchesFilter = filterStatus === 'all' || item.status === filterStatus
    return matchesSearch && matchesFilter
  })

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">历史记录</h1>
        </div>
        <Card className="animate-pulse">
          <CardHeader>
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            <div className="h-3 bg-gray-200 rounded w-1/3"></div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-gray-200 rounded"></div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-[400px] flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center text-red-600">
              <AlertCircle className="h-5 w-5 mr-2" />
              加载失败
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600 mb-4">{error}</p>
            <Button onClick={fetchHistory} className="w-full">
              <RefreshCw className="h-4 w-4 mr-2" />
              重新加载
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 页面标题和操作 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">历史记录</h1>
          <p className="text-gray-600">查看所有报告生成历史记录</p>
        </div>
        <Button onClick={fetchHistory} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          刷新
        </Button>
      </div>

      {/* 搜索和筛选 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="搜索报告ID或任务ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex items-center space-x-2">
              <Filter className="h-4 w-4 text-gray-400" />
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="border rounded-md px-3 py-2 bg-white"
              >
                <option value="all">所有状态</option>
                <option value="success">成功</option>
                <option value="failed">失败</option>
                <option value="running">进行中</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 历史记录列表 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <History className="h-5 w-5 mr-2" />
            生成历史
          </CardTitle>
          <CardDescription>
            共 {filteredHistory.length} 条记录
            {searchTerm && ` (搜索: "${searchTerm}")`}
            {filterStatus !== 'all' && ` (状态: ${filterStatus})`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {filteredHistory.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {searchTerm || filterStatus !== 'all' ? '未找到匹配的记录' : '暂无历史记录'}
              </h3>
              <p className="text-gray-600">
                {searchTerm || filterStatus !== 'all' 
                  ? '尝试调整搜索条件或筛选器' 
                  : '执行任务后，生成记录将显示在这里'
                }
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>报告ID</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>任务ID</TableHead>
                    <TableHead>生成时间</TableHead>
                    <TableHead>错误信息</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredHistory.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-mono">#{item.id}</TableCell>
                      <TableCell>
                        <StatusBadge status={item.status} />
                      </TableCell>
                      <TableCell>
                        {item.task_id ? (
                          <span className="font-mono">#{item.task_id}</span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center text-sm text-gray-600">
                          <Calendar className="h-3 w-3 mr-1" />
                          {formatDate(item.generated_at)}
                        </div>
                      </TableCell>
                      <TableCell>
                        {item.error_message ? (
                          <div className="max-w-xs truncate text-red-600 text-sm" title={item.error_message}>
                            {item.error_message}
                          </div>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex space-x-2">
                          {item.status === 'success' && (
                            <>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleViewReport(item.id)}
                              >
                                <Eye className="h-3 w-3 mr-1" />
                                查看
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleDownload(item.id)}
                              >
                                <Download className="h-3 w-3 mr-1" />
                                下载
                              </Button>
                            </>
                          )}
                          {item.status === 'failed' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleViewReport(item.id)}
                            >
                              <Eye className="h-3 w-3 mr-1" />
                              查看详情
                            </Button>
                          )}
                          {item.status === 'running' && (
                            <Badge variant="secondary" className="text-xs">
                              处理中...
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 统计信息 */}
      {filteredHistory.length > 0 && (
        <Card>
          <CardContent className="py-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-green-600">
                  {filteredHistory.filter(h => h.status === 'success').length}
                </div>
                <div className="text-sm text-gray-600">成功</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-red-600">
                  {filteredHistory.filter(h => h.status === 'failed').length}
                </div>
                <div className="text-sm text-gray-600">失败</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-blue-600">
                  {filteredHistory.filter(h => h.status === 'running').length}
                </div>
                <div className="text-sm text-gray-600">进行中</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">
                  {filteredHistory.length > 0 
                    ? `${Math.round((filteredHistory.filter(h => h.status === 'success').length / filteredHistory.length) * 100)}%`
                    : '0%'
                  }
                </div>
                <div className="text-sm text-gray-600">成功率</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
} 