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
