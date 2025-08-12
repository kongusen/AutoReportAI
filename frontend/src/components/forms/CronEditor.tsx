'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Tabs, TabPanel, useTabsContext } from '@/components/ui/Tabs'
import { isValidCron, parseCron, buildCron, formatDate } from '@/utils'

interface CronEditorProps {
  value: string
  onChange: (cron: string) => void
  error?: string
  autoSave?: boolean
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
  // 高频执行
  { label: '每分钟', value: '* * * * *', description: '每分钟执行一次', category: 'frequent' },
  { label: '每2分钟', value: '*/2 * * * *', description: '每2分钟执行一次', category: 'frequent' },
  { label: '每5分钟', value: '*/5 * * * *', description: '每5分钟执行一次', category: 'frequent' },
  { label: '每10分钟', value: '*/10 * * * *', description: '每10分钟执行一次', category: 'frequent' },
  { label: '每15分钟', value: '*/15 * * * *', description: '每15分钟执行一次', category: 'frequent' },
  { label: '每30分钟', value: '*/30 * * * *', description: '每30分钟执行一次', category: 'frequent' },
  
  // 每小时
  { label: '每小时', value: '0 * * * *', description: '每小时的第0分钟执行', category: 'hourly' },
  { label: '每2小时', value: '0 */2 * * *', description: '每2小时执行一次', category: 'hourly' },
  { label: '每3小时', value: '0 */3 * * *', description: '每3小时执行一次', category: 'hourly' },
  { label: '每4小时', value: '0 */4 * * *', description: '每4小时执行一次', category: 'hourly' },
  { label: '每6小时', value: '0 */6 * * *', description: '每6小时执行一次', category: 'hourly' },
  { label: '每8小时', value: '0 */8 * * *', description: '每8小时执行一次', category: 'hourly' },
  { label: '每12小时', value: '0 */12 * * *', description: '每12小时执行一次', category: 'hourly' },
  
  // 每天
  { label: '每天午夜', value: '0 0 * * *', description: '每天00:00执行', category: 'daily' },
  { label: '每天凌晨1点', value: '0 1 * * *', description: '每天01:00执行', category: 'daily' },
  { label: '每天凌晨2点', value: '0 2 * * *', description: '每天02:00执行', category: 'daily' },
  { label: '每天凌晨3点', value: '0 3 * * *', description: '每天03:00执行', category: 'daily' },
  { label: '每天上午6点', value: '0 6 * * *', description: '每天06:00执行', category: 'daily' },
  { label: '每天上午8点', value: '0 8 * * *', description: '每天08:00执行', category: 'daily' },
  { label: '每天上午9点', value: '0 9 * * *', description: '每天09:00执行', category: 'daily' },
  { label: '每天上午10点', value: '0 10 * * *', description: '每天10:00执行', category: 'daily' },
  { label: '每天中午12点', value: '0 12 * * *', description: '每天12:00执行', category: 'daily' },
  { label: '每天下午2点', value: '0 14 * * *', description: '每天14:00执行', category: 'daily' },
  { label: '每天下午4点', value: '0 16 * * *', description: '每天16:00执行', category: 'daily' },
  { label: '每天下午6点', value: '0 18 * * *', description: '每天18:00执行', category: 'daily' },
  { label: '每天晚上8点', value: '0 20 * * *', description: '每天20:00执行', category: 'daily' },
  { label: '每天晚上9点', value: '0 21 * * *', description: '每天21:00执行', category: 'daily' },
  { label: '每天晚上10点', value: '0 22 * * *', description: '每天22:00执行', category: 'daily' },
  
  // 工作日
  { label: '工作日上午9点', value: '0 9 * * 1-5', description: '周一到周五09:00执行', category: 'weekdays' },
  { label: '工作日上午10点', value: '0 10 * * 1-5', description: '周一到周五10:00执行', category: 'weekdays' },
  { label: '工作日中午12点', value: '0 12 * * 1-5', description: '周一到周五12:00执行', category: 'weekdays' },
  { label: '工作日下午2点', value: '0 14 * * 1-5', description: '周一到周五14:00执行', category: 'weekdays' },
  { label: '工作日下午5点', value: '0 17 * * 1-5', description: '周一到周五17:00执行', category: 'weekdays' },
  { label: '工作日下午6点', value: '0 18 * * 1-5', description: '周一到周五18:00执行', category: 'weekdays' },
  
