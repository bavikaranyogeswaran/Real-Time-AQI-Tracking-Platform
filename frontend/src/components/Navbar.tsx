import { NavLink } from 'react-router-dom'

const LINKS = [
  { to: '/',           label: 'Map',        end: true  },
  { to: '/historical', label: 'Historical', end: false },
  { to: '/forecast',   label: 'Forecast',   end: false },
  { to: '/alerts',     label: 'Alerts',     end: false },
]

export default function Navbar() {
  return (
    <nav className="flex items-center gap-1 px-6 h-14 bg-white border-b border-gray-100 shrink-0">
      <span className="text-sm font-semibold text-gray-900 mr-5">
        AQI Platform
      </span>
      {LINKS.map(({ to, label, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            `px-3 py-1.5 rounded-md text-sm transition-colors ${
              isActive
                ? 'bg-blue-50 text-blue-600 font-medium'
                : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50'
            }`
          }
        >
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
