import { z } from 'zod'

// 模板表单验证
export const templateSchema = z.object({
  name: z.string().min(1, '模板名称不能为空').max(100, '模板名称最多100个字符'),
  description: z.string().max(500, '模板描述最多500个字符').optional(),
  content: z.string().min(1, '模板内容不能为空'),
  template_type: z.string().min(1, '请选择模板类型'),
})