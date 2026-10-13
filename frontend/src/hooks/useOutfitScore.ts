import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { ScoreResult } from '../types'
import { selectUserProfile, useStyleStore } from './useStyleStore'

/** recommender.score_single_outfit() for the selected outfit, recomputed when items or profile change. */
export function useOutfitScore() {
  const outfit = useStyleStore((s) => s.selected_outfit)
  const profileKey = useStyleStore((s) => JSON.stringify(selectUserProfile(s)))
  const [score, setScore] = useState<ScoreResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const itemsKey = JSON.stringify(outfit?.items ?? {})

  useEffect(() => {
    const items = JSON.parse(itemsKey)
    if (!Object.keys(items).length) {
      setScore(null)
      return
    }
    let alive = true
    setLoading(true)
    setError(null)
    api
      .score({ items }, JSON.parse(profileKey))
      .then((r) => alive && setScore(r))
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [itemsKey, profileKey])

  return { score, error, loading }
}
