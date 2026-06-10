import { useEffect, useState } from 'react'
import TrendChart from '../components/TrendChart'
import { getLocations, getTrends, type Location, type Trend } from '../services/api'

const PERIODS = [
  { label: 'Daily', value: 'daily' },
  { label: 'Weekly', value: 'weekly' },
  { label: 'Monthly', value: 'monthly' },
]

export default function Historical() {
  const [locations, setLocations] = useState<Location[]>([])
  const [city, setCity] = useState('')
  const [period, setPeriod] = useState('weekly')
  const [trends, setTrends] = useState<Trend[]>([])
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

  const avgAqi = trends.length
    ? Math.round(trends.reduce((s, t) => s + t.avg_aqi, 0) / trends.length)
    : null
  const minAqi = trends.length ? Math.min(...trends.map(t => t.min_aqi)) : null
  const maxAqi = trends.length ? Math.max(...trends.map(t => t.max_aqi)) : null

  return (
    <div className="p-6 flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-gray-800">Historical Data</h1>

      <div className="flex flex-wrap gap-3">
        <select
          value={city}
          onChange={e => setCity(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-300"
        >
          {locations.map(l => (
            <option key={l.location_id} value={l.city}>{l.city}</option>
          ))}
        </select>

        <div className="flex rounded-lg border border-gray-200 overflow-hidden">
          {PERIODS.map(p => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-4 py-2 text-sm transition-colors ${
                period === p.value
                  ? 'bg-blue-500 text-white'
                  : 'bg-white text-gray-500 hover:bg-gray-50'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : (
        <>
          {trends.length > 0 && (
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: 'Avg AQI', value: avgAqi },
                { label: 'Min AQI', value: minAqi },
                { label: 'Max AQI', value: maxAqi },
              ].map(({ label, value }) => (
                <div key={label} className="bg-white rounded-xl border border-gray-100 p-4 text-center">
                  <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">{label}</p>
                  <p className="text-3xl font-bold text-gray-800">{value ?? '—'}</p>
                </div>
              ))}
            </div>
          )}
          <TrendChart data={trends} title={`${city} — ${period} trend`} />
        </>
      )}
    </div>
  )
}
