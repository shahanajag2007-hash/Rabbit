import { useState } from 'react'
import { Alert, Button, Columns, Loading } from '../common/Widgets'
import { SectionHeading } from '../layout/PageHeader'
import { CATEGORY_ICONS } from '../../constants/options'
import { selectUserProfile, useStyleStore } from '../../hooks/useStyleStore'
import { api } from '../../services/api'
import { CATEGORIES, type Category, type OutfitItem } from '../../types'
import { money } from '../../utils/format'

interface ReplaceState {
  category: Category
  loading: boolean
  candidates: OutfitItem[]
  error: string | null
}

/**
 * "Outfit Item Breakdown" card (05_Outfit_Details.py) with the replacement / cheaper-option
 * logic of 06_Customize_My_Outfit.py inlined, so Replace no longer needs a separate page.
 */
export function OutfitBreakdown({ total }: { total: number }) {
  const s = useStyleStore()
  const items = s.selected_outfit?.items ?? {}
  const [replace, setReplace] = useState<ReplaceState | null>(null)
  const [message, setMessage] = useState<{ category: Category; kind: 'success' | 'warning' | 'error'; text: string } | null>(null)

  async function openReplace(category: Category) {
    setMessage(null)
    if (replace?.category === category) {
      setReplace(null)
      return
    }
    if (!s.selected_outfit) return
    setReplace({ category, loading: true, candidates: [], error: null })
    try {
      const r = await api.replacements(category, s.selected_outfit, selectUserProfile(useStyleStore.getState()))
      setReplace({ category, loading: false, candidates: r.candidates, error: null })
    } catch (e) {
      setReplace({ category, loading: false, candidates: [], error: (e as Error).message })
    }
  }

  async function cheaper(category: Category, item: OutfitItem) {
    setReplace(null)
    try {
      const r = await api.cheaper(item)
      if (r.item) {
        s.setOutfitItem(category, r.item)
        setMessage({ category, kind: 'success', text: 'Found a cheaper alternative!' })
      } else {
        setMessage({ category, kind: 'warning', text: 'No cheaper compatible alternative found.' })
      }
    } catch (e) {
      setMessage({ category, kind: 'error', text: (e as Error).message })
    }
  }

  return (
    <div className="outfit-breakdown-card">
      <SectionHeading title="Outfit Item Breakdown" icon="🛍️" />
      {CATEGORIES.map((cat) => {
        const item = items[cat]
        if (!item) return null
        const locked = s.locked_items[cat]
        return (
          <div key={cat}>
            <div className="breakdown-row">
              <div className="item-left">
                <div className="item-icon-box">{CATEGORY_ICONS[cat] ?? '✨'}</div>
                <div>
                  <div className="item-title">
                    {item.item_name} {locked ? '🔒 (Locked)' : ''}
                  </div>
                  <div className="item-subtitle">
                    {cat} · {item.colour} · {item.fabric_tag ?? 'N/A'}
                  </div>
                </div>
              </div>
              <div className="item-price">{money(item.price)}</div>
            </div>
            <Columns n={4} className="keep" style={{ margin: '0.6rem 0 0.4rem' }}>
              <Button full title={`[-] Remove ${cat}`} onClick={() => s.removeOutfitItem(cat)}>
                [-] Remove {cat}
              </Button>
              <Button full title={`Replace ${cat}`} disabled={locked} onClick={() => openReplace(cat)}>
                Replace {cat}
              </Button>
              <Button full title="Cheaper Option" disabled={locked} onClick={() => cheaper(cat, item)}>
                Cheaper Option
              </Button>
              <Button full onClick={() => s.toggleLock(cat)}>
                {locked ? 'Unlock Item' : '🔒 Lock Item'}
              </Button>
            </Columns>
            {locked && <div className="caption">Item is locked. Unlock to replace.</div>}
            {message?.category === cat && <Alert kind={message.kind}>{message.text}</Alert>}
            {replace?.category === cat && (
              <div className="bordered gap-sm" style={{ margin: '0.5rem 0 0.8rem' }}>
                <div style={{ fontWeight: 600 }}>Select Replacement:</div>
                {replace.loading && <Loading label="Finding compatible replacements…" />}
                {replace.error && <Alert kind="error">{replace.error}</Alert>}
                {!replace.loading && !replace.error && replace.candidates.length === 0 && (
                  <Alert kind="warning">No suitable replacement found for this item.</Alert>
                )}
                {replace.candidates.map((cand) => (
                  <div key={String(cand.item_id)} className="row between">
                    <div>
                      <strong>{cand.item_name}</strong>
                      <div className="muted">
                        {cand.colour} · {money(cand.price)}
                      </div>
                    </div>
                    <Button
                      onClick={() => {
                        s.setOutfitItem(cat, cand)
                        setReplace(null)
                      }}
                    >
                      Use
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })}
      <div className="outfit-total-row">
        <div className="total-label">TOTAL OUTFIT PRICE</div>
        <div className="total-amount">{money(total)}</div>
      </div>
    </div>
  )
}
