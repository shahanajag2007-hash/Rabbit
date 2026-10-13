import { useNavigate } from 'react-router-dom'
import { Button, Columns, MultiSelect } from '../components/common/Widgets'
import { HeroPanel, PageHeader, SectionHeading, StepProgress } from '../components/layout/PageHeader'
import { AVOID_OPTIONS, BRANDS, FABRICS, FAVOURITE_COLOURS, FITS, OCCASIONS, SKIN_TONES, STYLES } from '../constants/options'
import { useStyleStore } from '../hooks/useStyleStore'

const SUBSTEPS = ['1. Skin Tone', '2. Favourite Colours', '3. Preferred Style', '4. Occasion Context']

function SelectGrid({ children }: { children: React.ReactNode }) {
  return <Columns n={4} className="keep-mobile-2">{children}</Columns>
}

export default function AppearancePage() {
  const s = useStyleStore()
  const navigate = useNavigate()
  const substep = s.appearance_substep

  return (
    <>
      <PageHeader title="Appearance & Preferences" subtitle="Tailor your color palette, style mood and event context step-by-step." />
      <StepProgress step={2} title="Appearance & Style Inputs" />

      <Columns n={4}>
        {SUBSTEPS.map((name, i) => (
          <Button key={name} full primary={substep === i + 1} onClick={() => s.set({ appearance_substep: i + 1 })}>
            {name}
          </Button>
        ))}
      </Columns>
      <div className="spacer" />

      {substep === 1 && (
        <div className="stack">
          <HeroPanel kicker="SUBSTEP 1 OF 4" title="Select Your Skin Tone">
            Our color harmony algorithm matches clothing palettes to complement your skin tone undertones.
          </HeroPanel>
          <SelectGrid>
            {SKIN_TONES.map(([name, hex, desc]) => {
              const active = s.skin_tone === name
              return (
                <div key={name} className="gap-sm">
                  <div className={`select-card${active ? ' active' : ''}`}>
                    <div
                      style={{ width: 54, height: 54, borderRadius: '50%', background: hex, margin: '0 auto 0.6rem', border: '3px solid #ffffff', boxShadow: '0 6px 14px rgba(0,0,0,0.15)' }}
                    />
                    <div className="card-title">
                      {name} {active ? '✓' : ''}
                    </div>
                    <div className="card-desc" style={{ marginTop: '0.4rem' }}>{desc}</div>
                  </div>
                  <Button full onClick={() => s.setSkinTone(name)}>
                    Select {name}
                  </Button>
                </div>
              )
            })}
          </SelectGrid>
        </div>
      )}

      {substep === 2 && (
        <div className="stack">
          <HeroPanel kicker="SUBSTEP 2 OF 4" title="Select Your Favourite Colours">
            Choose colors you feel most confident wearing. We will prioritize these in recommendations.
          </HeroPanel>
          <SelectGrid>
            {FAVOURITE_COLOURS.map(([name, hex]) => {
              const fav = s.favorite_colours.includes(name)
              return (
                <div key={name} className="gap-sm">
                  <div className={`select-card${fav ? ' active' : ''}`} style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', padding: '0.7rem 0.9rem', textAlign: 'left' }}>
                    <div style={{ width: 24, height: 24, borderRadius: '50%', background: hex, border: '1px solid rgba(0,0,0,0.2)', flex: 'none' }} />
                    <div className="card-title" style={{ fontSize: '0.82rem' }}>
                      {name} {fav ? '✓' : ''}
                    </div>
                  </div>
                  <Button
                    full
                    onClick={() =>
                      s.set({ favorite_colours: fav ? s.favorite_colours.filter((c) => c !== name) : [...s.favorite_colours, name] })
                    }
                  >
                    {fav ? `Remove ${name}` : `Add ${name}`}
                  </Button>
                </div>
              )
            })}
          </SelectGrid>
          <div className="mini-card">
            <strong>Active Palette Preferences:</strong> {s.favorite_colours.join(', ')}
          </div>
        </div>
      )}

      {substep === 3 && (
        <div className="stack">
          <HeroPanel kicker="SUBSTEP 3 OF 4" title="Select Preferred Style Aesthetic">
            What styling direction resonates most with your personal aesthetic?
          </HeroPanel>
          <SelectGrid>
            {STYLES.map(([name, icon, desc]) => {
              const active = s.style === name
              return (
                <div key={name} className="gap-sm">
                  <div className={`select-card${active ? ' active' : ''}`}>
                    <div className="card-icon">{icon}</div>
                    <div className="card-title">
                      {name} {active ? '✓' : ''}
                    </div>
                    <div className="card-desc">{desc}</div>
                  </div>
                  <Button full onClick={() => s.set({ style: name })}>
                    Choose {name}
                  </Button>
                </div>
              )
            })}
          </SelectGrid>
        </div>
      )}

      {substep === 4 && (
        <div className="stack">
          <HeroPanel kicker="SUBSTEP 4 OF 4" title="Select Occasion Context">
            Where are you planning to wear this outfit? Our stylist optimizes for setting propriety.
          </HeroPanel>
          <SelectGrid>
            {OCCASIONS.map(([name, icon, desc]) => {
              const active = s.occasion === name
              return (
                <div key={name} className="gap-sm">
                  <div className={`select-card${active ? ' active' : ''}`}>
                    <div className="card-icon">{icon}</div>
                    <div className="card-title">
                      {name} {active ? '✓' : ''}
                    </div>
                    <div className="card-desc">{desc}</div>
                  </div>
                  <Button full onClick={() => s.set({ occasion: name })}>
                    Pick {name}
                  </Button>
                </div>
              )
            })}
          </SelectGrid>

          {/* Former "03 Preferences" page, folded in here so the avoided colours still reach the recommender. */}
          <details className="panel">
            <summary style={{ cursor: 'pointer', fontWeight: 800, color: '#1f162d' }}>
              Fine-Tune Style Signals <span className="muted">(optional · fit, fabrics, colours to avoid, brands)</span>
            </summary>
            <div className="spacer" />
            <Columns n={2} gapLg>
              <div className="stack">
                <SectionHeading title="Fit & Silhouette Preference" icon="👗" />
                <div className="st-radio" role="radiogroup" aria-label="Preferred Cut">
                  <span className="field-label">Preferred Cut</span>
                  {FITS.map((fit) => (
                    <label key={fit}>
                      <input type="radio" name="fit" checked={s.preferred_fit === fit} onChange={() => s.set({ preferred_fit: fit })} />
                      {fit}
                    </label>
                  ))}
                </div>
                <SectionHeading title="Fabric & Textile Preferences" icon="🧵" />
                <MultiSelect label="Preferred Fabrics" options={FABRICS} value={s.preferred_fabrics} onChange={(v) => s.set({ preferred_fabrics: v })} />
              </div>
              <div className="stack">
                <SectionHeading title="Colours & Styles to Avoid" icon="🚫" />
                <MultiSelect label="Styles & Tones I Avoid" options={AVOID_OPTIONS} value={s.avoid_colours} onChange={(v) => s.set({ avoid_colours: v })} />
                <SectionHeading title="Favorite Fashion Brands" icon="🛍️" />
                <MultiSelect label="Preferred Stores / Brands" options={BRANDS} value={s.preferred_brands} onChange={(v) => s.set({ preferred_brands: v })} />
              </div>
            </Columns>
          </details>
        </div>
      )}

      <div className="spacer" />
      <div className="cols nav-3">
        {substep > 1 ? (
          <Button full onClick={() => s.set({ appearance_substep: substep - 1 })}>
            ← Previous Substep
          </Button>
        ) : (
          <Button full onClick={() => navigate('/profile')}>
            ← Back to Profile
          </Button>
        )}
        <div />
        {substep < 4 ? (
          <Button primary full onClick={() => s.set({ appearance_substep: substep + 1 })}>
            Next Substep →
          </Button>
        ) : (
          <Button primary full onClick={() => navigate('/avatar')}>
            CONTINUE TO AVATAR →
          </Button>
        )}
      </div>
    </>
  )
}
