'use client'

import { zodResolver } from '@hookform/resolvers/zod'
import { useFieldArray, useForm } from 'react-hook-form'
import { z } from 'zod'
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
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { useEffect, useState } from 'react'
import { TrashIcon } from '@radix-ui/react-icons'

// SECTION: Schemas and Types

// Zod schemas for validation
const filterParamsSchema = z.object({
  column: z.string().min(1, 'Column name is required'),
  operator: z.enum([
    '==',
    '!=',
    '>',
    '<',
    '>=',
    '<=',
    'in',
    'not in',
    'contains',
  ]),
  value: z.string().min(1, 'Value is required'),
})

const selectParamsSchema = z.object({
  columns: z.string().min(1, 'Specify at least one column (comma-separated)'),
})

const renameParamsSchema = z.object({
  rename_map: z.string().min(1, 'Provide mappings as old:new,old2:new2'),
})

const changeTypeParamsSchema = z.object({
  column: z.string().min(1, 'Column name is required'),
  new_type: z.enum(['str', 'int', 'float', 'datetime']),
})

// Operation schema using discriminated union
const operationSchema = z.discriminatedUnion('operation', [
  z.object({ operation: z.literal('filter_rows'), params: filterParamsSchema }),
  z.object({
    operation: z.literal('select_columns'),
    params: selectParamsSchema,
  }),
  z.object({
    operation: z.literal('rename_columns'),
    params: renameParamsSchema,
  }),
  z.object({
    operation: z.literal('change_column_type'),
    params: changeTypeParamsSchema,
  }),
])

// Main form schema
const formSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters.'),
  description: z.string().optional(),
  source_data_source_id: z.string().uuid('Please select a valid data source.'),
  destination_table_name: z
    .string()
    .min(1, 'Destination table name is required.'),
  source_query: z.string().min(10, 'Source query seems too short.'),
  transformation_config: z
    .object({
      operations: z.array(operationSchema).optional(),
    })
    .optional(),
  schedule: z.string().optional(),
  enabled: z.boolean().default(false),
})

// Use Zod inferred type
type ETLJobFormData = z.infer<typeof formSchema>

// SECTION: Component

const defaultValues: Partial<ETLJobFormData> = {
  name: '',
  description: '',
  source_data_source_id: '',
  destination_table_name: '',
  source_query: 'SELECT * FROM my_table;',
  transformation_config: { operations: [] },
  schedule: '0 0 * * *',
  enabled: false,
}

type DataSource = {
  id: string
  name: string
}

interface ETLJobFormProps {
  initialData?: Partial<ETLJobFormData>
  onSubmit: (values: ETLJobFormData) => void
  onCancel: () => void
}

const operationTypes = [
  { value: 'filter_rows', label: 'Filter Rows' },
  { value: 'select_columns', label: 'Select Columns' },
  { value: 'rename_columns', label: 'Rename Columns' },
  { value: 'change_column_type', label: 'Change Column Type' },
] as const

