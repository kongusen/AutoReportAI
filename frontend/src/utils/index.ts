import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * 合并Tailwind CSS类名
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * 格式化日期
 */
export function formatDate(date: string | Date, options?: Intl.DateTimeFormatOptions): string {
  const d = typeof date === 'string' ? new Date(date) : date
  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }
  return d.toLocaleDateString('zh-CN', { ...defaultOptions, ...options })
}

/**
 * 格式化相对时间
 */
export function formatRelativeTime(date: string | Date): string {
  const now = new Date()
  const target = typeof date === 'string' ? new Date(date) : date
  const diffInMs = now.getTime() - target.getTime()
  const diffInSeconds = Math.floor(diffInMs / 1000)
  const diffInMinutes = Math.floor(diffInSeconds / 60)
  const diffInHours = Math.floor(diffInMinutes / 60)
  const diffInDays = Math.floor(diffInHours / 24)

  if (diffInSeconds < 60) {
    return '刚刚'
  } else if (diffInMinutes < 60) {
    return `${diffInMinutes}分钟前`
  } else if (diffInHours < 24) {
    return `${diffInHours}小时前`
  } else if (diffInDays < 30) {
    return `${diffInDays}天前`
  } else {
    return formatDate(target)
  }
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * 格式化数字（添加千分位分隔符）
 */
export function formatNumber(num: number): string {
  return num.toLocaleString('zh-CN')
}

/**
 * 生成随机ID
 */
export function generateId(): string {
  return Math.random().toString(36).substring(2) + Date.now().toString(36)
}

/**
 * 防抖函数
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null
  
  return (...args: Parameters<T>) => {
    if (timeout) {
      clearTimeout(timeout)
    }
    timeout = setTimeout(() => func(...args), wait)
  }
}

/**
 * 节流函数
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean
  
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args)
      inThrottle = true
      setTimeout(() => (inThrottle = false), limit)
    }
  }
}

/**
 * 深拷贝
 */
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') return obj
  if (obj instanceof Date) return new Date(obj.getTime()) as unknown as T
  if (obj instanceof Array) return obj.map(item => deepClone(item)) as unknown as T
  if (typeof obj === 'object') {
    const copy: any = {}
    Object.keys(obj as any).forEach(key => {
      copy[key] = deepClone((obj as any)[key])
    })
    return copy
  }
  return obj
}

/**
 * 判断是否为空值
 */
export function isEmpty(value: any): boolean {
  if (value == null) return true
  if (typeof value === 'string') return value.trim() === ''
  if (Array.isArray(value)) return value.length === 0
  if (typeof value === 'object') return Object.keys(value).length === 0
  return false
}

/**
 * 验证邮箱格式
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

/**
 * 验证Cron表达式格式（简单验证）
 */
export function isValidCron(cron: string): boolean {
  const parts = cron.trim().split(/\s+/)
  return parts.length === 5 || parts.length === 6
}

/**
 * 解析Cron表达式
 */
export function parseCron(cron: string) {
  const parts = cron.trim().split(/\s+/)
  if (parts.length < 5) {
    throw new Error('Invalid cron expression')
  }
  
  return {
    minute: parts[0],
    hour: parts[1],
    day: parts[2],
    month: parts[3],
    dayOfWeek: parts[4],
    year: parts[5] || '*'
  }
}

/**
 * 构建Cron表达式
 */
export function buildCron(parts: {
  minute: string
  hour: string
  day: string
  month: string
  dayOfWeek: string
  year?: string
}): string {
  const { minute, hour, day, month, dayOfWeek, year } = parts
  const cronParts = [minute, hour, day, month, dayOfWeek]
  if (year && year !== '*') {
    cronParts.push(year)
  }
  return cronParts.join(' ')
}

/**
 * 获取数据源类型的显示名称
 */
export function getDataSourceTypeName(type: string): string {
  const typeNames: Record<string, string> = {
    sql: 'SQL数据库',
    csv: 'CSV文件',
    api: 'API接口',
    push: '推送数据',
    doris: 'Apache Doris'
  }
  return typeNames[type] || type.toUpperCase()
}

/**
 * 获取任务状态的显示信息
 */
export function getTaskStatusInfo(status: string) {
  const statusInfo: Record<string, { label: string; color: string }> = {
    pending: { label: '等待中', color: 'gray' },
    running: { label: '执行中', color: 'blue' },
    completed: { label: '已完成', color: 'green' },
    failed: { label: '已失败', color: 'red' }
  }
  return statusInfo[status] || { label: status, color: 'gray' }
}

/**
 * 复制文本到剪贴板
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(text)
      return true
    } else {
      // fallback for older browsers
      const textArea = document.createElement('textarea')
      textArea.value = text
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      return true
    }
  } catch (err) {
    console.error('Failed to copy text: ', err)
    return false
  }
}

/**
 * 下载文件
 */
export function downloadFile(url: string, filename: string): void {
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}