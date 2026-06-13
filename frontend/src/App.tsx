import { useEffect, useRef } from 'react'
import { BrowserRouter, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import Navbar, { Logo, NAV_LINKS } from './components/Navbar'
import { showToast, ToastContainer } from './components/Toast'
import AdminDashboard from './pages/AdminDashboard'
import AlertPerformance from './pages/AlertPerformance'
import Alerts from './pages/Alerts'
import CityDashboard from './pages/CityDashboard'
import Forecast from './pages/Forecast'
import ForecastAccuracy from './pages/ForecastAccuracy'
import Historical from './pages/Historical'
import Home from './pages/Home'
import { getAlerts } from './services/api'
import { getAQIColor } from './utils/aqiColors'

function AlertPoller() {
  const knownIds = useRef<Set<string> | null>(null)

  useEffect(() => {
    let cancelled = false

    async function poll() {
      if (cancelled) return
      try {
        const alerts = await getAlerts()
        const active = alerts.filter(a => a.status === 'active')

        if (knownIds.current === null) {
          knownIds.current = new Set(active.map(a => a.alert_id))
          return
        }

        for (const alert of active) {
          if (!knownIds.current.has(alert.alert_id)) {
            knownIds.current.add(alert.alert_id)
            showToast({
              city: alert.location_id,
              message: `AQI ${alert.actual_aqi} · ${alert.alert_type.replace(/_/g, ' ')}`,
              color: getAQIColor(alert.actual_aqi),
            })
          }
        }
      } catch { /* ignore */ }
    }

    poll()
    const id = setInterval(poll, 30_000)
    return () => { cancelled = true; clearInterval(id) }
  }, [])

  return null
}

function AppShell() {
  const location = useLocation()

  return (
    <div className="flex h-full bg-[var(--surface-bg)]">
      <Navbar />

      <div className="flex flex-col flex-1 min-w-0 h-full">
        {/* Mobile top bar */}
        <header className="md:hidden flex items-center px-4 h-14 bg-[var(--surface-card)] border-b border-[var(--surface-border)] shrink-0">
          <Logo />
        </header>

        {/* Page content — keyed so the fade animation fires on every navigation */}
        <main className="flex-1 min-h-0 overflow-auto flex flex-col">
          <div key={location.key} className="page-enter flex-1 flex flex-col min-h-0">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/city/:city" element={<CityDashboard />} />
              <Route path="/historical" element={<Historical />} />
              <Route path="/forecast" element={<Forecast />} />
              <Route path="/accuracy" element={<ForecastAccuracy />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/alert-performance" element={<AlertPerformance />} />
              <Route path="/admin" element={<AdminDashboard />} />
            </Routes>
          </div>
        </main>

        {/* Mobile bottom nav */}
        <nav className="md:hidden flex items-center bg-[var(--surface-card)] border-t border-[var(--surface-border)] shrink-0">
          {NAV_LINKS.map(({ to, label, end, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex flex-col items-center gap-0.5 flex-1 py-2.5 text-[10px] font-medium transition-colors ${
                  isActive ? 'text-blue-600' : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span className={isActive ? 'text-blue-600' : 'text-[var(--text-muted)]'}>{icon}</span>
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AlertPoller />
      <AppShell />
      <ToastContainer />
    </BrowserRouter>
  )
}
