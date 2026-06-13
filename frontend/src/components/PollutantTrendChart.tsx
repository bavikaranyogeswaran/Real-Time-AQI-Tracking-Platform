import { useState } from 'react'
import {
  CartesianGrid, Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { PollutantTrend } from '../services/api'

interface Props {
  data: PollutantTrend[]
  city: string
}

const POLLUTANTS: { key: keyof Omit<PollutantTrend, 'date'>; label: string; color: string }[] = [
  { key: 'avg_pm25', label: 'PM2.5', color: '#ef4444' },
  { key: 'avg_pm10', label: 'PM10',  color: '#f97316' },
  { key: 'avg_co',   label: 'CO',    color: '#eab308' },
  { key: 'avg_no2',  label: 'NO₂',  color: '#22c55e' },
  { key: 'avg_so2',  label: 'SO₂',  color: '#3b82f6' },
  { key: 'avg_o3',   label: 'O₃',   color: '#a855f7' },
]

const WHO_LIMITS: Record<string, number> = {
  avg_pm25: 15,
  avg_pm10: 45,
  avg_no2:  25,
  avg_so2:  40,
  avg_o3:   100,
}

export default function PollutantTrendChart({ data, city }: Props) {
  const [hidden, setHidden] = useState<Set<string>>(new Set())

  function toggleLine(key: string) {
    setHidden(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  if (!data.length) {
    return (
      <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-6 text-center text-sm text-[var(--text-muted)]">
        No pollutant data for the selected period.
      </div>
    )
  }

  const visible = POLLUTANTS.filter(p => !hidden.has(p.key))
  const activeLimit = visible.length === 1 ? WHO_LIMITS[visible[0].key] : undefined

  return (
    <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-6">
      <p className="text-sm font-medium text-[var(--text-secondary)] mb-1">
        Pollutant Trends — {city}
      </p>
      <p className="text-xs text-[var(--text-muted)] mb-4">μg/m³ · click legend to toggle · WHO limit shown when one pollutant selected</p>

      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 4, right: 16, bottom: 0, left: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            tickFormatter={d => {
              const date = new Date(d)
              return `${date.getMonth() + 1}/${date.getDate()}`
            }}
          />
          <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} unit=" μg" />
          <Tooltip
            formatter={(value: any, name: any) => [`${value} μg/m³`, name]}
            labelFormatter={d => new Date(d).toLocaleDateString()}
          />
          <Legend
            onClick={e => toggleLine(e.dataKey as string)}
            formatter={(value, entry) => (
              <span style={{ color: hidden.has((entry as { dataKey: string }).dataKey) ? '#d1d5db' : '#374151', cursor: 'pointer' }}>
                {value}
              </span>
            )}
          />
          {activeLimit && (
            <ReferenceLine
              y={activeLimit}
              stroke="#f87171"
              strokeDasharray="4 4"
              label={{ value: 'WHO limit', fill: '#f87171', fontSize: 10, position: 'insideTopRight' }}
            />
          )}
          {POLLUTANTS.map(p => (
            <Line
              key={p.key}
              dataKey={p.key}
              name={p.label}
              stroke={p.color}
              strokeWidth={2}
              dot={false}
              hide={hidden.has(p.key)}
              connectNulls
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
