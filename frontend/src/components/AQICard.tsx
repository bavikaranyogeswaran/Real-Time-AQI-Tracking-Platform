import { useEffect, useState } from 'react'
import { getAQIColor } from '../utils/aqiColors'

interface Props {
  city: string
  aqi: number
  category: string
  timestamp?: string
}

function useCountUp(target: number, duration = 900) {
  const [value, setValue] = useState(0)
  useEffect(() => {
    const startTime = performance.now()
    let raf: number
    function step(now: number) {
      const progress = Math.min((now - startTime) / duration, 1)
      // ease-out cubic: fast start, smooth landing
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(Math.round(eased * target))
      if (progress < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [target, duration])
  return value
}

function AQIGauge({ aqi, color }: { aqi: number; color: string }) {
  const animated = useCountUp(aqi)
  const pct = Math.min(animated / 500, 1)
  const cx = 70, cy = 65, R = 56

  const ex = (cx - R * Math.cos(pct * Math.PI)).toFixed(2)
  const ey = (cy - R * Math.sin(pct * Math.PI)).toFixed(2)

  const bgPath = `M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${cx + R} ${cy}`
  const fillPath = pct > 0 ? `M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${ex} ${ey}` : ''

  return (
    <svg viewBox="0 0 140 85" className="w-full max-w-[200px] mx-auto">
      {/* Track adapts to dark mode via CSS var */}
      <path d={bgPath} fill="none" stroke="var(--surface-muted)" strokeWidth={12} strokeLinecap="round" />
      {pct > 0 && (
        <path d={fillPath} fill="none" stroke={color} strokeWidth={12} strokeLinecap="round" />
      )}
      <text
        x={cx} y={cy + 8}
        textAnchor="middle"
        fontSize={22} fontWeight="bold"
        fill={color}
        fontFamily="system-ui, sans-serif"
      >
        {animated}
      </text>
    </svg>
  )
}

export default function AQICard({ city, aqi, category, timestamp }: Props) {
  const color = getAQIColor(aqi)
  return (
    <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-5 flex flex-col gap-2">
      <p className="text-xs text-[var(--text-muted)] font-medium uppercase tracking-wider">{city}</p>
      <AQIGauge aqi={aqi} color={color} />
      <div className="flex flex-col items-center gap-1.5">
        <span
          className="px-3 py-1 rounded-full text-xs font-semibold"
          style={{ backgroundColor: color + '18', color }}
        >
          {category}
        </span>
        {timestamp && (
          <p className="text-[11px] text-[var(--text-muted)]">
            Updated {new Date(timestamp).toLocaleTimeString()}
          </p>
        )}
      </div>
    </div>
  )
}
