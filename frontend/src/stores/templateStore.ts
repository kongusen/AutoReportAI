'use client'

import { create } from 'zustand'
import { Template, TemplateCreate, TemplateUpdate, ApiResponse } from '@/types'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

interface TemplateState {
  // 状态
  templates: Template[]
  currentTemplate: Template | null
  loading: boolean
  error: string | null

  // 操作
  fetchTemplates: () => Promise<void>
  fetchTemplate: (id: string) => Promise<Template | null>
  createTemplate: (templateData: TemplateCreate) => Promise<Template | null>
  updateTemplate: (id: string, templateData: TemplateUpdate) => Promise<Template | null>
  deleteTemplate: (id: string) => Promise<boolean>
  duplicateTemplate: (id: string) => Promise<Template | null>
  
  // 内部方法
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setCurrentTemplate: (template: Template | null) => void
}

export const useTemplateStore = create<TemplateState>()((set, get) => ({
  // 初始状态
  templates: [],
  currentTemplate: null,
  loading: false,
  error: null,

  // 设置加载状态
  setLoading: (loading: boolean) => set({ loading }),
  
  // 设置错误
  setError: (error: string | null) => set({ error }),
  
  // 设置当前模板
  setCurrentTemplate: (template: Template | null) => set({ currentTemplate: template }),

  // 获取所有模板
  fetchTemplates: async () => {
    try {
      set({ loading: true, error: null })
      const response = await api.get<ApiResponse<Template[]>>('/templates')
      set({ templates: response.data || [], loading: false })
    } catch (error: any) {
      console.error('Failed to fetch templates:', error)
      set({ error: error.message || '获取模板失败', loading: false })
      toast.error('获取模板失败')
    }
  },

  // 获取单个模板
  fetchTemplate: async (id: string) => {
    try {
      set({ loading: true, error: null })
      const response = await api.get<ApiResponse<Template>>(`/templates/${id}`)
      const template = response.data
      set({ currentTemplate: template || null, loading: false })
      return template || null
    } catch (error: any) {
      console.error('Failed to fetch template:', error)
      set({ error: error.message || '获取模板失败', loading: false })
      toast.error('获取模板失败')
      return null
    }
  },

  // 创建模板
  createTemplate: async (templateData: TemplateCreate) => {
    try {
      set({ loading: true, error: null })
      const response = await api.post<ApiResponse<Template>>('/templates', templateData)
      const newTemplate = response.data
      
      if (newTemplate) {
        set(state => ({
          templates: [...state.templates, newTemplate],
          loading: false
        }))
        toast.success('模板创建成功')
        return newTemplate
      }
      
      set({ loading: false })
      return null
    } catch (error: any) {
      console.error('Failed to create template:', error)
      set({ error: error.message || '创建模板失败', loading: false })
      toast.error('创建模板失败')
      return null
    }
  },

  // 更新模板
  updateTemplate: async (id: string, templateData: TemplateUpdate) => {
    try {
      set({ loading: true, error: null })
      const response = await api.put<ApiResponse<Template>>(`/templates/${id}`, templateData)
      const updatedTemplate = response.data
      
      if (updatedTemplate) {
        set(state => ({
          templates: state.templates.map(t => t.id === id ? updatedTemplate : t),
          currentTemplate: state.currentTemplate?.id === id ? updatedTemplate : state.currentTemplate,
          loading: false
        }))
        toast.success('模板更新成功')
        return updatedTemplate
      }
      
      set({ loading: false })
      return null
    } catch (error: any) {
      console.error('Failed to update template:', error)
      set({ error: error.message || '更新模板失败', loading: false })
      toast.error('更新模板失败')
      return null
    }
  },

  // 删除模板
  deleteTemplate: async (id: string) => {
    try {
      set({ loading: true, error: null })
      await api.delete(`/templates/${id}`)
      
      set(state => ({
        templates: state.templates.filter(t => t.id !== id),
        currentTemplate: state.currentTemplate?.id === id ? null : state.currentTemplate,
        loading: false
      }))
      
      toast.success('模板删除成功')
      return true
    } catch (error: any) {
      console.error('Failed to delete template:', error)
      set({ error: error.message || '删除模板失败', loading: false })
      toast.error('删除模板失败')
      return false
    }
  },

  // 复制模板
  duplicateTemplate: async (id: string) => {
    try {
      set({ loading: true, error: null })
      
      // 先获取原模板
      const originalTemplate = await get().fetchTemplate(id)
      if (!originalTemplate) {
        throw new Error('原模板不存在')
      }
      
      // 创建新模板数据
      const newTemplateData: TemplateCreate = {
        name: `${originalTemplate.name} (副本)`,
        description: originalTemplate.description,
        content: originalTemplate.content,
        template_type: originalTemplate.template_type,
        variables: originalTemplate.variables ? { ...originalTemplate.variables } : undefined
      }
      
      // 创建新模板
      const newTemplate = await get().createTemplate(newTemplateData)
      
      set({ loading: false })
      return newTemplate
    } catch (error: any) {
      console.error('Failed to duplicate template:', error)
      set({ error: error.message || '复制模板失败', loading: false })
      toast.error('复制模板失败')
      return null
    }
  },
}))