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
  
  // Batch operations
  batchUpdateStatus: (ids: string[], isActive: boolean) => Promise<void>
  batchDeleteTasks: (ids: string[]) => Promise<void>
  
  // Progress management
  updateTaskProgress: (progress: TaskProgress) => void
  getTaskProgress: (taskId: string) => TaskProgress | undefined
  
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

  // 执行任务
  executeTask: async (id: string) => {
    try {
      await api.post(`/tasks/${id}/execute`)
      toast.success('任务执行请求已发送')
    } catch (error: any) {
      console.error('Failed to execute task:', error)
      toast.error('执行任务失败')
      throw error
    }
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