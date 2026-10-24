import { useState } from 'react'
import { Alert } from '../common/Widgets'
import { CATEGORY_ICONS } from '../../constants/options'
import { useStyleStore } from '../../hooks/useStyleStore'
import { api } from '../../services/api'
import { CATEGORIES, type Category, type ColourOption } from '../../types'
import { carrySize } from '../../utils/variants'
import { colourToHex } from './garmentMapping'

/**
 * "Preview colours": the colours each product is actually sold in (from the brand's variants).
 * Choosing one switches the outfit to that real variant — image, price and product link follow —
 * and the avatar / try-on shows it. Products with a single colour (e.g. the original sample catalogue)
 * show only that colour; no colours are invented.
 */
export function GarmentColourPreview({ mode = 'avatar' }: { mode?: 'avatar' | 'photo' }) {
  const items = useStyleStore((s) => s.selected_outfit?.items ?? {})
  const locked = useStyleStore((s) => s.locked_items)
  const setOutfitItem = useStyleStore((s) => s.setOutfitItem)
  const [busy, setBusy] = useState<Category | null>(null)
  const [message, setMessage] = useState<{ kind: 'warning' | 'error' | 'success'; text: string } | null>(null)

  const categories = CATEGORIES.filter((c) => items[c])
  if (!categories.length) return null

  async function pick(cat: Category, option: ColourOption) {
    const current = items[cat]
    if (!current || String(current.item_id) === option.item_id) return
    setBusy(cat)
    setMessage(null)
    try {
      const { item } = await api.product(option.item_id)
      const { item: next, lost } = carrySize(item, current.selected_size)
      setOutfitItem(cat, next)
      setMessage(
        lost
          ? { kind: 'warning', text: `Size ${current.selected_size} is not available in ${option.colour_label}. Please pick a size for the ${cat.toLowerCase()}.` }
          : { kind: 'success', text: `${cat} switched to ${option.colour_label} (${item.item_name}).` },
      )
    } catch (e) {
      setMessage({ kind: 'error', text: (e as Error).message })
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="mini-card gap-sm" style={{ marginTop: '0.8rem' }}>
      <div className="page-kicker">Preview colours {mode === 'avatar' ? 'on the avatar' : 'for your try-on'}</div>
      {categories.map((cat) => {
        const item = items[cat]!
        const options: ColourOption[] = item.colour_options?.length
          ? item.colour_options
          : [{ item_id: String(item.item_id), colour: item.colour, colour_label: item.colour_label ?? item.colour, image: item.image_url ?? '', price: Number(item.price) }]
        return (
          <div key={cat} className="row">
            <span style={{ width: 92, fontSize: '0.8rem', fontWeight: 700 }}>
              {CATEGORY_ICONS[cat]} {cat}
            </span>
            {options.map((o) => {
              const on = o.item_id === String(item.item_id)
              const disabled = busy !== null || (locked[cat] && !on)
              return (
                <button
                  key={o.item_id}
                  type="button"
                  title={`${o.colour_label}${locked[cat] && !on ? ' (unlock the item to change colour)' : ''}`}
                  aria-label={`${cat}: ${o.colour_label}`}
                  aria-pressed={on}
                  disabled={disabled}
                  className={`colour-dot${on ? ' on' : ''}`}
                  style={{ background: colourToHex(o.colour), opacity: disabled && !on ? 0.5 : 1 }}
                  onClick={() => pick(cat, o)}
                />
              )
            })}
            <span className="muted">
              {item.colour_label ?? item.colour}
              {options.length === 1 ? ' (only colour available)' : ''}
            </span>
          </div>
        )
      })}
      {message && <Alert kind={message.kind}>{message.text}</Alert>}
      <div className="muted">Colours are the brand's in-stock variants; switching updates the item, price and link.</div>
    </div>
  )
}
