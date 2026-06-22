import { useEffect, useState } from 'react'
import { Activity, DollarSign, BarChart3, Target, Wifi, WifiOff, Server, ServerOff } from 'lucide-react'
import { useAssets } from '@/hooks/useAssets'
import { useMarketData } from '@/hooks/useMarketData'
import { useBackendHealth } from '@/hooks/useBackendHealth'
import { getPerformance, listTrades } from '@/services/api'
import type { PerformanceSummary, Trade } from '@/types'

function StatCard({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string
  value: string
  icon: React.ElementType
  accent?: string
}) {
  return (
    <div className="bg-elevated border border-border rounded-lg p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-muted uppercase tracking-wider">{label}</span>
        <Icon size={16} className={accent || 'text-muted'} />
      </div>
      <div className="text-2xl font-bold text-text">{value}</div>
    </div>
  )
}

export default function Dashboard() {
  const { assets, error: assetsError } = useAssets()
  const symbols = assets.map((a) => a.symbol)
  const { prices, connected } = useMarketData(symbols)
  const { healthy, latency } = useBackendHealth()
  const [perf, setPerf] = useState<PerformanceSummary | null>(null)
  const [trades, setTrades] = useState<Trade[]>([])

  useEffect(() => {
    getPerformance().then(setPerf).catch(() => null)
    listTrades({ limit: 5 }).then(setTrades).catch(() => null)
  }, [])

  const pnlColor = (v?: number) => (v ?? 0) >= 0 ? 'text-accent' : 'text-danger'
  const pnlSign = (v?: number) => (v ?? 0) >= 0 ? '+' : ''

  return (
    <div className="p-8">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Dashboard</h2>
          <p className="text-sm text-muted mt-1">Portfolio overview and trading activity</p>
        </div>
        <div className="flex items-center gap-2">
          {healthy === true ? (
            <span className="flex items-center gap-1.5 text-xs text-accent bg-accent/10 px-2.5 py-1 rounded-full">
              <Server size={12} /> API {latency}ms
            </span>
          ) : healthy === false ? (
            <span className="flex items-center gap-1.5 text-xs text-danger bg-danger/10 px-2.5 py-1 rounded-full">
              <ServerOff size={12} /> API Down
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs text-muted bg-muted/10 px-2.5 py-1 rounded-full">
              Checking...
            </span>
          )}
          {connected ? (
            <span className="flex items-center gap-1.5 text-xs text-accent bg-accent/10 px-2.5 py-1 rounded-full">
              <Wifi size={12} /> Live
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs text-warning bg-warning/10 px-2.5 py-1 rounded-full">
              <WifiOff size={12} /> Offline
            </span>
          )}
        </div>
      </header>

      {/* Diagnostic banner */}
      {assetsError && (
        <div className="mb-6 bg-danger/10 border border-danger/30 rounded-lg p-4">
          <div className="text-sm font-semibold text-danger mb-1">Failed to load assets</div>
          <div className="text-xs text-muted">{assetsError}</div>
          <div className="text-xs text-muted mt-2">Check browser console (F12 → Console) for details.</div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total P&L"
          value={`${pnlSign(perf?.total_pnl)}$${(perf?.total_pnl ?? 0).toFixed(2)}`}
          icon={DollarSign}
          accent={pnlColor(perf?.total_pnl)}
        />
        <StatCard
          label="Win Rate"
          value={`${((perf?.win_rate ?? 0) * 100).toFixed(1)}%`}
          icon={Target}
          accent="text-accent"
        />
        <StatCard
          label="Total Trades"
          value={`${perf?.total_trades ?? 0}`}
          icon={BarChart3}
        />
        <StatCard
          label="Profit Factor"
          value={`${(perf?.profit_factor ?? 0).toFixed(2)}`}
          icon={Activity}
          accent="text-accent"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Trades */}
        <div className="lg:col-span-2 bg-elevated border border-border rounded-lg p-5">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-muted mb-4">Recent Trades</h3>
          {trades.length === 0 ? (
            <p className="text-sm text-muted">No trades logged yet. Start paper trading or log a manual trade.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-muted uppercase tracking-wider border-b border-border">
                    <th className="pb-2">Asset</th>
                    <th className="pb-2">Direction</th>
                    <th className="pb-2">Entry</th>
                    <th className="pb-2">Exit</th>
                    <th className="pb-2 text-right">P&L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {trades.map((t) => (
                    <tr key={t.id} className="hover:bg-surface/50 transition-colors">
                      <td className="py-3 font-mono">{t.asset_id}</td>
                      <td className="py-3">
                        <span className={t.direction === 'long' ? 'text-accent' : 'text-danger'}>
                          {t.direction.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3">${t.entry_price.toFixed(2)}</td>
                      <td className="py-3">{t.exit_price ? `$${t.exit_price.toFixed(2)}` : '—'}</td>
                      <td className={`py-3 text-right font-mono ${pnlColor(t.pnl)}`}>
                        {t.pnl !== undefined ? `${pnlSign(t.pnl)}$${t.pnl.toFixed(2)}` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Watchlist with live prices */}
        <div className="bg-elevated border border-border rounded-lg p-5">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-muted mb-4">Watchlist ({assets.length})</h3>
          <div className="space-y-2 max-h-[400px] overflow-auto">
            {assets.length === 0 ? (
              <p className="text-sm text-muted">No assets. Add symbols in Settings.</p>
            ) : (
              assets.slice(0, 20).map((a) => {
                const live = prices[a.symbol]
                return (
                  <div
                    key={a.id}
                    className="flex items-center justify-between px-3 py-2 rounded-md hover:bg-surface transition-colors cursor-pointer"
                  >
                    <div>
                      <div className="font-mono text-sm font-semibold">{a.symbol}</div>
                      <div className="text-[11px] text-muted truncate max-w-[140px]">{a.name || a.asset_class}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-mono font-semibold">
                        {live ? `$${live.price.toFixed(2)}` : '—'}
                      </div>
                      <div className="text-[11px] text-muted">{a.exchange || 'N/A'}</div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
