'use client'

import { create } from 'zustand'
import { Template, TemplateCreate, TemplateUpdate, TemplatePreview, PlaceholderConfig, PlaceholderAnalytics, ApiResponse } from '@/types'
import { TemplateService, PlaceholderService } from '@/services/apiService'
import toast from 'react-hot-toast'

interface TemplateState {
  templates: Template[]
  currentTemplate: Template | null
  loading: boolean
  previewContent: string
  placeholderPreview: TemplatePreview | null
  previewLoading: boolean
  
  // 占位符相关状态
  placeholders: PlaceholderConfig[]
  placeholderAnalytics: PlaceholderAnalytics | null
  placeholderLoading: boolean
  
  // Actions
  fetchTemplates: () => Promise<void>
  getTemplate: (id: string) => Promise<Template>
  createTemplate: (data: TemplateCreate) => Promise<Template>
  updateTemplate: (id: string, data: TemplateUpdate) => Promise<Template>
  deleteTemplate: (id: string) => Promise<void>
  previewTemplate: (content: string, variables?: Record<string, any>) => Promise<string>
  uploadTemplateFile: (id: string, file: File) => Promise<Template>
  fetchPlaceholderPreview: (id: string) => Promise<void>
  
  // 占位符管理方法
  fetchPlaceholders: (templateId: string) => Promise<void>
  analyzePlaceholders: (templateId: string, forceReparse?: boolean) => Promise<void>
  analyzeWithAgent: (templateId: string, dataSourceId: string, forceReanalyze?: boolean) => Promise<void>
  updatePlaceholder: (templateId: string, placeholderId: string, updates: Partial<PlaceholderConfig>) => Promise<void>
  getTemplateReadiness: (templateId: string, dataSourceId?: string) => Promise<any>
  invalidateCache: (templateId: string, cacheLevel?: string) => Promise<void>
  getCacheStatistics: (templateId: string) => Promise<any>

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
  placeholderPreview: null,
  previewLoading: false,
  
  // 占位符相关状态
  placeholders: [],
  placeholderAnalytics: null,
  placeholderLoading: false,

  // 获取模板列表
  fetchTemplates: async () => {
    try {
      set({ loading: true })
      const response = await TemplateService.list()
      set({ templates: response.items || [] })
    } catch (error: any) {
      console.error('Failed to fetch templates:', error)
      set({ templates: [] })
    } finally {
      set({ loading: false })
    }
  },

