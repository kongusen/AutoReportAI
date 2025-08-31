/**
 * 增强的模板Store - 使用新的API客户端和更好的状态管理
 */

'use client'

import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { Template, TemplateCreate, TemplateUpdate, TemplatePreview, PlaceholderConfig, PlaceholderAnalytics } from '@/types'
import { ApiClient } from '@/lib/api-client'
import { useToast } from '@/hooks/useToast'

interface TemplateOperationState {
  loading: boolean
  progress: number
  error: string | null
}

interface EnhancedTemplateState {
  // 数据状态
  templates: Template[]
  currentTemplate: Template | null
  previewContent: string
  placeholderPreview: TemplatePreview | null
  placeholders: PlaceholderConfig[]
  placeholderAnalytics: PlaceholderAnalytics | null
  
  // 操作状态
  operations: {
    fetch: TemplateOperationState
    create: TemplateOperationState
    update: TemplateOperationState
    delete: TemplateOperationState
    upload: TemplateOperationState
    analyze: TemplateOperationState
    preview: TemplateOperationState
  }
  
  // 缓存状态
  lastFetchTime: Date | null
  cacheValid: boolean
  
  // Actions
  fetchTemplates: (force?: boolean) => Promise<void>
  getTemplate: (id: string, useCache?: boolean) => Promise<Template>
  createTemplate: (data: TemplateCreate, onProgress?: (progress: number) => void) => Promise<Template>
  updateTemplate: (id: string, data: TemplateUpdate) => Promise<Template>
  deleteTemplate: (id: string, confirm?: boolean) => Promise<void>
  uploadTemplateFile: (id: string, file: File, onProgress?: (progress: number) => void) => Promise<Template>
  
  // 占位符相关
  fetchPlaceholders: (templateId: string, force?: boolean) => Promise<void>
  analyzePlaceholders: (templateId: string, options?: { forceReparse?: boolean, showProgress?: boolean }) => Promise<void>
  analyzeWithDAG: (templateId: string, dataSourceId: string, mode: 'sql_generation' | 'chart_testing') => Promise<void>
  
  // 预览相关
  previewTemplate: (content: string, variables?: Record<string, any>) => Promise<string>
  fetchPlaceholderPreview: (id: string) => Promise<void>
  
  // 缓存管理
  invalidateCache: (pattern?: string) => void
  refreshTemplate: (id: string) => Promise<Template>
  
  // 内部方法
  setOperationState: (operation: keyof EnhancedTemplateState['operations'], state: Partial<TemplateOperationState>) => void
  addTemplate: (template: Template) => void
  updateTemplateInList: (template: Template) => void
  removeTemplate: (id: string) => void
  reset: () => void
}

const initialOperationState: TemplateOperationState = {
  loading: false,
  progress: 0,
  error: null
}

