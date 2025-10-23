'use client'

import * as React from 'react'
import { cn } from '@/utils'

interface Column<T = any> {
  key: string
  title: string | React.ReactNode
  dataIndex?: string
  width?: string | number
  align?: 'left' | 'center' | 'right'
  render?: (value: any, record: T, index: number) => React.ReactNode
  sorter?: boolean
  fixed?: 'left' | 'right'
  className?: string
}

interface TableProps<T = any> {
  columns: Column<T>[]
  dataSource: T[]
  rowKey?: string | ((record: T) => string)
  loading?: boolean
  pagination?: boolean
  pageSize?: number
  className?: string
  rowClassName?: string | ((record: T, index: number) => string)
  onRow?: (record: T, index: number) => React.HTMLAttributes<HTMLTableRowElement>
  scroll?: {
    x?: number | string
    y?: number | string
  }
  emptyText?: string
  expandable?: {
    expandedRowRender?: (record: T, index: number) => React.ReactNode
    rowExpandable?: (record: T) => boolean
    defaultExpandAllRows?: boolean
    expandedRowKeys?: React.Key[]
    onExpand?: (expanded: boolean, record: T) => void
    onExpandedRowsChange?: (expandedKeys: React.Key[]) => void
  }
}

export function Table<T = any>({
  columns,
  dataSource,
  rowKey = 'id',
  loading = false,
  className,
  rowClassName,
  onRow,
  scroll,
  emptyText = '暂无数据',
  expandable,
}: TableProps<T>) {
  const getRowKey = (record: T, index: number): string => {
    if (typeof rowKey === 'function') {
      return rowKey(record)
    }
    return (record as any)[rowKey] || index.toString()
  }

  // 展开状态管理
  const [internalExpandedKeys, setInternalExpandedKeys] = React.useState<React.Key[]>(
    expandable?.defaultExpandAllRows ? dataSource.map((_, index) => getRowKey(_, index)) : []
  )

  const expandedKeys = expandable?.expandedRowKeys ?? internalExpandedKeys

  const handleExpand = (record: T, index: number) => {
    const key = getRowKey(record, index)
    const isExpanded = expandedKeys.includes(key)
    const newExpandedKeys = isExpanded
      ? expandedKeys.filter(k => k !== key)
      : [...expandedKeys, key]

    if (!expandable?.expandedRowKeys) {
      setInternalExpandedKeys(newExpandedKeys)
    }

    expandable?.onExpand?.(!isExpanded, record)
    expandable?.onExpandedRowsChange?.(newExpandedKeys)
  }

  const isRowExpandable = (record: T): boolean => {
    if (!expandable?.expandedRowRender) return false
    return expandable?.rowExpandable ? expandable.rowExpandable(record) : true
  }

  // 如果有展开功能，添加展开按钮列
  const expandColumn: Column<T> | null = expandable?.expandedRowRender ? {
    key: '__expand__',
    title: '',
    width: 48,
    render: (_, record: T, index: number) => {
      if (!isRowExpandable(record)) {
        return <div className="w-6 h-6" />
      }

      const key = getRowKey(record, index)
      const isExpanded = expandedKeys.includes(key)

      return (
        <button
          onClick={(e) => {
            e.stopPropagation()
            handleExpand(record, index)
          }}
          className="w-6 h-6 flex items-center justify-center text-gray-400 hover:text-gray-600 transition-colors"
        >
          <svg
            className={cn("w-4 h-4 transition-transform", isExpanded && "rotate-90")}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
          </svg>
        </button>
      )
    }
  } : null

  const finalColumns = expandColumn ? [expandColumn, ...columns] : columns

  const getRowClassName = (record: T, index: number): string => {
    if (typeof rowClassName === 'function') {
      return rowClassName(record, index)
    }
    return rowClassName || ''
  }

  const getCellValue = (record: T, column: Column<T>) => {
    if (column.render) {
      const value = column.dataIndex ? (record as any)[column.dataIndex] : record
      return column.render(value, record, dataSource.indexOf(record))
    }
    return column.dataIndex ? (record as any)[column.dataIndex] : ''
  }

  const getAlignClass = (align?: 'left' | 'center' | 'right') => {
    switch (align) {
      case 'center':
        return 'text-center'
      case 'right':
        return 'text-right'
      default:
        return 'text-left'
    }
  }

  const getCellStyle = (column: Column<T>, isHeader: boolean): React.CSSProperties => {
    const style: React.CSSProperties = {}

    if (column.width !== undefined) {
      style.width = column.width as any
    }

    if (column.fixed === 'left') {
      style.position = 'sticky'
      style.left = 0
      style.zIndex = isHeader ? 40 : 20
      style.backgroundColor = isHeader ? '#f9fafb' : '#ffffff'
      style.boxShadow = 'inset -1px 0 0 rgba(229, 231, 235, 0.8)'
    } else if (column.fixed === 'right') {
      style.position = 'sticky'
      style.right = 0
      style.zIndex = isHeader ? 40 : 20
      style.backgroundColor = isHeader ? '#f9fafb' : '#ffffff'
      style.boxShadow = 'inset 1px 0 0 rgba(229, 231, 235, 0.8)'
    }

    return style
  }

  return (
    <div className={cn('overflow-hidden rounded-lg border border-gray-200', className)}>
      <div className={scroll?.x ? 'overflow-x-auto' : ''} style={{ maxWidth: scroll?.x }}>
        <table className="min-w-full divide-y divide-gray-200">
          {/* 表头 */}
          <thead className="bg-gray-50">
            <tr>
              {finalColumns.map((column) => (
                <th
                  key={column.key}
                  className={cn(
                    'py-3 text-xs font-medium text-gray-500 uppercase tracking-wider',
                    // 特殊处理选择列和操作列的padding
                    column.key === 'selection' ? 'px-1' :
                    column.key === 'actions' ? 'px-1 sm:px-2' :
                    'px-2 sm:px-4 lg:px-6',
                    getAlignClass(column.align),
                    column.className
                  )}
                  style={getCellStyle(column, true)}
                >
                  <div className="flex items-center gap-2">
                    {column.title}
                    {column.sorter && (
                      <button className="text-gray-400 hover:text-gray-600">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M5 8l5-5 5 5H5zM5 12l5 5 5-5H5z" />
                        </svg>
                      </button>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>

          {/* 表体 */}
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td
                  colSpan={finalColumns.length}
                  className="px-6 py-4 text-center text-gray-500"
                >
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-900"></div>
                    <span className="ml-2">加载中...</span>
                  </div>
                </td>
              </tr>
            ) : dataSource.length === 0 ? (
              <tr>
                <td
                  colSpan={finalColumns.length}
                  className="px-6 py-8 text-center text-gray-500"
                >
                  {emptyText}
                </td>
              </tr>
            ) : (
              dataSource.map((record, index) => {
                const rowProps = onRow?.(record, index) || {}
                const key = getRowKey(record, index)
                const isExpanded = expandedKeys.includes(key)

                return (
                  <React.Fragment key={key}>
                    <tr
                      className={cn(
                        'hover:bg-gray-50 transition-colors',
                        getRowClassName(record, index)
                      )}
                      {...rowProps}
                    >
                      {finalColumns.map((column) => (
                        <td
                          key={column.key}
                        className={cn(
                          'py-4 text-sm text-gray-900',
                          // 特殊处理选择列和操作列的padding
                          column.key === 'selection' ? 'px-1 text-center' :
                          column.key === 'actions' ? 'px-1 sm:px-2' :
                          'px-2 sm:px-4 lg:px-6',
                          getAlignClass(column.align),
                          column.className,
                          // 动态调整whitespace行为
                          column.className?.includes('min-w-0') ? '' : 'whitespace-nowrap'
                        )}
                        style={getCellStyle(column, false)}
                      >
                        {getCellValue(record, column)}
                      </td>
                    ))}
                  </tr>
                    {/* 展开行 */}
                    {isExpanded && expandable?.expandedRowRender && (
                      <tr>
                        <td colSpan={finalColumns.length} className="px-2 sm:px-4 lg:px-6 py-4 bg-gray-50">
                          {expandable.expandedRowRender(record, index)}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
