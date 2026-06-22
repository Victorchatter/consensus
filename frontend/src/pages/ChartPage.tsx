import { useEffect, useRef, useState, useCallback } from 'react'
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  HistogramData,
  LineData,
  Time,
  SeriesMarker,
  ColorType,
} from 'lightweight-charts'
import { useAssets } from '@/hooks/useAssets'
import { usePriceHistory } from '@/hooks/usePriceHistory'
import { useMarketData } from '@/hooks/useMarketData'
import { loadAssetHistory, getIndicators, listTrades } from '@/services/api'
import type { Asset, PriceBar } from '@/types'
import {
  Download,
  Wifi,
  WifiOff,
  Eye,
  EyeOff,
} from 'lucide-react'

const TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d']

interface IndicatorConfig {
  key: string
  label: string
  period: number
  active: boolean
  color: string
}

const DEFAULT_INDICATORS: IndicatorConfig[] = [
  { key: 'sma', label: 'SMA', period: 20, active: false, color: '#FFB800' },
  { key: 'ema', label: 'EMA', period: 20, active: false, color: '#00BFFF' },
  { key: 'bollinger', label: 'BB', period: 20, active: false, color: '#FF6B6B' },
  { key: 'rsi', label: 'RSI', period: 14, active: false, color: '#9B59B6' },
]

