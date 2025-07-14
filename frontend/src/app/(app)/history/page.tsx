'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Download, FileText, AlertCircle, Clock, CheckCircle } from 'lucide-react'

interface ReportHistory {
  id: number
  task_id: number
  status: 'success' | 'failure' | 'in_progress'
  file_path?: string
  error_message?: string
  generated_at: string
}

interface Task {
  id: number
  name: string
}

const StatusBadge = ({ status }: { status: ReportHistory['status'] }) => {
  switch (status) {
    case 'success':
      return (
        <div className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <CheckCircle className="w-3 h-3 mr-1" />
          Success
        </div>
      )
    case 'failure':
      return (
        <div className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
          <AlertCircle className="w-3 h-3 mr-1" />
          Failed
        </div>
      )
    case 'in_progress':
      return (
        <div className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          <Clock className="w-3 h-3 mr-1" />
          In Progress
        </div>
      )
    default:
      return <span className="text-gray-500">{status}</span>
  }
}

export default function HistoryPage() {
  const [history, setHistory] = useState<ReportHistory[]>([])
  const [tasks, setTasks] = useState<{ [key: number]: Task }>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchHistory()
  }, [])

  const fetchHistory = async () => {
    try {
      const response = await fetch('/api/history')
      if (response.ok) {
        const historyData: ReportHistory[] = await response.json()
        setHistory(historyData)
        
        // Fetch task details for each unique task_id
        const taskIds: number[] = [...new Set(historyData.map((h: ReportHistory) => h.task_id))]
        const taskPromises = taskIds.map(id => 
          fetch(`/api/tasks/${id}`).then(res => res.ok ? res.json() : null)
        )
        
        const taskResults = await Promise.all(taskPromises)
        const taskMap: { [key: number]: Task } = {}
        taskResults.forEach((task, index) => {
          if (task && taskIds[index] !== undefined) {
            taskMap[taskIds[index]] = task
          }
        })
        setTasks(taskMap)
      }
    } catch (error) {
      console.error('Error fetching history:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = (filePath: string) => {
    // Extract filename from path
    const filename = filePath.split('/').pop()
    window.open(`/api/reports/download/${filename}`, '_blank')
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Loading history...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Report History</h1>
        <p className="text-gray-600">View all report generation history</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Generation History</CardTitle>
          <CardDescription>
            {history.length} report generation{history.length !== 1 ? 's' : ''} recorded
          </CardDescription>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No report generation history found.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Task</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Generated At</TableHead>
                  <TableHead>Error Message</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell className="font-medium">
                      {tasks[entry.task_id]?.name || `Task ${entry.task_id}`}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={entry.status} />
                    </TableCell>
                    <TableCell>{formatDate(entry.generated_at)}</TableCell>
                    <TableCell>
                      {entry.error_message ? (
                        <div className="max-w-xs truncate text-red-600" title={entry.error_message}>
                          {entry.error_message}
                        </div>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {entry.status === 'success' && entry.file_path && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDownload(entry.file_path!)}
                        >
                          <Download className="w-4 h-4 mr-2" />
                          Download
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
} 