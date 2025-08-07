import { z } from 'zod'

// 用户设置表单验证
export const userSettingsSchema = z.object({
  username: z.string().min(3, '用户名至少3个字符').max(50, '用户名最多50个字符'),
  email: z.string().email('请输入有效的邮箱地址'),
  full_name: z.string().max(100, '姓名最多100个字符').optional(),
  bio: z.string().max(500, '个人简介最多500个字符').optional(),
})

// 通知设置表单验证
export const notificationSettingsSchema = z.object({
  email_notifications: z.boolean(),
  push_notifications: z.boolean(),
  report_completion: z.boolean(),
  task_failure: z.boolean(),
})

// 安全设置表单验证
export const securitySettingsSchema = z.object({
  current_password: z.string().min(1, '请输入当前密码'),
  new_password: z.string().min(6, '新密码至少6个字符').optional(),
  confirm_password: z.string().min(6, '请确认新密码').optional(),
}).refine(
  (data) => {
    if (data.new_password && !data.confirm_password) {
      return false
    }
    if (data.confirm_password && !data.new_password) {
      return false
    }
    if (data.new_password && data.confirm_password) {
      return data.new_password === data.confirm_password
    }
    return true
  },
  {
    message: '两次输入的新密码不一致',
    path: ['confirm_password'],
  }
)