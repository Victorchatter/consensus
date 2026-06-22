import { useEffect, useState, useRef } from 'react'
import { createChart, IChartApi, ISeriesApi, LineData, Time } from 'lightweight-charts'
import { listStrategies, runBacktest, getBacktest, listBacktests, loadAssetHistory, listAssets } from '@/services/api'
import type { Strategy } from '@/types'

interface BacktestMetrics {
  total_return_pct: number
  cagr_pct: number
  sharpe_ratio: number
  sortino_ratio: number
  calmar_ratio: number
  max_drawdown_pct: number
  total_trades: number
  win_rate_pct: number
  profit_factor: number
  expectancy: number
  best_trade?: number
  worst_trade?: number
}

interface BacktestRun {
  id: number
  status: string
  metrics_json?: BacktestMetrics
  equity_curve_json?: any[]
  trades_json?: any[]
  error_message?: string
  created_at: string
  completed_at?: string
}

export default function StrategyPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [assets, setAssets] = useState<any[]>([])
  const [backtests, setBacktests] = useState<BacktestRun[]>([])
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null)
  const [selectedAsset, setSelectedAsset] = useState<number | null>(null)
  const [timeframe, setTimeframe] = useState('1d')
  const [running, setRunning] = useState(false)
  const [activeResult, setActiveResult] = useState<BacktestRun | null>(null)

  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null)

  useEffect(() => {
    listStrategies().then(setStrategies)
    listAssets().then(setAssets)
    listBacktests().then((data) => setBacktests(data as BacktestRun[]))
  }, [])

  useEffect(() => {
    if (!chartContainerRef.current) return
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: '#0B0B0F' },
        textColor: '#8A8A98',
      },
      grid: {
        vertLines: { color: '#1E1E26' },
        horzLines: { color: '#1E1E26' },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: '#2A2A35' },
      timeScale: { borderColor: '#2A2A35' },
      autoSize: true,
    })
    chartRef.current = chart
    const series = chart.addLineSeries({ color: '#00D4AA', lineWidth: 2 })
    seriesRef.current = series

    return () => {
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [activeResult])

  useEffect(() => {
    if (!seriesRef.current || !activeResult?.metrics_json) return
    const equityData = activeResult.equity_curve_json || []
    if (equityData.length === 0) return

    const lineData: LineData<Time>[] = equityData.map((e: any) => ({
      time: (new Date(e.timestamp).getTime() / 1000) as Time,
      value: e.equity,
    }))
    seriesRef.current.setData(lineData)
    chartRef.current?.timeScale().fitContent()
  }, [activeResult])

  // Backtesting methodology: timeframe-appropriate lookback windows
  const getBacktestRange = (tf: string) => {
    const end = new Date()
    const start = new Date()
    switch (tf) {
      case '1m':
        start.setDate(end.getDate() - 5)
        break
      case '5m':
        start.setDate(end.getDate() - 30)
        break
      case '15m':
        start.setDate(end.getDate() - 45)
        break
      case '1h':
        start.setMonth(end.getMonth() - 6)
        break
      case '4h':
        start.setMonth(end.getMonth() - 9)
        break
      case '1wk':
        start.setFullYear(end.getFullYear() - 5)
        break
      default: // 1d
        start.setFullYear(end.getFullYear() - 2)
    }
    return { start, end }
  }

  const handleRunBacktest = async () => {
    if (!selectedStrategy || !selectedAsset) return
    setRunning(true)
    try {
      await loadAssetHistory(selectedAsset, { timeframe })

      const { start, end } = getBacktestRange(timeframe)

      const result = await runBacktest({
        strategy_id: selectedStrategy.id,
        asset_id: selectedAsset,
        start_date: start.toISOString().split('T')[0],
        end_date: end.toISOString().split('T')[0],
        timeframe,
        initial_cash: 100000,
        commission_pct: 0.001,
      })

      let run = result as BacktestRun
      let attempts = 0
      while (run.status === 'pending' || run.status === 'running') {
        await new Promise((r) => setTimeout(r, 500))
        run = await getBacktest(run.id) as BacktestRun
        attempts += 1
        if (attempts > 40) break
      }

      setActiveResult(run)
      const updated = await listBacktests()
      setBacktests(updated as BacktestRun[])
    } catch (e) {
      console.error(e)
    } finally {
      setRunning(false)
    }
  }

  const metrics = activeResult?.metrics_json

  return (
    <div className="p-8">
      <header className="mb-6">
        <h2 className="text-2xl font-bold">Strategies & Backtests</h2>
        <p className="text-sm text-muted mt-1">Configure strategies, run backtests, and review results</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Strategy list */}
        <div className="lg:col-span-1 space-y-3">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-muted mb-2">Available Strategies</h3>
          {strategies.map((s) => (
            <button
              key={s.id}
              onClick={() => setSelectedStrategy(s)}
              className={`w-full text-left bg-elevated border rounded-lg p-4 transition-colors ${
                selectedStrategy?.id === s.id ? 'border-accent' : 'border-border hover:border-border-hover'
              }`}
            >
              <div className="font-semibold">{s.name}</div>
              <div className="text-xs text-muted mt-1">{s.description || s.class_path}</div>
              {s.is_builtin && (
                <span className="inline-block mt-2 text-[10px] px-2 py-0.5 rounded-full bg-accent/10 text-accent">Built-in</span>
              )}
            </button>
          ))}
          {strategies.length === 0 && (
            <p className="text-sm text-muted">No strategies configured yet.</p>
          )}
        </div>

        {/* Backtest panel */}
        <div className="lg:col-span-2 space-y-6">
          {selectedStrategy ? (
            <div className="bg-elevated border border-border rounded-lg p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold">{selectedStrategy.name}</h3>
                  <p className="text-sm text-muted">{selectedStrategy.description || 'No description provided.'}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="text-xs text-muted uppercase">Asset</label>
                  <select
                    value={selectedAsset || ''}
                    onChange={(e) => setSelectedAsset(Number(e.target.value))}
                    className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm mt-1"
                  >
                    <option value="">Select asset...</option>
                    {assets.map((a) => (
                      <option key={a.id} value={a.id}>{a.symbol} — {a.name || a.asset_class}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted uppercase">Timeframe</label>
                  <select
                    value={timeframe}
                    onChange={(e) => setTimeframe(e.target.value)}
                    className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm mt-1"
                  >
                    <option value="1d">Daily</option>
                    <option value="1h">Hourly</option>
                    <option value="1wk">Weekly</option>
                  </select>
                </div>
              </div>

              <button
                onClick={handleRunBacktest}
                disabled={!selectedAsset || running}
                className="bg-accent text-bg px-4 py-2 rounded-md text-sm font-semibold hover:bg-accent-light transition-colors disabled:opacity-50"
              >
                {running ? 'Running...' : 'Run Backtest'}
              </button>

              {activeResult && activeResult.status === 'completed' && metrics && (
                <div className="mt-6 space-y-4">
                  <h4 className="text-sm font-semibold uppercase tracking-wider text-muted">Equity Curve</h4>
                  <div ref={chartContainerRef} className="h-64 border border-border rounded-lg"></div>

                  <h4 className="text-sm font-semibold uppercase tracking-wider text-muted mt-4">Performance Metrics</h4>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <MetricBox label="Total Return" value={`${metrics.total_return_pct}%`} />
                    <MetricBox label="CAGR" value={`${metrics.cagr_pct}%`} />
                    <MetricBox label="Sharpe" value={String(metrics.sharpe_ratio)} />
                    <MetricBox label="Max DD" value={`${metrics.max_drawdown_pct}%`} danger />
                    <MetricBox label="Trades" value={String(metrics.total_trades)} />
                    <MetricBox label="Win Rate" value={`${metrics.win_rate_pct}%`} accent />
                    <MetricBox label="Profit Factor" value={String(metrics.profit_factor)} />
                    <MetricBox label="Expectancy" value={`$${metrics.expectancy}`} />
                  </div>
                </div>
              )}

              {activeResult?.status === 'failed' && (
                <div className="mt-4 bg-danger/10 border border-danger/30 rounded-md p-3 text-sm text-danger">
                  Backtest failed: {activeResult.error_message}
                </div>
              )}
            </div>
          ) : (
            <div className="bg-elevated border border-border rounded-lg p-5">
              <p className="text-sm text-muted">Select a strategy from the list to configure and backtest.</p>
            </div>
          )}

          {/* Backtest history */}
          <div className="bg-elevated border border-border rounded-lg p-5">
            <h4 className="text-sm font-semibold uppercase tracking-wider text-muted mb-3">Backtest History</h4>
            {backtests.length === 0 ? (
              <p className="text-sm text-muted">No backtests run yet.</p>
            ) : (
              <div className="space-y-2">
                {backtests.map((b) => (
                  <button
                    key={b.id}
                    onClick={() => setActiveResult(b)}
                    className="w-full bg-surface border border-border hover:border-border-hover rounded-md px-4 py-3 flex items-center justify-between text-left transition-colors"
                  >
                    <div className="text-sm">
                      Run #{b.id} — {b.status}
                    </div>
                    <div className="text-xs text-muted">
                      {b.created_at ? new Date(b.created_at).toLocaleString() : '—'}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function MetricBox({
  label,
  value,
  accent,
  danger,
}: {
  label: string
  value: string
  accent?: boolean
  danger?: boolean
}) {
  const color = danger ? 'text-danger' : accent ? 'text-accent' : 'text-text'
  return (
    <div className="bg-surface border border-border rounded-md p-3">
      <div className="text-[10px] text-muted uppercase tracking-wider mb-1">{label}</div>
      <div className={`text-sm font-bold ${color}`}>{value}</div>
    </div>
  )
}
