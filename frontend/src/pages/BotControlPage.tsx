import { useEffect, useState, useCallback } from 'react'
import {
  listBots,
  createBot,
  startBot,
  stopBot,
  deleteBot,
  confirmBotLive,
  listStrategies,
  listAssets,
  listBrokerConnections,
} from '@/services/api'
import type { Strategy, Asset } from '@/types'
import {
  Play,
  Square,
  Plus,
  Trash2,
  RefreshCw,
  Terminal,
  Wallet,
  TrendingUp,
  Activity,
  ChevronDown,
  ChevronUp,
  Bot,
  ShieldAlert,
} from 'lucide-react'

interface BotState {
  config: {
    id: string
    name: string
    active: boolean
    strategy_id: number
    asset_ids: number[]
    timeframe: string
    data_source: string
    broker: string
    mode: string
    broker_connection_id?: number
    last_run_at?: string
  }
  paper_summary: {
    balance: number
    equity: number
    realized_pnl: number
    unrealized_pnl: number
    total_trades: number
    win_count: number
    loss_count: number
    win_rate: number
    max_drawdown: number
    open_positions: number
  }
  positions: Array<{
    asset_id: number
    symbol: string
    direction: string
    size: number
    avg_entry_price: number
    unrealized_pnl: number
  }>
  recent_orders: Array<{
    id: string
    symbol: string
    action: string
    size: number
    status: string
    fill_price?: number
    pnl?: number
    created_at: string
  }>
  error_log: string[]
}

