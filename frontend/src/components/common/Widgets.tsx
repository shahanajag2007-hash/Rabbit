import type { ReactNode } from 'react'

type AlertKind = 'success' | 'info' | 'warning' | 'error'

export function Alert({ kind, children }: { kind: AlertKind; children: ReactNode }) {
  return (
    <div className={`alert ${kind}`} role={kind === 'error' || kind === 'warning' ? 'alert' : 'status'}>
      {children}
    </div>
  )
}

export function Loading({ label }: { label: string }) {
  return (
    <div className="loading-row" role="status">
      <span className="spinner" /> {label}
    </div>
  )
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  primary?: boolean
  full?: boolean
}

export function Button({ primary, full, className = '', type = 'button', ...rest }: ButtonProps) {
  return <button type={type} className={`st-btn${primary ? ' primary' : ''}${full ? ' full' : ''} ${className}`.trim()} {...rest} />
}

export function Columns({ n = 2, gapLg, className = '', style, children }: { n?: number; gapLg?: boolean; className?: string; style?: React.CSSProperties; children: ReactNode }) {
  return (
    <div className={`cols${gapLg ? ' gap-lg' : ''} ${className}`.trim()} style={{ ['--n' as string]: n, ...style }}>
      {children}
    </div>
  )
}

interface SliderProps {
  label: string
  min: number
  max: number
  step?: number
  value: number
  onChange: (value: number) => void
  format?: (value: number) => string
}

/** st.slider look-alike: label, red value marker, range input. */
export function Slider({ label, min, max, step = 1, value, onChange, format = String }: SliderProps) {
  const id = `slider-${label.replace(/\W+/g, '-').toLowerCase()}`
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="slider-value">{format(value)}</div>
      <input
        id={id}
        className="st-slider"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  )
}

interface MultiSelectProps {
  label: string
  options: string[]
  value: string[]
  onChange: (value: string[]) => void
}

export function MultiSelect({ label, options, value, onChange }: MultiSelectProps) {
  return (
    <div className="field">
      <span className="field-label">{label}</span>
      <div className="chip-select" role="group" aria-label={label}>
        {options.map((option) => {
          const on = value.includes(option)
          return (
            <button
              key={option}
              type="button"
              aria-pressed={on}
              className={`chip-toggle${on ? ' on' : ''}`}
              onClick={() => onChange(on ? value.filter((v) => v !== option) : [...value, option])}
            >
              {on ? '✓ ' : ''}
              {option}
            </button>
          )
        })}
      </div>
    </div>
  )
}

/** ui_theme.render_empty_panel */
export function EmptyPanel({ title, text, icon = '✨', children }: { title: string; text: string; icon?: string; children?: ReactNode }) {
  return (
    <div className="panel">
      <div className="row" style={{ marginBottom: '0.5rem' }}>
        <div style={{ fontSize: '1.6rem' }}>{icon}</div>
        <div style={{ fontWeight: 800, color: '#21182f' }}>{title}</div>
      </div>
      <div style={{ color: '#5d5867', fontSize: '0.92rem' }}>{text}</div>
      {children && <div style={{ marginTop: '0.9rem' }}>{children}</div>}
    </div>
  )
}
