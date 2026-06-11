import { useState } from 'react'
import { Link } from 'react-router-dom'
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

  const sorted = [...alerts]
    .filter(a => !dismissed.has(a.alert_id))
    .sort((a, b) => (SEVERITY[a.alert_type] ?? 99) - (SEVERITY[b.alert_type] ?? 99))

  const visible = sorted.slice(0, 2)
  const hidden = sorted.length - visible.length

  if (!visible.length) return null

  return (
    <div className="flex flex-col gap-1.5 px-6 py-3 bg-[var(--surface-card)] border-b border-[var(--surface-border)] shrink-0">
      {visible.map(alert => {
        const color = getAQIColor(alert.actual_aqi)
        return (
          <div key={alert.alert_id} className="flex items-stretch overflow-hidden rounded-lg text-sm">
            <div className="w-1 shrink-0" style={{ background: color }} />
            <div
              className="flex flex-1 items-center justify-between px-3 py-2"
              style={{ backgroundColor: color + '0d' }}
            >
              <span>
                <span className="font-semibold uppercase tracking-wide text-xs mr-2" style={{ color }}>
                  {alert.alert_type.replace(/_/g, ' ')}
                </span>
                <span className="text-[var(--text-secondary)] text-xs">
                  {alert.location_id} · AQI {alert.actual_aqi}
                </span>
              </span>
              <button
                onClick={() => setDismissed(p => new Set([...p, alert.alert_id]))}
                className="ml-4 text-lg leading-none opacity-40 hover:opacity-80 transition-opacity shrink-0"
                aria-label="Dismiss alert"
                style={{ color }}
              >
                ×
              </button>
            </div>
          </div>
        )
      })}
      {hidden > 0 && (
        <Link
          to="/alerts"
          className="self-end text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
        >
          +{hidden} more alerts →
        </Link>
      )}
    </div>
  )
}
