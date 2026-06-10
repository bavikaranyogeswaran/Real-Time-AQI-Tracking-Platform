import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import { useNavigate } from 'react-router-dom'
import { getCityComparison, type CityComparison } from '../services/api'
import { getAQIColor } from '../utils/aqiColors'

export default function AQIMap() {
  const [cities, setCities] = useState<CityComparison[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    getCityComparison().then(setCities).catch(console.error)
  }, [])

  return (
    <MapContainer
      center={[20, 0]}
      zoom={2}
      style={{ height: '100%', width: '100%' }}
      scrollWheelZoom
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />
      {cities.map(city => (
        <CircleMarker
          key={city.city}
          center={[city.latitude, city.longitude]}
          radius={14}
          fillColor={getAQIColor(city.latest_aqi)}
          color="#fff"
          weight={2}
          fillOpacity={0.85}
          eventHandlers={{ click: () => navigate(`/city/${city.city}`) }}
        >
          <Popup>
            <div className="text-sm">
              <p className="font-semibold">{city.city}</p>
              <p className="text-gray-500">{city.country}</p>
              <p className="mt-1">
                AQI <strong>{city.latest_aqi}</strong> — {city.category}
              </p>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
