import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getCityRanking, type CityRanking } from '../services/api'
import { getAQIColor } from '../utils/aqiColors'

const PERIODS = [
  { label: '7 days',  value: 7 },
  { label: '30 days', value: 30 },
  { label: '90 days', value: 90 },
]

type SortKey = 'avg_aqi' | 'max_aqi' | 'unhealthy_days'

const SORT_OPTIONS: { label: string; key: SortKey }[] = [
  { label: 'Avg AQI',        key: 'avg_aqi' },
  { label: 'Max AQI',        key: 'max_aqi' },
  { label: 'Unhealthy Days', key: 'unhealthy_days' },
]

function TrendBadge({ trend, prev, curr }: { trend: string; prev: number | null; curr: number }) {
  if (trend === 'improving') {
    const delta = prev !== null ? (prev - curr).toFixed(1) : ''
    return (
      <span className="flex items-center gap-1 text-green-600 text-xs font-medium">
        <span>↓</span>
        {delta && <span>−{delta}</span>}
      </span>
    )
  }
  if (trend === 'worsening') {
    const delta = prev !== null ? (curr - prev).toFixed(1) : ''
    return (
      <span className="flex items-center gap-1 text-red-500 text-xs font-medium">
        <span>↑</span>
        {delta && <span>+{delta}</span>}
      </span>
    )
  }
  return <span className="text-[var(--text-muted)] text-xs">→ stable</span>
}

export default function CityRanking() {
  const [days, setDays] = useState(7)
  const [sortKey, setSortKey] = useState<SortKey>('avg_aqi')
  const [data, setData] = useState<CityRanking[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    getCityRanking(days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [days])

  const sorted = [...data].sort((a, b) => b[sortKey] - a[sortKey])

  const btnBase = 'px-3 py-1.5 text-sm rounded-lg border transition-colors'
  const btnActive = 'bg-blue-500 text-white border-blue-500'
  const btnInactive = 'bg-white border-[var(--surface-border)] text-[var(--text-secondary)] hover:bg-[var(--surface-muted)]'

  return (
    <div className="p-6 flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-[var(--text-primary)]">City Ranking</h1>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex rounded-lg border border-[var(--surface-border)] overflow-hidden">
          {PERIODS.map(p => (
            <button
              key={p.value}
              onClick={() => setDays(p.value)}
              className={`px-4 py-2 text-sm transition-colors ${
                days === p.value ? 'bg-blue-500 text-white' : 'bg-white text-[var(--text-secondary)] hover:bg-[var(--surface-muted)]'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        <span className="text-xs text-[var(--text-muted)]">Sort by:</span>
        {SORT_OPTIONS.map(o => (
          <button
            key={o.key}
            onClick={() => setSortKey(o.key)}
            className={`${btnBase} ${sortKey === o.key ? btnActive : btnInactive}`}
          >
            {o.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton h-14 rounded-xl" />
          ))}
        </div>
      ) : sorted.length === 0 ? (
        <div className="text-center text-sm text-[var(--text-muted)] py-12">No data for selected period.</div>
      ) : (
        <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--surface-border)]">
                <th className="px-4 py-3 text-left text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide w-10">#</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">City</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">Avg AQI</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">Max AQI</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">Unhealthy Days</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">vs Last Period</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((city, i) => {
                const color = getAQIColor(city.avg_aqi)
                return (
                  <tr
                    key={city.city}
                    className="border-b border-[var(--surface-border)] last:border-0 hover:bg-[var(--surface-muted)] transition-colors"
                  >
                    <td className="px-4 py-3 text-[var(--text-muted)] font-mono text-xs">{i + 1}</td>
                    <td className="px-4 py-3">
                      <Link
                        to={`/city/${city.city}`}
                        className="font-medium text-[var(--text-primary)] hover:text-blue-600 transition-colors"
                      >
                        {city.city}
                      </Link>
                      <p className="text-xs text-[var(--text-muted)]">{city.country}</p>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span
                        className="inline-block px-2.5 py-1 rounded-full text-xs font-bold"
                        style={{ background: color + '18', color }}
                      >
                        {city.avg_aqi}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-[var(--text-secondary)]">{city.max_aqi}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={`text-xs font-medium ${city.unhealthy_days > 0 ? 'text-red-500' : 'text-[var(--text-muted)]'}`}>
                        {city.unhealthy_days} / {days}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {city.prev_avg_aqi !== null ? (
                        <div className="flex flex-col items-end gap-0.5">
                          <TrendBadge trend={city.trend} prev={city.prev_avg_aqi} curr={city.avg_aqi} />
                          <span className="text-[10px] text-[var(--text-muted)]">prev {city.prev_avg_aqi}</span>
                        </div>
                      ) : (
                        <span className="text-xs text-[var(--text-muted)]">no prior data</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
