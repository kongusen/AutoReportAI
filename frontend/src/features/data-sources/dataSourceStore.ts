'use client'

import { create } from 'zustand'
import { 
  DataSource, 
  CreateDataSourceRequest as DataSourceCreate, 
  UpdateDataSourceRequest as DataSourceUpdate, 
  DataSourceTestResult as ConnectionTestResult
} from '@/types/api'
import { 
  DataSourceTablesResponse,
  DataSourceFieldsResponse,
  TableSchema,
  QueryExecutionResult,
  QueryRequest 
} from '@/types'
import { DataSourceService } from '@/services/apiService'
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
  getTables: (id: string) => Promise<string[]>
  getTableSchema: (id: string, tableName: string) => Promise<TableSchema | null>
  getFields: (id: string, tableName: string) => Promise<string[]>
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
      const response = await DataSourceService.list()
      set({ dataSources: response.items || [] })
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
      const dataSource = await DataSourceService.get(id)
      set({ currentDataSource: dataSource })
      return dataSource
    } catch (error: any) {
      console.error('Failed to fetch data source:', error)
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 创建数据源
  createDataSource: async (data: DataSourceCreate) => {
    try {
      set({ loading: true })
      const newDataSource = await DataSourceService.create(data)
      
      get().addDataSource(newDataSource)
      return newDataSource
    } catch (error: any) {
      console.error('Failed to create data source:', error)
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 更新数据源
  updateDataSource: async (id: string, data: DataSourceUpdate) => {
    try {
      set({ loading: true })
      const updatedDataSource = await DataSourceService.update(id, data)
      
      get().updateDataSourceInList(updatedDataSource)
      if (get().currentDataSource?.id === id) {
        set({ currentDataSource: updatedDataSource })
      }
      return updatedDataSource
    } catch (error: any) {
      console.error('Failed to update data source:', error)
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 删除数据源
  deleteDataSource: async (id: string) => {
    try {
      set({ loading: true })
      await DataSourceService.delete(id)
      
      get().removeDataSource(id)
      if (get().currentDataSource?.id === id) {
        set({ currentDataSource: null })
      }
    } catch (error: any) {
      console.error('Failed to delete data source:', error)
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 测试连接
  testConnection: async (id: string) => {
    try {
      const result = await DataSourceService.test(id)
      return result.success || false
    } catch (error: any) {
      console.error('Connection test failed:', error)
      return false
    }
  },

  // 获取数据源表列表
  getTables: async (id: string) => {
    try {
      return await DataSourceService.getTables(id)
    } catch (error: any) {
      console.error('Failed to get tables:', error)
      throw error
    }
  },

  // 获取表结构信息
  getTableSchema: async (id: string, tableName: string) => {
    try {
      const response = await DataSourceService.getSchema(id)
      // 从schema中找到对应的表
      return response.tables?.find(table => table.table_name === tableName) || null
    } catch (error: any) {
      console.error('Failed to get table schema:', error)
      throw error
    }
  },

  // 获取数据源字段列表
  getFields: async (id: string, tableName: string) => {
    try {
      return await DataSourceService.getFields(id, tableName)
    } catch (error: any) {
      console.error('Failed to get fields:', error)
      throw error
    }
  },

  // 执行查询
  executeQuery: async (id: string, query: QueryRequest) => {
    try {
      return await DataSourceService.executeQuery(id, query.sql, query.parameters)
    } catch (error: any) {
      console.error('Failed to execute query:', error)
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