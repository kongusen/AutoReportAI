'use client'

import { create } from 'zustand'
import { DataSource, DataSourceCreate, DataSourceUpdate } from '@/types'
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
      const dataSources = response.data || response
      set({ dataSources: Array.isArray(dataSources) ? dataSources : [] })
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
      const success = response.success !== false
      
      if (success) {
        toast.success('连接测试成功')
      } else {
        toast.error('连接测试失败')
      }
      return success
    } catch (error: any) {
      console.error('Connection test failed:', error)
      toast.error('连接测试失败')
      return false
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