'use client'

import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import api from '@/lib/api'
import { AxiosResponse } from 'axios'

import { Button } from '@/components/ui/button'
import {
  Form,
  FormControl,
  FormDescription,
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
import { ScheduleBuilder } from '@/components/ScheduleBuilder'

// Define types for API data
interface Template {
  id: number
  name: string
}

interface DataSource {
  id: number
  name: string
}

// This is a generic type for our paginated API responses
interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

// Schema based on backend model (TaskCreate)
export const taskFormSchema = z.object({
  name: z.string().min(1, 'Task name is required.'),
  template_id: z.string().min(1, 'Template is required.'),
  data_source_id: z.string().min(1, 'Data source is required.'),
  schedule: z.string().optional(),
  recipients: z.string().optional(),
  is_active: z.boolean(),
})

export type TaskFormValues = z.infer<typeof taskFormSchema>

export type ProcessedTaskFormValues = Omit<
  TaskFormValues,
  'template_id' | 'data_source_id'
> & {
  template_id: number
  data_source_id: number
}

type OnSubmitCallback = (values: ProcessedTaskFormValues) => void

interface TaskFormProps {
  onSubmit: OnSubmitCallback
  defaultValues?: Partial<TaskFormValues>
}

export function TaskForm({ onSubmit, defaultValues }: TaskFormProps) {
  const [templates, setTemplates] = useState<Template[]>([])
  const [dataSources, setDataSources] = useState<DataSource[]>([])

  const form = useForm<TaskFormValues>({
    resolver: zodResolver(taskFormSchema),
    // This robustly constructs the default values, preventing type errors.
    values: {
      name: defaultValues?.name ?? '',
      template_id: defaultValues?.template_id ?? '',
      data_source_id: defaultValues?.data_source_id ?? '',
      schedule: defaultValues?.schedule ?? '',
      recipients: defaultValues?.recipients ?? '',
      is_active: defaultValues?.is_active ?? true,
    },
  })

  useEffect(() => {
    api
      .get('/templates')
      .then((response: AxiosResponse<PaginatedResponse<Template>>) => {
        setTemplates(response.data.items || [])
      })
    api
      .get('/data-sources')
      .then((response: AxiosResponse<PaginatedResponse<DataSource>>) => {
        setDataSources(response.data.items || [])
      })
  }, [])

  const handleFormSubmit = (values: TaskFormValues) => {
    const convertedValues: ProcessedTaskFormValues = {
      ...values,
      template_id: parseInt(values.template_id, 10),
      data_source_id: parseInt(values.data_source_id, 10),
    }
    onSubmit(convertedValues)
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(handleFormSubmit)}
        className="space-y-6"
      >
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Task Name</FormLabel>
              <FormControl>
                <Input placeholder="e.g., Monthly Sales Report" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="template_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Template</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a template" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {templates.map((t) => (
                    <SelectItem key={t.id} value={String(t.id)}>
                      {t.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="data_source_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Data Source</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a data source" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {dataSources.map((ds) => (
                    <SelectItem key={ds.id} value={String(ds.id)}>
                      {ds.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="schedule"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Schedule</FormLabel>
              <FormControl>
                <ScheduleBuilder
                  onChange={field.onChange}
                  value={field.value}
                />
              </FormControl>
              <FormDescription>
                Select the frequency and time for the task to run.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="recipients"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Recipients</FormLabel>
              <FormControl>
                <Input
                  placeholder="email1@example.com,email2@example.com"
                  {...field}
                  value={field.value ?? ''}
                />
              </FormControl>
              <FormDescription>
                Comma-separated list of email addresses.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="is_active"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Task Status</FormLabel>
              <Select
                onValueChange={(value) => field.onChange(value === 'true')}
                defaultValue={String(field.value)}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="true">Active</SelectItem>
                  <SelectItem value="false">Inactive</SelectItem>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" className="w-full">
          Submit
        </Button>
      </form>
    </Form>
  )
}
