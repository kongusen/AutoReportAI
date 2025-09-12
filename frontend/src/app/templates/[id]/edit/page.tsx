'use client'

import { useEffect, useState, ChangeEvent } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Select } from '@/components/ui/Select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { TemplateEditor } from '@/components/forms/TemplateEditor'
import { useTemplateStore } from '@/features/templates/templateStore'
import { TemplateUpdate } from '@/types'

// Updated Zod schema
const templateSchema = z.object({
  name: z.string().min(1, '模板名称不能为空').max(100, '模板名称不能超过100个字符'),
  description: z.string().max(500, '描述不能超过500个字符').optional(),
  template_type: z.string().min(1, '请选择模板类型'),
  content: z.string().optional(), // Made optional
  variables: z.record(z.string()).optional(),
  file: z.any().optional(), // For file upload
}).superRefine((data, ctx) => {
  if (data.template_type === 'docx') {
    // For docx templates, content is not required
  } else {
    if (!data.content || data.content.trim() === '') {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: '模板内容不能为空',
        path: ['content'],
      });
    }
  }
});

type FormData = z.infer<typeof templateSchema>

// Updated template type options
const templateTypeOptions = [
  { label: 'DOCX 模板', value: 'docx' },
  { label: '报告模板 (文本)', value: 'report' },
  { label: '邮件模板', value: 'email' },
  { label: '仪表板模板', value: 'dashboard' },
]

interface EditTemplatePageProps {
  params: {
    id: string
  }
}