export function ETLJobForm({
  initialData,
  onSubmit,
  onCancel,
}: ETLJobFormProps) {
  const [dataSources, setDataSources] = useState<DataSource[]>([])

  useEffect(() => {
    async function fetchDataSources() {
      try {
        const response = await fetch('/api/v1/data-sources')
        if (!response.ok) {
          throw new Error('Failed to fetch data sources')
        }
        const data = await response.json()
        setDataSources(data)
      } catch (error) {
        console.error('Failed to fetch data sources:', error)
      }
    }
    fetchDataSources()
  }, [])

  // Type compatibility issue between @hookform/resolvers/zod v5.1.1 and react-hook-form v7.60.0
  // The zodResolver generates a slightly different type signature than what useForm expects
  // This is a known issue with these library versions and the functionality works correctly at runtime
  const form = useForm<ETLJobFormData>({
    // @ts-expect-error - Complex type compatibility issue between library versions
    resolver: zodResolver(formSchema),
    defaultValues: { ...defaultValues, ...initialData },
  })

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'transformation_config.operations',
  })

  const watchOperations = form.watch('transformation_config.operations')

  const handleAddOperation = () => {
    const newOperation = {
      operation: 'filter_rows' as const,
      params: { column: '', operator: '==' as const, value: '' },
    }
    append(newOperation)
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        {/* Basic fields: name, description, source_data_source_id, destination_table_name */}
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Job Name</FormLabel>
              <FormControl>
                <Input placeholder="e.g., Daily Sales Aggregation" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Input
                  placeholder="A brief description of what this job does"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="source_data_source_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Source Data</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a data source" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {dataSources.map((ds) => (
                    <SelectItem key={ds.id} value={ds.id}>
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
          name="destination_table_name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Destination Table Name</FormLabel>
              <FormControl>
                <Input placeholder="e.g., fact_daily_sales" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Source Query Field */}
        <FormField
          control={form.control}
          name="source_query"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Source Query</FormLabel>
              <FormControl>
                <Textarea {...field} rows={5} className="font-mono" />
              </FormControl>
              <FormDescription>
                The SQL query to execute on the source database to fetch the
                initial data.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Dynamic Transformations Section */}
        <div>
          <h3 className="text-lg font-medium mb-4">Transformations</h3>
          <div className="space-y-4">
            {fields.map((field, index) => (
              <div
                key={field.id}
                className="p-4 border rounded-md space-y-4 relative"
              >
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute top-2 right-2"
                  onClick={() => remove(index)}
                >
                  <TrashIcon className="h-4 w-4" />
                </Button>
                <FormField
                  control={form.control}
                  name={`transformation_config.operations.${index}.operation`}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Operation Type</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        defaultValue={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select an operation" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {operationTypes.map((op) => (
                            <SelectItem key={op.value} value={op.value}>
                              {op.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {watchOperations?.[index]?.operation === 'filter_rows' && (
                  <>
                    <FormField
                      control={form.control}
                      name={`transformation_config.operations.${index}.params.column`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Column</FormLabel>
                          <FormControl>
                            <Input placeholder="e.g., country" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name={`transformation_config.operations.${index}.params.operator`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Operator</FormLabel>
                          <Select
                            onValueChange={field.onChange}
                            defaultValue={field.value}
                          >
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="==">Equals (==)</SelectItem>
                              <SelectItem value="!=">
                                Not Equals (!=)
                              </SelectItem>
                              <SelectItem value=">">
                                Greater Than (&gt;)
                              </SelectItem>
                              <SelectItem value="<">
                                Less Than (&lt;)
                              </SelectItem>
                              <SelectItem value="contains">Contains</SelectItem>
                              <SelectItem value="in">In</SelectItem>
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name={`transformation_config.operations.${index}.params.value`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Value</FormLabel>
                          <FormControl>
                            <Input
                              placeholder="e.g., USA or ['USA', 'Canada']"
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </>
                )}
                {watchOperations?.[index]?.operation === 'select_columns' && (
                  <FormField
                    control={form.control}
                    name={`transformation_config.operations.${index}.params.columns`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Columns</FormLabel>
                        <FormControl>
                          <Input placeholder="e.g., id,name,email" {...field} />
                        </FormControl>
                        <FormDescription>
                          Comma-separated list of columns to keep.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}
                {watchOperations?.[index]?.operation === 'rename_columns' && (
                  <FormField
                    control={form.control}
                    name={`transformation_config.operations.${index}.params.rename_map`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Rename Map</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="e.g., old_name:new_name,id:customer_id"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Comma-separated old:new pairs.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}
                {watchOperations?.[index]?.operation ===
                  'change_column_type' && (
                  <>
                    <FormField
                      control={form.control}
                      name={`transformation_config.operations.${index}.params.column`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Column</FormLabel>
                          <FormControl>
                            <Input placeholder="e.g., amount" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name={`transformation_config.operations.${index}.params.new_type`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>New Type</FormLabel>
                          <Select
                            onValueChange={field.onChange}
                            defaultValue={field.value}
                          >
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="str">Text (string)</SelectItem>
                              <SelectItem value="int">Integer</SelectItem>
                              <SelectItem value="float">
                                Decimal (float)
                              </SelectItem>
                              <SelectItem value="datetime">
                                Date/Time
                              </SelectItem>
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </>
                )}
              </div>
            ))}
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="mt-4"
            onClick={handleAddOperation}
          >
            Add Transformation
          </Button>
        </div>

        {/* Schedule and Enabled fields */}
        <FormField
          control={form.control}
          name="schedule"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Schedule (Cron Expression)</FormLabel>
              <FormControl>
                <Input placeholder="e.g., 0 2 * * *" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="enabled"
          render={({ field }) => (
            <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
              <div className="space-y-0.5">
                <FormLabel>Enable Job</FormLabel>
              </div>
              <FormControl>
                <Switch
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              </FormControl>
            </FormItem>
          )}
        />

        {/* Action Buttons */}
        <div className="flex justify-end space-x-4">
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit">Save</Button>
        </div>
      </form>
    </Form>
  )
}
