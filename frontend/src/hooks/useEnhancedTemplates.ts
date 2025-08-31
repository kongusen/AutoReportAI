/**
 * 增强的模板管理Hook - 提供更好的用户反馈和状态管理
 */

import { useState, useCallback } from 'react'
import { useTemplateStore } from '@/features/templates/templateStore'
import { useToast } from '@/hooks/useToast'

interface OperationState {
  loading: boolean
  progress: number
  error: string | null
}

const initialState: OperationState = {
  loading: false,
  progress: 0,
  error: null
}

export function useEnhancedTemplates() {
  const originalStore = useTemplateStore()
  const { showSuccess, showError, showWarning } = useToast()
  
  const [operations, setOperations] = useState({
    fetch: { ...initialState },
    delete: { ...initialState },
    create: { ...initialState },
    update: { ...initialState }
  })

  const setOperationState = useCallback((operation: keyof typeof operations, state: Partial<OperationState>) => {
    setOperations(prev => ({
      ...prev,
      [operation]: { ...prev[operation], ...state }
    }))
  }, [])

  // 增强的删除功能
  const deleteTemplate = useCallback(async (id: string) => {
    try {
      setOperationState('delete', { loading: true, error: null, progress: 10 })
      
      await originalStore.deleteTemplate(id)
      
      setOperationState('delete', { loading: false, progress: 100 })
      showSuccess('模板删除成功')
      
    } catch (error: any) {
      setOperationState('delete', { 
        loading: false, 
        error: error.message || '删除模板失败',
        progress: 0 
      })
      showError(error.message || '删除模板失败')
      throw error
    }
  }, [originalStore.deleteTemplate, setOperationState, showSuccess, showError])

  // 增强的获取功能
  const fetchTemplates = useCallback(async () => {
    try {
      setOperationState('fetch', { loading: true, error: null, progress: 20 })
      
      await originalStore.fetchTemplates()
      
      setOperationState('fetch', { loading: false, progress: 100 })
      
    } catch (error: any) {
      setOperationState('fetch', { 
        loading: false, 
        error: error.message || '获取模板列表失败',
        progress: 0 
      })
      showError(error.message || '获取模板列表失败')
    }
  }, [originalStore.fetchTemplates, setOperationState, showError])

  return {
    ...originalStore,
    operations,
    fetchTemplates,
    deleteTemplate,
    setOperationState
  }
}