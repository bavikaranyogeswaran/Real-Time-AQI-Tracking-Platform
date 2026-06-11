import { useMemo } from 'react'
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { Trend } from '../services/api'

type MergedPoint = {
  date: string
  avg_aqi: number | null
  min_aqi: number | null
  max_aqi: number | null
  cmp_avg: number | null
  cmp_min: number | null
  cmp_max: number | null
}

interface Props {
  data: Trend[]
  title?: string
  compareData?: Trend[]
  compareLabel?: string
}

const fmtDate = (d: string) =>
  new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

export default function TrendChart({ data, title, compareData, compareLabel }: Props) {
  const hasCompare = (compareData?.length ?? 0) > 0

  const merged = useMemo<MergedPoint[]>(() => {
    const map = new Map<string, MergedPoint>()
    data.forEach(d => {
      map.set(d.date, { date: d.date, avg_aqi: d.avg_aqi, min_aqi: d.min_aqi, max_aqi: d.max_aqi, cmp_avg: null, cmp_min: null, cmp_max: null })
    })
    compareData?.forEach(d => {
      const existing = map.get(d.date)
      if (existing) {
        existing.cmp_avg = d.avg_aqi
        existing.cmp_min = d.min_aqi
        existing.cmp_max = d.max_aqi
      } else {
        map.set(d.date, { date: d.date, avg_aqi: null, min_aqi: null, max_aqi: null, cmp_avg: d.avg_aqi, cmp_min: d.min_aqi, cmp_max: d.max_aqi })
      }
    })
    return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date))
  }, [data, compareData])

  return (
    <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-6">
      {title && <p className="text-sm font-medium text-[var(--text-secondary)] mb-4">{title}</p>}
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={merged} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }} tickFormatter={fmtDate} />
          <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} domain={['auto', 'auto']} />
          <Tooltip
            labelFormatter={label => fmtDate(String(label))}
            formatter={(v, name) => {
              const labels: Record<string, string> = {
                avg_aqi: 'Avg', min_aqi: 'Min', max_aqi: 'Max',
                cmp_avg: `${compareLabel} Avg`,
                cmp_min: `${compareLabel} Min`,
                cmp_max: `${compareLabel} Max`,
              }
              return [v, labels[String(name)] ?? String(name)]
            }}
          />
          {hasCompare && <Legend iconType="line" wrapperStyle={{ fontSize: 11 }} />}
          <Line type="monotone" dataKey="avg_aqi" stroke="#3b82f6" strokeWidth={2} dot={false} name="Avg" connectNulls={false} isAnimationActive animationDuration={700} animationEasing="ease-out" />
          <Line type="monotone" dataKey="min_aqi" stroke="#22c55e" strokeWidth={1.5} dot={false} strokeDasharray="4 2" name="Min" connectNulls={false} isAnimationActive animationDuration={700} animationEasing="ease-out" />
          <Line type="monotone" dataKey="max_aqi" stroke="#ef4444" strokeWidth={1.5} dot={false} strokeDasharray="4 2" name="Max" connectNulls={false} isAnimationActive animationDuration={700} animationEasing="ease-out" />
          {hasCompare && (
            <>
              <Line type="monotone" dataKey="cmp_avg" stroke="#f59e0b" strokeWidth={2} dot={false} strokeDasharray="6 3" name={`${compareLabel} Avg`} connectNulls={false} isAnimationActive animationDuration={700} animationEasing="ease-out" />
              <Line type="monotone" dataKey="cmp_min" stroke="#10b981" strokeWidth={1.5} dot={false} strokeDasharray="2 4" name={`${compareLabel} Min`} connectNulls={false} isAnimationActive animationDuration={700} animationEasing="ease-out" />
              <Line type="monotone" dataKey="cmp_max" stroke="#f97316" strokeWidth={1.5} dot={false} strokeDasharray="2 4" name={`${compareLabel} Max`} connectNulls={false} isAnimationActive animationDuration={700} animationEasing="ease-out" />
            </>
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
