import { useEffect, useState } from 'react'
import { TableSkeleton } from '../components/LoadingSkeleton'
import { getAlerts, type Alert } from '../services/api'
import { getAQIColor } from '../utils/aqiColors'

const TYPE_LABEL: Record<string, string> = {
  unhealthy:      'Unhealthy',
  very_unhealthy: 'Very Unhealthy',
  hazardous:      'Hazardous',
  anomaly_spike:  'Anomaly Spike',
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
      status === 'active' ? 'bg-red-50 text-red-600' : 'bg-gray-100 text-gray-500'
    }`}>
      {status}
    </span>
  )
}

function TypeBadge({ type, aqi }: { type: string; aqi: number }) {
  const color = getAQIColor(aqi)
  return (
    <span className="px-2 py-0.5 rounded-full text-xs font-semibold" style={{ backgroundColor: color + '18', color }}>
      {TYPE_LABEL[type] ?? type}
    </span>
  )
}

function SortIndicator({ col, sortCol, sortDir }: { col: string; sortCol: string; sortDir: 'asc' | 'desc' }) {
  if (col !== sortCol) return <span className="ml-0.5 text-gray-300">⇅</span>
  return <span className="ml-0.5 text-blue-500">{sortDir === 'asc' ? '↑' : '↓'}</span>
}

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'active'>('active')
  const [search, setSearch] = useState('')
  const [sortCol, setSortCol] = useState('created_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  useEffect(() => {
    getAlerts()
      .then(setAlerts)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  function handleSort(col: string) {
    setSortDir(prev => (sortCol === col && prev === 'asc' ? 'desc' : 'asc'))
    setSortCol(col)
  }

  const activeCount = alerts.filter(a => a.status === 'active').length

  const shown = [...alerts]
    .filter(a => filter === 'all' || a.status === 'active')
    .filter(a => !search || a.location_id.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      const av = String((a as Record<string, unknown>)[sortCol] ?? '')
      const bv = String((b as Record<string, unknown>)[sortCol] ?? '')
      return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
    })

  const COLS = [
    { key: 'location_id', label: 'City',      align: 'left' },
    { key: 'alert_type',  label: 'Type',      align: 'left' },
    { key: 'actual_aqi',  label: 'AQI',       align: 'right' },
    { key: 'threshold_value', label: 'Threshold', align: 'right' },
    { key: 'status',      label: 'Status',    align: 'left' },
    { key: 'created_at',  label: 'Time',      align: 'left' },
  ]

  return (
    <div className="p-6 flex flex-col gap-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-semibold text-[var(--text-primary)]">
          Alerts
          {!loading && (
            <span className="ml-2 text-sm font-normal text-[var(--text-muted)]">
              {activeCount} active · {alerts.length} total
            </span>
          )}
        </h1>

        <div className="flex items-center gap-2">
          <input
            type="search"
            placeholder="Filter by city…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="border border-[var(--surface-border)] rounded-lg px-3 py-1.5 text-sm text-[var(--text-secondary)] bg-white focus:outline-none focus:ring-2 focus:ring-blue-200 w-44"
          />
          <div className="flex rounded-lg border border-[var(--surface-border)] overflow-hidden text-sm">
            {(['active', 'all'] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-1.5 capitalize transition-colors ${
                  filter === f ? 'bg-blue-500 text-white' : 'bg-[var(--surface-card)] text-[var(--text-secondary)] hover:bg-[var(--surface-muted)]'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading && <TableSkeleton rows={5} />}

      {!loading && shown.length === 0 && (
        <p className="text-[var(--text-muted)] text-sm">
          No {filter === 'active' ? 'active ' : ''}alerts{search ? ` matching "${search}"` : ''}.
        </p>
      )}

      {!loading && shown.length > 0 && (
        <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--surface-border)] text-xs text-[var(--text-muted)] uppercase tracking-wide">
                {COLS.map(col => (
                  <th
                    key={col.key}
                    className={`px-4 py-3 font-medium cursor-pointer select-none hover:text-[var(--text-secondary)] transition-colors ${
                      col.align === 'right' ? 'text-right' : 'text-left'
                    }`}
                    onClick={() => handleSort(col.key)}
                  >
                    {col.label}
                    <SortIndicator col={col.key} sortCol={sortCol} sortDir={sortDir} />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {shown.map((a, i) => (
                <tr
                  key={a.alert_id}
                  className={`border-b border-[var(--surface-border)] last:border-0 ${i % 2 !== 0 ? 'bg-[var(--surface-muted)]/40' : ''}`}
                >
                  <td className="px-4 py-3 font-medium text-[var(--text-primary)]">{a.location_id}</td>
                  <td className="px-4 py-3"><TypeBadge type={a.alert_type} aqi={a.actual_aqi} /></td>
                  <td className="px-4 py-3 text-right font-semibold" style={{ color: getAQIColor(a.actual_aqi) }}>{a.actual_aqi}</td>
                  <td className="px-4 py-3 text-right text-[var(--text-secondary)]">{a.threshold_value}</td>
                  <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                  <td className="px-4 py-3 text-[var(--text-muted)] text-xs">{new Date(a.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
