import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  CandlestickChart,
  BookOpen,
  CalendarDays,
  BrainCircuit,
  Bot,
  Radar,
  Settings,
} from 'lucide-react'

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/charts', label: 'Charts', icon: CandlestickChart },
  { to: '/journal', label: 'Journal', icon: BookOpen },
  { to: '/calendar', label: 'Calendar', icon: CalendarDays },
  { to: '/strategies', label: 'Strategies', icon: BrainCircuit },
  { to: '/bots', label: 'Bots', icon: Bot },
  { to: '/intelligence', label: 'Intelligence', icon: Radar },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation()

  return (
    <div className="flex h-screen bg-bg text-text font-sans">
      {/* Sidebar */}
      <aside className="w-60 bg-surface border-r border-border flex flex-col">
        <div className="px-5 py-6 border-b border-border">
          <h1 className="text-lg font-bold tracking-tight text-accent">
            EchoTrader
          </h1>
          <p className="text-[11px] text-muted mt-1">Algorithmic Trading Platform</p>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {nav.map((item) => {
            const Icon = item.icon
            const active = location.pathname === item.to
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors
                  ${active ? 'bg-accent/10 text-accent' : 'text-muted hover:text-text hover:bg-elevated'}
                `}
              >
                <Icon size={18} />
                {item.label}
              </Link>
            )
          })}
        </nav>
        <div className="px-3 py-4 border-t border-border">
          <Link
            to="/settings"
            className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors w-full ${
              location.pathname === '/settings'
                ? 'bg-accent/10 text-accent'
                : 'text-muted hover:text-text hover:bg-elevated'
            }`}
          >
            <Settings size={18} />
            Settings
          </Link>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}
