import {
  CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { Forecast, HistoryAQI } from '../services/api'

interface Props {
  history: HistoryAQI[]
  forecast: Forecast[]
}

interface Point {
  time: string
  actual?: number
  predicted?: number
}

const fmtTime = (t: string) =>
  new Date(t).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false })

export default function ForecastChart({ history, forecast }: Props) {
  const last24 = [...history].sort((a, b) => a.timestamp.localeCompare(b.timestamp)).slice(-24)

  const data: Point[] = [
    ...last24.map(r => ({ time: r.timestamp, actual: r.aqi })),
    ...forecast.map(f => ({ time: f.forecast_for, predicted: Math.round(f.predicted_aqi) })),
  ]

  return (
    <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-6">
      <p className="text-sm font-medium text-[var(--text-secondary)] mb-4">AQI forecast — next 24 hours</p>
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 10, fill: '#9ca3af' }}
            tickFormatter={fmtTime}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} domain={['auto', 'auto']} />
          <Tooltip labelFormatter={(label) => fmtTime(String(label))} />
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
