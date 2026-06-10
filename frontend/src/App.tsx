import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar'
import Alerts from './pages/Alerts'
import CityDashboard from './pages/CityDashboard'
import Forecast from './pages/Forecast'
import Historical from './pages/Historical'
import Home from './pages/Home'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col h-full bg-gray-50">
        <Navbar />
        <div className="flex-1 min-h-0 overflow-auto flex flex-col">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/city/:city" element={<CityDashboard />} />
            <Route path="/historical" element={<Historical />} />
            <Route path="/forecast" element={<Forecast />} />
            <Route path="/alerts" element={<Alerts />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
