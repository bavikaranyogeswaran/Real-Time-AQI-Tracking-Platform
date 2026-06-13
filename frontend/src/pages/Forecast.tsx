import { useEffect, useState } from 'react'
import ForecastChart from '../components/ForecastChart'
import { ChartSkeleton } from '../components/LoadingSkeleton'
import {
  getLocations, getHistory, getForecast,
  type Location, type HistoryAQI, type Forecast as ForecastData,
} from '../services/api'

export default function Forecast() {
  const [locations, setLocations] = useState<Location[]>([])
  const [city, setCity] = useState('')
  const [days, setDays] = useState(1)
  const [history, setHistory] = useState<HistoryAQI[]>([])
  const [forecast, setForecast] = useState<ForecastData[]>([])
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
    Promise.all([getHistory(city, 2), getForecast(city, days)])
      .then(([h, f]) => { setHistory(h); setForecast(f) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [city, days])

  return (
    <div className="p-6 flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-gray-800">AQI Forecast</h1>

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
          {([1, 7] as const).map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-4 py-2 transition-colors ${days === d ? 'bg-blue-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
            >
              {d === 1 ? '24 h' : '7 days'}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <ChartSkeleton />
      ) : (
        <>
          {forecast.length === 0 && !loading && (
            <p className="text-gray-400 text-sm">
              No forecast available yet — the model needs more data. Check back after the next scheduled training run.
            </p>
          )}
          <ForecastChart history={history} forecast={forecast} days={days} />
        </>
      )}
    </div>
  )
}
