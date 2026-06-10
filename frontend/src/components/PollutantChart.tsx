import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { Pollutants } from '../services/api'

interface Props {
  pollutants: Pollutants
}

const COLORS: Record<string, string> = {
  pm25: '#ef4444',
  pm10: '#f97316',
  co:   '#eab308',
  no2:  '#22c55e',
  so2:  '#3b82f6',
  o3:   '#a855f7',
}

const LABELS: Record<string, string> = {
  pm25: 'PM2.5', pm10: 'PM10', co: 'CO', no2: 'NO₂', so2: 'SO₂', o3: 'O₃',
}

export default function PollutantChart({ pollutants }: Props) {
  const data = (Object.keys(COLORS) as (keyof Pollutants)[]).map(key => ({
    key,
    name: LABELS[key],
    value: +(pollutants[key] ?? 0).toFixed(2),
  }))

  return (
    <div className="bg-white rounded-xl border border-gray-100 p-6">
      <p className="text-sm font-medium text-gray-600 mb-4">Pollutants (μg/m³)</p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#9ca3af' }} />
          <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} />
          <Tooltip formatter={(v) => [`${v as number} μg/m³`]} />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map(entry => (
              <Cell key={entry.key} fill={COLORS[entry.key]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
