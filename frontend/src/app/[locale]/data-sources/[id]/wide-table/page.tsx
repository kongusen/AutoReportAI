'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHeader, TableRow } from '@/components/ui/table'
import { Loader2, RefreshCw } from 'lucide-react'
import { useI18n } from '@/components/providers/I18nProvider'
import { useParams } from 'next/navigation'
import { httpClient } from '@/lib/api/client';

const PAGE_SIZE = 10

// 移除所有 mock 数据和 mock 逻辑，只保留真实 API 数据流
// 所有类型声明、类型守卫、linter 修复都以真实 API 类型为准
// 如无数据时显示 loading/error 占位符

export default function WideTablePage() {
  const { t } = useI18n()
  const params = useParams()
  const dataSourceId = params.id as string
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [fields, setFields] = useState<string[]>([])
  const [rows, setRows] = useState<any[][]>([])
  const [total, setTotal] = useState(0)
  const [updating, setUpdating] = useState(false)

  useEffect(() => {
    fetchData(page)
  }, [page, dataSourceId])

  const fetchData = async (p: number) => {
    setLoading(true)
    try {
      const offset = (p - 1) * PAGE_SIZE
      const res = await httpClient.get(`/v1/data-sources/${dataSourceId}/wide-table?limit=${PAGE_SIZE}&offset=${offset}`)
      setFields(res.data.fields || [])
      setRows(res.data.rows || [])
      setTotal(res.data.total || 0)
    } catch (e) {
      setFields([])
      setRows([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdate = () => {
    setUpdating(true)
    fetchData(page).finally(() => setUpdating(false))
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center py-4">
      <div className="w-full max-w-[95vw] px-2">
        <Card className="w-full shadow-lg">
          <CardHeader>
            <CardTitle>{t('wideTable', 'dataSources')}</CardTitle>
            {/* 数据源信息可省略 */}
          </CardHeader>
          <CardContent>
            <div className="flex justify-between items-center mb-2">
              <div className="font-medium text-gray-700">{t('wideTableData', 'dataSources')}</div>
              <Button onClick={handleUpdate} disabled={updating} variant="outline" size="sm">
                {updating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                {t('manualUpdate', 'dataSources')}
              </Button>
            </div>
            <div
              className="overflow-x-auto overflow-y-auto border rounded-lg bg-white"
              style={{ maxHeight: 'calc(100vh - 220px)' }}
            >
              <Table className="min-w-[1200px] w-full">
                <TableHeader>
                  <TableRow>
                    {fields.map(f => <TableCell key={f} className="font-bold">{f}</TableCell>)}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={fields.length || 1} className="text-center">
                        <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                      </TableCell>
                    </TableRow>
                  ) : rows.length > 0 ? (
                    rows.map((row, i) => (
                      <TableRow key={i}>
                        {row.map((cell, j) => <TableCell key={j}>{String(cell)}</TableCell>)}
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={fields.length || 1} className="text-center text-gray-400">{t('noData', 'dataSources')}</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
            {/* 分页控件 */}
            <div className="flex justify-end items-center mt-4 space-x-2">
              <Button size="sm" variant="outline" disabled={page === 1} onClick={() => setPage(p => Math.max(1, p - 1))}>{t('prevPage')}</Button>
              <span className="text-sm text-gray-500">{page} / {totalPages}</span>
              <Button size="sm" variant="outline" disabled={page === totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))}>{t('nextPage')}</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
} 