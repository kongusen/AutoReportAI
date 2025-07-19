'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'

// Define the shape of our objects
interface ReportHistory {
  id: number
  created_at: string
  status: 'success' | 'failure' | 'in_progress'
  report_path: string | null
  error_message: string | null
}

interface Task {
  id: number
  name: string
}

export default function TaskHistoryPage() {
  const params = useParams()
  const taskId = params.id as string

  const [history, setHistory] = useState<ReportHistory[]>([])
  const [task, setTask] = useState<Task | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!taskId) return

    const fetchHistory = async () => {
      try {
        // Fetch both task details and its history
        const [taskResponse, historyResponse] = await Promise.all([
          api.get(`/tasks/${taskId}`),
          api.get(`/history/task/${taskId}`),
        ])
        setTask(taskResponse.data)
        setHistory(Array.isArray(historyResponse.data) ? historyResponse.data : (historyResponse.data.items || []))
      } catch (err) {
        setError('Failed to fetch task history.')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    fetchHistory()
  }, [taskId])

  const getStatusChip = (status: ReportHistory['status']) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'failure':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      case 'in_progress':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      default:
        return 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
    }
  }

  if (loading) {
    return <div className="text-center text-gray-500">Loading history...</div>
  }

  if (error) {
    return <div className="text-center text-red-500">{error}</div>
  }

  return (
    <div className="container mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <Link href="/tasks" className="text-sm text-gray-500 hover:underline">
            &larr; Back to Tasks
          </Link>
          <h1 className="text-3xl font-bold text-gray-800 dark:text-white mt-1">
            History for: {task?.name || `Task ${taskId}`}
          </h1>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
        <ul className="divide-y divide-gray-200 dark:divide-gray-700">
          {history.length === 0 ? (
            <li className="p-6 text-center text-gray-500 dark:text-gray-400">
              No history found for this task.
            </li>
          ) : (
            history.map((entry) => (
              <li key={entry.id} className="p-4 sm:p-6">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center">
                  <div className="mb-4 sm:mb-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      Run at: {new Date(entry.created_at).toLocaleString()}
                    </p>
                    <span
                      className={`mt-2 inline-block px-3 py-1 text-xs font-semibold rounded-full ${getStatusChip(entry.status)}`}
                    >
                      {entry.status}
                    </span>
                  </div>
                  <div className="w-full sm:w-auto">
                    {entry.status === 'success' && entry.report_path && (
                      <a
                        href={`${api.defaults.baseURL}/reports/download/${entry.report_path.split('/').pop()}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Button variant="outline">Download Report</Button>
                      </a>
                    )}
                  </div>
                </div>
                {entry.status === 'failure' && entry.error_message && (
                  <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-md">
                    <p className="text-sm text-red-700 dark:text-red-300">
                      <strong>Error:</strong> {entry.error_message}
                    </p>
                  </div>
                )}
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  )
}
