import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import AQICard from '../components/AQICard'
import { CardSkeleton, ChartSkeleton } from '../components/LoadingSkeleton'
import PollutantChart from '../components/PollutantChart'
import TrendChart from '../components/TrendChart'
import {
  getCurrentAQI, getPollutants, getTrends, downloadCityPdf,
  type CurrentAQI, type Pollutants, type Trend,
} from '../services/api'
import { getAQIColor } from '../utils/aqiColors'

const HEALTH_ADVICE: Record<string, { general: string; sensitive: string }> = {
  'Good': {
    general: 'Great day for outdoor activities',
    sensitive: 'No precautions needed',
  },
  'Moderate': {
    general: 'Acceptable for most people outdoors',
    sensitive: 'Unusually sensitive individuals may want to limit prolonged outdoor exertion',
  },
  'Unhealthy for Sensitive Groups': {
    general: 'Reduce intensity of long outdoor activities',
    sensitive: 'People with heart/lung disease, elderly, and children should limit outdoor time',
  },
  'Unhealthy': {
    general: 'Limit prolonged outdoor exertion',
    sensitive: 'Sensitive groups should avoid outdoor exertion entirely',
  },
  'Very Unhealthy': {
    general: 'Avoid prolonged outdoor exertion',
    sensitive: 'Sensitive groups should stay indoors and keep activity low',
  },
  'Hazardous': {
    general: 'Avoid all outdoor physical activity',
    sensitive: 'Remain indoors with windows closed',
  },
}

function HealthAdvice({ category, color }: { category: string; color: string }) {
  const advice = HEALTH_ADVICE[category]
  if (!advice) return null
  return (
    <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-5">
      <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-3">Health Recommendations</h2>
      <div className="flex flex-col gap-3">
        {[
          { label: 'General public', text: advice.general },
          { label: 'Sensitive groups', text: advice.sensitive },
        ].map(({ label, text }) => (
          <div key={label} className="flex gap-3">
            <div className="w-1 rounded-full self-stretch shrink-0" style={{ background: color }} />
            <div>
              <p className="text-xs font-medium text-[var(--text-muted)] mb-0.5">{label}</p>
              <p className="text-sm text-[var(--text-secondary)]">{text}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function CityDashboard() {
  const { city } = useParams<{ city: string }>()
  const [current, setCurrent] = useState<CurrentAQI | null>(null)
  const [pollutants, setPollutants] = useState<Pollutants | null>(null)
  const [trends, setTrends] = useState<Trend[]>([])
  const [error, setError] = useState(false)
  const [retryKey, setRetryKey] = useState(0)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    if (!city) return
    setError(false)
    setCurrent(null)
    setPollutants(null)
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
  }, [city, retryKey])

  function retry() {
    setError(false)
    setRetryKey(k => k + 1)
  }

  async function handleDownloadReport() {
    if (!city) return
    setDownloading(true)
    try {
      await downloadCityPdf(city, 7)
    } catch {
      // silently fail — user still sees the page
    } finally {
      setDownloading(false)
    }
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-5 p-6 text-center">
        <svg className="w-14 h-14 text-[var(--surface-border)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div>
          <p className="text-base font-semibold text-[var(--text-primary)]">No data for {city}</p>
          <p className="text-sm text-[var(--text-muted)] mt-1 max-w-xs mx-auto">
            This city may not be in our network, or the server is temporarily unavailable.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={retry}
            className="px-4 py-2 rounded-lg bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 transition-colors"
          >
            Retry
          </button>
          <Link
            to="/"
            className="px-4 py-2 rounded-lg border border-[var(--surface-border)] text-sm text-[var(--text-secondary)] hover:bg-[var(--surface-muted)] transition-colors"
          >
            Back to map
          </Link>
        </div>
      </div>
    )
  }

  if (!current || !pollutants) {
    return (
      <div className="p-6 flex flex-col gap-6">
        <div className="skeleton h-5 w-32 rounded" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <CardSkeleton />
        </div>
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
    )
  }

  const color = getAQIColor(current.aqi)

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <Link to="/" className="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)]">← Map</Link>
        <h1 className="text-xl font-semibold text-[var(--text-primary)]">{city}</h1>
        <button
          onClick={handleDownloadReport}
          disabled={downloading}
          className="ml-auto px-3 py-1.5 rounded-lg border border-[var(--surface-border)] text-sm text-[var(--text-secondary)] hover:bg-[var(--surface-muted)] disabled:opacity-50 transition-colors"
        >
          {downloading ? 'Generating…' : 'Download Report'}
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <AQICard
          city={city ?? ''}
          aqi={current.aqi}
          category={current.category}
          timestamp={current.timestamp}
        />
        <HealthAdvice category={current.category} color={color} />
      </div>

      <PollutantChart pollutants={pollutants} />
      <TrendChart data={trends} title="7-day AQI trend" />
    </div>
  )
}
