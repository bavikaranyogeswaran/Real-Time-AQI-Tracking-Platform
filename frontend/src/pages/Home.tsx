import { useEffect, useState } from 'react'
import AQIMap from '../components/AQIMap'
import AlertBanner from '../components/AlertBanner'
import { getAlerts, type Alert } from '../services/api'

export default function Home() {
  const [alerts, setAlerts] = useState<Alert[]>([])

  useEffect(() => {
    getAlerts().then(data => setAlerts(data.filter(a => a.status === 'active'))).catch(console.error)
  }, [])

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <AlertBanner alerts={alerts} />
      <div className="flex-1 min-h-0">
        <AQIMap />
      </div>
    </div>
  )
}
