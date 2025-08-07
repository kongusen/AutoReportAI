'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Tabs, TabPanel, useTabsContext } from '@/components/ui/Tabs'
import { isValidCron, parseCron, buildCron } from '@/utils'

interface CronEditorProps {
  value: string
  onChange: (cron: string) => void
  error?: string
}

const minuteOptions = Array.from({ length: 60 }, (_, i) => ({ label: i.toString(), value: i.toString() }))
const hourOptions = Array.from({ length: 24 }, (_, i) => ({ label: i.toString(), value: i.toString() }))
const dayOptions = Array.from({ length: 31 }, (_, i) => ({ label: (i + 1).toString(), value: (i + 1).toString() }))
const monthOptions = Array.from({ length: 12 }, (_, i) => ({ label: (i + 1).toString(), value: (i + 1).toString() }))
const weekdayOptions = [
  { label: '星期日', value: '0' },
  { label: '星期一', value: '1' },
  { label: '星期二', value: '2' },
  { label: '星期三', value: '3' },
  { label: '星期四', value: '4' },
  { label: '星期五', value: '5' },
  { label: '星期六', value: '6' },
]

const presetSchedules = [
  { label: '每分钟', value: '* * * * *' },
  { label: '每小时', value: '0 * * * *' },
  { label: '每天午夜', value: '0 0 * * *' },
  { label: '每天上午9点', value: '0 9 * * *' },
  { label: '每周一上午9点', value: '0 9 * * 1' },
  { label: '每月1日上午9点', value: '0 9 1 * *' },
  { label: '工作日上午9点', value: '0 9 * * 1-5' },
  { label: '周末上午10点', value: '0 10 * * 0,6' },
]

