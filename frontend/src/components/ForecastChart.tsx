import {
  CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { Forecast, HistoryAQI } from '../services/api'

interface Props {
  history: HistoryAQI[]
  forecast: Forecast[]
  days?: number
}

interface Point {
  time: string
  actual?: number
  predicted?: number
}

const fmtHour = (t: string) =>
  new Date(t).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false })

const fmtDay = (t: string) =>
  new Date(t).toLocaleString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })

export default function ForecastChart({ history, forecast, days = 1 }: Props) {
  const historyHours = days > 1 ? 48 : 24
  const last = [...history].sort((a, b) => a.timestamp.localeCompare(b.timestamp)).slice(-historyHours)

  const data: Point[] = [
    ...last.map(r => ({ time: r.timestamp, actual: r.aqi })),
    ...forecast.map(f => ({ time: f.forecast_for, predicted: Math.round(f.predicted_aqi) })),
  ]

  const fmtTick = days > 1 ? fmtDay : fmtHour
  const tickInterval = days > 1 ? 23 : ('preserveStartEnd' as const)
  const title = days === 1 ? 'AQI forecast — next 24 hours' : `AQI forecast — next ${days} days`

  return (
    <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-6">
      <p className="text-sm font-medium text-[var(--text-secondary)] mb-4">{title}</p>
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 10, fill: '#9ca3af' }}
            tickFormatter={fmtTick}
            interval={tickInterval}
          />
          <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} domain={['auto', 'auto']} />
          <Tooltip labelFormatter={(label) => fmtHour(String(label))} />
          <Legend
            formatter={(v: string) => v === 'actual' ? 'Actual AQI' : 'Predicted AQI'}
          />
          <Line
            type="monotone"
            dataKey="actual"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="predicted"
            stroke="#f97316"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
            connectNulls={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
