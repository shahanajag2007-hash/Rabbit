import { useState, type ReactNode } from 'react'

interface Props {
  label: string
  selected: boolean
  onSelect: () => void
  /** Rendered thumbnail of the actual asset/result. */
  image?: string
  /** Colour swatch (skin tone, hair colour, garment colour) when there is no image. */
  swatch?: string
  disabled?: boolean
  note?: string
  /** Toggle semantics (accessories) instead of single choice. */
  toggle?: boolean
  size?: 'md' | 'sm'
  children?: ReactNode
}

/** Visual customisation option: thumbnail or swatch, name, selected indicator, disabled state. */
export function OptionCard({ label, selected, onSelect, image, swatch, disabled, note, toggle, size = 'md', children }: Props) {
  const [broken, setBroken] = useState(false)
  return (
    <button
      type="button"
      className={`option-card ${size}${selected ? ' selected' : ''}${disabled ? ' disabled' : ''}`}
      onClick={disabled ? undefined : onSelect}
      aria-pressed={toggle || !disabled ? selected : undefined}
      aria-disabled={disabled || undefined}
      title={disabled && note ? `${label} — ${note}` : label}
    >
      <span className="option-thumb">
        {image && !broken ? (
          <img src={image} alt="" loading="lazy" onError={() => setBroken(true)} />
        ) : swatch ? (
          <span className="option-swatch" style={{ background: swatch }} />
        ) : (
          <span className="option-glyph" aria-hidden="true">
            {disabled ? '⊘' : label.slice(0, 1)}
          </span>
        )}
        {children}
        {selected && <span className="option-check" aria-hidden="true">✓</span>}
      </span>
      <span className="option-label">{label}</span>
      {disabled && note && <span className="option-note">{note}</span>}
    </button>
  )
}

export function OptionSection({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="option-section">
      <div className="option-section-head">
        <h3>{title}</h3>
        {hint && <span className="muted">{hint}</span>}
      </div>
      <div className="option-grid">{children}</div>
    </section>
  )
}