export const useEnhancedTemplateStore = create<EnhancedTemplateState>()(
  devtools(
    (set, get) => ({
      // 初始状态
      templates: [],
      currentTemplate: null,
      previewContent: '',
      placeholderPreview: null,
      placeholders: [],
      placeholderAnalytics: null,
      
      operations: {
        fetch: { ...initialOperationState },
        create: { ...initialOperationState },
        update: { ...initialOperationState },
        delete: { ...initialOperationState },
        upload: { ...initialOperationState },
        analyze: { ...initialOperationState },
        preview: { ...initialOperationState }
      },
      
      lastFetchTime: null,
      cacheValid: false,

      // 设置操作状态
      setOperationState: (operation, state) => {
        set(prev => ({
          operations: {
            ...prev.operations,
            [operation]: {
              ...prev.operations[operation],
              ...state
            }
          }
        }))
      },

      // 获取模板列表（增强版）
      fetchTemplates: async (force = false) => {
        const { lastFetchTime, cacheValid } = get()
        
        // 缓存检查（5分钟有效期）
        if (!force && cacheValid && lastFetchTime && 
            (Date.now() - lastFetchTime.getTime()) < 5 * 60 * 1000) {
          return
        }

        try {
          get().setOperationState('fetch', { loading: true, error: null, progress: 10 })
          
          const templates = await ApiClient.get<Template[]>('/templates', {
            cache: !force,
            cacheTTL: 5 * 60 * 1000,
            onProgress: (progress) => get().setOperationState('fetch', { progress })
          })
          
          set({ 
            templates,
            lastFetchTime: new Date(),
            cacheValid: true
          })
          
          get().setOperationState('fetch', { loading: false, progress: 100 })
          
        } catch (error: any) {
          console.error('Failed to fetch templates:', error)
          get().setOperationState('fetch', { 
            loading: false, 
            error: error.message || '获取模板列表失败',
            progress: 0
          })
          set({ templates: [], cacheValid: false })
        }
      },

      // 获取单个模板（增强版）
      getTemplate: async (id: string, useCache = true) => {
        try {
          get().setOperationState('fetch', { loading: true, error: null })
          
          const template = await ApiClient.get<Template>(`/templates/${id}`, {
            cache: useCache,
            showToast: false,
            onProgress: (progress) => get().setOperationState('fetch', { progress })
          })
          
          set({ currentTemplate: template })
          get().setOperationState('fetch', { loading: false, progress: 100 })
          
          return template
        } catch (error: any) {
          console.error('Failed to fetch template:', error)
          get().setOperationState('fetch', { 
            loading: false, 
            error: error.message || '获取模板详情失败' 
          })
          throw error
        }
      },

      // 创建模板（增强版）
      createTemplate: async (data: TemplateCreate, onProgress?) => {
        try {
          get().setOperationState('create', { loading: true, error: null, progress: 0 })
          
          const { file, ...templateData } = data
          
          // 第一步：创建模板元数据
          onProgress?.(20)
          const newTemplate = await ApiClient.post<Template>('/templates', templateData, {
            onProgress: (progress) => {
              const adjustedProgress = 20 + (progress * 0.3) // 20-50%
              get().setOperationState('create', { progress: adjustedProgress })
              onProgress?.(adjustedProgress)
            }
          })

          if (!newTemplate?.id) {
            throw new Error('创建模板失败：未返回有效的模板ID')
          }

          // 第二步：上传文件（如果有）
          let finalTemplate = newTemplate
          if (file) {
            onProgress?.(60)
            finalTemplate = await get().uploadTemplateFile(newTemplate.id, file, (uploadProgress) => {
              const adjustedProgress = 60 + (uploadProgress * 0.4) // 60-100%
              get().setOperationState('create', { progress: adjustedProgress })
              onProgress?.(adjustedProgress)
            })
          }
          
          get().addTemplate(finalTemplate)
          get().setOperationState('create', { loading: false, progress: 100 })
          
          // 刷新缓存
          get().invalidateCache('templates')
          
          return finalTemplate
          
        } catch (error: any) {
          console.error('Failed to create template:', error)
          get().setOperationState('create', { 
            loading: false, 
            error: error.message || '创建模板失败',
            progress: 0
          })
          throw error
        }
      },

      // 更新模板（增强版）
      updateTemplate: async (id: string, data: TemplateUpdate) => {
        try {
          get().setOperationState('update', { loading: true, error: null })
          
          const updatedTemplate = await ApiClient.put<Template>(`/templates/${id}`, data, {
            onProgress: (progress) => get().setOperationState('update', { progress })
          })
          
          get().updateTemplateInList(updatedTemplate)
          if (get().currentTemplate?.id === id) {
            set({ currentTemplate: updatedTemplate })
          }
          
          get().setOperationState('update', { loading: false, progress: 100 })
          
          // 刷新缓存
          get().invalidateCache(`templates/${id}`)
          
          return updatedTemplate
          
        } catch (error: any) {
          console.error('Failed to update template:', error)
          get().setOperationState('update', { 
            loading: false, 
            error: error.message || '更新模板失败' 
          })
          throw error
        }
      },

      // 删除模板（增强版）
      deleteTemplate: async (id: string, confirm = true) => {
        if (confirm) {
          const confirmed = window.confirm('确定要删除这个模板吗？此操作不可撤销。')
          if (!confirmed) return
        }

        try {
          get().setOperationState('delete', { loading: true, error: null })
          
          await ApiClient.delete(`/templates/${id}`, {
            showToast: false
          })
          
          get().removeTemplate(id)
          if (get().currentTemplate?.id === id) {
            set({ currentTemplate: null })
          }
          
          get().setOperationState('delete', { loading: false, progress: 100 })
          
          // 刷新缓存
          get().invalidateCache('templates')
          
        } catch (error: any) {
          console.error('Failed to delete template:', error)
          get().setOperationState('delete', { 
            loading: false, 
            error: error.message || '删除模板失败' 
          })
          throw error
        }
      },

      // 上传模板文件（增强版）
      uploadTemplateFile: async (id: string, file: File, onProgress?) => {
        try {
          get().setOperationState('upload', { loading: true, error: null, progress: 0 })
          
          const formData = new FormData()
          formData.append('file', file)

          const updatedTemplate = await ApiClient.put<Template>(`/templates/${id}/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            onUploadProgress: (progressEvent) => {
              const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total!)
              get().setOperationState('upload', { progress })
              onProgress?.(progress)
            }
          })

          get().updateTemplateInList(updatedTemplate)
          if (get().currentTemplate?.id === id) {
            set({ currentTemplate: updatedTemplate })
          }
          
          get().setOperationState('upload', { loading: false, progress: 100 })
          
          // 刷新相关缓存
          get().invalidateCache(`templates/${id}`)
          
          return updatedTemplate
          
        } catch (error: any) {
          console.error('Failed to upload template file:', error)
          get().setOperationState('upload', { 
            loading: false, 
            error: error.message || '模板文件上传失败',
            progress: 0
          })
          throw error
        }
      },

      // 使用DAG架构分析占位符
      analyzeWithDAG: async (templateId: string, dataSourceId: string, mode: 'sql_generation' | 'chart_testing') => {
        try {
          get().setOperationState('analyze', { loading: true, error: null, progress: 0 })
          
          const analysisData = {
            mode: mode === 'sql_generation' ? 'template_sql_generation' : 'template_chart_testing',
            template_id: templateId,
            data_source_id: dataSourceId,
            context: {
              analysis_timestamp: new Date().toISOString(),
              user_preferences: {} // 可以添加用户偏好设置
            }
          }
          
          // 模拟分析进度
          const progressSteps = [
            { progress: 20, message: '构建上下文工程...' },
            { progress: 40, message: '调用DAG智能代理...' },
            { progress: 60, message: '生成SQL查询...' },
            { progress: 80, message: '验证数据源连接...' },
            { progress: 100, message: '分析完成' }
          ]
          
          for (const step of progressSteps) {
            get().setOperationState('analyze', { progress: step.progress })
            // 在实际实现中，这里会等待真实的分析步骤
            await new Promise(resolve => setTimeout(resolve, 500))
          }
          
          // 调用DAG分析API（目前返回占位符信息）
          const result = await ApiClient.post(`/placeholders/analyze`, analysisData, {
            showToast: false // 我们自己控制消息显示
          })
          
          // 分析完成后刷新占位符列表
          await get().fetchPlaceholders(templateId, true)
          
          get().setOperationState('analyze', { loading: false, progress: 100 })
          
          // 显示成功消息和结果详情
          const { showSuccess } = useToast()
          showSuccess(
            `DAG分析完成！${mode === 'sql_generation' ? '已生成SQL查询' : '已生成测试图表'}`,
            5000
          )
          
          return result
          
        } catch (error: any) {
          console.error('Failed to analyze with DAG:', error)
          
          // 如果是DAG功能未实现的错误，给出友好提示
          if (error.message?.includes('正在开发中')) {
            get().setOperationState('analyze', { 
              loading: false, 
              error: 'DAG智能分析功能正在开发中，请使用传统分析方法',
              progress: 0
            })
            
            const { showWarning } = useToast()
            showWarning('DAG功能开发中，已切换到传统分析模式')
            
            // 回退到传统分析方法
            return get().analyzePlaceholders(templateId)
          }
          
          get().setOperationState('analyze', { 
            loading: false, 
            error: error.message || 'DAG分析失败',
            progress: 0
          })
          throw error
        }
      },

      // 传统占位符分析（保持兼容）
      analyzePlaceholders: async (templateId: string, options = {}) => {
        const { forceReparse = false, showProgress = true } = options
        
        try {
          get().setOperationState('analyze', { loading: true, error: null, progress: 0 })
          
          const response = await ApiClient.post(`/templates/${templateId}/analyze-placeholders`, {
            force_reparse: forceReparse
          }, {
            onProgress: showProgress ? (progress) => get().setOperationState('analyze', { progress }) : undefined
          })
          
          if (response.success) {
            // 重新获取占位符列表
            await get().fetchPlaceholders(templateId, true)
          }
          
          get().setOperationState('analyze', { loading: false, progress: 100 })
          
        } catch (error: any) {
          console.error('Failed to analyze placeholders:', error)
          get().setOperationState('analyze', { 
            loading: false, 
            error: error.message || '占位符分析失败',
            progress: 0
          })
        }
      },

      // 获取占位符列表（增强版）
      fetchPlaceholders: async (templateId: string, force = false) => {
        try {
          get().setOperationState('fetch', { loading: true, error: null })
          
          const response = await ApiClient.get(`/templates/${templateId}/placeholders`, {
            cache: !force,
            cacheTTL: 2 * 60 * 1000, // 2分钟缓存
            showToast: false
          })
          
          const placeholderData = response.data || response || {}
          
          // 计算分析统计
          const placeholders = placeholderData.placeholders || []
          const analytics: PlaceholderAnalytics = {
            total_placeholders: placeholders.length,
            analyzed_placeholders: placeholders.filter((p: PlaceholderConfig) => p.agent_analyzed).length,
            sql_validated_placeholders: placeholders.filter((p: PlaceholderConfig) => p.sql_validated).length,
            average_confidence_score: placeholders.length > 0 
              ? placeholders.reduce((sum: number, p: PlaceholderConfig) => sum + (p.confidence_score || 0), 0) / placeholders.length 
              : 0,
            cache_hit_rate: 0, // TODO: 从后端获取实际缓存命中率
            analysis_coverage: placeholders.length > 0 
              ? (placeholders.filter((p: PlaceholderConfig) => p.agent_analyzed).length / placeholders.length * 100) 
              : 0,
            execution_stats: {
              total_executions: 0,
              successful_executions: 0, 
              failed_executions: 0,
              average_execution_time_ms: 0
            }
          }
          
          set({ 
            placeholders,
            placeholderAnalytics: analytics
          })
          
          get().setOperationState('fetch', { loading: false, progress: 100 })
          
        } catch (error: any) {
          console.error('Failed to fetch placeholders:', error)
          get().setOperationState('fetch', { 
            loading: false, 
            error: error.message || '获取占位符列表失败' 
          })
          set({ placeholders: [], placeholderAnalytics: null })
        }
      },

      // 预览模板（增强版）
      previewTemplate: async (content: string, variables = {}) => {
        try {
          get().setOperationState('preview', { loading: true, error: null })
          
          const response = await ApiClient.post('/templates/preview', {
            content,
            variables
          }, {
            showToast: false,
            onProgress: (progress) => get().setOperationState('preview', { progress })
          })
          
          const previewHtml = response.preview || response
          set({ previewContent: previewHtml })
          
          get().setOperationState('preview', { loading: false, progress: 100 })
          
          return previewHtml
          
        } catch (error: any) {
          console.error('Failed to preview template:', error)
          get().setOperationState('preview', { 
            loading: false, 
            error: error.message || '模板预览失败' 
          })
          throw error
        }
      },

      // 获取占位符预览（增强版）
      fetchPlaceholderPreview: async (id: string) => {
        try {
          get().setOperationState('preview', { loading: true, error: null })
          
          const previewData = await ApiClient.get<TemplatePreview>(`/templates/${id}/preview`, {
            cache: true,
            cacheTTL: 60 * 1000, // 1分钟缓存
            showToast: false
          })
          
          set({ placeholderPreview: previewData })
          get().setOperationState('preview', { loading: false, progress: 100 })
          
        } catch (error: any) {
          console.error('Failed to fetch placeholder preview:', error)
          get().setOperationState('preview', { 
            loading: false, 
            error: error.message || '获取占位符预览失败' 
          })
          set({ placeholderPreview: null })
        }
      },

      // 缓存管理
      invalidateCache: (pattern = '') => {
        const cacheStats = ApiClient.getCacheStats()
        if (pattern) {
          cacheStats.invalidatePattern(pattern)
        } else {
          cacheStats.clear()
        }
        
        // 重置本地缓存状态
        set({ cacheValid: false, lastFetchTime: null })
      },

      // 刷新单个模板
      refreshTemplate: async (id: string) => {
        get().invalidateCache(`templates/${id}`)
        return get().getTemplate(id, false)
      },

      // 内部方法
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

      // 重置状态
      reset: () => {
        set({
          templates: [],
          currentTemplate: null,
          previewContent: '',
          placeholderPreview: null,
          placeholders: [],
          placeholderAnalytics: null,
          operations: {
            fetch: { ...initialOperationState },
            create: { ...initialOperationState },
            update: { ...initialOperationState },
            delete: { ...initialOperationState },
            upload: { ...initialOperationState },
            analyze: { ...initialOperationState },
            preview: { ...initialOperationState }
          },
          lastFetchTime: null,
          cacheValid: false
        })
      }
    }),
    {
      name: 'enhanced-template-store'
    }
  )
)