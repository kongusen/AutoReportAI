'use client'

import { create } from 'zustand'
import { 
  DataSource, 
  DataSourceCreate, 
  DataSourceUpdate, 
  ConnectionTestResult,
  DataSourceTablesResponse,
  DataSourceFieldsResponse,
  TableSchema,
  QueryExecutionResult,
  QueryRequest 
} from '@/types'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

interface DataSourceState {
  dataSources: DataSource[]
  currentDataSource: DataSource | null
  loading: boolean
  
  // Actions
  fetchDataSources: () => Promise<void>
  getDataSource: (id: string) => Promise<DataSource>
  createDataSource: (data: DataSourceCreate) => Promise<DataSource>
  updateDataSource: (id: string, data: DataSourceUpdate) => Promise<DataSource>
  deleteDataSource: (id: string) => Promise<void>
  testConnection: (id: string) => Promise<boolean>
  
  // New enhanced API methods
  getTables: (id: string) => Promise<DataSourceTablesResponse>
  getTableSchema: (id: string, tableName: string) => Promise<TableSchema>
  getFields: (id: string, tableName?: string) => Promise<DataSourceFieldsResponse>
  executeQuery: (id: string, query: QueryRequest) => Promise<QueryExecutionResult>
  
  // Internal methods
  setLoading: (loading: boolean) => void
  setDataSources: (dataSources: DataSource[]) => void
  setCurrentDataSource: (dataSource: DataSource | null) => void
  addDataSource: (dataSource: DataSource) => void
  updateDataSourceInList: (dataSource: DataSource) => void
  removeDataSource: (id: string) => void
}

