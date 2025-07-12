'use client'

import { useState, useEffect } from 'react'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

type Frequency = 'daily' | 'weekly' | 'monthly'

interface ScheduleBuilderProps {
  value?: string
  onChange: (value: string) => void
}

export function ScheduleBuilder({
  onChange,
  value = '0 9 * * *',
}: ScheduleBuilderProps) {
  const [frequency, setFrequency] = useState<Frequency>('daily')
  const [dayOfWeek, setDayOfWeek] = useState('1') // 1 = Monday
  const [dayOfMonth, setDayOfMonth] = useState('1')
  const [hour, setHour] = useState('9')
  const [minute, setMinute] = useState('0')

  // Parse incoming cron expression to set initial state
  useEffect(() => {
    if (value) {
      const parts = value.split(' ')
      if (parts.length === 5) {
        const [m, h, dom, , dow] = parts
        setMinute(m)
        setHour(h)

        // Determine frequency based on the cron pattern
        if (dom !== '*' && dow === '*') {
          setFrequency('monthly')
          setDayOfMonth(dom)
        } else if (dom === '*' && dow !== '*') {
          setFrequency('weekly')
          setDayOfWeek(dow)
        } else {
          setFrequency('daily')
        }
      }
    }
  }, [value])

  useEffect(() => {
    let cron = ''
    const m = minute
    const h = hour

    switch (frequency) {
      case 'daily':
        cron = `${m} ${h} * * *`
        break
      case 'weekly':
        cron = `${m} ${h} * * ${dayOfWeek}`
        break
      case 'monthly':
        cron = `${m} ${h} ${dayOfMonth} * *`
        break
      default:
        cron = '0 9 * * *' // Default to 9 AM daily
    }
    onChange(cron)
  }, [frequency, dayOfWeek, dayOfMonth, hour, minute, onChange])

  const hours = Array.from({ length: 24 }, (_, i) => String(i))
  const minutes = ['0', '15', '30', '45']
  const daysOfMonth = Array.from({ length: 31 }, (_, i) => String(i + 1))
  const daysOfWeek = [
    { value: '1', label: 'Monday' },
    { value: '2', label: 'Tuesday' },
    { value: '3', label: 'Wednesday' },
    { value: '4', label: 'Thursday' },
    { value: '5', label: 'Friday' },
    { value: '6', label: 'Saturday' },
    { value: '0', label: 'Sunday' },
  ]

  return (
    <div className="p-4 border rounded-lg space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Frequency */}
        <div className="space-y-2">
          <Label htmlFor="frequency">Frequency</Label>
          <Select
            value={frequency}
            onValueChange={(v: Frequency) => setFrequency(v)}
          >
            <SelectTrigger id="frequency">
              <SelectValue placeholder="Select frequency" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="daily">Daily</SelectItem>
              <SelectItem value="weekly">Weekly</SelectItem>
              <SelectItem value="monthly">Monthly</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Conditional Day Picker */}
        <div className="space-y-2">
          {frequency === 'weekly' && (
            <>
              <Label htmlFor="day-of-week">Day of Week</Label>
              <Select value={dayOfWeek} onValueChange={setDayOfWeek}>
                <SelectTrigger id="day-of-week">
                  <SelectValue placeholder="Select day" />
                </SelectTrigger>
                <SelectContent>
                  {daysOfWeek.map((d) => (
                    <SelectItem key={d.value} value={d.value}>
                      {d.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          )}
          {frequency === 'monthly' && (
            <>
              <Label htmlFor="day-of-month">Day of Month</Label>
              <Select value={dayOfMonth} onValueChange={setDayOfMonth}>
                <SelectTrigger id="day-of-month">
                  <SelectValue placeholder="Select day" />
                </SelectTrigger>
                <SelectContent>
                  {daysOfMonth.map((d) => (
                    <SelectItem key={d} value={d}>
                      {d}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          )}
        </div>
      </div>

      {/* Time Picker */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="hour">Hour</Label>
          <Select value={hour} onValueChange={setHour}>
            <SelectTrigger id="hour">
              <SelectValue placeholder="Hour" />
            </SelectTrigger>
            <SelectContent>
              {hours.map((h) => (
                <SelectItem key={h} value={h}>
                  {h.padStart(2, '0')}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="minute">Minute</Label>
          <Select value={minute} onValueChange={setMinute}>
            <SelectTrigger id="minute">
              <SelectValue placeholder="Minute" />
            </SelectTrigger>
            <SelectContent>
              {minutes.map((m) => (
                <SelectItem key={m} value={m}>
                  {m.padStart(2, '0')}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  )
}
