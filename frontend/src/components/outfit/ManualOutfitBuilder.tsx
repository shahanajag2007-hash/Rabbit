import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Loading } from '../common/Widgets'
import { SectionHeading } from '../layout/PageHeader'
import { CATEGORY_ICONS } from '../../constants/options'
import { selectUserProfile, useStyleStore } from '../../hooks/useStyleStore'
import { api } from '../../services/api'
import { CATEGORIES, type BuilderStep, type Category, type OutfitItem } from '../../types'
import { money } from '../../utils/format'
import { ProductCard } from './ProductCard'

const STEP_TITLES: Record<Category, string> = {
  Top: 'Choose a top',
  Bottom: 'Choose matching bottom wear',
  Shoes: 'Choose footwear',
  Accessory: 'Add an accessory (optional)',
}
const PAGE = 8

/**
 * "Choose Your Style Manually" — build an outfit one category at a time. Each step asks the
 * backend (POST /api/builder/options) for products that suit the picks so far and fit the budget
 * that is left. Going back to an earlier step keeps later picks; if a change pushes the outfit over
 * budget, the later picks that no longer fit are dropped with a note.
 */
export function ManualOutfitBuilder() {
  const s = useStyleStore()
  const navigate = useNavigate()
  const picks = s.builder_items
  const step = s.builder_step
  const [data, setData] = useState<BuilderStep | null>(null)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const profileKey = JSON.stringify(selectUserProfile(s))
  const othersKey = JSON.stringify(CATEGORIES.filter((c) => c !== step).map((c) => picks[c]?.item_id ?? null))
  const total = CATEGORIES.reduce((sum, c) => sum + Number(picks[c]?.price ?? 0), 0)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)
    const selected = Object.fromEntries(CATEGORIES.filter((c) => c !== step && picks[c]).map((c) => [c, picks[c]]))
    api
      .builderOptions(JSON.parse(profileKey), step, selected, offset, PAGE)
      .then((r) => alive && setData(r))
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [step, offset, othersKey, profileKey]) // eslint-disable-line react-hooks/exhaustive-deps

  function goTo(category: Category) {
    setOffset(0)
    setNotice(null)
    s.set({ builder_step: category })
  }

  function choose(category: Category, item: OutfitItem) {
    const next: Partial<Record<Category, OutfitItem>> = { ...picks, [category]: item }
    // A kurta set / saree / dress already includes the bottom wear.
    if (category === 'Top' && item.covers_bottom) delete next.Bottom
    // Revalidate later picks against the budget; drop the last ones until the outfit fits again.
    const later = CATEGORIES.slice(CATEGORIES.indexOf(category) + 1).reverse()
    const dropped: string[] = []
    const sum = () => CATEGORIES.reduce((acc, c) => acc + Number(next[c]?.price ?? 0), 0)
    for (const c of later) {
      if (sum() <= s.budget) break
      if (next[c]) {
        dropped.push(next[c]!.item_name)
        delete next[c]
      }
    }
    setNotice(dropped.length ? `Removed ${dropped.join(', ')} so the outfit stays within your ${money(s.budget)} budget.` : null)
    const following = CATEGORIES.slice(CATEGORIES.indexOf(category) + 1).find((c) => !next[c] && !(c === 'Bottom' && next.Top?.covers_bottom))
    setOffset(0)
    s.set({ builder_items: next, builder_step: following ?? category })
  }

  function clear(category: Category) {
    const next = { ...picks }
    delete next[category]
    s.set({ builder_items: next })
  }

  const bottomCovered = Boolean(picks.Top?.covers_bottom)
  const complete = picks.Top && (picks.Bottom || bottomCovered) && picks.Shoes

  return (
    <div className="panel stack">
      <SectionHeading title="Choose Your Style Manually" icon="🧩" />
      <div className="caption">
        Build your own outfit one piece at a time. Each step shows real products that go with what you have already picked and fit the budget you have
        left.
      </div>

      <div className="row" role="tablist" aria-label="Outfit builder steps">
        {CATEGORIES.map((c, i) => (
          <button
            key={c}
            type="button"
            role="tab"
            aria-selected={step === c}
            className={`chip-toggle${step === c ? ' on' : ''}`}
            onClick={() => goTo(c)}
            disabled={(c === 'Bottom' && bottomCovered) || (i > 0 && !picks[CATEGORIES[i - 1]] && !picks[c] && !(CATEGORIES[i - 1] === 'Bottom' && bottomCovered))}
            title={c === 'Bottom' && bottomCovered ? 'Included in the set you picked' : undefined}
          >
            {i + 1}. {CATEGORY_ICONS[c]} {c} {picks[c] || (c === 'Bottom' && bottomCovered) ? '✓' : ''}
          </button>
        ))}
      </div>

      <div className="mini-card gap-sm">
        {CATEGORIES.filter((c) => picks[c]).length === 0 ? (
          <span className="muted">Nothing picked yet — start with a top.</span>
        ) : (
          CATEGORIES.filter((c) => picks[c]).map((c) => (
            <div key={c} className="row between" style={{ fontSize: '0.86rem' }}>
              <span>
                {CATEGORY_ICONS[c]} <strong>{c}:</strong> {picks[c]!.item_name}
              </span>
              <span className="row">
                <strong>{money(picks[c]!.price)}</strong>
                <button type="button" className="chip-toggle" onClick={() => goTo(c)}>
                  Change
                </button>
                <button type="button" className="chip-toggle" onClick={() => clear(c)} aria-label={`Remove ${c}`}>
                  ✕
                </button>
              </span>
            </div>
          ))
        )}
        <div className="row between" style={{ fontWeight: 800 }}>
          <span>Total {money(total)}</span>
          <span style={{ color: total > s.budget ? '#dc2626' : '#16a34a' }}>
            {total > s.budget ? `Over budget by ${money(total - s.budget)}` : `${money(s.budget - total)} left of ${money(s.budget)}`}
          </span>
        </div>
      </div>

      {notice && <Alert kind="warning">{notice}</Alert>}

      <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#1d1528' }}>
        Step {CATEGORIES.indexOf(step) + 1}: {STEP_TITLES[step]}
      </div>
      {data?.notes.map((note) => (
        <Alert key={note} kind="warning">
          {note}
        </Alert>
      ))}
      {loading && !data && <Loading label={`Finding ${step.toLowerCase()} options…`} />}
      {error && <Alert kind="error">{error}</Alert>}
      {data && !error && data.items.length === 0 && <Alert kind="warning">No {step.toLowerCase()} products match your preferences right now.</Alert>}

      <div className="product-grid-4" style={{ opacity: loading ? 0.55 : 1, transition: 'opacity 0.2s' }}>
        {data?.category === step &&
          data.items.map((item) => {
            const chosen = picks[step]?.item_id === item.item_id
            return (
              <div key={String(item.item_id)} className="gap-sm">
                <ProductCard item={item} />
                <div className="caption" style={{ marginTop: '-0.8rem' }}>
                  {item.available_sizes && item.available_sizes.length > 0 ? `Sizes: ${item.available_sizes.join(', ')}` : 'Size: not listed'}
                </div>
                <Button full primary={!chosen} disabled={chosen} onClick={() => choose(step, item)}>
                  {chosen ? '✓ Selected' : `Select ${step}`}
                </Button>
              </div>
            )
          })}
      </div>

      <div className="row between">
        <div className="row">
          <Button disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - PAGE))}>
            ← Previous
          </Button>
          <Button disabled={!data || offset + PAGE >= data.total || loading} onClick={() => setOffset(offset + PAGE)}>
            More {step.toLowerCase()} options →
          </Button>
          {step === 'Accessory' && !picks.Accessory && <span className="muted">Accessories are optional.</span>}
        </div>
        <Button
          primary
          disabled={!complete}
          title={complete ? undefined : 'Pick a top (or a set), bottom wear and footwear first'}
          onClick={() => {
            s.selectOutfit({ items: { ...picks } })
            navigate('/complete-look')
          }}
        >
          Use This Outfit →
        </Button>
      </div>
    </div>
  )
}
