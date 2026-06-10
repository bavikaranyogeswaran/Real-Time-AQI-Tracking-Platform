import { useEffect, useState } from 'react'
import ForecastChart from '../components/ForecastChart'
import {
  getLocations, getHistory, getForecast,
  type Location, type HistoryAQI, type Forecast as ForecastData,
} from '../services/api'

export default function Forecast() {
  const [locations, setLocations] = useState<Location[]>([])
  const [city, setCity] = useState('')
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
    Promise.all([getHistory(city, 2), getForecast(city)])
      .then(([h, f]) => { setHistory(h); setForecast(f) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [city])

  return (
    <div className="p-6 flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-gray-800">AQI Forecast</h1>

      <select
        value={city}
        onChange={e => setCity(e.target.value)}
        className="self-start border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-300"
      >
        {locations.map(l => (
          <option key={l.location_id} value={l.city}>{l.city}</option>
        ))}
      </select>

      {loading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : (
        <>
          {forecast.length === 0 && !loading && (
            <p className="text-gray-400 text-sm">
              No forecast available yet — the model needs more data. Check back after the next scheduled training run.
            </p>
          )}
          <ForecastChart history={history} forecast={forecast} />
        </>
      )}
    </div>
  )
}
