import { z } from 'zod'

// 仪表板筛选验证
export const dashboardFilterSchema = z.object({
  date_range: z.enum(['today', 'week', 'month', 'quarter', 'year']).optional(),
  data_source_id: z.string().optional(),
  template_id: z.string().optional(),
})