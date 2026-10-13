import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { Meta } from '../types'

let cache: Meta | null = null

/** Reference data from demo_data.py / skin_tone.py (palettes, chips, fabric notes). */
export function useMeta(): { meta: Meta | null; error: string | null } {
  const [meta, setMeta] = useState<Meta | null>(cache)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    if (cache) return
    let alive = true
    api
      .meta()
      .then((m) => {
        cache = m
        if (alive) setMeta(m)
      })
      .catch((e: Error) => alive && setError(e.message))
    return () => {
      alive = false
    }
  }, [])
  return { meta, error }
}
