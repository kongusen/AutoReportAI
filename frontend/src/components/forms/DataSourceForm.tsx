'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { LoadingSpinner, LoadingButton } from '@/components/ui/loading'
import { useFormErrorHandler } from '@/components/providers/ErrorNotificationProvider'
import { useApiCall } from '@/lib/hooks/useApiCall'
import { enhancedDataSourceApiService } from '@/lib/api/services/enhanced-data-source-service'

export const dataSourceFormSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  source_type: z.enum(['sql', 'csv', 'api']),
  db_query: z.string().optional(),
  file_path: z.string().optional(),
  api_url: z.string().url().optional().or(z.literal('')),
})

export type DataSourceFormValues = z.infer<typeof dataSourceFormSchema>

interface DataSourceFormProps {
  onSubmit: (values: DataSourceFormValues) => void
  defaultValues?: Partial<DataSourceFormValues>
  isEditing?: boolean
  dataSourceId?: string
}

export function DataSourceForm({
  onSubmit,
  defaultValues,
  isEditing = false,
  dataSourceId,
}: DataSourceFormProps) {
  const form = useForm<DataSourceFormValues>({
    resolver: zodResolver(dataSourceFormSchema),
    defaultValues: defaultValues || {
      name: '',
      source_type: 'sql',
      db_query: '',
      file_path: '',
      api_url: '',
    },
  })

  const { handleFormError } = useFormErrorHandler()
  const sourceType = form.watch('source_type')

  // API call for form submission
  const submitApi = useApiCall(
    async (values: DataSourceFormValues) => {
      if (isEditing && dataSourceId) {
        return await enhancedDataSourceApiService.updateDataSource(dataSourceId, values)
      } else {
        return await enhancedDataSourceApiService.createDataSource(values)
      }
    },
    {
      loadingMessage: isEditing ? 'Updating data source...' : 'Creating data source...',
      errorContext: isEditing ? 'update data source' : 'create data source',
      onSuccess: (result) => {
        onSubmit(result.data)
        form.reset()
      },
      onError: (error) => {
        // Handle validation errors from the API
        if (error.message.includes('validation')) {
          handleFormError(error.message)
        }
      }
    }
  )

  // Test connection API call
  const testConnectionApi = useApiCall(
    async (sourceId: string) => {
      return await enhancedDataSourceApiService.testDataSource(sourceId)
    },
    {
      loadingMessage: 'Testing connection...',
      errorContext: 'test data source connection',
      enableRetry: true,
      maxRetries: 2
    }
  )

  const handleSubmit = async (values: DataSourceFormValues) => {
    try {
      await submitApi.execute(values)
    } catch (error) {
      // Error is already handled by the API hook
      console.error('Form submission failed:', error)
    }
  }

  const handleTestConnection = async () => {
    if (!dataSourceId) return
    
    try {
      const result = await testConnectionApi.execute(dataSourceId)
      if (result.success) {
        // Show success message
      }
    } catch (error) {
      // Error is already handled by the API hook
      console.error('Connection test failed:', error)
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-8">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Data Source Name</FormLabel>
              <FormControl>
                <Input placeholder="e.g., Main Sales Database" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="source_type"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Source Type</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a source type" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="sql">SQL</SelectItem>
                  <SelectItem value="csv">CSV</SelectItem>
                  <SelectItem value="api">API</SelectItem>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        {sourceType === 'sql' && (
          <FormField
            control={form.control}
            name="db_query"
            render={({ field }) => (
              <FormItem>
                <FormLabel>SQL Query</FormLabel>
                <FormControl>
                  <Input placeholder="SELECT * FROM sales" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        )}

        {sourceType === 'csv' && (
          <FormField
            control={form.control}
            name="file_path"
            render={({ field }) => (
              <FormItem>
                <FormLabel>File Path</FormLabel>
                <FormControl>
                  <Input placeholder="/path/to/your/file.csv" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        )}

        {sourceType === 'api' && (
          <FormField
            control={form.control}
            name="api_url"
            render={({ field }) => (
              <FormItem>
                <FormLabel>API URL</FormLabel>
                <FormControl>
                  <Input
                    placeholder="https://api.example.com/data"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <LoadingButton
              type="submit"
              isLoading={submitApi.isLoading}
              loadingText={isEditing ? 'Updating...' : 'Creating...'}
              disabled={submitApi.isLoading}
            >
              {isEditing ? 'Update Data Source' : 'Create Data Source'}
            </LoadingButton>
            
            {isEditing && dataSourceId && (
              <LoadingButton
                type="button"
                variant="outline"
                isLoading={testConnectionApi.isLoading}
                loadingText="Testing..."
                onClick={handleTestConnection}
                disabled={testConnectionApi.isLoading}
              >
                Test Connection
              </LoadingButton>
            )}
          </div>
          
          {/* Show inline status for test connection */}
          {isEditing && (
            <LoadingSpinner />
          )}
        </div>
      </form>
    </Form>
  )
}
