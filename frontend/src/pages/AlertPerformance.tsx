import { useEffect, useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { ChartSkeleton } from '../components/LoadingSkeleton'
import { getAlertPerformance, type AlertPerformance } from '../services/api'

const DAYS_OPTIONS = [7, 30, 90] as const

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-4 flex flex-col gap-1">
      <p className="text-xs text-[var(--text-muted)] font-medium uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-semibold text-[var(--text-primary)]">{value}</p>
    </div>
  )
}

function toTitleCase(s: string) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function fmtDate(d: any) {
  if (typeof d !== 'string') return String(d || '');
  return new Date(d + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export default function AlertPerformance() {
  const [days, setDays] = useState<7 | 30 | 90>(30)
  const [data, setData] = useState<AlertPerformance | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    getAlertPerformance(days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [days])

  const byTypeChart = (data?.by_type ?? []).map(r => ({
    name: toTitleCase(r.alert_type),
    count: r.count,
  }))

  const byCityChart = (data?.by_city ?? []).map(r => ({ city: r.city, count: r.count }))

  const dailyChart = (data?.daily_counts ?? []).map(r => ({ date: r.date, count: r.count }))

  const emptyState = data && data.total === 0 && !loading

  return (
    <div className="p-6 flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-gray-800">Alert Performance</h1>

      <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm self-start">
        {DAYS_OPTIONS.map(d => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={`px-4 py-2 transition-colors ${days === d ? 'bg-blue-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
          >
            {d}d
          </button>
        ))}
      </div>

      {loading ? (
        <>
          <div className="grid grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-4 h-20 skeleton" />
            ))}
          </div>
          <ChartSkeleton />
          <ChartSkeleton />
          <ChartSkeleton />
        </>
      ) : emptyState ? (
        <p className="text-gray-400 text-sm">No alerts fired in the last {days} days.</p>
      ) : data ? (
        <>
          <div className="grid grid-cols-3 gap-4">
            <MetricCard label="Total Alerts" value={data.total} />
            <MetricCard label="Active" value={data.active} />
            <MetricCard label="Resolved" value={data.resolved} />
          </div>

          {byTypeChart.length > 0 && (
            <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-6">
              <p className="text-sm font-medium text-[var(--text-secondary)] mb-4">Alerts by Type</p>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={byTypeChart} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#9ca3af' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" name="Alerts" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {byCityChart.length > 0 && (
            <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-6">
              <p className="text-sm font-medium text-[var(--text-secondary)] mb-4">Alerts by City (top 10)</p>
              <ResponsiveContainer width="100%" height={Math.max(180, byCityChart.length * 36)}>
                <BarChart
                  data={byCityChart}
                  layout="vertical"
                  margin={{ top: 4, right: 24, bottom: 0, left: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: '#9ca3af' }} allowDecimals={false} />
                  <YAxis type="category" dataKey="city" tick={{ fontSize: 11, fill: '#9ca3af' }} width={80} />
                  <Tooltip />
                  <Bar dataKey="count" name="Alerts" fill="#f97316" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {dailyChart.length > 0 && (
            <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-6">
              <p className="text-sm font-medium text-[var(--text-secondary)] mb-4">Daily Alert Trend</p>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={dailyChart} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10, fill: '#9ca3af' }}
                    tickFormatter={fmtDate}
                    interval="preserveStartEnd"
                  />
                  <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} allowDecimals={false} />
                  <Tooltip labelFormatter={fmtDate} />
                  <Legend formatter={() => 'Alerts fired'} />
                  <Line
                    type="monotone"
                    dataKey="count"
                    stroke="#6366f1"
                    strokeWidth={2}
                    dot={false}
                    connectNulls={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      ) : null}
    </div>
  )
}
