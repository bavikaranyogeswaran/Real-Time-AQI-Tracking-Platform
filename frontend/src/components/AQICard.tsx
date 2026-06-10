import { getAQIColor } from '../utils/aqiColors'

interface Props {
  city: string
  aqi: number
  category: string
  timestamp?: string
}

export default function AQICard({ city, aqi, category, timestamp }: Props) {
  const color = getAQIColor(aqi)
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-6 flex flex-col gap-3">
      <p className="text-sm text-gray-400 font-medium uppercase tracking-wide">{city}</p>
      <p className="text-7xl font-bold leading-none" style={{ color }}>{aqi}</p>
      <span
        className="self-start px-3 py-1 rounded-full text-xs font-semibold"
        style={{ backgroundColor: color + '18', color }}
      >
        {category}
      </span>
      {timestamp && (
        <p className="text-xs text-gray-400 mt-auto">
          Updated {new Date(timestamp).toLocaleTimeString()}
        </p>
      )}
    </div>
  )
}
