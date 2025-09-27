/**
 * 占位符数据处理工具
 * 统一处理后端API返回的占位符数据格式
 */

export interface NormalizedPlaceholder {
  id?: string  // 数据库ID，用于编辑操作
  name: string
  text: string
  start: number
  end: number
  type?: string
  description?: string
  // SQL编辑相关字段
  execution_order?: number
  cache_ttl_hours?: number
  is_active?: boolean
  generated_sql?: string
  placeholder_type?: string
}

/**
 * 规范化占位符数据
 * 将后端API返回的不同格式统一为标准格式
 */
export function normalizePlaceholder(placeholder: any, index: number = 0): NormalizedPlaceholder {
  return {
    id: placeholder.id,
    name: placeholder.name || placeholder.placeholder_name || placeholder.description || `占位符 ${index + 1}`,
    text: placeholder.text || placeholder.placeholder_text || '',
    start: placeholder.start || placeholder.start_index || 0,
    end: placeholder.end || placeholder.end_index || 0,
    type: placeholder.type || inferPlaceholderType(placeholder.name || placeholder.description || ''),
    description: placeholder.description || placeholder.name,
    // SQL编辑相关字段
    execution_order: placeholder.execution_order || 0,
    cache_ttl_hours: placeholder.cache_ttl_hours || 24,
    is_active: placeholder.is_active !== undefined ? placeholder.is_active : true,
    generated_sql: placeholder.generated_sql || placeholder.suggested_sql,
    placeholder_type: placeholder.placeholder_type || placeholder.type
  }
}

/**
 * 批量规范化占位符数据
 */
export function normalizePlaceholders(placeholders: any[]): NormalizedPlaceholder[] {
  if (!Array.isArray(placeholders)) {
    return []
  }
  
  return placeholders.map((placeholder, index) => normalizePlaceholder(placeholder, index))
}

/**
 * 从占位符名称推断类型
 */
export function inferPlaceholderType(name: string): string {
  if (!name) return '变量'
  
  const lowerName = name.toLowerCase()
  
  if (lowerName.includes('sum') || lowerName.includes('count') || lowerName.includes('avg') || 
      lowerName.includes('总') || lowerName.includes('平均') || lowerName.includes('累计')) {
    return '统计'
  } else if (lowerName.includes('chart') || lowerName.includes('图') || 
            lowerName.includes('trend') || lowerName.includes('趋势')) {
    return '图表'
  } else if (lowerName.includes('analysis') || lowerName.includes('分析') || 
            lowerName.includes('洞察') || lowerName.includes('建议')) {
    return '分析'
  } else if (lowerName.includes('date') || lowerName.includes('time') || 
            lowerName.includes('日期') || lowerName.includes('时间')) {
    return '日期时间'
  } else if (lowerName.includes('title') || lowerName.includes('标题')) {
    return '标题'
  } else if (lowerName.includes('table') || lowerName.includes('表格') || lowerName.includes('列表')) {
    return '表格'
  } else {
    return '变量'
  }
}

/**
 * 获取占位符类型的样式配置
 */
export function getPlaceholderTypeStyle(type: string) {
  const styleMap: Record<string, { variant: any; bgColor: string; textColor: string }> = {
    '统计': { variant: 'success', bgColor: 'bg-green-50', textColor: 'text-green-700' },
    '图表': { variant: 'info', bgColor: 'bg-blue-50', textColor: 'text-blue-700' },
    '表格': { variant: 'info', bgColor: 'bg-indigo-50', textColor: 'text-indigo-700' },
    '分析': { variant: 'warning', bgColor: 'bg-orange-50', textColor: 'text-orange-700' },
    '日期时间': { variant: 'warning', bgColor: 'bg-yellow-50', textColor: 'text-yellow-700' },
    '标题': { variant: 'info', bgColor: 'bg-cyan-50', textColor: 'text-cyan-700' },
    '变量': { variant: 'secondary', bgColor: 'bg-gray-50', textColor: 'text-gray-600' },
    '错误': { variant: 'destructive', bgColor: 'bg-red-50', textColor: 'text-red-700' }
  }
  
  return styleMap[type] || styleMap['变量']
}

/**
 * 计算占位符统计信息
 */
export function calculatePlaceholderStats(placeholders: NormalizedPlaceholder[]) {
  const totalCount = placeholders.length
  
  // 按类型统计
  const typeCounts = placeholders.reduce((acc: Record<string, number>, placeholder) => {
    const type = placeholder.type || '变量'
    acc[type] = (acc[type] || 0) + 1
    return acc
  }, {})
  
  return {
    totalCount,
    typeCounts,
    hasContent: totalCount > 0
  }
}