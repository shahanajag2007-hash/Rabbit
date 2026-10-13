import { TopNav } from '../navigation/TopNav'

interface Props {
  title: string
  subtitle: string
  badge?: string
}

/** ui_theme.render_page_header: top nav + brand shell. */
export function PageHeader({ title, subtitle, badge = 'StyleAI' }: Props) {
  return (
    <>
      <TopNav />
      <div className="brand-shell">
        <div className="brand-row">
          <div className="brand-left">
            <div className="brand-mark">✦</div>
            <div>
              <h1 className="brand-title">{title}</h1>
              <p className="brand-sub">{subtitle}</p>
            </div>
          </div>
          <div className="nav-pill">{badge}</div>
        </div>
      </div>
    </>
  )
}

/** ui_theme.render_step_progress */
export function StepProgress({ step, total = 5, title }: { step: number; total?: number; title: string }) {
  return (
    <div className="step-indicator-bar">
      <div className="step-badge">
        STEP {step} OF {total} · {title}
      </div>
      <div className="step-dots" aria-hidden="true">
        {Array.from({ length: total }, (_, i) => (
          <div key={i} className={`dot${i + 1 === step ? ' active' : ''}`} />
        ))}
      </div>
    </div>
  )
}

/** ui_theme.render_section_heading */
export function SectionHeading({ title, icon = '✨' }: { title: string; icon?: string }) {
  return (
    <div className="page-kicker section-heading">
      {icon} {title}
    </div>
  )
}

/** The large gradient intro card used at the top of each onboarding stage. */
export function HeroPanel({ kicker, title, children }: { kicker: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="hero-panel">
      <div className="page-kicker">{kicker}</div>
      <h2 style={{ fontSize: 'clamp(1.4rem, 2.2vw, 2.2rem)', fontWeight: 800, color: '#1f162d', marginTop: '0.2rem' }}>{title}</h2>
      {children && <div style={{ color: '#5f5a6d', fontSize: '0.92rem', marginTop: '0.3rem' }}>{children}</div>}
    </div>
  )
}
