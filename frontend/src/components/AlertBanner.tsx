import { useState } from 'react'
import type { Alert } from '../services/api'
import { getAQIColor } from '../utils/aqiColors'

interface Props {
  alerts: Alert[]
}

const SEVERITY: Record<string, number> = {
  hazardous: 0, very_unhealthy: 1, unhealthy: 2, anomaly_spike: 3,
}

export default function AlertBanner({ alerts }: Props) {
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  const visible = [...alerts]
    .filter(a => !dismissed.has(a.alert_id))
    .sort((a, b) => (SEVERITY[a.alert_type] ?? 99) - (SEVERITY[b.alert_type] ?? 99))

  if (!visible.length) return null

  return (
    <div className="flex flex-col gap-2 px-6 py-3">
      {visible.map(alert => {
        const color = getAQIColor(alert.actual_aqi)
        return (
          <div
            key={alert.alert_id}
            className="flex items-center justify-between px-4 py-2.5 rounded-lg border text-sm"
            style={{ backgroundColor: color + '12', borderColor: color + '35', color }}
          >
            <span>
              <span className="font-semibold uppercase tracking-wide text-xs mr-2">
                {alert.alert_type.replace(/_/g, ' ')}
              </span>
              AQI {alert.actual_aqi} — threshold {alert.threshold_value}
            </span>
            <button
              onClick={() => setDismissed(p => new Set([...p, alert.alert_id]))}
              className="ml-6 text-lg leading-none opacity-50 hover:opacity-100 transition-opacity"
              aria-label="Dismiss alert"
            >
              ×
            </button>
          </div>
        )
      })}
    </div>
  )
}
