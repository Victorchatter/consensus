import { useState, useEffect } from 'react'
import { listAssets } from '@/services/api'
import type { Asset } from '@/types'

export function useAssets(params?: Record<string, string>) {
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    listAssets(params)
      .then((data) => {
        if (!cancelled) setAssets(data)
      })
      .catch((e) => {
        if (!cancelled) {
          console.error('[useAssets] Failed to load assets:', e)
          setError(e.message)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [JSON.stringify(params)])

  return { assets, loading, error }
}
