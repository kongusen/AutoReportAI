import { z } from 'zod'

// 报告表单验证
export const reportSchema = z.object({
  name: z.string().min(1, '报告名称不能为空').max(100, '报告名称最多100个字符'),
  task_id: z.string().min(1, '请选择任务'),
})

// 报告筛选验证
export const reportFilterSchema = z.object({
  task_id: z.string().optional(),
  status: z.enum(['generating', 'completed', 'failed']).optional(),
  start_date: z.string().optional(),
  end_date: z.string().optional(),
})