export default function BotControlPage() {
  const [bots, setBots] = useState<BotState[]>([])
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedBot, setExpandedBot] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)

  // Form state
  const [formName, setFormName] = useState('')
  const [formStrategy, setFormStrategy] = useState('')
  const [formAssets, setFormAssets] = useState<number[]>([])
  const [formTimeframe, setFormTimeframe] = useState('1d')
  const [formDataSource, setFormDataSource] = useState('yahoo')
  const [formBroker, setFormBroker] = useState('paper')
  const [formMode, setFormMode] = useState('paper')
  const [formCash, setFormCash] = useState(100000)
  const [formMaxHoldMinutes, setFormMaxHoldMinutes] = useState(120)
  const [formCloseBeforeMarketClose, setFormCloseBeforeMarketClose] = useState(true)
  const [formBrokerConnectionId, setFormBrokerConnectionId] = useState<number | ''>('')
  const [formError, setFormError] = useState<string | null>(null)
  const [brokerConnections, setBrokerConnections] = useState<Array<{ id: number; broker_name: string; user_label?: string; is_paper: boolean }>>([])
  const [liveConfirmBotId, setLiveConfirmBotId] = useState<string | null>(null)

  const fetchBots = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listBots()
      if (Array.isArray(data)) {
        setBots(data.filter((b: any) => b?.config))
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchBots()
    listStrategies().then(setStrategies)
    listAssets().then(setAssets)
    listBrokerConnections().then((data) => {
      if (Array.isArray(data)) setBrokerConnections(data)
    })
    const interval = setInterval(fetchBots, 5000)
    return () => clearInterval(interval)
  }, [fetchBots])

  const handleCreate = async () => {
    if (!formName.trim() || !formStrategy || formAssets.length === 0) return
    setFormError(null)
    try {
      const result = await createBot({
        name: formName,
        strategy_id: Number(formStrategy),
        asset_ids: formAssets,
        timeframe: formTimeframe,
        data_source: formDataSource,
        broker: formBroker,
        mode: formMode,
        broker_connection_id: formMode === 'live' && formBrokerConnectionId ? Number(formBrokerConnectionId) : null,
        initial_cash: formCash,
        max_hold_minutes: formMaxHoldMinutes,
        close_before_market_close: formCloseBeforeMarketClose,
      })
      if (result?.error) {
        setFormError(result.error)
        return
      }
      setShowForm(false)
      resetForm()
      fetchBots()
    } catch (e: any) {
      console.error(e)
      setFormError(e?.response?.data?.detail || e?.message || 'Failed to create bot')
    }
  }

  const resetForm = () => {
    setFormName('')
    setFormStrategy('')
    setFormAssets([])
    setFormTimeframe('1d')
    setFormDataSource('yahoo')
    setFormBroker('paper')
    setFormMode('paper')
    setFormBrokerConnectionId('')
    setFormCash(100000)
    setFormMaxHoldMinutes(120)
    setFormCloseBeforeMarketClose(true)
  }

  const toggleAsset = (id: number) => {
    setFormAssets((prev) =>
      prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id]
    )
  }

  const handleStart = async (id: string, mode: string) => {
    if (mode === 'live') {
      setLiveConfirmBotId(id)
      return
    }
    try {
      await startBot(id)
      fetchBots()
    } catch (e) {
      console.error(e)
    }
  }

  const handleConfirmLive = async () => {
    if (!liveConfirmBotId) return
    try {
      await confirmBotLive(liveConfirmBotId)
      await startBot(liveConfirmBotId)
      setLiveConfirmBotId(null)
      fetchBots()
    } catch (e) {
      console.error(e)
    }
  }

  const handleStop = async (id: string) => {
    try {
      await stopBot(id)
      fetchBots()
    } catch (e) {
      console.error(e)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this bot?')) return
    try {
      await deleteBot(id)
      fetchBots()
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="p-8">
      <header className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Bot size={24} className="text-accent" />
            Bot Control Panel
          </h2>
          <p className="text-sm text-muted mt-1">
            Start, stop, and monitor automated trading bots
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchBots}
            className="bg-elevated border border-border hover:border-border-hover text-muted hover:text-text px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-1.5"
          >
            <RefreshCw size={14} />
            Refresh
          </button>
          <button
            onClick={() => setShowForm(true)}
            className="bg-accent text-bg px-4 py-2 rounded-md text-sm font-semibold hover:bg-accent-light transition-colors flex items-center gap-2"
          >
            <Plus size={16} />
            Create Bot
          </button>
        </div>
      </header>

      {/* Create Bot Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-surface border border-border rounded-xl w-full max-w-lg shadow-xl max-h-[90vh] overflow-auto">
            <div className="px-6 py-4 border-b border-border">
              <h3 className="text-lg font-semibold">Create Trading Bot</h3>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="text-xs text-muted uppercase block mb-1">Name</label>
                <input
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="My SMA Bot"
                  className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted uppercase block mb-1">Strategy</label>
                  <select
                    value={formStrategy}
                    onChange={(e) => setFormStrategy(e.target.value)}
                    className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                  >
                    <option value="">Select...</option>
                    {strategies.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted uppercase block mb-1">Timeframe</label>
                  <select
                    value={formTimeframe}
                    onChange={(e) => setFormTimeframe(e.target.value)}
                    className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                  >
                    <option value="1m">1m</option>
                    <option value="5m">5m</option>
                    <option value="15m">15m</option>
                    <option value="1h">1h</option>
                    <option value="4h">4h</option>
                    <option value="1d">1d</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs text-muted uppercase block mb-1">Assets</label>
                <div className="flex flex-wrap gap-2 max-h-32 overflow-auto bg-bg border border-border rounded-md p-2">
                  {assets.map((a) => (
                    <button
                      key={a.id}
                      onClick={() => toggleAsset(a.id)}
                      className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                        formAssets.includes(a.id)
                          ? 'bg-accent text-bg'
                          : 'bg-elevated text-muted hover:text-text'
                      }`}
                    >
                      {a.symbol}
                    </button>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted uppercase block mb-1">Data Source</label>
                  <select
                    value={formDataSource}
                    onChange={(e) => setFormDataSource(e.target.value)}
                    className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                  >
                    <option value="yahoo">Yahoo Finance</option>
                    <option value="alpaca">Alpaca</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted uppercase block mb-1">Broker</label>
                  <select
                    value={formBroker}
                    onChange={(e) => setFormBroker(e.target.value)}
                    className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                  >
                    <option value="paper">Paper</option>
                    <option value="alpaca">Alpaca</option>
                    <option value="ccxt">CCXT</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted uppercase block mb-1">Mode</label>
                  <select
                    value={formMode}
                    onChange={(e) => setFormMode(e.target.value)}
                    className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                  >
                    <option value="paper">Paper</option>
                    <option value="live">Live</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted uppercase block mb-1">Initial Cash</label>
                  <input
                    type="number"
                    value={formCash}
                    onChange={(e) => setFormCash(Number(e.target.value))}
                    className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                  />
                </div>
              </div>

              {formMode === 'live' && (
                <div>
                  <label className="text-xs text-muted uppercase block mb-1">Exchange Connection</label>
                  <select
                    value={formBrokerConnectionId}
                    onChange={(e) => setFormBrokerConnectionId(e.target.value === '' ? '' : Number(e.target.value))}
                    className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                  >
                    <option value="">Select a connected broker...</option>
                    {brokerConnections.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.user_label || c.broker_name} {c.is_paper ? '(Paper)' : '(Live)'}
                      </option>
                    ))}
                  </select>
                  {brokerConnections.length === 0 && (
                    <p className="text-[10px] text-danger mt-1">
                      No broker connections found. Go to Settings → Brokers to connect one.
                    </p>
                  )}
                </div>
              )}

              {formMode === 'live' && (
                <div className="bg-danger/5 border border-danger/20 rounded-md p-3 flex items-start gap-2">
                  <ShieldAlert size={14} className="text-danger shrink-0 mt-0.5" />
                  <p className="text-[11px] text-danger">
                    Live mode will place real orders with real money. You must explicitly confirm before the bot starts trading.
                  </p>
                </div>
              )}

              <div className="border-t border-border pt-4 mt-2">
                <h4 className="text-xs font-semibold text-muted uppercase mb-2">Scalp / Intraday Guards</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-muted uppercase block mb-1">Max Hold Minutes</label>
                    <input
                      type="number"
                      min={0}
                      max={1440}
                      value={formMaxHoldMinutes}
                      onChange={(e) => setFormMaxHoldMinutes(Number(e.target.value))}
                      className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                    />
                    <p className="text-[10px] text-muted mt-1">0 = disabled. Auto-closes positions after N minutes.</p>
                  </div>
                  <div className="flex items-center">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formCloseBeforeMarketClose}
                        onChange={(e) => setFormCloseBeforeMarketClose(e.target.checked)}
                        className="w-4 h-4 accent-accent"
                      />
                      <span className="text-sm text-text">Close before 16:00 ET</span>
                    </label>
                    <p className="text-[10px] text-muted mt-1 pl-6">Flattens all positions at 15:55 ET to avoid overnight fees.</p>
                  </div>
                </div>
              </div>
            </div>
            {formError && (
              <div className="px-6 py-2 text-xs text-danger bg-danger/10 border-t border-danger/20">
                {formError}
              </div>
            )}
            <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-border bg-surface/50">
              <button
                onClick={() => setShowForm(false)}
                className="px-4 py-2 rounded-md text-sm text-muted hover:text-text"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                className="bg-accent text-bg px-4 py-2 rounded-md text-sm font-semibold hover:bg-accent-light"
              >
                Create Bot
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Live Confirmation Modal */}
      {liveConfirmBotId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-surface border border-danger/30 rounded-xl w-full max-w-md shadow-xl">
            <div className="px-6 py-4 border-b border-danger/20">
              <h3 className="text-lg font-semibold text-danger flex items-center gap-2">
                <ShieldAlert size={18} />
                Confirm Live Trading
              </h3>
            </div>
            <div className="p-6 space-y-3">
              <p className="text-sm text-text">
                You are about to start a bot in <strong className="text-danger">LIVE MODE</strong>. This will place real orders with real money on your connected exchange account.
              </p>
              <ul className="text-xs text-muted list-disc pl-4 space-y-1">
                <li>Orders are sent to the real exchange API.</li>
                <li>P&amp;L is realized with actual capital.</li>
                <li>There is no undo for market orders.</li>
              </ul>
            </div>
            <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-danger/20 bg-danger/5">
              <button
                onClick={() => setLiveConfirmBotId(null)}
                className="px-4 py-2 rounded-md text-sm text-muted hover:text-text"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmLive}
                className="bg-danger text-bg px-4 py-2 rounded-md text-sm font-semibold hover:bg-danger/90"
              >
                I Understand — Start Live Bot
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bot list */}
      <div className="space-y-4">
        {loading && bots.length === 0 && (
          <p className="text-muted text-sm">Loading bots...</p>
        )}
        {bots.map((bot) => {
          const cfg = bot.config
          const summary = bot.paper_summary || {}
          const isExpanded = expandedBot === cfg.id
          return (
            <div
              key={cfg.id}
              className="bg-elevated border border-border rounded-lg overflow-hidden"
            >
              <div className="px-5 py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-2.5 h-2.5 rounded-full ${
                      cfg.active ? 'bg-accent animate-pulse' : 'bg-muted'
                    }`}
                  />
                  <div>
                    <div className="font-semibold text-sm flex items-center gap-2">
                      {cfg.name}
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                          cfg.mode === 'live'
                            ? 'bg-danger/10 text-danger border border-danger/20'
                            : 'bg-accent/10 text-accent border border-accent/20'
                        }`}
                      >
                        {cfg.mode === 'live' ? 'LIVE' : 'PAPER'}
                      </span>
                    </div>
                    <div className="text-[11px] text-muted">
                      {cfg.broker} · {cfg.timeframe} · {cfg.asset_ids.length} assets
                      {cfg.last_run_at && ` · Last run ${new Date(cfg.last_run_at).toLocaleTimeString()}`}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {cfg.active ? (
                    <button
                      onClick={() => handleStop(cfg.id)}
                      className="flex items-center gap-1.5 bg-danger/10 text-danger hover:bg-danger/20 px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
                    >
                      <Square size={12} />
                      Stop
                    </button>
                  ) : (
                    <button
                      onClick={() => handleStart(cfg.id, cfg.mode)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                        cfg.mode === 'live'
                          ? 'bg-danger/10 text-danger hover:bg-danger/20'
                          : 'bg-accent/10 text-accent hover:bg-accent/20'
                      }`}
                    >
                      <Play size={12} />
                      {cfg.mode === 'live' ? 'Start Live' : 'Start'}
                    </button>
                  )}
                  <button
                    onClick={() => setExpandedBot(isExpanded ? null : cfg.id)}
                    className="text-muted hover:text-text p-1"
                  >
                    {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                  <button
                    onClick={() => handleDelete(cfg.id)}
                    className="text-muted hover:text-danger p-1"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {isExpanded && (
                <div className="border-t border-border px-5 py-4 space-y-4">
                  {/* Summary cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <MiniCard label="Balance" value={`$${(summary.balance ?? 0).toFixed(2)}`} icon={Wallet} />
                    <MiniCard
                      label="Equity"
                      value={`$${(summary.equity ?? 0).toFixed(2)}`}
                      icon={Activity}
                      accent={summary.equity >= summary.balance}
                      danger={summary.equity < summary.balance}
                    />
                    <MiniCard
                      label="Realized P&L"
                      value={`$${(summary.realized_pnl ?? 0).toFixed(2)}`}
                      icon={TrendingUp}
                      accent={(summary.realized_pnl ?? 0) > 0}
                      danger={(summary.realized_pnl ?? 0) < 0}
                    />
                    <MiniCard label="Open Positions" value={String(summary.open_positions ?? 0)} icon={Bot} />
                  </div>

                  {/* Positions */}
                  {(bot.positions?.length ?? 0) > 0 && (
                    <div>
                      <h4 className="text-[10px] uppercase tracking-wider text-muted mb-2">Positions</h4>
                      <div className="space-y-1.5">
                        {bot.positions!.map((p) => (
                          <div
                            key={p.asset_id}
                            className="flex items-center justify-between bg-surface border border-border rounded-md px-3 py-2 text-sm"
                          >
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-semibold">{p.symbol}</span>
                              <span
                                className={`text-[10px] px-1.5 py-0.5 rounded ${
                                  p.direction === 'long'
                                    ? 'bg-accent/10 text-accent'
                                    : 'bg-danger/10 text-danger'
                                }`}
                              >
                                {p.direction.toUpperCase()}
                              </span>
                              <span className="text-muted text-xs">{p.size.toFixed(4)} @ ${p.avg_entry_price.toFixed(2)}</span>
                            </div>
                            <span
                              className={`font-mono text-xs ${
                                p.unrealized_pnl >= 0 ? 'text-accent' : 'text-danger'
                              }`}
                            >
                              {p.unrealized_pnl >= 0 ? '+' : ''}${p.unrealized_pnl.toFixed(2)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Recent orders */}
                  {(bot.recent_orders?.length ?? 0) > 0 && (
                    <div>
                      <h4 className="text-[10px] uppercase tracking-wider text-muted mb-2">Recent Orders</h4>
                      <div className="space-y-1.5">
                        {bot.recent_orders!.map((o) => (
                          <div
                            key={o.id}
                            className="flex items-center justify-between bg-surface border border-border rounded-md px-3 py-2 text-sm"
                          >
                            <div className="flex items-center gap-2">
                              <span
                                className={`text-[10px] px-1.5 py-0.5 rounded ${
                                  o.action === 'buy'
                                    ? 'bg-accent/10 text-accent'
                                    : 'bg-danger/10 text-danger'
                                }`}
                              >
                                {o.action.toUpperCase()}
                              </span>
                              <span className="font-mono">{o.symbol}</span>
                              <span className="text-muted text-xs">{o.size.toFixed(4)}</span>
                              <span className="text-muted text-[10px]">{o.status}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              {o.fill_price && (
                                <span className="text-muted text-xs">@${o.fill_price.toFixed(2)}</span>
                              )}
                              {o.pnl !== undefined && (
                                <span
                                  className={`font-mono text-xs ${o.pnl >= 0 ? 'text-accent' : 'text-danger'}`}
                                >
                                  {o.pnl >= 0 ? '+' : ''}${o.pnl.toFixed(2)}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Error log */}
                  {(bot.error_log?.length ?? 0) > 0 && (
                    <div>
                      <h4 className="text-[10px] uppercase tracking-wider text-muted mb-2 flex items-center gap-1">
                        <Terminal size={10} />
                        Logs
                      </h4>
                      <div className="bg-black/40 border border-border rounded-md p-3 max-h-48 overflow-auto font-mono text-[11px] text-muted space-y-0.5">
                        {bot.error_log!.map((line, i) => (
                          <div key={i} className="truncate">
                            {line}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
        {bots.length === 0 && !loading && (
          <div className="text-center py-12 text-muted">
            <Bot size={32} className="mx-auto mb-3 opacity-50" />
            <p className="text-sm">No bots configured yet.</p>
            <p className="text-xs mt-1">Create a bot to start automated paper trading.</p>
          </div>
        )}
      </div>
    </div>
  )
}

function MiniCard({
  label,
  value,
  icon: Icon,
  accent,
  danger,
}: {
  label: string
  value: string
  icon: React.ElementType
  accent?: boolean
  danger?: boolean
}) {
  const color = danger ? 'text-danger' : accent ? 'text-accent' : 'text-text'
  return (
    <div className="bg-surface border border-border rounded-md p-3 flex items-center gap-3">
      <Icon size={16} className="text-muted" />
      <div>
        <div className="text-[10px] text-muted uppercase tracking-wider">{label}</div>
        <div className={`text-sm font-bold ${color}`}>{value}</div>
      </div>
    </div>
  )
}
