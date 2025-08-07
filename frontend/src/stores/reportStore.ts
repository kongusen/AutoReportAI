'use client'

import { create } from 'zustand'
import { Report } from '@/types'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

interface ReportState {
  reports: Report[]
  currentReport: Report | null
  loading: boolean
  
  // Actions
  fetchReports: () => Promise<void>
  getReport: (id: string) => Promise<Report>
  deleteReport: (id: string) => Promise<void>
  downloadReport: (id: string) => Promise<void>
  batchDeleteReports: (ids: string[]) => Promise<void>
  
  // Real-time updates
  addReport: (report: Report) => void
  updateReportStatus: (id: string, status: Report['status']) => void
  
  // Internal methods
  setLoading: (loading: boolean) => void
  setReports: (reports: Report[]) => void
  setCurrentReport: (report: Report | null) => void
  updateReportInList: (report: Report) => void
  removeReport: (id: string) => void
  removeReports: (ids: string[]) => void
}

export const useReportStore = create<ReportState>((set, get) => ({
  reports: [],
  currentReport: null,
  loading: false,

  // 获取报告列表
  fetchReports: async () => {
    try {
      set({ loading: true })
      const response = await api.get('/reports')
      const reports = response.data || response
      set({ reports: Array.isArray(reports) ? reports : [] })
    } catch (error: any) {
      console.error('Failed to fetch reports:', error)
      toast.error('获取报告列表失败')
      set({ reports: [] })
    } finally {
      set({ loading: false })
    }
  },

  // 获取单个报告
  getReport: async (id: string) => {
    try {
      set({ loading: true })
      const response = await api.get(`/reports/${id}`)
      const report = response.data || response
      set({ currentReport: report })
      return report
    } catch (error: any) {
      console.error('Failed to fetch report:', error)
      toast.error('获取报告详情失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 删除报告
  deleteReport: async (id: string) => {
    try {
      set({ loading: true })
      await api.delete(`/reports/${id}`)
      
      get().removeReport(id)
      if (get().currentReport?.id === id) {
        set({ currentReport: null })
      }
      toast.success('报告删除成功')
    } catch (error: any) {
      console.error('Failed to delete report:', error)
      toast.error('删除报告失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 下载报告
  downloadReport: async (id: string) => {
    try {
      const response = await api.get(`/reports/${id}/download`, {
        responseType: 'blob'
      })
      
      // 从响应头获取文件名
      const contentDisposition = response.headers['content-disposition']
      let fileName = 'report.pdf'
      if (contentDisposition) {
        const fileNameMatch = contentDisposition.match(/filename="?(.+)"?/)
        if (fileNameMatch) {
          fileName = fileNameMatch[1]
        }
      }
      
      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.download = fileName
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      toast.success('报告下载成功')
    } catch (error: any) {
      console.error('Failed to download report:', error)
      toast.error('下载报告失败')
      throw error
    }
  },

  // 批量删除报告
  batchDeleteReports: async (ids: string[]) => {
    try {
      set({ loading: true })
      await api.delete('/reports/batch', {
        data: { report_ids: ids }
      })
      
      get().removeReports(ids)
      toast.success('批量删除报告成功')
    } catch (error: any) {
      console.error('Failed to batch delete reports:', error)
      toast.error('批量删除报告失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 实时添加报告（WebSocket）
  addReport: (report: Report) => {
    const { reports } = get()
    set({ reports: [report, ...reports] })
  },

  // 更新报告状态
  updateReportStatus: (id: string, status: Report['status']) => {
    const { reports } = get()
    const updatedReports = reports.map(report => 
      report.id === id ? { ...report, status } : report
    )
    set({ reports: updatedReports })
    
    // 如果是当前查看的报告，也更新
    const { currentReport } = get()
    if (currentReport?.id === id) {
      set({ currentReport: { ...currentReport, status } })
    }
  },

  // Internal methods
  setLoading: (loading: boolean) => set({ loading }),
  
  setReports: (reports: Report[]) => set({ reports }),
  
  setCurrentReport: (report: Report | null) => set({ currentReport: report }),
  
  updateReportInList: (updatedReport: Report) => {
    const { reports } = get()
    const updatedList = reports.map(report => 
      report.id === updatedReport.id ? updatedReport : report
    )
    set({ reports: updatedList })
  },
  
  removeReport: (id: string) => {
    const { reports } = get()
    const filteredList = reports.filter(report => report.id !== id)
    set({ reports: filteredList })
  },

  removeReports: (ids: string[]) => {
    const { reports } = get()
    const filteredList = reports.filter(report => !ids.includes(report.id))
    set({ reports: filteredList })
  },
}))