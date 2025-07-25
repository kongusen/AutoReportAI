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
  TestTube, 
  Eye, 
  Edit, 
  Trash2, 
  Database,
  Search,
  Filter,
  RefreshCw,
  AlertCircle,
  CheckCircle2
} from 'lucide-react'
import { httpClient } from '@/lib/api/client'
import { DataSource } from '@/types/api'

export default function DataSourcesPage() {
  const router = useRouter()
  const params = useParams()
  const locale = params.locale as string
  
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterType, setFilterType] = useState<string>('all')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDataSources()
  }, [])

  const fetchDataSources = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await httpClient.get('/v1/data-sources?limit=100')
      if (res.data && res.data.success) {
        setDataSources(res.data.data?.items || [])
      } else {
        setDataSources([])
      }
    } catch (err) {
      setError('获取数据源失败，请稍后重试')
      setDataSources([])
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    router.push(`/${locale}/data-sources/create`)
  }

  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除这个数据源吗？此操作不可撤销。')) return
    try {
      const res = await httpClient.delete(`/v1/data-sources/${id}`)
      if (res.data?.success) {
        await fetchDataSources()
      } else {
        alert('删除失败，请稍后重试')
      }
    } catch (err) {
      alert('删除失败，请稍后重试')
    }
  }

  const handleTest = async (id: string) => {
    try {
      const res = await httpClient.post(`/v1/data-sources/${id}/test`)
      if (res.data?.success) {
        alert('数据源连接测试成功')
      } else {
        alert('数据源连接测试失败')
      }
    } catch (err) {
      alert('数据源连接测试失败')
    }
  }

  const handlePreview = (id: string) => {
    router.push(`/${locale}/data-sources/${id}/wide-table`)
  }

  const handleEdit = (id: string) => {
    router.push(`/${locale}/data-sources/create?id=${id}`)
  }

  const getSourceTypeIcon = (type: string) => {
    switch (type) {
      case 'sql':
        return <Database className="h-4 w-4" />
      case 'csv':
        return <Database className="h-4 w-4" />
      case 'api':
        return <Database className="h-4 w-4" />
      default:
        return <Database className="h-4 w-4" />
    }
  }

  const getSourceTypeName = (type: string) => {
    switch (type) {
      case 'sql':
        return 'SQL 数据库'
      case 'csv':
        return 'CSV 文件'
      case 'api':
        return 'API 接口'
      case 'push':
        return '推送数据'
      default:
        return type
    }
  }

  const filteredDataSources = dataSources.filter(source => {
    const matchesSearch = source.name.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesFilter = filterType === 'all' || source.source_type === filterType
    return matchesSearch && matchesFilter
  })

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">数据源管理</h1>
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
            <Button onClick={fetchDataSources} className="w-full">
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
          <h1 className="text-2xl font-bold text-gray-900">数据源管理</h1>
          <p className="text-gray-600">管理和配置您的数据源连接</p>
        </div>
        <Button onClick={handleAdd}>
          <Plus className="h-4 w-4 mr-2" />
          新建数据源
        </Button>
      </div>

      {/* 搜索和筛选 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="搜索数据源..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex items-center space-x-2">
              <Filter className="h-4 w-4 text-gray-400" />
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="border rounded-md px-3 py-2 bg-white"
              >
                <option value="all">所有类型</option>
                <option value="sql">SQL 数据库</option>
                <option value="csv">CSV 文件</option>
                <option value="api">API 接口</option>
                <option value="push">推送数据</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据源列表 */}
      {filteredDataSources.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDataSources.map((source) => (
            <Card key={source.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {getSourceTypeIcon(source.source_type)}
                    <CardTitle className="text-lg">{source.name}</CardTitle>
                  </div>
                  <Badge 
                    variant={source.is_active ? 'default' : 'secondary'}
                    className={source.is_active ? 'bg-green-100 text-green-800' : ''}
                  >
                    {source.is_active ? (
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
                  {getSourceTypeName(source.source_type)}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="text-sm text-gray-600">
                    <p>创建时间: {new Date(source.created_at).toLocaleDateString()}</p>
                    {source.last_sync_time && (
                      <p>最后同步: {new Date(source.last_sync_time).toLocaleString()}</p>
                    )}
                  </div>
                  
                  <div className="flex space-x-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handleTest(source.id)}
                      className="flex-1"
                    >
                      <TestTube className="h-4 w-4 mr-1" />
                      测试
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handlePreview(source.id)}
                      className="flex-1"
                    >
                      <Eye className="h-4 w-4 mr-1" />
                      预览
                    </Button>
                  </div>
                  
                  <div className="flex space-x-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handleEdit(source.id)}
                      className="flex-1"
                    >
                      <Edit className="h-4 w-4 mr-1" />
                      编辑
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handleDelete(source.id)}
                      className="flex-1 text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="h-4 w-4 mr-1" />
                      删除
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {searchTerm || filterType !== 'all' ? '未找到匹配的数据源' : '暂无数据源'}
              </h3>
              <p className="text-gray-600 mb-4">
                {searchTerm || filterType !== 'all' 
                  ? '尝试调整搜索条件或筛选器' 
                  : '创建您的第一个数据源以开始使用'
                }
              </p>
              {!searchTerm && filterType === 'all' && (
                <Button onClick={handleAdd}>
                  <Plus className="h-4 w-4 mr-2" />
                  创建数据源
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 统计信息 */}
      {filteredDataSources.length > 0 && (
        <Card>
          <CardContent className="py-4">
            <div className="flex justify-between items-center text-sm text-gray-600">
              <div>
                共 {filteredDataSources.length} 个数据源
                {searchTerm && ` (搜索: "${searchTerm}")`}
                {filterType !== 'all' && ` (类型: ${getSourceTypeName(filterType)})`}
              </div>
              <div className="flex space-x-4">
                <span>活跃: {filteredDataSources.filter(s => s.is_active).length}</span>
                <span>停用: {filteredDataSources.filter(s => !s.is_active).length}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}