  // 获取单个模板
  getTemplate: async (id: string) => {
    try {
      set({ loading: true })
      const template = await TemplateService.get(id)
      set({ currentTemplate: template })
      return template
    } catch (error: any) {
      console.error('Failed to fetch template:', error)
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 创建模板
  createTemplate: async (data: TemplateCreate) => {
    try {
      set({ loading: true });
      const { file, ...templateData } = data;

      const newTemplate = await TemplateService.create(templateData);

      if (!newTemplate?.id) {
        throw new Error('创建模板失败：未返回有效的模板ID');
      }

      if (file) {
        const updatedTemplate = await TemplateService.uploadFile(file);
        get().addTemplate(updatedTemplate);
        return updatedTemplate;
      }
      
      get().addTemplate(newTemplate);
      return newTemplate;
    } catch (error: any) {
      console.error('Failed to create template:', error);
      throw error;
    } finally {
      set({ loading: false });
    }
  },

  // 更新模板
  updateTemplate: async (id: string, data: TemplateUpdate) => {
    try {
      set({ loading: true })
      const updatedTemplate = await TemplateService.update(id, data)
      
      get().updateTemplateInList(updatedTemplate)
      if (get().currentTemplate?.id === id) {
        set({ currentTemplate: updatedTemplate })
      }
      return updatedTemplate
    } catch (error: any) {
      console.error('Failed to update template:', error)
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 删除模板
  deleteTemplate: async (id: string) => {
    try {
      set({ loading: true })
      await TemplateService.delete(id)
      
      get().removeTemplate(id)
      if (get().currentTemplate?.id === id) {
        set({ currentTemplate: null })
      }
    } catch (error: any) {
      console.error('Failed to delete template:', error)
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 预览模板  
  previewTemplate: async (content: string, variables?: Record<string, any>) => {
    try {
      // 创建临时模板进行预览
      const tempTemplate = await TemplateService.create({
        name: 'temp_preview',
        content,
        template_type: 'preview'
      })
      
      const preview = await TemplateService.preview(tempTemplate.id)
      set({ previewContent: preview.content })
      
      // 删除临时模板
      await TemplateService.delete(tempTemplate.id)
      
      return preview.content
    } catch (error: any) {
      console.error('Failed to preview template:', error)
      throw error
    }
  },

  // 上传模板文件
  uploadTemplateFile: async (id: string, file: File) => {
    try {
      get().setLoading(true);
      const updatedTemplate = await TemplateService.uploadFile(file);

      get().updateTemplateInList(updatedTemplate);
      if (get().currentTemplate?.id === id) {
        get().setCurrentTemplate(updatedTemplate);
      }
      return updatedTemplate;
    } catch (error: any) {
      console.error('Failed to upload template file:', error);
      throw error;
    } finally {
      get().setLoading(false);
    }
  },

  // 获取占位符预览
  fetchPlaceholderPreview: async (id: string) => {
    try {
      set({ previewLoading: true, placeholderPreview: null });
      const previewData = await TemplateService.preview(id)
      if (previewData) {
        set({ placeholderPreview: previewData });
      }
    } catch (error: any) {
      console.error('Failed to fetch placeholder preview:', error);
      set({ placeholderPreview: null });
    } finally {
      set({ previewLoading: false });
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

  // =====================================================================
  // 占位符管理方法
  // =====================================================================

  // 获取模板占位符列表
  fetchPlaceholders: async (templateId: string) => {
    try {
      set({ placeholderLoading: true })
      const placeholders = await PlaceholderService.list(templateId)
      
      set({ 
        placeholders: placeholders || [],
        placeholderAnalytics: {
          total_placeholders: placeholders?.length || 0,
          analyzed_placeholders: placeholders?.filter((p: PlaceholderConfig) => p.agent_analyzed).length || 0,
          sql_validated_placeholders: placeholders?.filter((p: PlaceholderConfig) => p.sql_validated).length || 0,
          average_confidence_score: placeholders?.reduce((sum: number, p: PlaceholderConfig) => sum + p.confidence_score, 0) / (placeholders?.length || 1) || 0,
          cache_hit_rate: 0,
          analysis_coverage: (placeholders?.length > 0 ? (placeholders?.filter((p: PlaceholderConfig) => p.agent_analyzed).length || 0) / placeholders.length * 100 : 0),
          execution_stats: {
            total_executions: 0,
            successful_executions: 0,
            failed_executions: 0,
            average_execution_time_ms: 0
          }
        }
      })
    } catch (error: any) {
      console.error('Failed to fetch placeholders:', error)
      set({ placeholders: [], placeholderAnalytics: null })
    } finally {
      set({ placeholderLoading: false })
    }
  },

  // 分析模板占位符
  analyzePlaceholders: async (templateId: string, forceReparse = false) => {
    try {
      set({ placeholderLoading: true })
      await TemplateService.parsePlaceholders(templateId)
      
      toast.success('占位符分析完成')
      // 重新获取占位符列表
      await get().fetchPlaceholders(templateId)
    } catch (error: any) {
      console.error('Failed to analyze placeholders:', error)
    } finally {
      set({ placeholderLoading: false })
    }
  },

  // 使用Agent分析占位符
  analyzeWithAgent: async (templateId: string, dataSourceId: string, forceReanalyze = false) => {
    try {
      set({ placeholderLoading: true })
      // 获取所有占位符并逐个智能分析
      const placeholders = await PlaceholderService.list(templateId)
      
      for (const placeholder of placeholders) {
        await PlaceholderService.analyze(placeholder.id)
      }
      
      toast.success('Agent分析完成')
      // 重新获取占位符列表
      await get().fetchPlaceholders(templateId)
    } catch (error: any) {
      console.error('Failed to analyze with agent:', error)
    } finally {
      set({ placeholderLoading: false })
    }
  },

  // 更新占位符配置
  updatePlaceholder: async (templateId: string, placeholderId: string, updates: Partial<PlaceholderConfig>) => {
    try {
      set({ placeholderLoading: true })
      await PlaceholderService.update(placeholderId, updates)
      
      toast.success('占位符更新成功')
      // 重新获取占位符列表
      await get().fetchPlaceholders(templateId)
    } catch (error: any) {
      console.error('Failed to update placeholder:', error)
    } finally {
      set({ placeholderLoading: false })
    }
  },

  // 获取模板就绪状态
  getTemplateReadiness: async (templateId: string, dataSourceId?: string) => {
    try {
      const params = dataSourceId ? { data_source_id: dataSourceId } : {}
      const response = await api.get(`/templates/${templateId}/readiness`, { params })
      return response.data?.data || response.data
    } catch (error: any) {
      console.error('Failed to get template readiness:', error)
      toast.error('获取模板就绪状态失败')
      throw error
    }
  },

  // 清除模板缓存
  invalidateCache: async (templateId: string, cacheLevel?: string) => {
    try {
      const params = cacheLevel ? { cache_level: cacheLevel } : {}
      const response = await api.post(`/templates/${templateId}/invalidate-cache`, {}, { params })
      
      if (response.data?.success) {
        toast.success(`缓存清除完成，共清除 ${response.data.data?.cleared_cache_entries || 0} 个缓存条目`)
      } else {
        toast.error(response.data?.message || '缓存清除失败')
      }
    } catch (error: any) {
      console.error('Failed to invalidate cache:', error)
      toast.error(error.response?.data?.detail || '缓存清除失败')
    }
  },

  // 获取缓存统计
  getCacheStatistics: async (templateId: string) => {
    try {
      const response = await api.get(`/templates/${templateId}/cache-statistics`)
      return response.data?.data || response.data
    } catch (error: any) {
      console.error('Failed to get cache statistics:', error)
      toast.error('获取缓存统计失败')
      throw error
    }
  },
}))
