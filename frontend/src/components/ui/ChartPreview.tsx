'use client'

import { useState, useEffect, useRef } from 'react'
import {
  ChartBarIcon,
  ArrowDownTrayIcon,
  ArrowsPointingOutIcon,
  XMarkIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'

// 动态导入ECharts以避免SSR问题
let echarts: any = null
if (typeof window !== 'undefined') {
  import('echarts').then((module) => {
    echarts = module
  })
}

interface ChartPreviewProps {
  echartsConfig: any
  chartType: string
  chartData: any[]
  metadata?: {
    data_points?: number
    chart_elements?: any
    data_summary?: any
    generation_time?: string
    data_source?: {
      sql_query?: string
      execution_time_ms?: number
      row_count?: number
      data_quality_score?: number
    }
  }
  title?: string
  className?: string
  onExport?: (format: 'png' | 'svg' | 'json') => void
}

export function ChartPreview({ 
  echartsConfig, 
  chartType, 
  chartData, 
  metadata,
  title = "图表预览",
  className = "",
  onExport 
}: ChartPreviewProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const [chartInstance, setChartInstance] = useState<any>(null)
  const [fullscreenOpen, setFullscreenOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 初始化图表
  useEffect(() => {
    if (!echarts || !chartRef.current || !echartsConfig) return

    try {
      setLoading(true)
      setError(null)

      // 创建图表实例
      const chart = echarts.init(chartRef.current)
      setChartInstance(chart)

      // 设置图表配置
      chart.setOption(echartsConfig, true)

      // 处理窗口大小变化
      const handleResize = () => {
        chart.resize()
      }
      window.addEventListener('resize', handleResize)

      setLoading(false)

      return () => {
        window.removeEventListener('resize', handleResize)
        chart.dispose()
      }
    } catch (err) {
      console.error('图表初始化失败:', err)
      setError('图表渲染失败，请检查配置')
      setLoading(false)
    }
  }, [echartsConfig])

  // 导出图表
  const handleExport = async (format: 'png' | 'svg' | 'json') => {
    if (!chartInstance) return

    try {
      let exportData: string | any

      switch (format) {
        case 'png':
          exportData = chartInstance.getDataURL({
            type: 'png',
            pixelRatio: 2,
            backgroundColor: '#fff'
          })
          // 下载PNG
          const link = document.createElement('a')
          link.download = `${title || 'chart'}.png`
          link.href = exportData
          link.click()
          break

        case 'svg':
          exportData = chartInstance.getDataURL({
            type: 'svg',
            pixelRatio: 1
          })
          // 下载SVG
          const svgLink = document.createElement('a')
          svgLink.download = `${title || 'chart'}.svg`
          svgLink.href = exportData
          svgLink.click()
          break

        case 'json':
          exportData = {
            config: echartsConfig,
            data: chartData,
            metadata: metadata,
            exportTime: new Date().toISOString()
          }
          // 下载JSON配置
          const jsonBlob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
          const jsonUrl = URL.createObjectURL(jsonBlob)
          const jsonLink = document.createElement('a')
          jsonLink.download = `${title || 'chart'}-config.json`
          jsonLink.href = jsonUrl
          jsonLink.click()
          URL.revokeObjectURL(jsonUrl)
          break
      }

      onExport?.(format)
    } catch (err) {
      console.error('图表导出失败:', err)
    }
  }

  // 获取图表类型显示名
  const getChartTypeName = (type: string) => {
    const typeNames: { [key: string]: string } = {
      'bar_chart': '柱状图',
      'pie_chart': '饼图',
      'line_chart': '折线图',
      'scatter_chart': '散点图',
      'radar_chart': '雷达图',
      'funnel_chart': '漏斗图'
    }
    return typeNames[type] || type
  }

  // 格式化数据质量分数
  const formatDataQuality = (score: number) => {
    if (score >= 0.9) return { label: '优秀', color: 'success' }
    if (score >= 0.7) return { label: '良好', color: 'warning' }
    if (score >= 0.5) return { label: '一般', color: 'secondary' }
    return { label: '较差', color: 'destructive' }
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 图表信息 */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
                <ChartBarIcon className="w-4 h-4 text-blue-600" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-900">{title}</h3>
                <div className="flex items-center space-x-2">
                  <Badge variant="outline">
                    {getChartTypeName(chartType)}
                  </Badge>
                  <span className="text-xs text-gray-500">
                    {metadata?.data_points || chartData.length} 个数据点
                  </span>
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              {/* 数据质量指标 */}
              {metadata?.data_source?.data_quality_score && (
                <Badge variant={formatDataQuality(metadata.data_source.data_quality_score).color as any}>
                  数据质量: {formatDataQuality(metadata.data_source.data_quality_score).label}
                </Badge>
              )}
              
              {/* 导出按钮 */}
              <div className="flex items-center space-x-1">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleExport('png')}
                  disabled={loading || !!error}
                >
                  <ArrowDownTrayIcon className="w-3 h-3 mr-1" />
                  PNG
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleExport('json')}
                  disabled={loading || !!error}
                >
                  配置
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setFullscreenOpen(true)}
                  disabled={loading || !!error}
                >
                  <ArrowsPointingOutIcon className="w-3 h-3" />
                </Button>
              </div>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-0">
          <div className="space-y-4">
            {/* 图表容器 */}
            <div className="relative">
              {loading && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-50 rounded-lg">
                  <div className="text-sm text-gray-500">图表渲染中...</div>
                </div>
              )}
              
              {error && (
                <div className="absolute inset-0 flex items-center justify-center bg-red-50 rounded-lg">
                  <div className="text-center">
                    <InformationCircleIcon className="w-8 h-8 text-red-400 mx-auto mb-2" />
                    <div className="text-sm text-red-600">{error}</div>
                  </div>
                </div>
              )}
              
              <div
                ref={chartRef}
                className="w-full h-80 min-h-[320px] rounded-lg border"
                style={{ display: loading || error ? 'none' : 'block' }}
              />
            </div>

            {/* 图表统计信息 */}
            {metadata && (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 pt-4 border-t">
                {metadata.data_source?.execution_time_ms && (
                  <div className="text-center">
                    <div className="text-lg font-semibold text-gray-900">
                      {metadata.data_source.execution_time_ms < 1000 
                        ? `${metadata.data_source.execution_time_ms}ms` 
                        : `${(metadata.data_source.execution_time_ms / 1000).toFixed(2)}s`}
                    </div>
                    <div className="text-xs text-gray-500">查询耗时</div>
                  </div>
                )}
                
                <div className="text-center">
                  <div className="text-lg font-semibold text-gray-900">
                    {metadata.data_points || chartData.length}
                  </div>
                  <div className="text-xs text-gray-500">数据点</div>
                </div>
                
                {metadata.data_source?.row_count && (
                  <div className="text-center">
                    <div className="text-lg font-semibold text-gray-900">
                      {metadata.data_source.row_count}
                    </div>
                    <div className="text-xs text-gray-500">原始行数</div>
                  </div>
                )}
                
                {metadata.chart_elements?.series_count && (
                  <div className="text-center">
                    <div className="text-lg font-semibold text-gray-900">
                      {metadata.chart_elements.series_count}
                    </div>
                    <div className="text-xs text-gray-500">数据系列</div>
                  </div>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 全屏预览模态框 */}
      <Modal
        isOpen={fullscreenOpen}
        onClose={() => setFullscreenOpen(false)}
        title={`${title} - 全屏预览`}
        size="full"
      >
        <div className="h-full flex flex-col">
          <div className="flex-1 min-h-0">
            <div 
              className="w-full h-full"
              ref={(ref) => {
                if (ref && echarts && echartsConfig && fullscreenOpen) {
                  const fullChart = echarts.init(ref)
                  fullChart.setOption(echartsConfig, true)
                  
                  // 清理函数
                  const cleanup = () => fullChart.dispose()
                  ref.addEventListener('beforeunload', cleanup)
                  
                  return cleanup
                }
              }}
            />
          </div>
          
          <div className="flex justify-end space-x-2 pt-4 border-t">
            <Button
              variant="outline"
              onClick={() => handleExport('png')}
            >
              <ArrowDownTrayIcon className="w-4 h-4 mr-2" />
              下载图片
            </Button>
            <Button
              variant="outline"
              onClick={() => setFullscreenOpen(false)}
            >
              <XMarkIcon className="w-4 h-4 mr-2" />
              关闭
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}