export default function ChartPage() {
  const { assets } = useAssets()
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null)
  const [timeframe, setTimeframe] = useState('1d')
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [indicators, setIndicators] = useState<IndicatorConfig[]>(DEFAULT_INDICATORS)

  const { bars, loading: barsLoading, refresh } = usePriceHistory(selectedAsset?.id ?? null, timeframe)
  const symbols = selectedAsset ? [selectedAsset.symbol] : []
  const { prices, connected } = useMarketData(symbols, selectedAsset?.id ?? null)

  // Chart refs
  const mainContainerRef = useRef<HTMLDivElement>(null)
  const rsiContainerRef = useRef<HTMLDivElement>(null)
  const mainChartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const rsiChartRef = useRef<IChartApi | null>(null)
  const rsiSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const barsRef = useRef<PriceBar[]>([])

  // Keep bars ref in sync
  useEffect(() => {
    barsRef.current = bars
  }, [bars])

  // ── Main Chart Initialization ──
  useEffect(() => {
    if (!mainContainerRef.current) return
    const chart = createChart(mainContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0B0B0F' },
        textColor: '#8A8A98',
      },
      grid: {
        vertLines: { color: '#1E1E26' },
        horzLines: { color: '#1E1E26' },
      },
      crosshair: {
        mode: 1,
        vertLine: { color: '#00D4AA', labelBackgroundColor: '#00D4AA' },
        horzLine: { color: '#00D4AA', labelBackgroundColor: '#00D4AA' },
      },
      rightPriceScale: { borderColor: '#2A2A35' },
      timeScale: {
        borderColor: '#2A2A35',
        timeVisible: true,
      },
      autoSize: true,
    })
    mainChartRef.current = chart

    const candle = chart.addCandlestickSeries({
      upColor: '#00D4AA',
      downColor: '#FF4757',
      borderUpColor: '#00D4AA',
      borderDownColor: '#FF4757',
      wickUpColor: '#00D4AA',
      wickDownColor: '#FF4757',
    })
    candleSeriesRef.current = candle

    const volume = chart.addHistogramSeries({
      color: '#00D4AA',
      priceFormat: { type: 'volume' },
      priceScaleId: '', // Overlay scale
    })
    volume.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })
    volumeSeriesRef.current = volume

    return () => {
      chart.remove()
      mainChartRef.current = null
      candleSeriesRef.current = null
      volumeSeriesRef.current = null
    }
  }, []) // Only create chart once

  // ── RSI Chart Initialization ──
  useEffect(() => {
    if (!rsiContainerRef.current) return
    const chart = createChart(rsiContainerRef.current, {
      height: 120,
      layout: {
        background: { type: ColorType.Solid, color: '#0B0B0F' },
        textColor: '#8A8A98',
      },
      grid: {
        vertLines: { color: '#1E1E26' },
        horzLines: { color: '#1E1E26' },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: '#2A2A35' },
      timeScale: {
        borderColor: '#2A2A35',
        visible: false, // Hide time labels on RSI chart
      },
      leftPriceScale: { visible: false },
      handleScroll: false, // Disable scroll on RSI; sync from main
      handleScale: false,
    })
    rsiChartRef.current = chart
    const rsi = chart.addLineSeries({
      color: '#9B59B6',
      lineWidth: 2,
      lastValueVisible: false,
      priceLineVisible: false,
    })
    rsiSeriesRef.current = rsi
    rsi.applyOptions({
      autoscaleInfoProvider: () => ({
        priceRange: { minValue: 0, maxValue: 100 },
        margins: { above: 0.1, below: 0.1 },
      }),
    })

    // Overbought / oversold lines
    const overbought = chart.addLineSeries({
      color: '#FF4757',
      lineWidth: 1,
      lastValueVisible: false,
      priceLineVisible: false,
      lineStyle: 2,
    })
    const oversold = chart.addLineSeries({
      color: '#00D4AA',
      lineWidth: 1,
      lastValueVisible: false,
      priceLineVisible: false,
      lineStyle: 2,
    })
    ;(chart as any)._overlayLines = { overbought, oversold }

    return () => {
      chart.remove()
      rsiChartRef.current = null
      rsiSeriesRef.current = null
    }
  }, []) // Only create once

  // ── Synchronize time scales: Main → RSI ──
  useEffect(() => {
    const mainChart = mainChartRef.current
    const rsiChart = rsiChartRef.current
    if (!mainChart || !rsiChart) return

    const syncRsi = () => {
      const range = mainChart.timeScale().getVisibleLogicalRange()
      if (range) {
        rsiChart.timeScale().setVisibleLogicalRange(range)
      }
    }

    mainChart.timeScale().subscribeVisibleLogicalRangeChange(syncRsi)

    // Initial sync
    syncRsi()

    return () => {
      mainChart.timeScale().unsubscribeVisibleLogicalRangeChange(syncRsi)
    }
  }, [selectedAsset])

  // ── Load bars + volume into main chart ──
  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current) return
    if (bars.length === 0) {
      candleSeriesRef.current.setData([])
      volumeSeriesRef.current.setData([])
      return
    }

    const candleData: CandlestickData<Time>[] = bars.map((b) => ({
      time: (new Date(b.timestamp).getTime() / 1000) as Time,
      open: b.open,
      high: b.high,
      low: b.low,
      close: b.close,
    }))
    candleSeriesRef.current.setData(candleData)

    const volumeData: HistogramData<Time>[] = bars.map((b) => ({
      time: (new Date(b.timestamp).getTime() / 1000) as Time,
      value: b.volume ?? 0,
      color: b.close >= b.open ? '#00D4AA40' : '#FF475740',
    }))
    volumeSeriesRef.current.setData(volumeData)

    mainChartRef.current?.timeScale().fitContent()
  }, [bars])

  // ── Load trade markers ──
  useEffect(() => {
    if (!candleSeriesRef.current || !selectedAsset) return
    listTrades({ asset_id: selectedAsset.id })
      .then((data: any[]) => {
        if (!data.length) {
          candleSeriesRef.current?.setMarkers([])
          return
        }
        const markers: SeriesMarker<Time>[] = data.flatMap((t) => {
          const out: SeriesMarker<Time>[] = []
          if (t.entry_time) {
            out.push({
              time: (new Date(t.entry_time).getTime() / 1000) as Time,
              position: t.direction === 'long' ? 'belowBar' : 'aboveBar',
              color: t.direction === 'long' ? '#00D4AA' : '#FF4757',
              shape: t.direction === 'long' ? 'arrowUp' : 'arrowDown',
              text: t.direction === 'long' ? 'Buy' : 'Sell',
            })
          }
          if (t.exit_time) {
            out.push({
              time: (new Date(t.exit_time).getTime() / 1000) as Time,
              position: t.direction === 'long' ? 'aboveBar' : 'belowBar',
              color: t.pnl && t.pnl > 0 ? '#00D4AA' : '#FF4757',
              shape: 'arrowDown',
              text: t.pnl !== undefined ? `Close ${t.pnl > 0 ? '+' : ''}${t.pnl.toFixed(2)}` : 'Close',
            })
          }
          return out
        })
        candleSeriesRef.current?.setMarkers(markers)
      })
      .catch(() => {
        candleSeriesRef.current?.setMarkers([])
      })
  }, [selectedAsset])

  // ── Load / unload indicator overlays ──
  useEffect(() => {
    const chart = mainChartRef.current
    if (!chart || !candleSeriesRef.current || bars.length === 0) return

    // Remove all previously added indicator series
    chart.applyOptions({}) // Force re-render

    // We need to track overlay series and remove them. Since lightweight-charts
    // doesn't expose a listSeries() API, we'll store refs ourselves.
    const prevOverlays = (chart as any)._indicatorOverlays || []
    prevOverlays.forEach((s: ISeriesApi<any>) => {
      try { chart.removeSeries(s) } catch {}
    })
    ;(chart as any)._indicatorOverlays = []

    const assetId = selectedAsset?.id
    if (!assetId) return

    // Build promises for each active indicator
    const activeIndicators = indicators.filter((ind) => ind.active)
    if (activeIndicators.length === 0) {
      // Still need to update RSI if it was turned off
      if (rsiSeriesRef.current) rsiSeriesRef.current.setData([])
      const rsiChart = rsiChartRef.current as any
      if (rsiChart?._overlayLines) {
        rsiChart._overlayLines.overbought.setData([])
        rsiChart._overlayLines.oversold.setData([])
      }
      return
    }

    activeIndicators.forEach((ind) => {
      getIndicators(assetId, ind.key, ind.period, timeframe, 500)
        .then((res: any) => {
          if (!candleSeriesRef.current) return
          const values: any[] = res.values || []
          if (values.length === 0) return

          if (ind.key === 'bollinger') {
            const upper = chart.addLineSeries({
              color: ind.color,
              lineWidth: 1,
              lastValueVisible: false,
              priceLineVisible: false,
              priceScaleId: 'right',
            })
            const middle = chart.addLineSeries({
              color: '#FFFFFF',
              lineWidth: 1,
              lastValueVisible: false,
              priceLineVisible: false,
              priceScaleId: 'right',
            })
            const lower = chart.addLineSeries({
              color: ind.color,
              lineWidth: 1,
              lastValueVisible: false,
              priceLineVisible: false,
              priceScaleId: 'right',
            })
            ;(chart as any)._indicatorOverlays.push(upper, middle, lower)

            const upperData: LineData<Time>[] = []
            const middleData: LineData<Time>[] = []
            const lowerData: LineData<Time>[] = []
            values.forEach((v: any) => {
              const t = (new Date(v.timestamp).getTime() / 1000) as Time
              upperData.push({ time: t, value: v.upper })
              middleData.push({ time: t, value: v.middle })
              lowerData.push({ time: t, value: v.lower })
            })
            upper.setData(upperData)
            middle.setData(middleData)
            lower.setData(lowerData)
          } else if (ind.key === 'rsi') {
            if (!rsiSeriesRef.current) return
            const lineData: LineData<Time>[] = values.map((v: any) => ({
              time: (new Date(v.timestamp).getTime() / 1000) as Time,
              value: v.value,
            }))
            rsiSeriesRef.current.setData(lineData)

            const rsiChart = rsiChartRef.current as any
            if (rsiChart?._overlayLines && lineData.length > 0) {
              const firstT = lineData[0].time
              const lastT = lineData[lineData.length - 1].time
              rsiChart._overlayLines.overbought.setData([
                { time: firstT, value: 70 },
                { time: lastT, value: 70 },
              ])
              rsiChart._overlayLines.oversold.setData([
                { time: firstT, value: 30 },
                { time: lastT, value: 30 },
              ])
            }
          } else {
            const series = chart.addLineSeries({
              color: ind.color,
              lineWidth: 2,
              lastValueVisible: false,
              priceLineVisible: false,
              priceScaleId: 'right',
            })
            ;(chart as any)._indicatorOverlays.push(series)
            const lineData: LineData<Time>[] = values.map((v: any) => ({
              time: (new Date(v.timestamp).getTime() / 1000) as Time,
              value: v.value,
            }))
            series.setData(lineData)
          }
        })
        .catch((e) => console.error(`Indicator ${ind.key} failed:`, e))
    })
  }, [indicators, bars, selectedAsset, timeframe])

  // ── Live tick update ──
  useEffect(() => {
    if (!candleSeriesRef.current || !selectedAsset || barsRef.current.length === 0) return
    const tick = prices[selectedAsset.symbol]
    if (!tick) return

    const lastBar = barsRef.current[barsRef.current.length - 1]
    const lastTime = new Date(lastBar.timestamp).getTime() / 1000

    const update: CandlestickData<Time> = {
      time: lastTime as Time,
      open: lastBar.open,
      high: Math.max(lastBar.high, tick.price),
      low: Math.min(lastBar.low, tick.price),
      close: tick.price,
    }
    candleSeriesRef.current.update(update)

    if (volumeSeriesRef.current) {
      volumeSeriesRef.current.update({
        time: lastTime as Time,
        value: tick.volume ?? lastBar.volume ?? 0,
        color: tick.price >= lastBar.open ? '#00D4AA40' : '#FF475740',
      })
    }
  }, [prices, selectedAsset])

  // ── Auto-load history when switching asset/timeframe ──
  useEffect(() => {
    if (selectedAsset && bars.length === 0 && !loadingHistory && !barsLoading) {
      handleLoadHistory()
    }
  }, [selectedAsset, timeframe, bars.length, loadingHistory, barsLoading])

  const toggleIndicator = useCallback((key: string) => {
    setIndicators((prev) =>
      prev.map((ind) => (ind.key === key ? { ...ind, active: !ind.active } : ind))
    )
  }, [])

  const handleLoadHistory = useCallback(async () => {
    if (!selectedAsset) return
    setLoadingHistory(true)
    try {
      await loadAssetHistory(selectedAsset.id, { timeframe })
      refresh()
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingHistory(false)
    }
  }, [selectedAsset, timeframe, refresh])

  return (
    <div className="flex h-full">
      {/* Asset list */}
      <div className="w-60 bg-surface border-r border-border flex flex-col">
        <div className="px-4 py-3 border-b border-border">
          <input
            type="text"
            placeholder="Search assets..."
            className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm text-text placeholder-muted focus:outline-none focus:border-accent"
          />
        </div>
        <div className="flex-1 overflow-auto p-2 space-y-1">
          {assets.map((a) => (
            <button
              key={a.id}
              onClick={() => setSelectedAsset(a)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-left text-sm transition-colors ${
                selectedAsset?.id === a.id
                  ? 'bg-accent/10 text-accent'
                  : 'hover:bg-elevated text-text'
              }`}
            >
              <span className="font-mono font-semibold">{a.symbol}</span>
              <span className="text-[11px] text-muted">{a.asset_class}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Chart area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-surface flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <span className="text-lg font-bold font-mono">
              {selectedAsset?.symbol || 'Select an asset'}
            </span>
            {selectedAsset?.name && (
              <span className="text-sm text-muted">{selectedAsset.name}</span>
            )}
            <span className="flex items-center gap-1 ml-2">
              {connected ? (
                <Wifi size={14} className="text-accent" />
              ) : (
                <WifiOff size={14} className="text-warning" />
              )}
            </span>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={handleLoadHistory}
              disabled={!selectedAsset || loadingHistory}
              className="flex items-center gap-1.5 bg-elevated border border-border hover:border-border-hover text-muted hover:text-text px-3 py-1.5 rounded-md text-xs font-medium transition-colors disabled:opacity-50"
            >
              <Download size={14} />
              {loadingHistory ? 'Loading...' : 'Load History'}
            </button>

            {/* Timeframe buttons */}
            <div className="flex gap-1">
              {TIMEFRAMES.map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                    timeframe === tf
                      ? 'bg-accent text-bg'
                      : 'bg-elevated text-muted hover:text-text'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>

            {/* Indicator toggles */}
            <div className="flex gap-1">
              {indicators.map((ind) => (
                <button
                  key={ind.key}
                  onClick={() => toggleIndicator(ind.key)}
                  className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
                    ind.active
                      ? 'bg-accent/15 text-accent border border-accent/30'
                      : 'bg-elevated text-muted hover:text-text border border-transparent'
                  }`}
                  title={`${ind.label} (${ind.period})`}
                >
                  {ind.active ? <Eye size={12} /> : <EyeOff size={12} />}
                  {ind.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Charts */}
        <div className="flex-1 flex flex-col min-h-0 relative">
          <div ref={mainContainerRef} className="flex-[3] min-h-0" />
          <div
            ref={rsiContainerRef}
            className={`transition-all ${
              indicators.find((i) => i.key === 'rsi')?.active
                ? 'h-32 border-t border-border'
                : 'h-0 overflow-hidden border-none'
            }`}
          />
          {!selectedAsset && (
            <div className="absolute inset-0 flex items-center justify-center text-muted bg-bg/80 z-10">
              Select an asset from the sidebar to view its chart
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
