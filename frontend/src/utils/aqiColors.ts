interface AQIBand {
  max: number
  color: string
  category: string
}

const BANDS: AQIBand[] = [
  { max: 50,  color: '#22c55e', category: 'Good' },
  { max: 100, color: '#eab308', category: 'Moderate' },
  { max: 150, color: '#f97316', category: 'Unhealthy for Sensitive Groups' },
  { max: 200, color: '#ef4444', category: 'Unhealthy' },
  { max: 300, color: '#a855f7', category: 'Very Unhealthy' },
  { max: Infinity, color: '#7f1d1d', category: 'Hazardous' },
]

export function getAQIColor(aqi: number): string {
  return (BANDS.find(b => aqi <= b.max) ?? BANDS[BANDS.length - 1]).color
}

export function getAQICategory(aqi: number): string {
  return (BANDS.find(b => aqi <= b.max) ?? BANDS[BANDS.length - 1]).category
}
