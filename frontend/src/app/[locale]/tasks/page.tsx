'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { 
  Plus, 
  PlayCircle, 
  Pause, 
  Edit, 
  Trash2, 
  Search,
  Filter,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  Calendar,
  Users
} from 'lucide-react'
import { httpClient } from '@/lib/api/client'
import { Task } from '@/types/api'

export default function TasksPage() {
  const router = useRouter()
  const params = useParams()
  const locale = params.locale as string
  
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchTasks()
  }, [])

  const fetchTasks = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await httpClient.get('/v1/tasks?limit=100')
      if (res.data && res.data.success) {
        setTasks(res.data.data?.items || [])
      } else {
        setTasks([])
      }
    } catch (err) {
      setError('获取任务失败，请稍后重试')
      setTasks([])
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = () => {
    router.push(`/${locale}/tasks/create`)
  }

  const handleEdit = (id: number) => {
    router.push(`/${locale}/tasks/${id}/edit`)
  }

  const handleView = (id: number) => {
    router.push(`/${locale}/tasks/${id}`)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除这个任务吗？此操作不可撤销。')) return
    try {
      const res = await httpClient.delete(`/v1/tasks/${id}`)
      if (res.data?.success) {
        await fetchTasks()
        alert('任务删除成功')
      } else {
        alert('删除失败，请稍后重试')
      }
    } catch (err) {
      alert('删除失败，请稍后重试')
    }
  }

  const handleToggleStatus = async (id: number, isActive: boolean) => {
    try {
      const action = isActive ? 'disable' : 'enable'
      const res = await httpClient.post(`/v1/tasks/${id}/${action}`)
      if (res.data?.success) {
        await fetchTasks()
        alert(`任务已${isActive ? '停用' : '启用'}`)
      } else {
        alert('操作失败，请稍后重试')
      }
    } catch (err) {
      alert('操作失败，请稍后重试')
    }
  }

  const handleRunTask = async (id: number) => {
    try {
      const res = await httpClient.post(`/v1/tasks/${id}/run`)
      if (res.data?.success) {
        alert('任务已开始执行')
      } else {
        alert('执行失败，请稍后重试')
      }
    } catch (err) {
      alert('执行失败，请稍后重试')
    }
  }

  const getTaskStatusIcon = (isActive: boolean) => {
    return isActive ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />
  }

  const getTaskStatusName = (isActive: boolean) => {
    return isActive ? '正常' : '停用'
  }

  const formatSchedule = (schedule?: string) => {
    if (!schedule) return '手动执行'
    // 简单的 cron 表达式解析，实际项目中可能需要更复杂的解析
    if (schedule === '0 0 * * *') return '每日执行'
    if (schedule === '0 0 * * 0') return '每周执行'
    if (schedule === '0 0 1 * *') return '每月执行'
    return schedule
  }

  const filteredTasks = tasks.filter(task => {
    const matchesSearch = task.name.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesFilter = filterStatus === 'all' || 
      (filterStatus === 'active' && task.is_active) ||
      (filterStatus === 'inactive' && !task.is_active)
    return matchesSearch && matchesFilter
  })

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">任务管理</h1>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              </CardHeader>
              <CardContent>
                <div className="h-20 bg-gray-200 rounded"></div>
              </CardContent>
            </Card>
          ))}
        </div>
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
            <Button onClick={fetchTasks} className="w-full">
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
          <h1 className="text-2xl font-bold text-gray-900">任务管理</h1>
          <p className="text-gray-600">管理您的自动化报告生成任务</p>
        </div>
        <Button onClick={handleCreate}>
          <Plus className="h-4 w-4 mr-2" />
          新建任务
        </Button>
      </div>

      {/* 搜索和筛选 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="搜索任务..."
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
                <option value="active">正常运行</option>
                <option value="inactive">已停用</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 任务列表 */}
      {filteredTasks.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTasks.map((task) => (
            <Card key={task.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <PlayCircle className="h-4 w-4" />
                    <CardTitle className="text-lg">{task.name}</CardTitle>
                  </div>
                  <Badge 
                    variant={task.is_active ? 'default' : 'secondary'}
                    className={task.is_active ? 'bg-green-100 text-green-800' : ''}
                  >
                    {task.is_active ? (
                      <>
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        正常
                      </>
                    ) : (
                      <>
                        <AlertCircle className="h-3 w-3 mr-1" />
                        停用
                      </>
                    )}
                  </Badge>
                </div>
                <CardDescription>
                  {task.description || '无描述'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="text-sm text-gray-600 space-y-1">
                    <div className="flex items-center">
                      <Calendar className="h-3 w-3 mr-2" />
                      <span>调度: {formatSchedule(task.schedule)}</span>
                    </div>
                    {task.recipients && task.recipients.length > 0 && (
                      <div className="flex items-center">
                        <Users className="h-3 w-3 mr-2" />
                        <span>收件人: {task.recipients.length} 人</span>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex space-x-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handleRunTask(task.id)}
                      className="flex-1"
                      disabled={!task.is_active}
                    >
                      <PlayCircle className="h-4 w-4 mr-1" />
                      执行
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handleToggleStatus(task.id, task.is_active)}
                      className="flex-1"
                    >
                      {task.is_active ? (
                        <>
                          <Pause className="h-4 w-4 mr-1" />
                          停用
                        </>
                      ) : (
                        <>
                          <PlayCircle className="h-4 w-4 mr-1" />
                          启用
                        </>
                      )}
                    </Button>
                  </div>
                  
                  <div className="flex space-x-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handleView(task.id)}
                      className="flex-1"
                    >
                      查看详情
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handleEdit(task.id)}
                      className="flex-1"
                    >
                      <Edit className="h-4 w-4 mr-1" />
                      编辑
                    </Button>
                  </div>

                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => handleDelete(task.id)}
                    className="w-full text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    删除任务
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <PlayCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {searchTerm || filterStatus !== 'all' ? '未找到匹配的任务' : '暂无任务'}
              </h3>
              <p className="text-gray-600 mb-4">
                {searchTerm || filterStatus !== 'all' 
                  ? '尝试调整搜索条件或筛选器' 
                  : '创建您的第一个自动化任务'
                }
              </p>
              {!searchTerm && filterStatus === 'all' && (
                <Button onClick={handleCreate}>
                  <Plus className="h-4 w-4 mr-2" />
                  新建任务
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 统计信息 */}
      {filteredTasks.length > 0 && (
        <Card>
          <CardContent className="py-4">
            <div className="flex justify-between items-center text-sm text-gray-600">
              <div>
                共 {filteredTasks.length} 个任务
                {searchTerm && ` (搜索: "${searchTerm}")`}
                {filterStatus !== 'all' && ` (状态: ${filterStatus === 'active' ? '正常' : '停用'})`}
              </div>
              <div className="flex space-x-4">
                <span>正常: {filteredTasks.filter(t => t.is_active).length}</span>
                <span>停用: {filteredTasks.filter(t => !t.is_active).length}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
