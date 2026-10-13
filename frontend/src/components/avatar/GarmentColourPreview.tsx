import { CATEGORY_ICONS } from '../../constants/options'
import { useStyleStore } from '../../hooks/useStyleStore'
import { CATEGORIES, type Swatch } from '../../types'
import { colourToHex } from './garmentMapping'

/**
 * Lets the user preview an item in other colours on the 3D avatar.
 * This is display-only: the recommended item (and its price/score) are not changed,
 * because the dataset has no per-colour variants of an item.
 */
export function GarmentColourPreview({ palette }: { palette: Swatch[] }) {
  const items = useStyleStore((s) => s.selected_outfit?.items ?? {})
  const overrides = useStyleStore((s) => s.garment_colour_overrides)
  const set = useStyleStore((s) => s.set)

  const categories = CATEGORIES.filter((c) => items[c])
  if (!categories.length) return null

  return (
    <div className="mini-card gap-sm" style={{ marginTop: '0.8rem' }}>
      <div className="page-kicker">Preview colours on the avatar</div>
      {categories.map((cat) => {
        const original = colourToHex(items[cat]!.colour)
        const current = overrides[cat] ?? original
        const options = [{ name: `${items[cat]!.colour} (recommended)`, hex: original }, ...palette.filter((p) => p.hex.toLowerCase() !== original)]
        return (
          <div key={cat} className="row">
            <span style={{ width: 92, fontSize: '0.8rem', fontWeight: 700 }}>
              {CATEGORY_ICONS[cat]} {cat}
            </span>
            {options.map((o) => (
              <button
                key={o.hex}
                type="button"
                title={o.name}
                aria-label={`${cat}: ${o.name}`}
                aria-pressed={current === o.hex}
                className={`colour-dot${current === o.hex ? ' on' : ''}`}
                style={{ background: o.hex }}
                onClick={() => {
                  const next = { ...overrides }
                  if (o.hex === original) delete next[cat]
                  else next[cat] = o.hex
                  set({ garment_colour_overrides: next })
                }}
              />
            ))}
          </div>
        )
      })}
      <div className="muted">Display only — the recommended item, price and score stay the same.</div>
    </div>
  )
}
