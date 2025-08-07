'use client'

import { create } from 'zustand'
import { Template, TemplateCreate, TemplateUpdate } from '@/types'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

interface TemplateState {
  templates: Template[]
  currentTemplate: Template | null
  loading: boolean
  previewContent: string
  
  // Actions
  fetchTemplates: () => Promise<void>
  getTemplate: (id: string) => Promise<Template>
  createTemplate: (data: TemplateCreate) => Promise<Template>
  updateTemplate: (id: string, data: TemplateUpdate) => Promise<Template>
  deleteTemplate: (id: string) => Promise<void>
  previewTemplate: (content: string, variables?: Record<string, any>) => Promise<string>
  
  // Internal methods
  setLoading: (loading: boolean) => void
  setTemplates: (templates: Template[]) => void
  setCurrentTemplate: (template: Template | null) => void
  setPreviewContent: (content: string) => void
  addTemplate: (template: Template) => void
  updateTemplateInList: (template: Template) => void
  removeTemplate: (id: string) => void
}

export const useTemplateStore = create<TemplateState>((set, get) => ({
  templates: [],
  currentTemplate: null,
  loading: false,
  previewContent: '',

  // 获取模板列表
  fetchTemplates: async () => {
    try {
      set({ loading: true })
      const response = await api.get('/templates')
      const templates = response.data || response
      set({ templates: Array.isArray(templates) ? templates : [] })
    } catch (error: any) {
      console.error('Failed to fetch templates:', error)
      toast.error('获取模板列表失败')
      set({ templates: [] })
    } finally {
      set({ loading: false })
    }
  },

  // 获取单个模板
  getTemplate: async (id: string) => {
    try {
      set({ loading: true })
      const response = await api.get(`/templates/${id}`)
      const template = response.data || response
      set({ currentTemplate: template })
      return template
    } catch (error: any) {
      console.error('Failed to fetch template:', error)
      toast.error('获取模板详情失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 创建模板
  createTemplate: async (data: TemplateCreate) => {
    try {
      set({ loading: true })
      const response = await api.post('/templates', data)
      const newTemplate = response.data || response
      
      get().addTemplate(newTemplate)
      toast.success('模板创建成功')
      return newTemplate
    } catch (error: any) {
      console.error('Failed to create template:', error)
      toast.error('创建模板失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 更新模板
  updateTemplate: async (id: string, data: TemplateUpdate) => {
    try {
      set({ loading: true })
      const response = await api.put(`/templates/${id}`, data)
      const updatedTemplate = response.data || response
      
      get().updateTemplateInList(updatedTemplate)
      if (get().currentTemplate?.id === id) {
        set({ currentTemplate: updatedTemplate })
      }
      toast.success('模板更新成功')
      return updatedTemplate
    } catch (error: any) {
      console.error('Failed to update template:', error)
      toast.error('更新模板失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 删除模板
  deleteTemplate: async (id: string) => {
    try {
      set({ loading: true })
      await api.delete(`/templates/${id}`)
      
      get().removeTemplate(id)
      if (get().currentTemplate?.id === id) {
        set({ currentTemplate: null })
      }
      toast.success('模板删除成功')
    } catch (error: any) {
      console.error('Failed to delete template:', error)
      toast.error('删除模板失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 预览模板
  previewTemplate: async (content: string, variables?: Record<string, any>) => {
    try {
      const response = await api.post('/templates/preview', {
        content,
        variables: variables || {}
      })
      const previewHtml = response.data?.preview || response.preview || response
      set({ previewContent: previewHtml })
      return previewHtml
    } catch (error: any) {
      console.error('Failed to preview template:', error)
      toast.error('模板预览失败')
      throw error
    }
  },

  // Internal methods
  setLoading: (loading: boolean) => set({ loading }),
  
  setTemplates: (templates: Template[]) => set({ templates }),
  
  setCurrentTemplate: (template: Template | null) => set({ currentTemplate: template }),
  
  setPreviewContent: (content: string) => set({ previewContent: content }),
  
  addTemplate: (template: Template) => {
    const { templates } = get()
    set({ templates: [template, ...templates] })
  },
  
  updateTemplateInList: (updatedTemplate: Template) => {
    const { templates } = get()
    const updatedList = templates.map(template => 
      template.id === updatedTemplate.id ? updatedTemplate : template
    )
    set({ templates: updatedList })
  },
  
  removeTemplate: (id: string) => {
    const { templates } = get()
    const filteredList = templates.filter(template => template.id !== id)
    set({ templates: filteredList })
  },
}))