export default function EditTemplatePage({ params }: EditTemplatePageProps) {
  const router = useRouter()
  const { currentTemplate, loading, getTemplate, updateTemplate, uploadTemplateFile } = useTemplateStore()
  const [templateVariables, setTemplateVariables] = useState<Record<string, any>>({})
  const [hasChanges, setHasChanges] = useState(false)
  const [templateFile, setTemplateFile] = useState<File | null>(null); // State for the uploaded file

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
    reset,
    clearErrors,
  } = useForm<FormData>({
    resolver: zodResolver(templateSchema),
  })

  const watchedContent = watch('content') || ''
  const watchedTemplateType = watch('template_type') || 'docx'

  // 加载模板数据
  useEffect(() => {
    const loadTemplate = async () => {
      try {
        await getTemplate(params.id)
      } catch (error) {
        router.push('/templates')
      }
    }
    loadTemplate()
  }, [params.id, getTemplate, router])

  // 填充表单数据
  useEffect(() => {
    if (currentTemplate) {
      reset({
        name: currentTemplate.name,
        description: currentTemplate.description || '',
        template_type: currentTemplate.template_type,
        content: currentTemplate.content,
        variables: currentTemplate.variables || {},
      })
      if (currentTemplate.template_type !== 'docx') {
        setTemplateVariables(currentTemplate.variables || {})
      }
      setHasChanges(false)
    }
  }, [currentTemplate, reset])

  // 监听表单变化
  useEffect(() => {
    if (currentTemplate) {
      const formData = watch()
      const hasFormChanges = (
        formData.name !== currentTemplate.name ||
        formData.description !== currentTemplate.description ||
        formData.template_type !== currentTemplate.template_type ||
        formData.content !== currentTemplate.content ||
        JSON.stringify(templateVariables) !== JSON.stringify(currentTemplate.variables || {})
      )
      setHasChanges(hasFormChanges)
    }
  }, [watch(), templateVariables, currentTemplate])

  const onSubmit = async (data: FormData) => {
    if (!currentTemplate) return

    try {
      // Handle file upload for docx templates
      if (data.template_type === 'docx' && templateFile) {
        await uploadTemplateFile(currentTemplate.id, templateFile);
      } else {
        // Handle regular template update
        await updateTemplate(currentTemplate.id, {
          name: data.name,
          description: data.description,
          template_type: data.template_type,
          content: data.content || '',
          variables: templateVariables,
        })
      }
      router.push(`/templates/${currentTemplate.id}`)
    } catch (error) {
      // 错误处理在store中已处理
    }
  }

  const handleContentChange = (content: string) => {
    setValue('content', content)
    clearErrors('content')
  }

  const handleVariablesChange = (variables: Record<string, any>) => {
    setTemplateVariables(variables)
    setValue('variables', variables)
  }

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setTemplateFile(file);
    setValue('file', file, { shouldValidate: true });
    if(file){
        clearErrors('file');
    }
  };

  const handleCancel = () => {
    if (hasChanges) {
      if (confirm('您有未保存的更改，确定要离开吗？')) {
        router.back()
      }
    } else {
      router.back()
    }
  }

  if (loading || !currentTemplate) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-gray-200 rounded w-48"></div>
        <div className="space-y-4">
          <div className="bg-white p-6 rounded-lg shadow space-y-4">
            <div className="h-6 bg-gray-200 rounded w-32"></div>
            <div className="grid grid-cols-2 gap-4">
              <div className="h-10 bg-gray-200 rounded"></div>
              <div className="h-10 bg-gray-200 rounded"></div>
            </div>
            <div className="h-20 bg-gray-200 rounded"></div>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="h-96 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <PageHeader
        title="编辑模板"
        description={`编辑模板: ${currentTemplate.name}`}
        breadcrumbs={[
          { label: '模板管理', href: '/templates' },
          { label: currentTemplate.name, href: `/templates/${currentTemplate.id}` },
          { label: '编辑' },
        ]}
        actions={
          hasChanges ? (
            <div className="flex items-center space-x-2">
              <span className="text-sm text-orange-600">有未保存的更改</span>
              <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse"></div>
            </div>
          ) : undefined
        }
      />

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* 基本信息 */}
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  模板名称 *
                </label>
                <Input
                  placeholder="输入模板名称"
                  error={!!errors.name}
                  {...register('name')}
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  模板类型 *
                </label>
                <Select
                  options={templateTypeOptions}
                  value={watchedTemplateType}
                  onChange={(value) => {
                    setValue('template_type', value as string, { shouldValidate: true });
                    // Clear conditional fields when type changes
                    if (value === 'docx') {
                      setValue('content', '');
                    } else {
                      setValue('file', null);
                      setTemplateFile(null);
                    }
                    clearErrors(['content', 'file']);
                  }}
                />
                {errors.template_type && (
                  <p className="mt-1 text-sm text-red-600">{errors.template_type.message}</p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                模板描述
              </label>
              <Textarea
                placeholder="输入模板描述（可选）"
                {...register('description')}
              />
              {errors.description && (
                <p className="mt-1 text-sm text-red-600">{errors.description.message}</p>
              )}
            </div>
            
            {/* 文件信息显示 (仅对DOCX模板) */}
            {currentTemplate.template_type === 'docx' && false && (
              <div className="bg-blue-50 p-3 rounded-md">
                <p className="text-sm text-blue-800">
                  <span className="font-medium">当前文件:</span> {}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 模板编辑器 或 文件上传 */}
        <Card>
          <CardHeader>
            <CardTitle>模板内容</CardTitle>
          </CardHeader>
          <CardContent>
            {watchedTemplateType === 'docx' ? (
              <div className="space-y-2">
                <label htmlFor="template-file" className="block text-sm font-medium text-gray-700">
                  上传模板文件 (.docx)
                </label>
                <Input
                  id="template-file"
                  type="file"
                  accept=".docx"
                  onChange={handleFileChange}
                />
                 {templateFile && (
                  <p className="mt-2 text-sm text-gray-600">
                    已选择文件: {templateFile.name} ({(templateFile.size / 1024).toFixed(2)} KB)
                  </p>
                )}
                {errors.file && (
                  <p className="mt-1 text-sm text-red-600">{(errors.file as any).message}</p>
                )}
                <p className="text-sm text-gray-500 mt-2">
                  注意：上传新文件将替换当前模板文件
                </p>
              </div>
            ) : (
              <>
                <TemplateEditor
                  content={watchedContent}
                  onChange={handleContentChange}
                  variables={templateVariables}
                  onVariablesChange={handleVariablesChange}
                  height={500}
                />
                {errors.content && (
                  <p className="mt-2 text-sm text-red-600">{errors.content.message}</p>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* 操作按钮 */}
        <div className="flex justify-between">
          <div className="text-sm text-gray-500">
            {hasChanges ? '您有未保存的更改' : '所有更改已保存'}
          </div>
          <div className="flex space-x-4">
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
            >
              取消
            </Button>
            <Button 
              type="submit" 
              loading={loading}
              disabled={!hasChanges}
            >
              保存更改
            </Button>
          </div>
        </div>
      </form>
    </>
  )
}