  // 每周
  { label: '每周一上午9点', value: '0 9 * * 1', description: '每周一09:00执行', category: 'weekly' },
  { label: '每周二上午9点', value: '0 9 * * 2', description: '每周二09:00执行', category: 'weekly' },
  { label: '每周三上午9点', value: '0 9 * * 3', description: '每周三09:00执行', category: 'weekly' },
  { label: '每周四上午9点', value: '0 9 * * 4', description: '每周四09:00执行', category: 'weekly' },
  { label: '每周五上午9点', value: '0 9 * * 5', description: '每周五09:00执行', category: 'weekly' },
  { label: '每周五下午5点', value: '0 17 * * 5', description: '每周五17:00执行', category: 'weekly' },
  { label: '每周六上午10点', value: '0 10 * * 6', description: '每周六10:00执行', category: 'weekly' },
  { label: '每周日上午10点', value: '0 10 * * 0', description: '每周日10:00执行', category: 'weekly' },
  { label: '周末上午10点', value: '0 10 * * 0,6', description: '周六、周日10:00执行', category: 'weekly' },
  
  // 每月
  { label: '每月1日上午9点', value: '0 9 1 * *', description: '每月第一天09:00执行', category: 'monthly' },
  { label: '每月1日中午12点', value: '0 12 1 * *', description: '每月第一天12:00执行', category: 'monthly' },
  { label: '每月15日上午9点', value: '0 9 15 * *', description: '每月15日09:00执行', category: 'monthly' },
  { label: '每月15日下午2点', value: '0 14 15 * *', description: '每月15日14:00执行', category: 'monthly' },
  { label: '每月最后一天', value: '0 0 L * *', description: '每月最后一天00:00执行', category: 'monthly' },
  
  // 特殊
  { label: '每季度第一天', value: '0 0 1 */3 *', description: '每3个月第一天00:00执行', category: 'special' },
  { label: '每半年第一天', value: '0 0 1 */6 *', description: '每6个月第一天00:00执行', category: 'special' },
  { label: '每年1月1日', value: '0 0 1 1 *', description: '每年1月1日00:00执行', category: 'special' },
  { label: '每年7月1日', value: '0 0 1 7 *', description: '每年7月1日00:00执行', category: 'special' },
]

