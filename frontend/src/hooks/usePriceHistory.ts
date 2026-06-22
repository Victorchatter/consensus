import { useState, useEffect } from 'react'
import { getAssetBars } from '@/services/api'
import type { PriceBar } from '@/types'

export function usePriceHistory(assetId: number | null, timeframe = '1d', limit = 500) {
  const [bars, setBars] = useState<PriceBar[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!assetId) {
      setBars([])
      return
    }
    setLoading(true)
    setError(null)
    getAssetBars(assetId, timeframe, limit)
      .then((data) => {
        setBars(data)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [assetId, timeframe, limit])

  const refresh = () => {
    if (!assetId) return
    setLoading(true)
    getAssetBars(assetId, timeframe, limit)
      .then((data) => setBars(data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  return { bars, loading, error, refresh }
}
