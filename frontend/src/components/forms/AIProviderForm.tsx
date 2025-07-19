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

export const aiProviderFormSchema = z.object({
  name: z.string().min(1, 'Provider name is required'),
  api_key: z.string().min(1, 'API key is required'),
  api_base: z
    .string()
    .url('Please enter a valid URL')
    .optional()
    .or(z.literal('')),
  model_name: z.string().min(1, 'Model name is required'),
})

export type AIProviderFormValues = z.infer<typeof aiProviderFormSchema>

interface AIProviderFormProps {
  onSubmit: (values: AIProviderFormValues) => void
  defaultValues?: Partial<AIProviderFormValues>
}

export function AIProviderForm({
  onSubmit,
  defaultValues,
}: AIProviderFormProps) {
  const form = useForm<AIProviderFormValues>({
    resolver: zodResolver(aiProviderFormSchema),
    defaultValues: defaultValues || {
      name: '',
      api_key: '',
      api_base: '',
      model_name: '',
    },
  })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Provider Name</FormLabel>
              <FormControl>
                <Input placeholder="e.g., OpenAI" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="model_name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Model Name</FormLabel>
              <FormControl>
                <Input placeholder="e.g., gpt-4-turbo" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="api_key"
          render={({ field }) => (
            <FormItem>
              <FormLabel>API Key</FormLabel>
              <FormControl>
                <Input
                  type="password"
                  placeholder="••••••••••••••••"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="api_base"
          render={({ field }) => (
            <FormItem>
              <FormLabel>API Base URL (Optional)</FormLabel>
              <FormControl>
                <Input
                  placeholder="e.g., https://api.openai.com/v1"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit">Submit</Button>
      </form>
    </Form>
  )
}
