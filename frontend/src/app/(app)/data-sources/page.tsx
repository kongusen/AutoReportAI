'use client'

import { useState, useEffect } from 'react'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'

interface DataSource {
  id: number
  name: string
  source_type: string
}

export default function DataSourcesPage() {
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchDataSources = async () => {
      try {
        const response = await api.get('/data-sources')
        setDataSources(response.data.items || [])
      } catch (err) {
        setError('Failed to fetch data sources.')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchDataSources()
  }, [])

  if (loading) {
    return (
      <div className="text-center text-gray-500">Loading data sources...</div>
    )
  }

  if (error) {
    return <div className="text-center text-red-500">{error}</div>
  }

  return (
    <div className="container mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-white">
          Data Sources
        </h1>
        <Button>Add New Data Source</Button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
              >
                ID
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
              >
                Name
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
              >
                Type
              </th>
              <th scope="col" className="relative px-6 py-3">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {dataSources.map((source) => (
              <tr key={source.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                  {source.id}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                  {source.name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                  <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                    {source.source_type}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <Button
                    variant="link"
                    className="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300"
                  >
                    Edit
                  </Button>
                  <Button
                    variant="link"
                    className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                  >
                    Delete
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
