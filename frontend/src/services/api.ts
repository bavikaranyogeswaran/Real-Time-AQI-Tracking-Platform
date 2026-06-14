import axios from 'axios'

const api = axios.create({ baseURL: '' })

export interface Location {
  location_id: string
  city: string
  country: string
  latitude: number
  longitude: number
  source: string
}

export interface CurrentAQI {
  reading_id: string
  location_id: string
  city: string
  timestamp: string
  aqi: number
  category: string
  pm25: number | null
  pm10: number | null
  co: number | null
  no2: number | null
  so2: number | null
  o3: number | null
  data_source: string
}

export interface HistoryAQI {
  reading_id: string
  timestamp: string
  aqi: number
  category: string
  pm25: number | null
  pm10: number | null
  co: number | null
  no2: number | null
  so2: number | null
  o3: number | null
}

export interface Pollutants {
  pm25: number | null
  pm10: number | null
  co: number | null
  no2: number | null
  so2: number | null
  o3: number | null
}

export interface Forecast {
  prediction_id: string
  forecast_for: string
  predicted_aqi: number
  model_name: string
}

export interface ForecastAccuracyRow {
  forecast_for: string
  predicted_aqi: number
  actual_aqi: number
  error: number
}

export interface ForecastAccuracy {
  rows: ForecastAccuracyRow[]
  mae: number
  rmse: number
  sample_count: number
}

export interface CityStatus {
  city: string
  country: string
  latest_aqi: number | null
  last_reading_at: string | null
  reading_count_7d: number
  data_source: string | null
}

export interface AdminSummary {
  total_readings: number
  readings_by_source: Record<string, number>
  alerts_active: number
  alerts_total_7d: number
  cities_monitored: number
  city_status: CityStatus[]
}

export interface AlertByType {
  alert_type: string
  count: number
  avg_aqi: number
}

export interface AlertByCity {
  city: string
  count: number
}

export interface AlertDailyCount {
  date: string
  count: number
}

export interface AlertPerformance {
  total: number
  active: number
  resolved: number
  by_type: AlertByType[]
  by_city: AlertByCity[]
  daily_counts: AlertDailyCount[]
}

export interface Alert {
  alert_id: string
  location_id: string
  alert_type: string
  threshold_value: number
  actual_aqi: number
  status: string
  created_at: string
}

export interface CityComparison {
  city: string
  country: string
  latitude: number
  longitude: number
  latest_aqi: number
  category: string
  timestamp: string
}

export interface Trend {
  date: string
  avg_aqi: number
  min_aqi: number
  max_aqi: number
}

export interface HourlyAvg {
  hour: number
  avg_aqi: number
}

export interface AQIDistribution {
  category: string
  count: number
}

export interface PollutantTrend {
  date: string
  avg_pm25: number | null
  avg_pm10: number | null
  avg_co: number | null
  avg_no2: number | null
  avg_so2: number | null
  avg_o3: number | null
}

export interface DominantPollutant {
  pollutant: string
  label: string
  avg_value: number
  safe_limit: number
  exceedance_count: number
}

export const getLocations = () =>
  api.get<Location[]>('/api/locations').then(r => r.data)

export const getCurrentAQI = (city: string) =>
  api.get<CurrentAQI>('/api/aqi/current', { params: { city } }).then(r => r.data)

export const getHistory = (city: string, days = 7) =>
  api.get<HistoryAQI[]>('/api/aqi/history', { params: { city, days } }).then(r => r.data)

export const getPollutants = (city: string) =>
  api.get<Pollutants>('/api/aqi/pollutants', { params: { city } }).then(r => r.data)

export const getForecast = (city: string, days = 1) =>
  api.get<Forecast[]>('/api/aqi/forecast', { params: { city, days } }).then(r => r.data)

export const getForecastAccuracy = (city: string, days = 7) =>
  api.get<ForecastAccuracy>('/api/analytics/forecast-accuracy', { params: { city, days } }).then(r => r.data)

export const getAdminSummary = () =>
  api.get<AdminSummary>('/api/admin/summary').then(r => r.data)

export const getAlertPerformance = (days = 30) =>
  api.get<AlertPerformance>('/api/analytics/alert-performance', { params: { days } }).then(r => r.data)

export const downloadCityPdf = (city: string, days = 7): Promise<void> =>
  api
    .get('/api/reports/city-pdf', { params: { city, days }, responseType: 'blob' })
    .then(r => {
      const url = URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `${city.toLowerCase().replace(/\s+/g, '-')}-aqi-report.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    })

export const getAlerts = () =>
  api.get<Alert[]>('/api/alerts').then(r => r.data)

export const getCityComparison = () =>
  api.get<CityComparison[]>('/api/analytics/city-comparison').then(r => r.data)

export const getTrends = (city: string, period = 'weekly') =>
  api.get<Trend[]>('/api/analytics/trends', { params: { city, period } }).then(r => r.data)

export const getPeakHours = (city: string) =>
  api.get<HourlyAvg[]>('/api/analytics/peak-hours', { params: { city } }).then(r => r.data)

export const getDistribution = (city: string) =>
  api.get<AQIDistribution[]>('/api/analytics/distribution', { params: { city } }).then(r => r.data)

export const getPollutantTrends = (city: string, period = 'weekly') =>
  api.get<PollutantTrend[]>('/api/analytics/pollutant-trends', { params: { city, period } }).then(r => r.data)

export const getDominantPollutant = (city: string, days = 7) =>
  api.get<DominantPollutant[]>('/api/analytics/dominant-pollutant', { params: { city, days } }).then(r => r.data)

export interface CityRanking {
  city: string
  country: string
  avg_aqi: number
  max_aqi: number
  unhealthy_days: number
  prev_avg_aqi: number | null
  trend: 'improving' | 'worsening' | 'stable'
}

export const getCityRanking = (days = 7) =>
  api.get<CityRanking[]>('/api/analytics/city-ranking', { params: { days } }).then(r => r.data)
