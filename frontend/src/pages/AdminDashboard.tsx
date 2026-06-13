import { useEffect, useState } from 'react'
import { StatSkeleton, TableSkeleton } from '../components/LoadingSkeleton'
import { getAdminSummary, type AdminSummary } from '../services/api'
import { getAQIColor } from '../utils/aqiColors'

function MetricCard({ label, value, unit }: { label: string; value: string | number; unit?: string }) {
  return (
    <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-4 flex flex-col gap-1">
      <p className="text-xs text-[var(--text-muted)] font-medium uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-semibold text-[var(--text-primary)]">
        {value}
        {unit && <span className="text-sm font-normal text-[var(--text-muted)] ml-1">{unit}</span>}
      </p>
    </div>
  )
}

function fmtTime(ts: string | null) {
  if (!ts) return '—'
  return new Date(ts).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false,
  })
}

export default function AdminDashboard() {
  const [data, setData] = useState<AdminSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getAdminSummary()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const sourceText = data
    ? Object.entries(data.readings_by_source)
        .map(([src, n]) => `${src}: ${n.toLocaleString()}`)
        .join(' · ')
    : ''

  return (
    <div className="p-6 flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-gray-800">Admin Dashboard</h1>

      {loading ? (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => <StatSkeleton key={i} />)}
          </div>
          <TableSkeleton />
        </>
      ) : data ? (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <MetricCard label="Total Readings" value={data.total_readings.toLocaleString()} />
            <MetricCard label="Active Alerts" value={data.alerts_active} />
            <MetricCard label="Alerts (7d)" value={data.alerts_total_7d} />
            <MetricCard label="Cities Monitored" value={data.cities_monitored} />
          </div>

          {sourceText && (
            <p className="text-sm text-[var(--text-muted)]">{sourceText}</p>
          )}

          <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] overflow-hidden">
            <div className="px-5 py-3 border-b border-[var(--surface-border)]">
              <p className="text-sm font-medium text-[var(--text-secondary)]">City Status</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--surface-border)] text-[var(--text-muted)] text-xs uppercase tracking-wide">
                    <th className="text-left px-5 py-3">City</th>
                    <th className="text-left px-4 py-3">Country</th>
                    <th className="text-right px-4 py-3">Latest AQI</th>
                    <th className="text-left px-4 py-3">Last Reading</th>
                    <th className="text-right px-4 py-3">7d Readings</th>
                    <th className="text-left px-4 py-3">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {data.city_status.map((row, i) => (
                    <tr
                      key={row.city}
                      className={`border-b border-[var(--surface-border)] last:border-0 ${i % 2 === 1 ? 'bg-[var(--surface-muted)]' : ''}`}
                    >
                      <td className="px-5 py-3 font-medium text-[var(--text-primary)]">{row.city}</td>
                      <td className="px-4 py-3 text-[var(--text-secondary)]">{row.country}</td>
                      <td className="px-4 py-3 text-right">
                        {row.latest_aqi != null ? (
                          <span
                            className="inline-block px-2 py-0.5 rounded text-white text-xs font-semibold"
                            style={{ background: getAQIColor(row.latest_aqi) }}
                          >
                            {row.latest_aqi}
                          </span>
                        ) : (
                          <span className="text-[var(--text-muted)]">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-[var(--text-secondary)]">{fmtTime(row.last_reading_at)}</td>
                      <td className="px-4 py-3 text-right text-[var(--text-secondary)]">{row.reading_count_7d}</td>
                      <td className="px-4 py-3 text-[var(--text-muted)] text-xs">{row.data_source ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}
    </div>
  )
}
