'use client'

import { useEffect, useState, ChangeEvent, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { AppLayout } from '@/components/layout/AppLayout'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Select } from '@/components/ui/Select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { TemplateEditor } from '@/components/forms/TemplateEditor'
import { useTemplateStore } from '@/features/templates/templateStore'
import { TemplateCreate } from '@/types'

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
    if (!data.file) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'DOCX模板必须上传一个文件',
        path: ['file'],
      });
    }
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

const templatePresets = {
  report: {
    name: '销售报告模板',
    content: `# {{ title }}

## 报告摘要
本报告生成于 {{ date }}，涵盖了 {{ period }} 的销售数据分析。

## 主要指标
- **总销售额**: {{ total_sales }}
- **订单数量**: {{ order_count }}
- **平均订单值**: {{ avg_order_value }}
- **客户数量**: {{ customer_count }}

## 详细分析

### 销售趋势
{{ sales_trend }}

### 产品表现
{{ product_performance }}

### 客户分析
{{ customer_analysis }}

## 总结
{{ summary }}

---
报告生成时间: {{ timestamp }}
生成人: {{ user }}`,
    variables: {
      title: '月度销售报告',
      date: '2024-01-01',
      period: '2024年1月',
      total_sales: '¥1,000,000',
      order_count: '500',
      avg_order_value: '¥2,000',
      customer_count: '300',
      sales_trend: '销售额较上月增长15%',
      product_performance: 'A产品表现最佳，占总销售额40%',
      customer_analysis: '新客户占比30%，复购率70%',
      summary: '整体表现良好，建议继续推广A产品',
      timestamp: new Date().toISOString(),
      user: '系统管理员'
    }
  },
  email: {
    name: '邮件通知模板',
    content: `亲爱的 {{ recipient_name }}，

您好！

我们已为您生成了 {{ report_type }} 报告。

**报告详情：**
- 报告名称：{{ report_name }}
- 生成时间：{{ generated_at }}
- 数据时间范围：{{ date_range }}

**主要发现：**
{{ key_findings }}

您可以通过以下链接下载完整报告：
{{ download_link }}

如有任何问题，请随时联系我们。

此致
敬礼！

{{ company_name }}
{{ contact_info }}`,
    variables: {
      recipient_name: '用户姓名',
      report_type: '销售分析',
      report_name: '月度销售报告',
      generated_at: new Date().toISOString(),
      date_range: '2024年1月',
      key_findings: '销售额增长15%，新客户增加30%',
      download_link: 'https://example.com/download/report',
      company_name: 'AutoReportAI',
      contact_info: 'support@autoreportai.com'
    }
  },
  dashboard: {
    name: '仪表板模板',
    content: `# {{ dashboard_title }}

<div class="dashboard-container">

## KPI 概览
<div class="kpi-grid">
  <div class="kpi-card">
    <h3>{{ kpi1_title }}</h3>
    <div class="kpi-value">{{ kpi1_value }}</div>
    <div class="kpi-change">{{ kpi1_change }}</div>
  </div>
  
  <div class="kpi-card">
    <h3>{{ kpi2_title }}</h3>
    <div class="kpi-value">{{ kpi2_value }}</div>
    <div class="kpi-change">{{ kpi2_change }}</div>
  </div>
  
  <div class="kpi-card">
    <h3>{{ kpi3_title }}</h3>
    <div class="kpi-value">{{ kpi3_value }}</div>
    <div class="kpi-change">{{ kpi3_change }}</div>
  </div>
  
  <div class="kpi-card">
    <h3>{{ kpi4_title }}</h3>
    <div class="kpi-value">{{ kpi4_value }}</div>
    <div class="kpi-change">{{ kpi4_change }}</div>
  </div>
</div>

## 趋势图表
{{ trend_charts }}

## 数据表格
{{ data_tables }}

</div>

<style>
.dashboard-container { max-width: 1200px; margin: 0 auto; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
.kpi-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }
.kpi-value { font-size: 2em; font-weight: bold; color: #2563eb; }
.kpi-change { font-size: 0.9em; color: #059669; }
</style>`,
    variables: {
      dashboard_title: '销售仪表板',
      kpi1_title: '总销售额',
      kpi1_value: '¥1,000,000',
      kpi1_change: '+15%',
      kpi2_title: '订单数',
      kpi2_value: '500',
      kpi2_change: '+8%',
      kpi3_title: '客户数',
      kpi3_value: '300',
      kpi3_change: '+12%',
      kpi4_title: '转化率',
      kpi4_value: '3.5%',
      kpi4_change: '+2%',
      trend_charts: '[图表占位符]',
      data_tables: '[数据表格占位符]'
    }
  },
}

function CreateTemplatePageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const duplicateId = searchParams.get('duplicate')
  const { createTemplate, getTemplate, loading } = useTemplateStore()
  const [templateVariables, setTemplateVariables] = useState<Record<string, any>>({})
  const [templateFile, setTemplateFile] = useState<File | null>(null); // State for the uploaded file

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
    getValues,
    reset, // use reset
    clearErrors, // use clearErrors
  } = useForm<FormData>({
    resolver: zodResolver(templateSchema),
    defaultValues: {
      template_type: 'docx', // Default to docx
      content: '',
      variables: {},
    },
  })

  const watchedContent = watch('content') || ''
  const watchedTemplateType = watch('template_type')

  // 如果是复制模板，加载原模板数据
  useEffect(() => {
    if (duplicateId) {
      getTemplate(duplicateId).then((template) => {
        reset({
          name: `${template.name} - 副本`,
          description: template.description,
          template_type: template.template_type,
          content: template.content,
        });
        if (template.template_type !== 'docx') {
          setTemplateVariables(template.variables || {})
        }
      }).catch(() => {
        // 错误处理在store中已处理
      })
    }
  }, [duplicateId, getTemplate, reset])

  const onSubmit = async (data: FormData) => {
    try {
      const submissionData: TemplateCreate = {
        name: data.name,
        description: data.description,
        template_type: data.template_type,
        content: data.template_type === 'docx' ? '' : data.content || '',
        variables: data.template_type === 'docx' ? {} : templateVariables,
        file: data.file,
      }
      
      await createTemplate(submissionData)
      router.push('/templates')
    } catch (error) {
      // 错误处理在store中已处理
    }
  }

  const handleUsePreset = (presetKey: keyof typeof templatePresets) => {
    const preset = templatePresets[presetKey]
    setValue('name', preset.name)
    setValue('content', preset.content)
    setTemplateVariables(preset.variables)
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

  return (
    <AppLayout>
      <PageHeader
        title={duplicateId ? '复制模板' : '创建模板'}
        description={duplicateId ? '基于现有模板创建副本' : '创建新的报告模板'}
        breadcrumbs={[
          { label: '模板管理', href: '/templates' },
          { label: duplicateId ? '复制模板' : '创建模板' },
        ]}
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

            {/* 预设模板 */}
            {!duplicateId && watchedTemplateType !== 'docx' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  使用预设模板
                </label>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(templatePresets).map(([key, preset]) => (
                    <Button
                      key={key}
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => handleUsePreset(key as keyof typeof templatePresets)}
                    >
                      {preset.name}
                    </Button>
                  ))}
                </div>
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
                  上传模板文件 (.docx) *
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
        <div className="flex justify-end space-x-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.back()}
          >
            取消
          </Button>
          <Button type="submit" loading={loading}>
            {duplicateId ? '复制模板' : '创建模板'}
          </Button>
        </div>
      </form>
    </AppLayout>
  )
}

export default function CreateTemplatePage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <CreateTemplatePageContent />
    </Suspense>
  )
}
