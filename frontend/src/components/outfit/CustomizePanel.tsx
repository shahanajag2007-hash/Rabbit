import { useEffect, useState } from 'react'
import { Alert, Button, Loading } from '../common/Widgets'
import { SectionHeading } from '../layout/PageHeader'
import { CATEGORY_ICONS } from '../../constants/options'
import { selectUserProfile, useStyleStore } from '../../hooks/useStyleStore'
import { api } from '../../services/api'
import { CATEGORIES, type Category, type ScoreResult } from '../../types'
import { money, pyFloat } from '../../utils/format'

/**
 * "Make It Yours" — the lock / regenerate / budget logic of 06_Customize_My_Outfit.py,
 * which also replaces the hardcoded 07_Budget_Stylist.py with the real budget figures and the
 * shopping-service alternatives.
 */
export function CustomizePanel({ score, id }: { score: ScoreResult; id?: string }) {
  const s = useStyleStore()
  const outfit = s.selected_outfit
  const budget = s.budget
  const total = score.total_price
  const diff = budget - total
  const lockedCats = CATEGORIES.filter((c) => s.locked_items[c])
  const signature = JSON.stringify([CATEGORIES.map((c) => outfit?.items[c]?.item_id ?? null), lockedCats, budget])
  const [shoppingLoading, setShoppingLoading] = useState(false)
  const [shoppingError, setShoppingError] = useState<string | null>(null)
  const [regenerating, setRegenerating] = useState(false)
  const [regenError, setRegenError] = useState<string | null>(null)

  // Search platforms for cheaper alternatives when over budget (cached per outfit signature, like the Streamlit session cache).
  useEffect(() => {
    if (!outfit || diff >= 0) return
    const cached = useStyleStore.getState()
    if (cached.shopping_results && cached.shopping_signature === signature) return
    let alive = true
    setShoppingLoading(true)
    setShoppingError(null)
    api
      .shoppingAlternatives(outfit, budget, lockedCats)
      .then((r) => alive && s.set({ shopping_results: r, shopping_signature: signature }))
      .catch((e: Error) => alive && setShoppingError(e.message))
      .finally(() => alive && setShoppingLoading(false))
    return () => {
      alive = false
    }
  }, [signature, diff < 0]) // eslint-disable-line react-hooks/exhaustive-deps

  async function regenerate() {
    if (!outfit) return
    setRegenerating(true)
    setRegenError(null)
    try {
      const r = await api.regenerate(outfit, selectUserProfile(useStyleStore.getState()), lockedCats)
      if (r.outfit) {
        s.set({ selected_outfit: r.outfit, shopping_results: null, garment_colour_overrides: {} })
        if (r.notes?.length) setRegenError(r.notes.join(' '))
      } else setRegenError(r.notes?.length ? r.notes.join(' ') : 'No different outfit could be generated with the current locks.')
    } catch (e) {
      setRegenError((e as Error).message)
    } finally {
      setRegenerating(false)
    }
  }

  const alternatives = s.shopping_signature === signature ? s.shopping_results?.alternatives ?? {} : {}
  const altEntries = Object.entries(alternatives) as [Category, NonNullable<(typeof alternatives)[Category]>][]
  const totalSavings = altEntries.reduce((sum, [, alt]) => sum + alt.savings, 0)
  const pct = Math.max(0, Math.min(100, (total / Math.max(budget, 1)) * 100))

  return (
    <div className="panel stack" id={id}>
      <SectionHeading title="Make It Yours · Lock what you love" icon="🔒" />
      <div className="caption">Keep what you love and personalize the rest of your outfit.</div>
      <div className="row">
        {CATEGORIES.filter((c) => outfit?.items[c]).map((c) => (
          <label key={c} className="st-check mini-card">
            <input type="checkbox" checked={s.locked_items[c]} onChange={() => s.toggleLock(c)} />
            {CATEGORY_ICONS[c]} Lock {c}
          </label>
        ))}
      </div>

      <div style={{ background: diff >= 0 ? '#f0fdf4' : '#fef2f2', padding: '1rem', borderRadius: 12 }} className="gap-sm">
        <div>
          <strong>Total Outfit Price:</strong> {money(total)} (Budget: {money(budget)})
        </div>
        <div className="progress-bar" aria-label="Budget used">
          <span className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        {diff < 0 ? (
          <>
            <span style={{ color: '#dc2626', fontWeight: 'bold' }}>Over budget by {money(Math.abs(diff))}</span>
            {shoppingLoading && <Loading label="Searching multi-platform for cheaper alternatives..." />}
            {shoppingError && <Alert kind="error">{shoppingError}</Alert>}
            {!shoppingLoading && !shoppingError && s.shopping_signature === signature && (
              altEntries.length > 0 ? (
                <div className="md-list">
                  <p><strong>Platform Alternatives Found:</strong></p>
                  {altEntries.map(([cat, alt]) => (
                    <p key={cat}>
                      • <strong>{cat}</strong>: <em>Current</em>: {money(alt.price + alt.savings)} → <em>Alternative</em>: {money(alt.price)} · <em>Platform</em>:{' '}
                      {alt.platform} | <em>Type</em>: {alt.match_type} · <em>Savings</em>: {money(alt.savings)} ·{' '}
                      <a className="inline-link" href={alt.url} target="_blank" rel="noreferrer noopener">
                        View on {alt.platform}
                      </a>
                    </p>
                  ))}
                  <p><strong>New Total:</strong> {money(total - totalSavings)}</p>
                  <p>
                    {budget - (total - totalSavings) >= 0 ? (
                      <><strong>Remaining Budget:</strong> {money(budget - (total - totalSavings))}</>
                    ) : (
                      <><strong>Still over budget by:</strong> {money(Math.abs(budget - (total - totalSavings)))}</>
                    )}
                  </p>
                  <p><em>You can buy these alternatives instead to keep the outfit within your budget.</em></p>
                </div>
              ) : (
                <div className="md-list">
                  <p>
                    • <em>No cheaper compatible alternatives found on external platforms.</em>
                    {s.shopping_results?.configured_providers.length === 0 && !s.shopping_results?.mock_mode && (
                      <span className="muted"> (No shopping provider is configured on the backend — see README.)</span>
                    )}
                  </p>
                  <p className="muted">Tip: use “Cheaper Option” on an item or “Regenerate Unlocked Items” to stay within budget.</p>
                </div>
              )
            )}
          </>
        ) : (
          <span style={{ color: '#16a34a', fontWeight: 'bold' }}>Under budget by {money(diff)}</span>
        )}
        <div>
          <strong>Compatibility Score:</strong> {pyFloat(score.score)}/100
        </div>
      </div>

      <Button primary full disabled={regenerating} onClick={regenerate}>
        {regenerating ? 'Regenerating…' : '✨ Regenerate Unlocked Items'}
      </Button>
      {regenError && <Alert kind="error">{regenError}</Alert>}
    </div>
  )
}
