import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { Trend } from '../services/api'

interface Props {
  data: Trend[]
  title?: string
}

const fmtDate = (d: string) =>
  new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

export default function TrendChart({ data, title }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-6">
      {title && <p className="text-sm font-medium text-gray-600 mb-4">{title}</p>}
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            tickFormatter={fmtDate}
          />
          <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} domain={['auto', 'auto']} />
          <Tooltip
            labelFormatter={(label) => fmtDate(String(label))}
            formatter={(v, name) => {
              const labels: Record<string, string> = { avg_aqi: 'Avg', min_aqi: 'Min', max_aqi: 'Max' }
              return [v, labels[String(name)] ?? String(name)]
            }}
          />
          <Line type="monotone" dataKey="avg_aqi" stroke="#3b82f6" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="min_aqi" stroke="#22c55e" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
          <Line type="monotone" dataKey="max_aqi" stroke="#ef4444" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
