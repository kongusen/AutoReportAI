'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'

import { Button } from '@/components/ui/button'
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
}

export function DataSourceForm({
  onSubmit,
  defaultValues,
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

  const sourceType = form.watch('source_type')

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
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

        <Button type="submit">Submit</Button>
      </form>
    </Form>
  )
}
