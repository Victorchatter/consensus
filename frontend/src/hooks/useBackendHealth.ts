import { useState, useEffect } from 'react'

export function useBackendHealth() {
  const [healthy, setHealthy] = useState<boolean | null>(null)
  const [latency, setLatency] = useState<number | null>(null)

  useEffect(() => {
    const check = async () => {
      try {
        const start = performance.now()
        const res = await fetch('/api/health')
        const elapsed = performance.now() - start
        setLatency(Math.round(elapsed))
        setHealthy(res.ok)
      } catch (e) {
        console.error('[useBackendHealth] Backend unreachable:', e)
        setHealthy(false)
        setLatency(null)
      }
    }
    check()
    const interval = setInterval(check, 5000)
    return () => clearInterval(interval)
  }, [])

  return { healthy, latency }
}
