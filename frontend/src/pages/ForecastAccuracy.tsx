import { useEffect, useState } from 'react'
import {
  CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { ChartSkeleton } from '../components/LoadingSkeleton'
import {
  getForecastAccuracy, getLocations,
  type ForecastAccuracy, type Location,
} from '../services/api'

const DAYS_OPTIONS = [7, 14, 30] as const

const fmtTime = (t: string) =>
  new Date(t).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false })

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

export default function ForecastAccuracy() {
  const [locations, setLocations] = useState<Location[]>([])
  const [city, setCity] = useState('')
  const [days, setDays] = useState<7 | 14 | 30>(7)
  const [data, setData] = useState<ForecastAccuracy | null>(null)
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
    getForecastAccuracy(city, days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [city, days])

  const chartData = (data?.rows ?? []).map(r => ({
    time: r.forecast_for,
    predicted: Math.round(r.predicted_aqi),
    actual: r.actual_aqi,
  }))

  return (
    <div className="p-6 flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-gray-800">Forecast Accuracy</h1>

      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={city}
          onChange={e => setCity(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-300"
        >
          {locations.map(l => (
            <option key={l.location_id} value={l.city}>{l.city}</option>
          ))}
        </select>

        <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm">
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
      </div>

      {loading ? (
        <ChartSkeleton />
      ) : data && data.sample_count === 0 ? (
        <p className="text-gray-400 text-sm">
          No accuracy data yet — past predictions accumulate over time. Check back after the model has been running for at least one training cycle.
        </p>
      ) : data ? (
        <>
          <div className="grid grid-cols-3 gap-4">
            <MetricCard label="MAE" value={data.mae} unit="AQI" />
            <MetricCard label="RMSE" value={data.rmse} unit="AQI" />
            <MetricCard label="Samples" value={data.sample_count} />
          </div>

          <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-6">
            <p className="text-sm font-medium text-[var(--text-secondary)] mb-4">Predicted vs Actual AQI</p>
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
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
                <Line type="monotone" dataKey="actual" stroke="#3b82f6" strokeWidth={2} dot={false} connectNulls={false} />
                <Line type="monotone" dataKey="predicted" stroke="#f97316" strokeWidth={2} strokeDasharray="6 3" dot={false} connectNulls={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </>
      ) : null}
    </div>
  )
}
