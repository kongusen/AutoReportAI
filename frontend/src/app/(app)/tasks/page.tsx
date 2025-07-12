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
import { TaskForm, ProcessedTaskFormValues } from '@/components/TaskForm'

interface Task {
  id: number
  name: string
  schedule?: string
  is_active: boolean
  template: { name: string }
  data_source: { name: string }
}

interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  const fetchTasks = () => {
    api
      .get('/tasks')
      .then((response: AxiosResponse<PaginatedResponse<Task>>) => {
        setTasks(response.data.items)
      })
  }

  useEffect(() => {
    fetchTasks()
  }, [])

  const handleCreateTask = async (values: ProcessedTaskFormValues) => {
    try {
      await api.post('/tasks', values)
      // Refresh the tasks list to show the new task without a full page reload.
      fetchTasks()
      setIsDialogOpen(false) // Close the dialog
    } catch (error) {
      console.error('Failed to create task:', error)
      // Here you could show an error message to the user
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Tasks</h1>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button>Create New Task</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>Create a New Task</DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <TaskForm onSubmit={handleCreateTask} />
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
                Template: {task.template.name} | Data Source:{' '}
                {task.data_source.name}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center space-x-2">
                <span
                  className={`h-2 w-2 rounded-full ${task.is_active ? 'bg-green-500' : 'bg-gray-400'}`}
                ></span>
                <span className="text-sm text-gray-500">
                  {task.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              {task.schedule && (
                <p className="text-sm text-gray-600 mt-2">
                  Schedule: <code>{task.schedule}</code>
                </p>
              )}
            </CardContent>
            <CardFooter>
              <Link href={`/tasks/${task.id}/history`} passHref>
                <Button variant="outline" size="sm">
                  View History
                </Button>
              </Link>
            </CardFooter>
          </Card>
        ))}
      </div>
    </div>
  )
}
