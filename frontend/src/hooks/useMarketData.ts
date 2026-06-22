import { useEffect, useRef, useState, useCallback } from 'react'
import { getAssetQuote } from '@/services/api'

export interface LiveTick {
  symbol: string
  price: number
  bid?: number
  ask?: number
  volume?: number
  timestamp: string
}

export function useMarketData(symbols: string[], assetId?: number | null) {
  const [prices, setPrices] = useState<Record<string, LiveTick>>({})
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const connect = useCallback(() => {
    // Don't create duplicate connections
    if (wsRef.current && (wsRef.current.readyState === WebSocket.CONNECTING || wsRef.current.readyState === WebSocket.OPEN)) {
      return
    }

    const wsUrl = `ws://${window.location.hostname}:8000/ws/market-data`
    let ws: WebSocket
    try {
      ws = new WebSocket(wsUrl)
    } catch {
      return
    }
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      // Stop polling if we were polling
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
      if (symbols.length > 0) {
        try {
          ws.send(JSON.stringify({ action: 'subscribe', symbols }))
        } catch { /* ignore */ }
      }
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'tick') {
          setPrices((prev) => ({
            ...prev,
            [data.symbol]: {
              symbol: data.symbol,
              price: data.price ?? 0,
              bid: data.bid,
              ask: data.ask,
              volume: data.volume,
              timestamp: data.timestamp,
            },
          }))
        } else if (data.type === 'snapshot') {
          const snapshot: Record<string, LiveTick> = {}
          for (const [sym, info] of Object.entries(data.prices)) {
            const i = info as any
            snapshot[sym] = {
              symbol: sym,
              price: i.price ?? 0,
              bid: i.bid,
              ask: i.ask,
              volume: undefined,
              timestamp: new Date().toISOString(),
            }
          }
          setPrices((prev) => ({ ...prev, ...snapshot }))
        }
      } catch {
        // Ignore malformed messages
      }
    }

    ws.onclose = () => {
      setConnected(false)
    }

    ws.onerror = () => {
      setConnected(false)
    }
  }, [symbols])

  const startPolling = useCallback(() => {
    if (!assetId) return
    if (pollIntervalRef.current) return

    const poll = async () => {
      try {
        const quote = await getAssetQuote(assetId)
        if (quote && symbols[0]) {
          setPrices((prev) => ({
            ...prev,
            [symbols[0]]: {
              symbol: symbols[0],
              price: quote.last_price ?? 0,
              bid: quote.bid,
              ask: quote.ask,
              volume: quote.volume,
              timestamp: quote.timestamp ?? new Date().toISOString(),
            },
          }))
        }
      } catch {
        // Ignore polling errors
      }
    }

    poll() // immediate first call
    pollIntervalRef.current = setInterval(poll, 5000)
  }, [assetId, symbols])

  useEffect(() => {
    connect()
    const reconnectInterval = setInterval(() => {
      if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
        connect()
      }
    }, 5000)

    return () => {
      clearInterval(reconnectInterval)
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connect])

  useEffect(() => {
    if (connected && wsRef.current && symbols.length > 0) {
      try {
        wsRef.current.send(JSON.stringify({ action: 'subscribe', symbols }))
      } catch { /* ignore */ }
    }
  }, [connected, symbols])

  // Fallback polling when WebSocket is disconnected
  useEffect(() => {
    if (!connected && assetId) {
      startPolling()
    } else {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
    }
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
    }
  }, [connected, assetId, startPolling])

  return { prices, connected }
}
