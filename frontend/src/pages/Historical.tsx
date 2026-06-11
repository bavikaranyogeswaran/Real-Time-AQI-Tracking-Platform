import { useEffect, useState } from 'react'
import { ChartSkeleton, StatSkeleton } from '../components/LoadingSkeleton'
import TrendChart from '../components/TrendChart'
import { getLocations, getTrends, type Location, type Trend } from '../services/api'

const PERIODS = [
  { label: 'Daily',   value: 'daily' },
  { label: 'Weekly',  value: 'weekly' },
  { label: 'Monthly', value: 'monthly' },
]

export default function Historical() {
  const [locations, setLocations] = useState<Location[]>([])
  const [city, setCity] = useState('')
  const [compareCity, setCompareCity] = useState('')
  const [period, setPeriod] = useState('weekly')
  const [trends, setTrends] = useState<Trend[]>([])
  const [compareTrends, setCompareTrends] = useState<Trend[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getLocations().then(locs => {
      setLocations(locs)
      if (locs.length) setCity(locs[0].city)
    }).catch(console.error)
  }, [])

  useEffect(() => {
    if (!city) return
    setLoading(true)
    getTrends(city, period)
      .then(setTrends)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [city, period])

  useEffect(() => {
    if (!compareCity) { setCompareTrends([]); return }
    getTrends(compareCity, period)
      .then(setCompareTrends)
      .catch(console.error)
  }, [compareCity, period])

  const avgAqi = trends.length ? Math.round(trends.reduce((s, t) => s + t.avg_aqi, 0) / trends.length) : null
  const minAqi = trends.length ? Math.min(...trends.map(t => t.min_aqi)) : null
  const maxAqi = trends.length ? Math.max(...trends.map(t => t.max_aqi)) : null

  const selectClass = 'border border-[var(--surface-border)] rounded-lg px-3 py-2 text-sm text-[var(--text-secondary)] bg-white focus:outline-none focus:ring-2 focus:ring-blue-200'

  return (
    <div className="p-6 flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-[var(--text-primary)]">Historical Data</h1>

      <div className="flex flex-wrap items-center gap-3">
        <select value={city} onChange={e => setCity(e.target.value)} className={selectClass}>
          {locations.map(l => <option key={l.location_id} value={l.city}>{l.city}</option>)}
        </select>

        <span className="text-sm text-[var(--text-muted)]">vs</span>

        <select value={compareCity} onChange={e => setCompareCity(e.target.value)} className={selectClass}>
          <option value="">None</option>
          {locations.filter(l => l.city !== city).map(l => (
            <option key={l.location_id} value={l.city}>{l.city}</option>
          ))}
        </select>

        <div className="flex rounded-lg border border-[var(--surface-border)] overflow-hidden">
          {PERIODS.map(p => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-4 py-2 text-sm transition-colors ${
                period === p.value ? 'bg-blue-500 text-white' : 'bg-white text-[var(--text-secondary)] hover:bg-[var(--surface-muted)]'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <>
          <div className="grid grid-cols-3 gap-4">
            <StatSkeleton /><StatSkeleton /><StatSkeleton />
          </div>
          <ChartSkeleton />
        </>
      ) : (
        <>
          {trends.length > 0 && (
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: 'Avg AQI', value: avgAqi },
                { label: 'Min AQI', value: minAqi },
                { label: 'Max AQI', value: maxAqi },
              ].map(({ label, value }) => (
                <div key={label} className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-4 text-center">
                  <p className="text-xs text-[var(--text-muted)] uppercase tracking-wide mb-1">{label}</p>
                  <p className="text-3xl font-bold text-[var(--text-primary)]">{value ?? '—'}</p>
                </div>
              ))}
            </div>
          )}
          <TrendChart
            data={trends}
            title={`${city} — ${period} trend`}
            compareData={compareTrends.length ? compareTrends : undefined}
            compareLabel={compareCity || undefined}
          />
        </>
      )}
    </div>
  )
}
