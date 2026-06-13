import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'

function WindIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/>
    </svg>
  )
}

function MapPinIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
      <circle cx="12" cy="10" r="3"/>
    </svg>
  )
}

function BarChartIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10"/>
      <line x1="12" y1="20" x2="12" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="14"/>
    </svg>
  )
}

function ActivityIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  )
}

function BellIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
      <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
    </svg>
  )
}

function SunIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5"/>
      <line x1="12" y1="1" x2="12" y2="3"/>
      <line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/>
      <line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
  )
}

function TargetIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <circle cx="12" cy="12" r="6"/>
      <circle cx="12" cy="12" r="2"/>
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  )
}

export const NAV_LINKS = [
  { to: '/',           label: 'Map',        end: true,  icon: <MapPinIcon /> },
  { to: '/historical', label: 'Historical', end: false, icon: <BarChartIcon /> },
  { to: '/forecast',   label: 'Forecast',   end: false, icon: <ActivityIcon /> },
  { to: '/accuracy',   label: 'Accuracy',   end: false, icon: <TargetIcon /> },
  { to: '/alerts',     label: 'Alerts',     end: false, icon: <BellIcon /> },
]

export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <span className="text-blue-600"><WindIcon /></span>
      <span className="text-sm font-bold text-[var(--text-primary)]">AQI Tracker</span>
    </div>
  )
}

function ThemeToggle() {
  const [dark, setDark] = useState(() => localStorage.getItem('theme') !== 'light')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  return (
    <button
      onClick={() => setDark(d => !d)}
      className="flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg text-sm text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-[var(--surface-muted)] transition-colors"
      aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {dark ? <SunIcon /> : <MoonIcon />}
      <span>{dark ? 'Light mode' : 'Dark mode'}</span>
    </button>
  )
}

export default function Navbar() {
  return (
    <aside className="hidden md:flex flex-col w-[220px] shrink-0 bg-[var(--surface-card)] border-r border-[var(--surface-border)] h-full">
      <div className="flex items-center h-14 px-5 border-b border-[var(--surface-border)]">
        <Logo />
      </div>

      <nav className="flex flex-col gap-0.5 p-2 mt-2">
        {NAV_LINKS.map(({ to, label, end, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-[var(--accent-bg)] text-blue-600 font-medium'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-muted)]'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span className={isActive ? 'text-blue-500' : 'text-[var(--text-muted)]'}>{icon}</span>
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto p-2 border-t border-[var(--surface-border)]">
        <ThemeToggle />
        <p className="text-[11px] text-[var(--text-muted)] px-3 pt-2">Real-time air quality</p>
      </div>
    </aside>
  )
}
