'use client'

import { create } from 'zustand'
import { Task, TaskCreate, TaskUpdate, TaskProgress } from '@/types'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

interface TaskState {
  tasks: Task[]
  currentTask: Task | null
  taskProgress: Map<string, TaskProgress>
  loading: boolean
  
  // Actions
  fetchTasks: () => Promise<void>
  getTask: (id: string) => Promise<Task>
  createTask: (data: TaskCreate) => Promise<Task>
  updateTask: (id: string, data: TaskUpdate) => Promise<Task>
  deleteTask: (id: string) => Promise<void>
  toggleTaskStatus: (id: string, isActive: boolean) => Promise<void>
  executeTask: (id: string) => Promise<void>
  
  // Task status methods
  fetchTaskStatus: (id: string) => Promise<any>
  startTaskStatusPolling: (taskId: string) => void
  startLongTaskPolling: (taskId: string) => void
  
  // Batch operations
  batchUpdateStatus: (ids: string[], isActive: boolean) => Promise<void>
  batchDeleteTasks: (ids: string[]) => Promise<void>
  
  // Progress management
  updateTaskProgress: (progress: TaskProgress) => void
  getTaskProgress: (taskId: string) => TaskProgress | undefined
  clearTaskProgress: (taskId: string) => void
  
  // Internal methods
  setLoading: (loading: boolean) => void
  setTasks: (tasks: Task[]) => void
  setCurrentTask: (task: Task | null) => void
  addTask: (task: Task) => void
  updateTaskInList: (task: Task) => void
  removeTask: (id: string) => void
  removeTasks: (ids: string[]) => void
}

