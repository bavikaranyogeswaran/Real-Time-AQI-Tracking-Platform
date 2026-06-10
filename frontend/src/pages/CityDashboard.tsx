import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import AQICard from '../components/AQICard'
import PollutantChart from '../components/PollutantChart'
import TrendChart from '../components/TrendChart'
import {
  getCurrentAQI, getPollutants, getTrends,
  type CurrentAQI, type Pollutants, type Trend,
} from '../services/api'

export default function CityDashboard() {
  const { city } = useParams<{ city: string }>()
  const [current, setCurrent] = useState<CurrentAQI | null>(null)
  const [pollutants, setPollutants] = useState<Pollutants | null>(null)
  const [trends, setTrends] = useState<Trend[]>([])
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!city) return
    setError(false)
    Promise.all([
      getCurrentAQI(city),
      getPollutants(city),
      getTrends(city, 'weekly'),
    ])
      .then(([cur, pol, tr]) => {
        setCurrent(cur)
        setPollutants(pol)
        setTrends(tr)
      })
      .catch(() => setError(true))
  }, [city])

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-3 text-gray-400">
        <p className="text-lg">No data found for <strong className="text-gray-700">{city}</strong></p>
        <Link to="/" className="text-sm text-blue-500 hover:underline">← Back to map</Link>
      </div>
    )
  }

  if (!current || !pollutants) {
    return (
      <div className="flex items-center justify-center flex-1 text-gray-400">
        Loading…
      </div>
    )
  }

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <Link to="/" className="text-sm text-gray-400 hover:text-gray-700">← Map</Link>
        <h1 className="text-xl font-semibold text-gray-800">{city}</h1>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <AQICard
          city={city ?? ''}
          aqi={current.aqi}
          category={current.category}
          timestamp={current.timestamp}
        />
      </div>

      <PollutantChart pollutants={pollutants} />
      <TrendChart data={trends} title="7-day AQI trend" />
    </div>
  )
}
