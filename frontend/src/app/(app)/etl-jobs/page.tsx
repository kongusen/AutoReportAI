'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { MoreHorizontal, Plus, Play, TestTube } from 'lucide-react'
import { ETLJobForm } from '@/components/forms'

// Define the shape of an ETL Job object
export type ETLJob = {
  id: string
  name: string
  description: string | null
  schedule: string | null
  enabled: boolean
  created_at: string
  updated_at: string | null
}

export default function ETLJobsPage() {
  const [jobs, setJobs] = useState<ETLJob[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingJob, setEditingJob] = useState<ETLJob | null>(null)
  const [runningJobs, setRunningJobs] = useState<Set<string>>(new Set())

  const fetchJobs = async () => {
    try {
      setIsLoading(true)
      const response = await api.get('/etl-jobs')
      setJobs(Array.isArray(response.data) ? response.data : (response.data.items || []))
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('An unknown error occurred')
      }
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchJobs()
  }, [])

  const handleCreateJob = async (values: any) => {
    try {
      await api.post('/etl-jobs', values)
      fetchJobs()
      setIsDialogOpen(false)
    } catch (error) {
      console.error('Failed to create ETL job:', error)
      alert('Failed to create ETL job')
    }
  }

  const handleEditJob = async (values: any) => {
    if (!editingJob) return
    
    try {
      await api.put(`/etl-jobs/${editingJob.id}`, values)
      fetchJobs()
      setIsDialogOpen(false)
      setEditingJob(null)
    } catch (error) {
      console.error('Failed to edit ETL job:', error)
      alert('Failed to edit ETL job')
    }
  }

  const handleEdit = (jobId: string) => {
    const job = jobs.find(j => j.id === jobId)
    if (job) {
      setEditingJob(job)
      setIsDialogOpen(true)
    }
  }

  const handleDelete = async (jobId: string) => {
    if (!confirm('Are you sure you want to delete this job?')) return
    
    try {
      await api.delete(`/etl-jobs/${jobId}`)
      setJobs(jobs.filter(job => job.id !== jobId))
    } catch (err) {
      console.error('Failed to delete job:', err)
      alert('Failed to delete job')
    }
  }

  const handleRun = async (jobId: string) => {
    setRunningJobs(prev => new Set(prev).add(jobId))
    try {
      await api.post(`/etl-jobs/${jobId}/run`)
      alert('Job execution started successfully')
      fetchJobs() // 刷新状态
    } catch (err) {
      console.error('Failed to run job:', err)
      alert('Failed to start job execution')
    } finally {
      setRunningJobs(prev => {
        const newSet = new Set(prev)
        newSet.delete(jobId)
        return newSet
      })
    }
  }

  const openCreateDialog = () => {
    setEditingJob(null)
    setIsDialogOpen(true)
  }

  if (error) {
    return <div className="text-center text-red-500">{typeof error === 'string' ? error : (error as any).msg || JSON.stringify(error)}</div>
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">ETL Jobs</h2>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={openCreateDialog}>
              <Plus className="mr-2 h-4 w-4" />
              Create New Job
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>
                {editingJob ? 'Edit ETL Job' : 'Create New ETL Job'}
              </DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <ETLJobForm 
                onSubmit={editingJob ? handleEditJob : handleCreateJob}
                defaultValues={editingJob ? {
                  name: editingJob.name,
                  description: editingJob.description || '',
                  schedule: editingJob.schedule || '',
                  enabled: editingJob.enabled
                } : undefined}
              />
            </div>
          </DialogContent>
        </Dialog>
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Schedule</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created At</TableHead>
              <TableHead>Last Updated</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="h-24 text-center">
                  Loading...
                </TableCell>
              </TableRow>
            ) : jobs.length > 0 ? (
              jobs.map((job) => (
                <TableRow key={job.id}>
                  <TableCell className="font-medium">{job.name}</TableCell>
                  <TableCell className="max-w-xs truncate">
                    {job.description || 'No description'}
                  </TableCell>
                  <TableCell>
                    {job.schedule ? (
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {job.schedule}
                      </code>
                    ) : (
                      'Not scheduled'
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={job.enabled ? 'default' : 'secondary'}>
                      {job.enabled ? 'Enabled' : 'Disabled'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {new Date(job.created_at).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    {job.updated_at
                      ? new Date(job.updated_at).toLocaleString()
                      : 'N/A'}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="h-8 w-8 p-0">
                          <span className="sr-only">Open menu</span>
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuLabel>Actions</DropdownMenuLabel>
                        <DropdownMenuItem onClick={() => handleEdit(job.id)}>
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem 
                          onClick={() => handleRun(job.id)}
                          disabled={runningJobs.has(job.id)}
                        >
                          <Play className="mr-2 h-4 w-4" />
                          {runningJobs.has(job.id) ? 'Running...' : 'Run Now'}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-red-600"
                          onClick={() => handleDelete(job.id)}
                        >
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={7} className="h-24 text-center">
                  No ETL jobs found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}