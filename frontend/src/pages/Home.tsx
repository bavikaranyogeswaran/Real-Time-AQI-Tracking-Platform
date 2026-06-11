import { useEffect, useState } from 'react'
import AlertBanner from '../components/AlertBanner'
import AQIMap from '../components/AQIMap'
import { getAlerts, getCityComparison, type Alert, type CityComparison } from '../services/api'
import { getAQIColor } from '../utils/aqiColors'

export default function Home() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [cities, setCities] = useState<CityComparison[]>([])

  useEffect(() => {
    getAlerts()
      .then(data => setAlerts(data.filter(a => a.status === 'active')))
      .catch(console.error)
    getCityComparison()
      .then(setCities)
      .catch(console.error)
  }, [])

  const worstCity = cities.reduce<CityComparison | null>(
    (max, c) => (c.latest_aqi > (max?.latest_aqi ?? 0) ? c : max),
    null,
  )
  const unhealthyCount = cities.filter(c => c.latest_aqi > 150).length

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <AlertBanner alerts={alerts} />

      {cities.length > 0 && (
        <div className="flex items-center gap-6 px-6 py-2.5 bg-white border-b border-[var(--surface-border)] text-sm shrink-0">
          <span className="text-[var(--text-muted)]">
            <span className="font-semibold text-[var(--text-primary)]">{cities.length}</span> cities monitored
          </span>
          {worstCity && (
            <span className="flex items-center gap-1.5">
              <span className="text-[var(--text-muted)]">Worst:</span>
              <span className="font-semibold" style={{ color: getAQIColor(worstCity.latest_aqi) }}>
                {worstCity.city} {worstCity.latest_aqi}
              </span>
            </span>
          )}
          {unhealthyCount > 0 && (
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-red-500 shrink-0" />
              <span className="text-red-500 font-medium">{unhealthyCount} unhealthy+</span>
            </span>
          )}
        </div>
      )}

      <div className="flex-1 min-h-0">
        <AQIMap cities={cities} />
      </div>
    </div>
  )
}
