import { divIcon } from 'leaflet'
import { CircleMarker, MapContainer, Marker, Tooltip, TileLayer } from 'react-leaflet'
import { useNavigate } from 'react-router-dom'
import type { CityComparison } from '../services/api'
import { getAQIColor } from '../utils/aqiColors'

const AQI_BANDS = [
  { label: 'Good',           color: '#22c55e', range: '0–50' },
  { label: 'Moderate',       color: '#eab308', range: '51–100' },
  { label: 'Sensitive',      color: '#f97316', range: '101–150' },
  { label: 'Unhealthy',      color: '#ef4444', range: '151–200' },
  { label: 'Very Unhealthy', color: '#a855f7', range: '201–300' },
  { label: 'Hazardous',      color: '#7f1d1d', range: '300+' },
]

function createPulsingIcon(color: string) {
  return divIcon({
    className: '',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    html: `<div style="position:relative;width:32px;height:32px">
      <div class="aqi-pulse-ring" style="position:absolute;inset:0;border-radius:50%;background:${color}"></div>
      <div style="position:absolute;inset:8px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.25)"></div>
    </div>`,
  })
}

function MarkerTooltip({ city }: { city: CityComparison }) {
  const color = getAQIColor(city.latest_aqi)
  const fill = Math.min((city.latest_aqi / 500) * 100, 100)
  return (
    <div style={{
      background: 'var(--surface-card)',
      border: '1px solid var(--surface-border)',
      borderRadius: '10px',
      padding: '10px 12px',
      minWidth: '164px',
      boxShadow: '0 4px 14px rgba(0,0,0,0.14)',
      fontFamily: 'system-ui, sans-serif',
    }}>
      <p style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)', margin: 0 }}>
        {city.city}
      </p>
      <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: '2px 0 8px' }}>
        {city.country}
      </p>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <span style={{ fontSize: '22px', fontWeight: 700, color, lineHeight: 1 }}>
          {city.latest_aqi}
        </span>
        <span style={{
          fontSize: '10px', fontWeight: 600,
          padding: '2px 8px', borderRadius: '999px',
          background: color + '18', color,
        }}>
          {city.category}
        </span>
      </div>
      {/* Mini AQI position bar */}
      <div style={{ height: '4px', background: 'var(--surface-muted)', borderRadius: '999px', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${fill}%`, background: color, borderRadius: '999px' }} />
      </div>
    </div>
  )
}

interface Props {
  cities: CityComparison[]
}

export default function AQIMap({ cities }: Props) {
  const navigate = useNavigate()

  return (
    <div className="relative h-full w-full">
      <MapContainer center={[20, 0]} zoom={2} style={{ height: '100%', width: '100%' }} scrollWheelZoom>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />
        {cities.map(city => {
          const color = getAQIColor(city.latest_aqi)
          const tooltip = (
            <Tooltip className="aqi-tooltip" direction="top" offset={[0, -18]}>
              <MarkerTooltip city={city} />
            </Tooltip>
          )

          if (city.latest_aqi > 150) {
            return (
              <Marker
                key={city.city}
                position={[city.latitude, city.longitude]}
                icon={createPulsingIcon(color)}
                eventHandlers={{ click: () => navigate(`/city/${city.city}`) }}
              >
                {tooltip}
              </Marker>
            )
          }

          return (
            <CircleMarker
              key={city.city}
              center={[city.latitude, city.longitude]}
              radius={13}
              fillColor={color}
              color="#fff"
              weight={2}
              fillOpacity={0.85}
              eventHandlers={{ click: () => navigate(`/city/${city.city}`) }}
            >
              {tooltip}
            </CircleMarker>
          )
        })}
      </MapContainer>

      {/* AQI legend */}
      <div className="absolute bottom-5 right-2 z-[1000] bg-[var(--surface-card)]/95 rounded-xl border border-[var(--surface-border)] px-3 py-2.5 shadow-sm min-w-[148px]">
        <p className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">AQI Index</p>
        {AQI_BANDS.map(b => (
          <div key={b.label} className="flex items-center gap-2 py-[3px]">
            <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: b.color }} />
            <span className="text-[11px] text-[var(--text-secondary)] flex-1">{b.label}</span>
            <span className="text-[10px] text-[var(--text-muted)]">{b.range}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
