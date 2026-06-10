import { useEffect, useState } from 'react'
import { getAlerts, type Alert } from '../services/api'
import { getAQIColor } from '../utils/aqiColors'

const TYPE_LABEL: Record<string, string> = {
  unhealthy:      'Unhealthy',
  very_unhealthy: 'Very Unhealthy',
  hazardous:      'Hazardous',
  anomaly_spike:  'Anomaly Spike',
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
        status === 'active'
          ? 'bg-red-50 text-red-600'
          : 'bg-gray-100 text-gray-500'
      }`}
    >
      {status}
    </span>
  )
}

function TypeBadge({ type, aqi }: { type: string; aqi: number }) {
  const color = getAQIColor(aqi)
  return (
    <span
      className="px-2 py-0.5 rounded-full text-xs font-semibold"
      style={{ backgroundColor: color + '18', color }}
    >
      {TYPE_LABEL[type] ?? type}
    </span>
  )
}

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'active'>('active')

  useEffect(() => {
    getAlerts()
      .then(setAlerts)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const shown = filter === 'active' ? alerts.filter(a => a.status === 'active') : alerts

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-800">Alerts</h1>
        <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm">
          {(['active', 'all'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-1.5 capitalize transition-colors ${
                filter === f ? 'bg-blue-500 text-white' : 'bg-white text-gray-500 hover:bg-gray-50'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {loading && <p className="text-gray-400 text-sm">Loading…</p>}

      {!loading && shown.length === 0 && (
        <p className="text-gray-400 text-sm">No {filter === 'active' ? 'active ' : ''}alerts.</p>
      )}

      {!loading && shown.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wide">
                <th className="text-left px-4 py-3 font-medium">City</th>
                <th className="text-left px-4 py-3 font-medium">Type</th>
                <th className="text-right px-4 py-3 font-medium">AQI</th>
                <th className="text-right px-4 py-3 font-medium">Threshold</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-left px-4 py-3 font-medium">Time</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((a, i) => (
                <tr
                  key={a.alert_id}
                  className={`border-b border-gray-50 last:border-0 ${
                    i % 2 === 0 ? '' : 'bg-gray-50/40'
                  }`}
                >
                  <td className="px-4 py-3 font-medium text-gray-700">{a.location_id}</td>
                  <td className="px-4 py-3">
                    <TypeBadge type={a.alert_type} aqi={a.actual_aqi} />
                  </td>
                  <td className="px-4 py-3 text-right font-semibold" style={{ color: getAQIColor(a.actual_aqi) }}>
                    {a.actual_aqi}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-500">{a.threshold_value}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={a.status} />
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {new Date(a.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
