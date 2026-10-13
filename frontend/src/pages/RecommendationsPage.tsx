/**
 * PROTECTED PAGE — Recommended Outfit page.
 *
 * Faithful React port of pages/04_AI_Outfit_Recommendations.py. Layout, copy, card markup,
 * ordering and interactions are intentionally identical to the Streamlit version.
 * Outfits come from recommender.recommend_outfits() (via POST /api/recommendations) with
 * the same user_profile and limit=3; nothing is selected, ranked or generated client-side.
 * Do not redesign this page.
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Columns, Loading } from '../components/common/Widgets'
import { PageHeader, SectionHeading, StepProgress } from '../components/layout/PageHeader'
import { ProductCard } from '../components/outfit/ProductCard'
import { useMeta } from '../hooks/useMeta'
import { selectUserProfile, useStyleStore } from '../hooks/useStyleStore'
import { api } from '../services/api'
import { CATEGORIES } from '../types'
import { money, pyFloat } from '../utils/format'

function paletteKeyFor(skin: string): string {
  if (['Porcelain', 'Light Beige'].includes(skin)) return 'Light'
  if (['Golden Tan', 'Tan'].includes(skin)) return 'Tan'
  if (['Deep Cocoa', 'Espresso', 'Deep'].includes(skin)) return 'Deep'
  return 'Medium'
}

export default function RecommendationsPage() {
  const s = useStyleStore()
  const navigate = useNavigate()
  const { meta, error: metaError } = useMeta()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [analyzedNow, setAnalyzedNow] = useState(false)

  const profile = selectUserProfile(s)
  const profileKey = JSON.stringify(profile)

  // Streamlit recomputed the recommendations on every visit/rerun; same here whenever the profile changes.
  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)
    api
      .recommend(JSON.parse(profileKey), 3)
      .then((r) => alive && useStyleStore.getState().set({ recommended_outfits: r.outfits }))
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [profileKey])

  const outfits = s.recommended_outfits
  const palette = useMemo(() => {
    const palettes = meta?.demo_palettes
    if (!palettes) return []
    return palettes[paletteKeyFor(s.skin_tone)] ?? palettes.Medium
  }, [meta, s.skin_tone])

  return (
    <>
      <PageHeader
        title="AI Preference Analysis & Fashion Marketplace"
        subtitle="Tell your AI stylist your vision and explore curated marketplace recommendations."
      />
      <StepProgress step={4} title="Preference Analysis & Marketplace" />

      {/* SCREEN 5: "TELL US YOUR PREFERENCE" - AI STYLIST ANALYSIS */}
      <div className="panel stack" style={{ marginBottom: '1.5rem' }}>
        <SectionHeading title="Tell Us Your Preference" icon="💬" />
        <div className="caption">Tell your AI stylist what you are looking for today.</div>
        <div className="field">
          <label htmlFor="pref-text">Describe your styling mood or occasion goals</label>
          <textarea
            id="pref-text"
            className="st-textarea"
            value={s.preference_text}
            placeholder="Example: I want a comfortable college outfit with a minimal style, preferably in blue or neutral shades..."
            onChange={(e) => s.set({ preference_text: e.target.value })}
          />
        </div>

        <div className="page-kicker" style={{ marginTop: '0.6rem' }}>
          QUICK SUGGESTION CHIPS
        </div>
        <div className="chip-grid">
          {(meta?.suggestion_chips ?? []).map((chip) => (
            <Button
              key={chip}
              full
              title={chip}
              onClick={() => {
                if (!s.preference_text.includes(chip)) s.set({ preference_text: `${s.preference_text} ${chip}`.trim() })
              }}
            >
              {chip}
            </Button>
          ))}
        </div>

        <Button
          primary
          full
          onClick={() => {
            s.set({ style_analyzed: true })
            setAnalyzedNow(true)
          }}
        >
          ✨ ANALYZE MY STYLE
        </Button>
        {analyzedNow && <Alert kind="success">Preference analysis complete! Styling profile generated.</Alert>}

        {(s.style_analyzed || s.preference_text) && (
          <div
            style={{
              background: 'linear-gradient(135deg, rgba(107,75,176,0.08), rgba(239,125,143,0.08))',
              border: '1px solid rgba(107,75,176,0.18)',
              borderRadius: 18,
              padding: '1rem',
              marginTop: '1rem',
            }}
          >
            <div className="page-kicker">YOUR GENERATED STYLE PROFILE</div>
            <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#1f162d', marginTop: '0.2rem' }}>
              {s.style} + {s.occasion} + Comfortable
            </div>
            <div style={{ fontSize: '0.82rem', color: '#5f5a6d', marginTop: '0.3rem' }}>
              <strong>Styling Direction:</strong> Clean, practical and modern. Prioritizing breathable textiles and harmonized color palettes
              suitable for {s.occasion.toLowerCase()}.
            </div>
          </div>
        )}
      </div>

      {/* SCREEN 6: MAIN CLOTHING RECOMMENDATION MARKETPLACE DASHBOARD */}
      <div className="panel">
        <SectionHeading title="Recommended Colour Palette" icon="🎨" />
        <div style={{ fontSize: '0.82rem', color: '#625b6e', marginBottom: '0.8rem' }}>
          Curated color swatches based on your <strong>{s.skin_tone}</strong> skin tone and <strong>{s.occasion}</strong> setting.
        </div>
        {metaError && <Alert kind="error">{metaError}</Alert>}
        <Columns n={palette.length || 5} className="keep">
          {palette.map((swatch) => (
            <div key={swatch.name} className="swatch-card">
              <div className="swatch-color" style={{ background: swatch.hex }} />
              <div className="swatch-name">{swatch.name}</div>
            </div>
          ))}
        </Columns>

        <div className="spacer" />
        <SectionHeading title="Fashion Marketplace Product Grid" icon="🛍️" />

        {loading && outfits.length === 0 && <Loading label="Generating your recommended outfits…" />}
        {error && <Alert kind="error">{error}</Alert>}
        {!loading && !error && outfits.length === 0 && <Alert kind="warning">No outfits found for this criteria.</Alert>}

        <div style={{ opacity: loading && outfits.length > 0 ? 0.55 : 1, transition: 'opacity 0.2s' }}>
          {outfits.map((outfit, idx) => (
            <div key={(outfit.signature ?? [idx]).join('-')}>
              <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#1d1528', margin: '1.5rem 0 0.5rem' }}>Recommended Outfit {idx + 1}</div>
              <div style={{ fontSize: '0.9rem', color: '#625b6e', marginBottom: '1rem' }}>
                Total: {money(outfit.total_price)} | Compatibility Score: {pyFloat(outfit.score)}/100
              </div>
              <Button
                primary
                onClick={() => {
                  s.selectOutfit(outfit)
                  navigate('/complete-look')
                }}
              >
                Select Outfit {idx + 1}
              </Button>
              <div className="spacer" />
              <div className="product-grid-4">
                {CATEGORIES.map((cat) => {
                  const item = outfit.items[cat]
                  return item ? <ProductCard key={cat} item={item} /> : <div key={cat} />
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="spacer" />
      <Columns n={2}>
        <div />
        <Button primary full onClick={() => navigate('/complete-look')}>
          GO TO COMPLETE OUTFIT STYLING →
        </Button>
      </Columns>
    </>
  )
}