export const useTaskStore = create<TaskState>((set, get) => ({
  tasks: [],
  currentTask: null,
  taskProgress: new Map(),
  loading: false,

  // 获取任务列表
  fetchTasks: async () => {
    try {
      set({ loading: true })
      const response = await api.get('/tasks')
      // 处理后端返回的ApiResponse和PaginatedResponse格式
      let tasks = []
      if (response.data?.items) {
        // 处理分页响应
        tasks = response.data.items
      } else if (response.data && Array.isArray(response.data)) {
        // 处理数组响应
        tasks = response.data
      } else if (Array.isArray(response)) {
        // 处理直接数组响应
        tasks = response
      }
      set({ tasks })
    } catch (error: any) {
      console.error('Failed to fetch tasks:', error)
      toast.error('获取任务列表失败')
      set({ tasks: [] })
    } finally {
      set({ loading: false })
    }
  },

  // 获取单个任务
  getTask: async (id: string) => {
    try {
      set({ loading: true })
      const response = await api.get(`/tasks/${id}`)
      const task = response.data || response
      set({ currentTask: task })
      return task
    } catch (error: any) {
      console.error('Failed to fetch task:', error)
      toast.error('获取任务详情失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 创建任务
  createTask: async (data: TaskCreate) => {
    try {
      set({ loading: true })
      const response = await api.post('/tasks', data)
      const newTask = response.data || response
      
      get().addTask(newTask)
      toast.success('任务创建成功')
      return newTask
    } catch (error: any) {
      console.error('Failed to create task:', error)
      toast.error('创建任务失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 更新任务
  updateTask: async (id: string, data: TaskUpdate) => {
    try {
      set({ loading: true })
      const response = await api.put(`/tasks/${id}`, data)
      const updatedTask = response.data || response
      
      get().updateTaskInList(updatedTask)
      if (get().currentTask?.id.toString() === id) {
        set({ currentTask: updatedTask })
      }
      toast.success('任务更新成功')
      return updatedTask
    } catch (error: any) {
      console.error('Failed to update task:', error)
      toast.error('更新任务失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 删除任务
  deleteTask: async (id: string) => {
    try {
      set({ loading: true })
      await api.delete(`/tasks/${id}`)
      
      get().removeTask(id)
      if (get().currentTask?.id.toString() === id) {
        set({ currentTask: null })
      }
      toast.success('任务删除成功')
    } catch (error: any) {
      console.error('Failed to delete task:', error)
      toast.error('删除任务失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 切换任务状态
  toggleTaskStatus: async (id: string, isActive: boolean) => {
    try {
      const response = await api.patch(`/tasks/${id}/status`, { is_active: isActive })
      const updatedTask = response.data || response
      
      get().updateTaskInList(updatedTask)
      toast.success(`任务已${isActive ? '启用' : '停用'}`)
    } catch (error: any) {
      console.error('Failed to toggle task status:', error)
      toast.error('更新任务状态失败')
      throw error
    }
  },

  // 执行任务 - 改进错误处理
  executeTask: async (id: string) => {
    try {
      const response = await api.post(`/tasks/${id}/execute?use_intelligent_placeholders=true`)
      const result = response.data || response
      
      // 开始轮询任务状态
      get().startTaskStatusPolling(id)
      
      toast.success('任务执行请求已发送，开始处理...')
      return result
    } catch (error: any) {
      console.error('Failed to execute task:', error)
      
      // 提供更详细的错误信息
      const errorMessage = error.response?.data?.message || error.message || '执行任务失败'
      const errorDetails = error.response?.data?.details || error.response?.data?.error
      
      // 使用增强的错误显示
      toast.error(errorMessage, {
        duration: 8000,
      })
      
      if (errorDetails) {
        console.error('Task execution error details:', errorDetails)
      }
      
      throw error
    }
  },

  // 获取任务状态 - 改进错误处理
  fetchTaskStatus: async (id: string) => {
    try {
      const response = await api.get(`/tasks/${id}/status`)
      const statusData = response.data || response
      
      // 更新任务进度
      if (statusData) {
        const progress: TaskProgress = {
          task_id: id,
          progress: parseInt(statusData.progress) || 0,
          status: statusData.status || 'pending',
          message: statusData.current_step || statusData.message
        }
        get().updateTaskProgress(progress)
        
        // 检查是否有错误状态
        if (statusData.status === 'failed' && statusData.error) {
          // 这里可以使用增强的toast系统显示错误
          console.error(`Task ${id} failed:`, statusData.error)
        }
      }
      
      return statusData
    } catch (error: any) {
      console.error('Failed to fetch task status:', error)
      return null
    }
  },

  // 开始任务状态轮询 - 改进错误显示和处理95%卡住问题
  startTaskStatusPolling: (taskId: string) => {
    let pollCount = 0
    let lastProgress = -1
    let stuckProgressCount = 0
    const maxStuckCount = 10 // 10次相同进度后认为卡住
    
    const pollInterval = setInterval(async () => {
      pollCount++
      const status = await get().fetchTaskStatus(taskId)
      
      if (status) {
        const currentProgress = parseInt(status.progress) || 0
        
        // 检测是否卡在同一进度
        if (currentProgress === lastProgress && currentProgress >= 95) {
          stuckProgressCount++
          console.warn(`任务 ${taskId} 可能卡在 ${currentProgress}% (连续 ${stuckProgressCount} 次)`)
          
          // 如果卡在95%以上超过10次，显示警告
          if (stuckProgressCount >= maxStuckCount) {
            toast(`任务 #${taskId} 似乎在 ${currentProgress}% 处暂停，可能正在处理大文件...`, {
              icon: '⏳',
              duration: 5000,
              style: {
                background: '#FEF3C7',
                color: '#D97706'
              }
            })
            stuckProgressCount = 0 // 重置计数，避免重复提示
          }
        } else {
          lastProgress = currentProgress
          stuckProgressCount = 0
        }
      }
      
      if (status && (status.status === 'completed' || status.status === 'failed')) {
        clearInterval(pollInterval)
        
        // 显示完成通知
        if (status.status === 'completed') {
          const successMessage = status.successful_count && status.total_placeholders 
            ? `任务 #${taskId} 执行完成 (${status.successful_count}/${status.total_placeholders} 个占位符处理成功)`
            : `任务 #${taskId} 执行完成`
          toast.success(successMessage)
          
          // 如果有错误但整体完成，显示警告
          if (status.has_errors) {
            toast(`任务完成但存在部分错误，请查看详情`, {
              icon: '⚠️',
              style: {
                background: '#FEF3C7',
                color: '#D97706',
                border: '1px solid #F59E0B'
              }
            })
          }
        } else {
          // 使用增强的错误显示
          const errorMessage = status.error || status.message || '未知错误'
          const errorDetails = status.traceback || status.details
          
          toast.error(`任务 #${taskId} 执行失败: ${errorMessage}`, {
            duration: 10000,
          })
          
          console.error('Task failed with details:', {
            taskId,
            error: errorMessage,
            details: errorDetails,
            status
          })
        }
      }
      
      // 如果轮询超过60次(2分钟)且任务仍在运行，延长轮询时间
      if (pollCount > 60 && status && status.status === 'processing') {
        console.log(`任务 ${taskId} 运行时间较长，延长轮询间隔`)
        clearInterval(pollInterval)
        
        // 启动更长间隔的轮询
        get().startLongTaskPolling(taskId)
      }
    }, 2000) // 每2秒轮询一次

    // 2分钟后停止快速轮询
    setTimeout(() => {
      clearInterval(pollInterval)
      
      // 检查任务是否仍在运行
      const currentStatus = get().getTaskProgress(taskId)
      if (currentStatus && currentStatus.status === 'processing') {
        console.log(`任务 ${taskId} 仍在运行，启动长时间轮询`)
        get().startLongTaskPolling(taskId)
      }
    }, 120000)
  },

  // 长时间任务轮询
  startLongTaskPolling: (taskId: string) => {
    const longPollInterval = setInterval(async () => {
      const status = await get().fetchTaskStatus(taskId)
      
      if (status && (status.status === 'completed' || status.status === 'failed')) {
        clearInterval(longPollInterval)
        
        if (status.status === 'completed') {
          toast.success(`长时间任务 #${taskId} 最终完成了！`)
        } else {
          toast.error(`长时间任务 #${taskId} 执行失败`)
        }
      }
    }, 10000) // 每10秒轮询一次

    // 10分钟后停止长时间轮询
    setTimeout(() => {
      clearInterval(longPollInterval)
      toast(`任务 #${taskId} 轮询已停止，请手动检查状态`, {
        icon: 'ℹ️',
        duration: 8000
      })
    }, 600000)
  },

  // 批量更新状态
  batchUpdateStatus: async (ids: string[], isActive: boolean) => {
    try {
      set({ loading: true })
      await api.patch('/tasks/batch/status', { 
        task_ids: ids.map(id => parseInt(id)), 
        is_active: isActive 
      })
      
      // 更新本地状态
      const { tasks } = get()
      const updatedTasks = tasks.map(task => 
        ids.includes(task.id.toString()) 
          ? { ...task, is_active: isActive }
          : task
      )
      set({ tasks: updatedTasks })
      
      toast.success(`批量${isActive ? '启用' : '停用'}任务成功`)
    } catch (error: any) {
      console.error('Failed to batch update task status:', error)
      toast.error('批量更新任务状态失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 批量删除任务
  batchDeleteTasks: async (ids: string[]) => {
    try {
      set({ loading: true })
      await api.delete('/tasks/batch', {
        data: { task_ids: ids.map(id => parseInt(id)) }
      })
      
      get().removeTasks(ids)
      toast.success('批量删除任务成功')
    } catch (error: any) {
      console.error('Failed to batch delete tasks:', error)
      toast.error('批量删除任务失败')
      throw error
    } finally {
      set({ loading: false })
    }
  },

  // 更新任务进度
  updateTaskProgress: (progress: TaskProgress) => {
    const { taskProgress } = get()
    const newProgress = new Map(taskProgress)
    newProgress.set(progress.task_id, progress)
    set({ taskProgress: newProgress })
  },

  // 获取任务进度
  getTaskProgress: (taskId: string) => {
    const { taskProgress } = get()
    return taskProgress.get(taskId)
  },

  // 清除任务进度
  clearTaskProgress: (taskId: string) => {
    const { taskProgress } = get()
    const newProgress = new Map(taskProgress)
    newProgress.delete(taskId)
    set({ taskProgress: newProgress })
  },

  // Internal methods
  setLoading: (loading: boolean) => set({ loading }),
  
  setTasks: (tasks: Task[]) => set({ tasks }),
  
  setCurrentTask: (task: Task | null) => set({ currentTask: task }),
  
  addTask: (task: Task) => {
    const { tasks } = get()
    set({ tasks: [task, ...tasks] })
  },
  
  updateTaskInList: (updatedTask: Task) => {
    const { tasks } = get()
    const updatedList = tasks.map(task => 
      task.id === updatedTask.id ? updatedTask : task
    )
    set({ tasks: updatedList })
  },
  
  removeTask: (id: string) => {
    const { tasks } = get()
    const filteredList = tasks.filter(task => task.id.toString() !== id)
    set({ tasks: filteredList })
  },

  removeTasks: (ids: string[]) => {
    const { tasks } = get()
    const numericIds = ids.map(id => parseInt(id))
    const filteredList = tasks.filter(task => !numericIds.includes(task.id))
    set({ tasks: filteredList })
  },
}))