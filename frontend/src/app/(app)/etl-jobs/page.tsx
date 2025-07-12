'use client'

import { useEffect, useState } from 'react'
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
import { MoreHorizontal } from 'lucide-react'

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

  useEffect(() => {
    async function fetchJobs() {
      try {
        setIsLoading(true)
        // We'll need to handle authentication token properly later
        const response = await fetch('/api/v1/etl-jobs')
        if (!response.ok) {
          throw new Error('Failed to fetch ETL jobs')
        }
        const data = await response.json()
        setJobs(data)
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
    fetchJobs()
  }, [])

  const handleEdit = (jobId: string) => {
    // Placeholder for edit functionality
    console.log('Edit job:', jobId)
  }

  const handleDelete = async (jobId: string) => {
    // Placeholder for delete functionality
    if (confirm('Are you sure you want to delete this job?')) {
      console.log('Delete job:', jobId)
      // try {
      //     await fetch(`/api/v1/etl-jobs/${jobId}`, { method: 'DELETE' });
      //     setJobs(jobs.filter(job => job.id !== jobId));
      // } catch (err) {
      //     console.error("Failed to delete job", err);
      // }
    }
  }

  const handleRun = async (jobId: string) => {
    // Placeholder for run functionality
    console.log('Run job:', jobId)
    // try {
    //     await fetch(`/api/v1/etl-jobs/${jobId}/run`, { method: 'POST' });
    //     alert("Job execution started.");
    // } catch (err) {
    //     console.error("Failed to run job", err);
    //     alert("Failed to start job execution.");
    // }
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">ETL Jobs</h2>
        <Button>Create New Job</Button>
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
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
                <TableCell colSpan={6} className="h-24 text-center">
                  Loading...
                </TableCell>
              </TableRow>
            ) : error ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="h-24 text-center text-red-500"
                >
                  {error}
                </TableCell>
              </TableRow>
            ) : jobs.length > 0 ? (
              jobs.map((job) => (
                <TableRow key={job.id}>
                  <TableCell className="font-medium">{job.name}</TableCell>
                  <TableCell>{job.schedule || 'Not scheduled'}</TableCell>
                  <TableCell>{job.enabled ? 'Enabled' : 'Disabled'}</TableCell>
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
                        <DropdownMenuItem onClick={() => handleRun(job.id)}>
                          Run Now
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
                <TableCell colSpan={6} className="h-24 text-center">
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
