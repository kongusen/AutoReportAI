'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import api from '@/lib/api'
import { AxiosResponse } from 'axios'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { TaskForm, ProcessedTaskFormValues } from '../forms/TaskForm'
import { useI18n } from '@/lib/i18n'

interface Task {
  id: number
  name: string
  schedule?: string
  is_active: boolean
  template: { id: number; name: string }
  data_source: { id: number; name: string }
  execution_count?: number
  last_execution?: string
  next_execution?: string
}

interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

export function TaskList() {
  const { t } = useI18n()
  const [tasks, setTasks] = useState<Task[]>([])
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingTask, setEditingTask] = useState<Task | null>(null)

  const fetchTasks = () => {
    api
      .get('/tasks')
      .then((response: AxiosResponse<PaginatedResponse<Task>>) => {
        setTasks(Array.isArray(response.data) ? response.data : (response.data.items || []))
      })
  }

  useEffect(() => {
    fetchTasks()
  }, [])

  const handleCreateTask = async (values: ProcessedTaskFormValues) => {
    try {
      await api.post('/tasks', values)
      fetchTasks()
      setIsDialogOpen(false)
    } catch (error) {
      console.error('Failed to create task:', error)
    }
  }

  const handleEditTask = async (values: ProcessedTaskFormValues) => {
    if (!editingTask) return
    
    try {
      await api.put(`/tasks/${editingTask.id}`, values)
      fetchTasks()
      setIsDialogOpen(false)
      setEditingTask(null)
    } catch (error) {
      console.error('Failed to edit task:', error)
    }
  }

  const openEditDialog = (task: Task) => {
    setEditingTask(task)
    setIsDialogOpen(true)
  }

  const openCreateDialog = () => {
    setEditingTask(null)
    setIsDialogOpen(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">{t('tasks.title')}</h1>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={openCreateDialog}>{t('tasks.create')}</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>
                {editingTask ? t('tasks.edit') : t('tasks.create')}
              </DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <TaskForm 
                onSubmit={editingTask ? handleEditTask : handleCreateTask}
                defaultValues={editingTask ? {
                  name: editingTask.name,
                  template_id: String(editingTask.template.id),
                  data_source_id: String(editingTask.data_source.id),
                  schedule: editingTask.schedule,
                  is_active: editingTask.is_active
                } : undefined}
              />
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {tasks.map((task) => (
          <Card key={task.id}>
            <CardHeader>
              <CardTitle>{task.name}</CardTitle>
              <CardDescription>
                {t('tasks.template')}: {task.template.name} | {t('tasks.dataSource')}: {task.data_source.name}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <span
                    className={`h-2 w-2 rounded-full ${task.is_active ? 'bg-green-500' : 'bg-gray-400'}`}
                  ></span>
                  <span className="text-sm text-gray-500">
                    {task.is_active ? t('status.active') : t('status.inactive')}
                  </span>
                </div>
                {task.schedule && (
                  <p className="text-sm text-gray-600">
                    {t('tasks.schedule')}: <code>{task.schedule}</code>
                  </p>
                )}
                {task.execution_count !== undefined && (
                  <p className="text-sm text-gray-600">
                    {t('tasks.executionCount')}: {task.execution_count}
                  </p>
                )}
                {task.last_execution && (
                  <p className="text-sm text-gray-600">
                    {t('tasks.lastExecution')}: {new Date(task.last_execution).toLocaleString()}
                  </p>
                )}
                {task.next_execution && (
                  <p className="text-sm text-gray-600">
                    {t('tasks.nextExecution')}: {new Date(task.next_execution).toLocaleString()}
                  </p>
                )}
              </div>
            </CardContent>
            <CardFooter className="flex gap-2">
              <Link href={`/tasks/${task.id}/history`} passHref>
                <Button variant="outline" size="sm">
                  {t('tasks.history')}
                </Button>
              </Link>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => openEditDialog(task)}
              >
                {t('common.edit')}
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    </div>
  )
}