export function CronEditor({ value, onChange, error, autoSave = false }: CronEditorProps) {
  const [mode, setMode] = useState<'quick' | 'preset' | 'visual' | 'text'>('quick')
  const [textValue, setTextValue] = useState(value || '0 9 * * 1-5')
  const [nextExecutions, setNextExecutions] = useState<Date[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  // 同步外部 value 到内部状态
  useEffect(() => {
    if (value !== textValue) {
      setTextValue(value || '0 9 * * 1-5')
    }
  }, [value])

  const tabItems = [
    { key: 'quick', label: '快速设置' },
    { key: 'preset', label: '预设模板' },
    { key: 'visual', label: '可视化编辑' },
    { key: 'text', label: '表达式编辑' },
  ]

  const handlePresetSelect = (preset: string) => {
    setTextValue(preset)
    onChange(preset)
    calculateNextExecutions(preset)
    
    // 如果启用了自动保存，延迟触发保存事件
    if (autoSave) {
      setTimeout(() => {
        const event = new CustomEvent('cronAutoSave', { detail: { cron: preset } })
        window.dispatchEvent(event)
      }, 100)
    }
  }

  const handleTextChange = (newValue: string) => {
    setTextValue(newValue)
    if (isValidCron(newValue)) {
      onChange(newValue)
      calculateNextExecutions(newValue)
      
      // 如果启用了自动保存，延迟触发保存事件
      if (autoSave) {
        setTimeout(() => {
          const event = new CustomEvent('cronAutoSave', { detail: { cron: newValue } })
          window.dispatchEvent(event)
        }, 500) // 延迟500ms，避免频繁触发
      }
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

  // Calculate next execution times
  const calculateNextExecutions = (cronExpression: string) => {
    if (!isValidCron(cronExpression)) {
      setNextExecutions([])
      return
    }

    try {
      const executions: Date[] = []
      const now = new Date()
      
      // Simple calculation for next executions (basic implementation)
      // In a real application, you'd use a proper cron parser library like node-cron
      const parts = parseCron(cronExpression)
      
      for (let i = 0; i < 5; i++) {
        const nextTime = new Date(now)
        nextTime.setSeconds(0)
        nextTime.setMilliseconds(0)
        
        // Add days to get future executions
        nextTime.setDate(now.getDate() + i)
        
        // Set hour and minute based on cron expression
        if (parts.hour !== '*' && !parts.hour.includes('/')) {
          nextTime.setHours(parseInt(parts.hour))
        }
        if (parts.minute !== '*' && !parts.minute.includes('/')) {
          nextTime.setMinutes(parseInt(parts.minute))
        }
        
        executions.push(new Date(nextTime))
      }
      
      setNextExecutions(executions)
    } catch (error) {
      setNextExecutions([])
    }
  }

  // Update executions when component mounts or value changes
  useEffect(() => {
    if (textValue) {
      calculateNextExecutions(textValue)
    }
  }, [textValue])

  return (
    <div className="space-y-4">
      <Tabs items={tabItems} defaultActiveKey="quick">
        <TabPanel value="quick" activeValue={useTabsContext().activeKey}>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">快速设置调度</CardTitle>
            </CardHeader>
            <CardContent>
              <QuickScheduleEditor value={textValue} onChange={handleTextChange} autoSave={autoSave} />
            </CardContent>
          </Card>
        </TabPanel>
        <TabPanel value="preset" activeValue={useTabsContext().activeKey}>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">预设调度模板</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* 分类筛选 */}
                <div className="flex flex-wrap gap-2 mb-4">
                  <button
                    type="button"
                    className={`px-3 py-1 text-xs rounded-full transition-colors ${
                      selectedCategory === 'all' 
                        ? 'bg-blue-100 text-blue-800 border border-blue-200' 
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                    onClick={() => setSelectedCategory('all')}
                  >
                    全部
                  </button>
                  {[
                    { key: 'frequent', label: '高频执行' },
                    { key: 'hourly', label: '每小时' },
                    { key: 'daily', label: '每日' },
                    { key: 'weekdays', label: '工作日' },
                    { key: 'weekly', label: '每周' },
                    { key: 'monthly', label: '每月' },
                    { key: 'special', label: '特殊' }
                  ].map(cat => (
                    <button
                      key={cat.key}
                      type="button"
                      className={`px-3 py-1 text-xs rounded-full transition-colors ${
                        selectedCategory === cat.key 
                          ? 'bg-blue-100 text-blue-800 border border-blue-200' 
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                      onClick={() => setSelectedCategory(cat.key)}
                    >
                      {cat.label}
                    </button>
                  ))}
                </div>
                
                {/* 预设模板 */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {presetSchedules
                    .filter(preset => selectedCategory === 'all' || preset.category === selectedCategory)
                    .map((preset) => (
                    <Button
                      key={preset.value}
                      variant={textValue === preset.value ? 'default' : 'outline'}
                      size="sm"
                      className="justify-start p-3 h-auto"
                      onClick={() => handlePresetSelect(preset.value)}
                    >
                      <div className="text-left w-full">
                        <div className="font-medium text-sm">{preset.label}</div>
                        <div className="text-xs text-gray-500 font-mono mt-1">{preset.value}</div>
                        <div className="text-xs text-gray-400 mt-1">{preset.description}</div>
                      </div>
                    </Button>
                  ))}
                </div>
                
                {/* 快速输入 */}
                <div className="border-t pt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    或直接输入Cron表达式
                  </label>
                  <div className="flex gap-2">
                    <Input
                      value={textValue}
                      onChange={(e) => handleTextChange(e.target.value)}
                      placeholder="0 9 * * 1-5"
                      className="font-mono text-sm flex-1"
                      error={!!error}
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (isValidCron(textValue)) {
                          handlePresetSelect(textValue)
                        }
                      }}
                      disabled={!isValidCron(textValue)}
                    >
                      应用
                    </Button>
                  </div>
                  {error && (
                    <p className="mt-1 text-xs text-red-600">{error}</p>
                  )}
                </div>
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
              <CardTitle className="text-base">Cron表达式编辑器</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Input
                  value={textValue}
                  onChange={(e) => handleTextChange(e.target.value)}
                  placeholder="0 9 * * 1-5"
                  className="font-mono text-base"
                  error={!!error}
                />
                
                {/* Cron字段说明 */}
                <div className="grid grid-cols-5 gap-2 text-xs">
                  <div className="bg-blue-50 p-2 rounded text-center">
                    <div className="font-semibold text-blue-700">分钟</div>
                    <div className="text-blue-600">0-59</div>
                  </div>
                  <div className="bg-green-50 p-2 rounded text-center">
                    <div className="font-semibold text-green-700">小时</div>
                    <div className="text-green-600">0-23</div>
                  </div>
                  <div className="bg-yellow-50 p-2 rounded text-center">
                    <div className="font-semibold text-yellow-700">日</div>
                    <div className="text-yellow-600">1-31</div>
                  </div>
                  <div className="bg-purple-50 p-2 rounded text-center">
                    <div className="font-semibold text-purple-700">月</div>
                    <div className="text-purple-600">1-12</div>
                  </div>
                  <div className="bg-pink-50 p-2 rounded text-center">
                    <div className="font-semibold text-pink-700">星期</div>
                    <div className="text-pink-600">0-7</div>
                  </div>
                </div>

                {/* 语法帮助 */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="text-sm font-medium text-gray-700 mb-3">Cron语法说明</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-gray-600">
                    <div>
                      <h5 className="font-semibold mb-2">基本符号</h5>
                      <ul className="space-y-1">
                        <li><span className="font-mono bg-white px-1 rounded">*</span> - 匹配任意值</li>
                        <li><span className="font-mono bg-white px-1 rounded">?</span> - 不指定值（日和星期互斥）</li>
                        <li><span className="font-mono bg-white px-1 rounded">-</span> - 范围分隔符</li>
                        <li><span className="font-mono bg-white px-1 rounded">,</span> - 值列表分隔符</li>
                        <li><span className="font-mono bg-white px-1 rounded">/</span> - 步长指定符</li>
                      </ul>
                    </div>
                    <div>
                      <h5 className="font-semibold mb-2">示例</h5>
                      <ul className="space-y-1">
                        <li><span className="font-mono bg-white px-1 rounded">*/5</span> - 每5分钟</li>
                        <li><span className="font-mono bg-white px-1 rounded">1-5</span> - 1到5</li>
                        <li><span className="font-mono bg-white px-1 rounded">1,3,5</span> - 1、3、5</li>
                        <li><span className="font-mono bg-white px-1 rounded">0 */2</span> - 每2小时的第0分钟</li>
                        <li><span className="font-mono bg-white px-1 rounded">0 9-17</span> - 9点到17点的第0分钟</li>
                      </ul>
                    </div>
                  </div>
                </div>

                {/* 常用模式 */}
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-3">常用模式</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {[
                      { pattern: '0 * * * *', desc: '每小时执行' },
                      { pattern: '*/15 * * * *', desc: '每15分钟执行' },
                      { pattern: '0 2 * * *', desc: '每天凌晨2点执行' },
                      { pattern: '0 9-17 * * 1-5', desc: '工作日9-17点每小时执行' },
                      { pattern: '0 0 1 * *', desc: '每月1日执行' },
                      { pattern: '0 0 * * 0', desc: '每周日执行' }
                    ].map((item, index) => (
                      <Button
                        key={index}
                        variant="ghost"
                        size="sm"
                        className="justify-between text-xs h-auto py-2"
                        onClick={() => handleTextChange(item.pattern)}
                      >
                        <span className="font-mono">{item.pattern}</span>
                        <span className="text-gray-500">{item.desc}</span>
                      </Button>
                    ))}
                  </div>
                </div>

                {/* 在线验证 */}
                <div className="border rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-medium text-gray-700">表达式验证</h4>
                    <Badge variant={isValidCron(textValue) ? 'success' : 'destructive'} size="sm">
                      {isValidCron(textValue) ? '有效' : '无效'}
                    </Badge>
                  </div>
                  {isValidCron(textValue) && (
                    <div className="text-xs text-gray-600">
                      ✓ 表达式格式正确，可以正常使用
                    </div>
                  )}
                  {!isValidCron(textValue) && (
                    <div className="text-xs text-red-600">
                      ✗ 表达式格式错误，请检查语法
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabPanel>
      </Tabs>

      {/* Cron表达式解释和预览 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="space-y-3">
              <div>
                <div className="text-sm font-medium text-gray-700">当前表达式</div>
                <div className="text-lg font-mono text-gray-900 bg-gray-50 px-2 py-1 rounded">{textValue}</div>
              </div>
              <div>
                <div className="text-sm font-medium text-gray-700">执行规则</div>
                <div className="text-sm text-gray-600">{getCronDescription(textValue)}</div>
              </div>
              {error && (
                <div className="text-sm text-red-600 bg-red-50 p-2 rounded">{error}</div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center justify-between">
              <span>预计执行时间</span>
              <Badge variant={isValidCron(textValue) ? 'success' : 'destructive'} size="sm">
                {isValidCron(textValue) ? '有效' : '无效'}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isValidCron(textValue) && nextExecutions.length > 0 ? (
              <div className="space-y-2">
                {nextExecutions.slice(0, 3).map((time, index) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-blue-50 rounded text-sm">
                    <span className="text-gray-600">第 {index + 1} 次</span>
                    <span className="font-medium text-gray-900">
                      {formatDate(time, { 
                        month: 'short', 
                        day: 'numeric', 
                        hour: '2-digit', 
                        minute: '2-digit',
                        weekday: 'short'
                      })}
                    </span>
                  </div>
                ))}
                <div className="text-xs text-gray-500 text-center pt-2">
                  显示接下来的 3 次执行时间（预估）
                </div>
              </div>
            ) : (
              <div className="text-center py-4 text-gray-500">
                <div className="text-sm">表达式无效或无法计算执行时间</div>
                <div className="text-xs mt-1">请检查Cron表达式格式</div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

interface QuickScheduleEditorProps {
  value: string
  onChange: (cron: string) => void
  autoSave?: boolean
}

function QuickScheduleEditor({ value, onChange, autoSave }: QuickScheduleEditorProps) {
  // 解析传入的 cron 值来初始化状态
  const parseCronValue = (cronValue: string) => {
    try {
      const parts = parseCron(cronValue)
      const hour = parts.hour === '*' ? '9' : parts.hour
      const minute = parts.minute === '*' ? '0' : parts.minute
      
      let scheduleType: 'daily' | 'weekly' | 'monthly' = 'daily'
      let weekdays: string[] = ['1', '2', '3', '4', '5']
      let monthDay = '1'

      // 判断调度类型
      if (parts.day !== '*') {
        scheduleType = 'monthly'
        monthDay = parts.day
      } else if (parts.dayOfWeek !== '*') {
        scheduleType = 'weekly'
        if (parts.dayOfWeek.includes(',')) {
          weekdays = parts.dayOfWeek.split(',')
        } else if (parts.dayOfWeek.includes('-')) {
          const [start, end] = parts.dayOfWeek.split('-')
          weekdays = []
          for (let i = parseInt(start); i <= parseInt(end); i++) {
            weekdays.push(i.toString())
          }
        } else {
          weekdays = [parts.dayOfWeek]
        }
      } else {
        scheduleType = 'daily'
      }

      return {
        scheduleType,
        time: { hour, minute },
        weekdays,
        monthDay
      }
    } catch {
      return {
        scheduleType: 'daily' as const,
        time: { hour: '9', minute: '0' },
        weekdays: ['1', '2', '3', '4', '5'],
        monthDay: '1'
      }
    }
  }

  const initialState = parseCronValue(value)
  const [scheduleType, setScheduleType] = useState(initialState.scheduleType)
  const [time, setTime] = useState(initialState.time)
  const [weekdays, setWeekdays] = useState(initialState.weekdays)
  const [monthDay, setMonthDay] = useState(initialState.monthDay)

  // 当外部值变化时重新解析
  useEffect(() => {
    if (value) {
      const newState = parseCronValue(value)
      setScheduleType(newState.scheduleType)
      setTime(newState.time)
      setWeekdays(newState.weekdays)
      setMonthDay(newState.monthDay)
    }
  }, [value])

  const weekdayOptions = [
    { label: '周一', value: '1' },
    { label: '周二', value: '2' },
    { label: '周三', value: '3' },
    { label: '周四', value: '4' },
    { label: '周五', value: '5' },
    { label: '周六', value: '6' },
    { label: '周日', value: '0' },
  ]

  const generateCron = () => {
    const { hour, minute } = time
    
    switch (scheduleType) {
      case 'daily':
        return `${minute} ${hour} * * *`
      case 'weekly':
        return `${minute} ${hour} * * ${weekdays.join(',')}`
      case 'monthly':
        return `${minute} ${hour} ${monthDay} * *`
      default:
        return `${minute} ${hour} * * *`
    }
  }

  const toggleWeekday = (day: string) => {
    setWeekdays(prev => {
      const newWeekdays = prev.includes(day) 
        ? prev.filter(d => d !== day)
        : [...prev, day].sort((a, b) => parseInt(a) - parseInt(b))
      return newWeekdays
    })
  }

  // 当状态变化时更新 cron 表达式
  useEffect(() => {
    const cron = generateCron()
    onChange(cron)
    
    // 如果启用了自动保存，延迟触发保存事件
    if (autoSave) {
      setTimeout(() => {
        const event = new CustomEvent('cronAutoSave', { detail: { cron } })
        window.dispatchEvent(event)
      }, 100)
    }
  }, [scheduleType, time, weekdays, monthDay, onChange, autoSave])

  return (
    <div className="space-y-6">
      {/* 调度类型选择 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">调度频率</label>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <Button
            type="button"
            variant={scheduleType === 'daily' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setScheduleType('daily')}
            className="justify-center"
          >
            每天
          </Button>
          <Button
            type="button"
            variant={scheduleType === 'weekly' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setScheduleType('weekly')}
            className="justify-center"
          >
            每周
          </Button>
          <Button
            type="button"
            variant={scheduleType === 'monthly' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setScheduleType('monthly')}
            className="justify-center"
          >
            每月
          </Button>
        </div>
      </div>

      {/* 时间设置 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">执行时间</label>
        <div className="grid grid-cols-2 gap-4 max-w-xs">
          <div>
            <label className="block text-xs text-gray-500 mb-1">小时</label>
            <Select
              options={Array.from({ length: 24 }, (_, i) => ({ 
                label: i.toString().padStart(2, '0'), 
                value: i.toString() 
              }))}
              value={time.hour}
              onChange={(value) => setTime(prev => ({ ...prev, hour: value as string }))}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">分钟</label>
            <Select
              options={[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55].map(i => ({ 
                label: i.toString().padStart(2, '0'), 
                value: i.toString() 
              }))}
              value={time.minute}
              onChange={(value) => setTime(prev => ({ ...prev, minute: value as string }))}
            />
          </div>
        </div>
      </div>

      {/* 周日设置 */}
      {scheduleType === 'weekly' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">选择星期</label>
          <div className="grid grid-cols-4 md:grid-cols-7 gap-2">
            {weekdayOptions.map(day => (
              <Button
                key={day.value}
                type="button"
                variant={weekdays.includes(day.value) ? 'default' : 'outline'}
                size="sm"
                onClick={() => toggleWeekday(day.value)}
                className="justify-center"
              >
                {day.label}
              </Button>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            已选择: {weekdays.length > 0 ? weekdayOptions.filter(d => weekdays.includes(d.value)).map(d => d.label).join(', ') : '无'}
          </p>
        </div>
      )}

      {/* 自定义时间输入 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">自定义时间（24小时制）</label>
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <label className="block text-xs text-gray-500 mb-1">小时:分钟</label>
            <Input
              type="time"
              value={`${time.hour.padStart(2, '0')}:${time.minute.padStart(2, '0')}`}
              onChange={(e) => {
                const [hour, minute] = e.target.value.split(':')
                setTime({ hour, minute })
              }}
              className="text-center"
            />
          </div>
          <div className="flex-1">
            <label className="block text-xs text-gray-500 mb-1">或分钟数</label>
            <Select
              options={Array.from({ length: 60 }, (_, i) => ({ 
                label: `${i.toString().padStart(2, '0')}分`, 
                value: i.toString() 
              }))}
              value={time.minute}
              onChange={(value) => setTime(prev => ({ ...prev, minute: value as string }))}
            />
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          提示：可以直接选择时间，或使用时间输入框进行精确设置
        </p>
      </div>

      {/* 月日设置 */}
      {scheduleType === 'monthly' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">每月第几天</label>
          <div className="max-w-xs">
            <Select
              options={Array.from({ length: 31 }, (_, i) => ({
                label: `${i + 1}日`,
                value: (i + 1).toString()
              }))}
              value={monthDay}
              onChange={(value) => setMonthDay(value as string)}
            />
          </div>
        </div>
      )}

      {/* 说明信息 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="text-sm font-medium text-blue-900 mb-2">当前设置</h4>
        <div className="text-sm text-blue-800 space-y-1">
          <p>• <strong>频率</strong>: {{
            'once': '单次执行',
            'daily': '每天执行',
            'weekly': '每周执行',
            'monthly': '每月执行'
          }[scheduleType]}</p>
          <p>• <strong>时间</strong>: {time.hour.padStart(2, '0')}:{time.minute.padStart(2, '0')}</p>
          {scheduleType === 'weekly' && (
            <p>• <strong>星期</strong>: {weekdays.length > 0 ? weekdayOptions.filter(d => weekdays.includes(d.value)).map(d => d.label).join(', ') : '无'}</p>
          )}
          {scheduleType === 'monthly' && (
            <p>• <strong>日期</strong>: 每月 {monthDay} 日</p>
          )}
          <p>• <strong>表达式</strong>: <code className="bg-blue-100 px-1 rounded">{generateCron()}</code></p>
        </div>
      </div>
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
        hour: '9',
        day: '*',
        month: '*',
        dayOfWeek: '1-5'
      }
    }
  })

  const [scheduleType, setScheduleType] = useState<'custom' | 'interval' | 'specific'>('specific')

  const updateCronPart = (part: keyof typeof cronParts, newValue: string) => {
    const newParts = { ...cronParts, [part]: newValue }
    setCronParts(newParts)
    onChange(buildCron(newParts))
  }

  const updateScheduleType = (type: 'custom' | 'interval' | 'specific') => {
    setScheduleType(type)
    
    // 根据类型设置默认值
    if (type === 'interval') {
      const newParts = { minute: '*/5', hour: '*', day: '*', month: '*', dayOfWeek: '*' }
      setCronParts(newParts)
      onChange(buildCron(newParts))
    } else if (type === 'specific') {
      const newParts = { minute: '0', hour: '9', day: '*', month: '*', dayOfWeek: '*' }
      setCronParts(newParts)
      onChange(buildCron(newParts))
    }
  }

  const intervalOptions = [
    { label: '每分钟', value: '*/1' },
    { label: '每2分钟', value: '*/2' },
    { label: '每5分钟', value: '*/5' },
    { label: '每10分钟', value: '*/10' },
    { label: '每15分钟', value: '*/15' },
    { label: '每20分钟', value: '*/20' },
    { label: '每30分钟', value: '*/30' }
  ]

  const hourIntervalOptions = [
    { label: '每小时', value: '*/1' },
    { label: '每2小时', value: '*/2' },
    { label: '每3小时', value: '*/3' },
    { label: '每4小时', value: '*/4' },
    { label: '每6小时', value: '*/6' },
    { label: '每8小时', value: '*/8' },
    { label: '每12小时', value: '*/12' }
  ]

  return (
    <div className="space-y-6">
      {/* 调度类型选择 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">调度类型</label>
        <div className="grid grid-cols-3 gap-3">
          <Button
            variant={scheduleType === 'interval' ? 'default' : 'outline'}
            size="sm"
            onClick={() => updateScheduleType('interval')}
            className="justify-start"
          >
            间隔执行
          </Button>
          <Button
            variant={scheduleType === 'specific' ? 'default' : 'outline'}
            size="sm"
            onClick={() => updateScheduleType('specific')}
            className="justify-start"
          >
            定时执行
          </Button>
          <Button
            variant={scheduleType === 'custom' ? 'default' : 'outline'}
            size="sm"
            onClick={() => updateScheduleType('custom')}
            className="justify-start"
          >
            自定义
          </Button>
        </div>
      </div>

      {/* 间隔执行模式 */}
      {scheduleType === 'interval' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                分钟间隔
              </label>
              <Select
                options={[
                  { label: '不限制 (*)', value: '*' },
                  ...intervalOptions
                ]}
                value={cronParts.minute}
                onChange={(value) => updateCronPart('minute', value as string)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                小时间隔
              </label>
              <Select
                options={[
                  { label: '不限制 (*)', value: '*' },
                  ...hourIntervalOptions
                ]}
                value={cronParts.hour}
                onChange={(value) => updateCronPart('hour', value as string)}
              />
            </div>
          </div>
        </div>
      )}

      {/* 定时执行模式 */}
      {scheduleType === 'specific' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                执行时间
              </label>
              <div className="grid grid-cols-2 gap-2">
                <Select
                  options={hourOptions.map(h => ({ label: `${h.value}时`, value: h.value }))}
                  value={cronParts.hour}
                  onChange={(value) => updateCronPart('hour', value as string)}
                />
                <Select
                  options={minuteOptions.map(m => ({ label: `${m.value}分`, value: m.value }))}
                  value={cronParts.minute}
                  onChange={(value) => updateCronPart('minute', value as string)}
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                执行频率
              </label>
              <Select
                options={[
                  { label: '每天', value: 'daily' },
                  { label: '工作日', value: 'weekdays' },
                  { label: '周末', value: 'weekend' },
                  { label: '每周', value: 'weekly' },
                  { label: '每月', value: 'monthly' }
                ]}
                value={
                  cronParts.dayOfWeek === '1-5' ? 'weekdays' :
                  cronParts.dayOfWeek === '0,6' ? 'weekend' :
                  cronParts.dayOfWeek !== '*' ? 'weekly' :
                  cronParts.day !== '*' ? 'monthly' : 'daily'
                }
                onChange={(value) => {
                  if (value === 'weekdays') {
                    updateCronPart('dayOfWeek', '1-5')
                    updateCronPart('day', '*')
                  } else if (value === 'weekend') {
                    updateCronPart('dayOfWeek', '0,6')
                    updateCronPart('day', '*')
                  } else if (value === 'weekly') {
                    updateCronPart('dayOfWeek', '1')
                    updateCronPart('day', '*')
                  } else if (value === 'monthly') {
                    updateCronPart('dayOfWeek', '*')
                    updateCronPart('day', '1')
                  } else {
                    updateCronPart('dayOfWeek', '*')
                    updateCronPart('day', '*')
                  }
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* 自定义模式 */}
      {scheduleType === 'custom' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              分钟
            </label>
            <Select
              options={[
                { label: '每分钟 (*)', value: '*' },
                ...minuteOptions,
                ...intervalOptions.map(opt => ({ label: opt.label, value: opt.value }))
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
                ...hourOptions,
                ...hourIntervalOptions.map(opt => ({ label: opt.label, value: opt.value }))
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
                ...dayOptions,
                { label: '每2天 (*/2)', value: '*/2' },
                { label: '每3天 (*/3)', value: '*/3' },
                { label: '每5天 (*/5)', value: '*/5' },
                { label: '每10天 (*/10)', value: '*/10' }
              ]}
              value={cronParts.day}
              onChange={(value) => updateCronPart('day', value as string)}
            />
          </div>
        </div>
      )}

      {/* 高级选项 */}
      {scheduleType === 'custom' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              月份
            </label>
            <Select
              options={[
                { label: '每月 (*)', value: '*' },
                { label: '1月', value: '1' },
                { label: '2月', value: '2' },
                { label: '3月', value: '3' },
                { label: '4月', value: '4' },
                { label: '5月', value: '5' },
                { label: '6月', value: '6' },
                { label: '7月', value: '7' },
                { label: '8月', value: '8' },
                { label: '9月', value: '9' },
                { label: '10月', value: '10' },
                { label: '11月', value: '11' },
                { label: '12月', value: '12' },
                { label: '每季度 (*/3)', value: '*/3' },
                { label: '上半年 (1-6)', value: '1-6' },
                { label: '下半年 (7-12)', value: '7-12' }
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
                ...weekdayOptions,
                { label: '工作日 (1-5)', value: '1-5' },
                { label: '周末 (0,6)', value: '0,6' },
                { label: '周一三五 (1,3,5)', value: '1,3,5' },
                { label: '周二四 (2,4)', value: '2,4' }
              ]}
              value={cronParts.dayOfWeek}
              onChange={(value) => updateCronPart('dayOfWeek', value as string)}
            />
          </div>
        </div>
      )}

      <div className="bg-gray-50 p-4 rounded-lg">
        <h4 className="text-sm font-medium text-gray-700 mb-2">提示</h4>
        <div className="text-xs text-gray-600 space-y-1">
          <p>• <strong>间隔执行</strong>：适合需要定期重复执行的任务</p>
          <p>• <strong>定时执行</strong>：适合在特定时间点执行的任务</p>
          <p>• <strong>自定义</strong>：适合需要复杂调度规则的任务</p>
          <p>• 使用 <span className="font-mono">1,3,5</span> 表示多个值</p>
          <p>• 使用 <span className="font-mono">1-5</span> 表示范围</p>
          <p>• 使用 <span className="font-mono">*/5</span> 表示每5个单位执行一次</p>
        </div>
      </div>
    </div>
  )
}