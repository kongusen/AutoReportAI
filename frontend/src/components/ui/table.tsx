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
}: TableProps<T>) {
  const getRowKey = (record: T, index: number): string => {
    if (typeof rowKey === 'function') {
      return rowKey(record)
    }
    return (record as any)[rowKey] || index.toString()
  }

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

  return (
    <div className={cn('overflow-hidden rounded-lg border border-gray-200', className)}>
      <div className={scroll?.x ? 'overflow-x-auto' : ''} style={{ maxWidth: scroll?.x }}>
        <table className="min-w-full divide-y divide-gray-200">
          {/* 表头 */}
          <thead className="bg-gray-50">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={cn(
                    'px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider',
                    getAlignClass(column.align),
                    column.className
                  )}
                  style={{ width: column.width }}
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
                  colSpan={columns.length}
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
                  colSpan={columns.length}
                  className="px-6 py-8 text-center text-gray-500"
                >
                  {emptyText}
                </td>
              </tr>
            ) : (
              dataSource.map((record, index) => {
                const rowProps = onRow?.(record, index) || {}
                return (
                  <tr
                    key={getRowKey(record, index)}
                    className={cn(
                      'hover:bg-gray-50 transition-colors',
                      getRowClassName(record, index)
                    )}
                    {...rowProps}
                  >
                    {columns.map((column) => (
                      <td
                        key={column.key}
                        className={cn(
                          'px-6 py-4 whitespace-nowrap text-sm text-gray-900',
                          getAlignClass(column.align),
                          column.className
                        )}
                      >
                        {getCellValue(record, column)}
                      </td>
                    ))}
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}