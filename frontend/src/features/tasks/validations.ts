import { z } from 'zod'

// 任务表单验证
export const taskSchema = z.object({
  name: z.string().min(1, '任务名称不能为空').max(100, '任务名称最多100个字符'),
  description: z.string().max(500, '任务描述最多500个字符').optional(),
  template_id: z.string().min(1, '请选择模板'),
  data_source_id: z.string().min(1, '请选择数据源'),
  schedule: z.string().max(100, '调度表达式最多100个字符').optional(),
  recipients: z.array(z.string().email('请输入有效的邮箱地址')).optional(),
  is_active: z.boolean(),
})

// Cron表达式验证
export const cronSchema = z.string().refine(
  (cron) => {
    const parts = cron.trim().split(/\s+/)
    return parts.length === 5 || parts.length === 6
  },
  {
    message: '请输入有效的Cron表达式（5或6个字段）',
  }
)