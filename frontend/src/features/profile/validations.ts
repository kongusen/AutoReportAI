import { z } from 'zod'

// 用户资料表单验证
export const profileSchema = z.object({
  full_name: z.string().max(100, '姓名最多100个字符').optional(),
  bio: z.string().max(500, '个人简介最多500个字符').optional(),
  avatar_url: z.string().url('请输入有效的URL').optional(),
})

// 用户资料更新验证
export const profileUpdateSchema = z.object({
  full_name: z.string().max(100, '姓名最多100个字符').optional(),
  bio: z.string().max(500, '个人简介最多500个字符').optional(),
})