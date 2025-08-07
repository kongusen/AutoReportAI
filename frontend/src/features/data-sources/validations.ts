import { z } from 'zod'
import { DataSourceType } from '@/types'

// 数据源表单验证
export const dataSourceSchema = z.object({
  name: z.string().min(1, '数据源名称不能为空').max(100, '数据源名称最多100个字符'),
  slug: z.string().optional(),
  display_name: z.string().optional(),
  source_type: z.enum(['sql', 'csv', 'api', 'push', 'doris']),
  is_active: z.boolean().default(true),
  
  // SQL数据库配置
  connection_string: z.string().optional(),
  sql_query_type: z.enum(['single_table', 'multi_table', 'custom_view']).default('single_table'),
  base_query: z.string().optional(),
  join_config: z.record(z.any()).optional(),
  column_mapping: z.record(z.any()).optional(),
  where_conditions: z.record(z.any()).optional(),
  wide_table_name: z.string().optional(),
  wide_table_schema: z.record(z.any()).optional(),
  
  // API数据源配置
  api_url: z.string().optional(),
  api_method: z.enum(['GET', 'POST', 'PUT', 'DELETE']).default('GET'),
  api_headers: z.string().optional(), // 前端作为JSON字符串处理
  api_body: z.string().optional(), // 前端作为JSON字符串处理
  
  // 推送数据源配置
  push_endpoint: z.string().optional(),
  push_auth_config: z.record(z.any()).optional(),
  
  // Doris数据库配置
  doris_fe_hosts: z.string().optional(), // 前端作为逗号分隔字符串处理
  doris_be_hosts: z.array(z.string()).optional(),
  doris_http_port: z.number().default(8030),
  doris_query_port: z.number().default(9030),
  doris_database: z.string().optional(),
  doris_username: z.string().optional(),
  doris_password: z.string().optional(),
}).superRefine((data, ctx) => {
  // 根据数据源类型验证必填字段
  switch (data.source_type) {
    case 'sql':
      if (!data.connection_string) {
        ctx.addIssue({
          path: ['connection_string'],
          message: 'SQL数据库连接字符串不能为空',
          code: z.ZodIssueCode.custom,
        })
      }
      break
    case 'api':
      if (!data.api_url) {
        ctx.addIssue({
          path: ['api_url'],
          message: 'API URL不能为空',
          code: z.ZodIssueCode.custom,
        })
      }
      break
    case 'push':
      if (!data.push_endpoint) {
        ctx.addIssue({
          path: ['push_endpoint'],
          message: '推送端点不能为空',
          code: z.ZodIssueCode.custom,
        })
      }
      break
    case 'doris':
      if (!data.doris_fe_hosts || data.doris_fe_hosts.trim().length === 0) {
        ctx.addIssue({
          path: ['doris_fe_hosts'],
          message: 'Doris FE主机不能为空',
          code: z.ZodIssueCode.custom,
        })
      }
      if (!data.doris_username) {
        ctx.addIssue({
          path: ['doris_username'],
          message: 'Doris用户名不能为空',
          code: z.ZodIssueCode.custom,
        })
      }
      break
  }
})