export function CronEditor({ value, onChange, error }: CronEditorProps) {
  const [mode, setMode] = useState<'preset' | 'visual' | 'text'>('preset')
  const [textValue, setTextValue] = useState(value || '0 0 * * *')

  const tabItems = [
    { key: 'preset', label: '预设模板' },
    { key: 'visual', label: '可视化编辑' },
    { key: 'text', label: '表达式编辑' },
  ]

  const handlePresetSelect = (preset: string) => {
    setTextValue(preset)
    onChange(preset)
  }

  const handleTextChange = (newValue: string) => {
    setTextValue(newValue)
    if (isValidCron(newValue)) {
      onChange(newValue)
    }
  }

  const getCronDescription = (cronExpression: string) => {
    try {
      const parts = parseCron(cronExpression)
      const descriptions = []
      
      if (parts.minute === '*') {
        descriptions.push('每分钟')
      } else if (parts.minute.includes(',')) {
        descriptions.push(`在第 ${parts.minute} 分钟`)
      } else if (parts.minute !== '0') {
        descriptions.push(`在第 ${parts.minute} 分钟`)
      }

      if (parts.hour === '*') {
        descriptions.push('每小时')
      } else if (parts.hour.includes(',')) {
        descriptions.push(`在 ${parts.hour} 点`)
      } else {
        descriptions.push(`在 ${parts.hour} 点`)
      }

      if (parts.day === '*' && parts.dayOfWeek === '*') {
        descriptions.push('每天')
      } else if (parts.day !== '*') {
        descriptions.push(`每月第 ${parts.day} 天`)
      }

      if (parts.dayOfWeek !== '*') {
        const weekdays = parts.dayOfWeek.split(',').map(d => {
          const weekday = weekdayOptions.find(w => w.value === d)
          return weekday ? weekday.label : d
        })
        descriptions.push(`在 ${weekdays.join(', ')}`)
      }

      if (parts.month !== '*') {
        descriptions.push(`在第 ${parts.month} 月`)
      }

      return descriptions.join(', ')
    } catch {
      return '无效的Cron表达式'
    }
  }

  return (
    <div className="space-y-4">
      <Tabs items={tabItems} defaultActiveKey="preset">
        <TabPanel value="preset" activeValue={useTabsContext().activeKey}>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">预设调度模板</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {presetSchedules.map((preset) => (
                  <Button
                    key={preset.value}
                    variant={textValue === preset.value ? 'default' : 'outline'}
                    size="sm"
                    className="justify-start"
                    onClick={() => handlePresetSelect(preset.value)}
                  >
                    <div className="text-left">
                      <div className="font-medium">{preset.label}</div>
                      <div className="text-xs text-gray-500 font-mono">{preset.value}</div>
                    </div>
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabPanel>

        <TabPanel value="visual" activeValue={useTabsContext().activeKey}>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">可视化Cron编辑器</CardTitle>
            </CardHeader>
            <CardContent>
              <VisualCronEditor value={textValue} onChange={handleTextChange} />
            </CardContent>
          </Card>
        </TabPanel>

        <TabPanel value="text" activeValue={useTabsContext().activeKey}>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Cron表达式</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Input
                  value={textValue}
                  onChange={(e) => handleTextChange(e.target.value)}
                  placeholder="0 9 * * 1-5"
                  className="font-mono"
                  error={!!error}
                />
                
                <div className="text-xs text-gray-500 space-y-1">
                  <p>格式：分钟 小时 日 月 星期</p>
                  <p>示例：0 9 * * 1-5 表示每个工作日上午9点执行</p>
                  <p>通配符：* 表示任意值，, 表示列表，- 表示范围，/ 表示步长</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabPanel>
      </Tabs>

      {/* Cron表达式解释 */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-gray-700">当前表达式</div>
              <div className="text-lg font-mono text-gray-900">{textValue}</div>
            </div>
            <div className="text-right">
              <div className="text-sm font-medium text-gray-700">执行时间</div>
              <div className="text-sm text-gray-600">{getCronDescription(textValue)}</div>
            </div>
          </div>
          {error && (
            <div className="mt-2 text-sm text-red-600">{error}</div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

interface VisualCronEditorProps {
  value: string
  onChange: (cron: string) => void
}

function VisualCronEditor({ value, onChange }: VisualCronEditorProps) {
  const [cronParts, setCronParts] = useState(() => {
    try {
      return parseCron(value)
    } catch {
      return {
        minute: '0',
        hour: '0',
        day: '*',
        month: '*',
        dayOfWeek: '*'
      }
    }
  })

  const updateCronPart = (part: keyof typeof cronParts, newValue: string) => {
    const newParts = { ...cronParts, [part]: newValue }
    setCronParts(newParts)
    onChange(buildCron(newParts))
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            分钟
          </label>
          <Select
            options={[
              { label: '每分钟 (*)', value: '*' },
              ...minuteOptions
            ]}
            value={cronParts.minute}
            onChange={(value) => updateCronPart('minute', value as string)}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            小时
          </label>
          <Select
            options={[
              { label: '每小时 (*)', value: '*' },
              ...hourOptions
            ]}
            value={cronParts.hour}
            onChange={(value) => updateCronPart('hour', value as string)}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            日期
          </label>
          <Select
            options={[
              { label: '每天 (*)', value: '*' },
              ...dayOptions
            ]}
            value={cronParts.day}
            onChange={(value) => updateCronPart('day', value as string)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            月份
          </label>
          <Select
            options={[
              { label: '每月 (*)', value: '*' },
              ...monthOptions
            ]}
            value={cronParts.month}
            onChange={(value) => updateCronPart('month', value as string)}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            星期
          </label>
          <Select
            options={[
              { label: '每天 (*)', value: '*' },
              ...weekdayOptions
            ]}
            value={cronParts.dayOfWeek}
            onChange={(value) => updateCronPart('dayOfWeek', value as string)}
          />
        </div>
      </div>

      <div className="bg-gray-50 p-4 rounded-lg">
        <h4 className="text-sm font-medium text-gray-700 mb-2">高级选项</h4>
        <div className="text-xs text-gray-600 space-y-1">
          <p>• 使用 <span className="font-mono">1,3,5</span> 表示多个值（如第1、3、5分钟）</p>
          <p>• 使用 <span className="font-mono">1-5</span> 表示范围（如周一到周五）</p>
          <p>• 使用 <span className="font-mono">*/5</span> 表示步长（如每5分钟）</p>
          <p>• 可以直接在上方输入框中编辑表达式</p>
        </div>
      </div>
    </div>
  )
}