export const useDataSourceStore = create<DataSourceState>((set, get) => ({
  dataSources: [],
  currentDataSource: null,
  loading: false,

  // 获取数据源列表
  fetchDataSources: async () => {
    try {
      set({ loading: true })
      const response = await api.get('/data-sources')
      // 处理后端返回的ApiResponse和PaginatedResponse格式
      let dataSources = []
      if (response.data?.items) {
        // 处理分页响应
        dataSources = response.data.items
      } else if (response.data && Array.isArray(response.data)) {
        // 处理数组响应
        dataSources = response.data
      } else if (Array.isArray(response)) {
        // 处理直接数组响应
        dataSources = response
      }
      set({ dataSources })
    } catch (error: any) {
      console.error('Failed to fetch data sources:', error)
      toast.error('获取数据源列表失败')
      set({ dataSources: [] })
    } finally {
      set({ loading: false })
    }
  },

  // 获取单个数据源
  getDataSource: async (id: string) => {
    try {
      set({ loading: true })
      const response = await api.get(`/data-sources/${id}`)
      // 处理后端返回的ApiResponse格式
      const dataSource = response.data || response
      set({ currentDataSource: dataSource })
      return dataSource
    } catch (error: any) {
      console.error('Failed to fetch data source:', error)
      toast.error('获取数据源详情失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 创建数据源
  createDataSource: async (data: DataSourceCreate) => {
    try {
      set({ loading: true })
      const response = await api.post('/data-sources', data)
      // 处理后端返回的数据源对象（可能直接返回或在data字段中）
      const newDataSource = response.data || response
      
      get().addDataSource(newDataSource)
      toast.success('数据源创建成功')
      return newDataSource
    } catch (error: any) {
      console.error('Failed to create data source:', error)
      toast.error('创建数据源失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 更新数据源
  updateDataSource: async (id: string, data: DataSourceUpdate) => {
    try {
      set({ loading: true })
      const response = await api.put(`/data-sources/${id}`, data)
      const updatedDataSource = response.data || response
      
      get().updateDataSourceInList(updatedDataSource)
      if (get().currentDataSource?.id === id) {
        set({ currentDataSource: updatedDataSource })
      }
      toast.success('数据源更新成功')
      return updatedDataSource
    } catch (error: any) {
      console.error('Failed to update data source:', error)
      toast.error('更新数据源失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 删除数据源
  deleteDataSource: async (id: string) => {
    try {
      set({ loading: true })
      await api.delete(`/data-sources/${id}`)
      
      get().removeDataSource(id)
      if (get().currentDataSource?.id === id) {
        set({ currentDataSource: null })
      }
      toast.success('数据源删除成功')
    } catch (error: any) {
      console.error('Failed to delete data source:', error)
      toast.error('删除数据源失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 测试连接
  testConnection: async (id: string) => {
    try {
      const response = await api.post(`/data-sources/${id}/test`)
      
      // 处理后端ApiResponse格式，检查success字段
      const success = response.success === true
      
      if (success) {
        const message = response.message || response.data?.message || '连接测试成功'
        toast.success(message)
      } else {
        const errorMessage = response.message || response.data?.error || '连接测试失败'
        toast.error(errorMessage)
      }
      return success
    } catch (error: any) {
      console.error('Connection test failed:', error)
      // 从错误响应中提取错误信息
      const errorMessage = error?.response?.data?.message || error?.message || '连接测试失败'
      toast.error(errorMessage)
      return false
    }
  },

  // 获取数据源表列表
  getTables: async (id: string) => {
    try {
      const response = await api.get(`/data-sources/${id}/tables`)
      if (response.success) {
        return response.data as DataSourceTablesResponse
      } else {
        throw new Error(response.message || '获取表列表失败')
      }
    } catch (error: any) {
      console.error('Failed to get tables:', error)
      const errorMessage = error?.response?.data?.message || error?.message || '获取表列表失败'
      toast.error(errorMessage)
      throw error
    }
  },

  // 获取表结构信息
  getTableSchema: async (id: string, tableName: string) => {
    try {
      const response = await api.get(`/data-sources/${id}/tables/${tableName}/schema`)
      if (response.success) {
        return response.data.schema as TableSchema
      } else {
        throw new Error(response.message || '获取表结构失败')
      }
    } catch (error: any) {
      console.error('Failed to get table schema:', error)
      const errorMessage = error?.response?.data?.message || error?.message || '获取表结构失败'
      toast.error(errorMessage)
      throw error
    }
  },

  // 获取数据源字段列表
  getFields: async (id: string, tableName?: string) => {
    try {
      const url = tableName 
        ? `/data-sources/${id}/fields?table_name=${tableName}`
        : `/data-sources/${id}/fields`
      const response = await api.get(url)
      if (response.success) {
        return response.data as DataSourceFieldsResponse
      } else {
        throw new Error(response.message || '获取字段列表失败')
      }
    } catch (error: any) {
      console.error('Failed to get fields:', error)
      const errorMessage = error?.response?.data?.message || error?.message || '获取字段列表失败'
      toast.error(errorMessage)
      throw error
    }
  },

  // 执行查询
  executeQuery: async (id: string, query: QueryRequest) => {
    try {
      const response = await api.post(`/data-sources/${id}/query`, query)
      if (response.success) {
        return response.data as QueryExecutionResult
      } else {
        throw new Error(response.message || '查询执行失败')
      }
    } catch (error: any) {
      console.error('Failed to execute query:', error)
      const errorMessage = error?.response?.data?.message || error?.message || '查询执行失败'
      toast.error(errorMessage)
      throw error
    }
  },

  // Internal methods
  setLoading: (loading: boolean) => set({ loading }),
  
  setDataSources: (dataSources: DataSource[]) => set({ dataSources }),
  
  setCurrentDataSource: (dataSource: DataSource | null) => set({ currentDataSource: dataSource }),
  
  addDataSource: (dataSource: DataSource) => {
    const { dataSources } = get()
    set({ dataSources: [dataSource, ...dataSources] })
  },
  
  updateDataSourceInList: (updatedDataSource: DataSource) => {
    const { dataSources } = get()
    const updatedList = dataSources.map(ds => 
      ds.id === updatedDataSource.id ? updatedDataSource : ds
    )
    set({ dataSources: updatedList })
  },
  
  removeDataSource: (id: string) => {
    const { dataSources } = get()
    const filteredList = dataSources.filter(ds => ds.id !== id)
    set({ dataSources: filteredList })
  },
}))