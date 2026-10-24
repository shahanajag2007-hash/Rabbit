/**
 * PROTECTED PAGE — Recommended Outfit page.
 *
 * Faithful React port of pages/04_AI_Outfit_Recommendations.py. Layout, copy, card markup and
 * ordering are kept. Outfits come from recommender.recommend_with_notes() (POST /api/recommendations)
 * with the full profile, the analysed text request and the palette pick; nothing is selected, ranked
 * or generated client-side. The manual outfit builder is added below the three outfits.
 * Do not redesign this page.
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Columns, Loading } from '../components/common/Widgets'
import { PageHeader, SectionHeading, StepProgress } from '../components/layout/PageHeader'
import { ManualOutfitBuilder } from '../components/outfit/ManualOutfitBuilder'
import { ProductCard } from '../components/outfit/ProductCard'
import { useMeta } from '../hooks/useMeta'
import { selectUserProfile, useStyleStore } from '../hooks/useStyleStore'
import { api } from '../services/api'
import { CATEGORIES, type PaletteSwatch, type RecommendResponse } from '../types'
import { money, pyFloat } from '../utils/format'

export default function RecommendationsPage() {
  const s = useStyleStore()
  const navigate = useNavigate()
  const { meta, error: metaError } = useMeta()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [analyzedNow, setAnalyzedNow] = useState(false)
  const [notes, setNotes] = useState<string[]>([])
  const [understood, setUnderstood] = useState<string[]>([])
  const [context, setContext] = useState<RecommendResponse['context'] | null>(null)
  const [palette, setPalette] = useState<PaletteSwatch[]>([])
  const [paletteError, setPaletteError] = useState<string | null>(null)

  const profile = selectUserProfile(s)
  const profileKey = JSON.stringify(profile)
  const paletteKey = JSON.stringify({ ...profile, palette_colour: null })

  // Recomputed whenever any input changes (profile, Appearance, analysed text, palette pick).
  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)
    api
      .recommend(JSON.parse(profileKey), 3)
      .then((r) => {
        if (!alive) return
        useStyleStore.getState().set({ recommended_outfits: r.outfits })
        setNotes(r.notes ?? [])
        setUnderstood(r.understood ?? [])
        setContext(r.context ?? null)
      })
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [profileKey])

  // Palette: colours for this profile that real products are available in.
  useEffect(() => {
    let alive = true
    setPaletteError(null)
    api
      .palette(JSON.parse(paletteKey))
      .then((r) => alive && setPalette(r.swatches))
      .catch((e: Error) => alive && setPaletteError(e.message))
    return () => {
      alive = false
    }
  }, [paletteKey])

  const outfits = s.recommended_outfits
  const pickedColour = s.palette_colour
  const paletteNames = useMemo(() => palette.map((p) => p.name), [palette])

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
            s.set({ style_analyzed: true, applied_preference_text: s.preference_text.trim() })
            setAnalyzedNow(true)
          }}
        >
          ✨ ANALYZE MY STYLE
        </Button>
        {analyzedNow && !loading && (
          <Alert kind={understood.length || !s.applied_preference_text ? 'success' : 'warning'}>
            {understood.length || !s.applied_preference_text
              ? 'Preference analysis complete! Styling profile generated.'
              : 'We could not pick out a style, colour, occasion, fit or budget from your text. Try words like "formal", "navy", "oversized tops" or "under 2000".'}
          </Alert>
        )}

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
              {context?.style ?? s.style} + {context?.occasion ?? s.occasion} + {s.preferred_fit}
            </div>
            <div style={{ fontSize: '0.82rem', color: '#5f5a6d', marginTop: '0.3rem' }}>
              <strong>Styling Direction:</strong>{' '}
              {understood.length
                ? `From your request: ${understood.join(' · ')}.`
                : `Your ${s.style.toLowerCase()} style for ${s.occasion.toLowerCase()}, ${s.skin_tone.toLowerCase()} skin-tone palette and favourite colours (${s.favorite_colours.join(', ') || 'none'}).`}{' '}
              Applied to every recommendation below.
            </div>
          </div>
        )}
      </div>

      {/* SCREEN 6: MAIN CLOTHING RECOMMENDATION MARKETPLACE DASHBOARD */}
      <div className="panel">
        <SectionHeading title="Recommended Colour Palette" icon="🎨" />
        <div style={{ fontSize: '0.82rem', color: '#625b6e', marginBottom: '0.8rem' }}>
          Curated color swatches based on your <strong>{s.skin_tone}</strong> skin tone and <strong>{context?.occasion ?? s.occasion}</strong> setting. Tap a colour to
          prioritise it in your outfits.
        </div>
        {metaError && <Alert kind="error">{metaError}</Alert>}
        {paletteError && <Alert kind="error">{paletteError}</Alert>}
        <Columns n={Math.min(palette.length, 6) || 5} className="keep">
          {palette.slice(0, 6).map((swatch) => {
            const on = pickedColour === swatch.name
            return (
              <button
                key={swatch.name}
                type="button"
                className="swatch-card"
                aria-pressed={on}
                title={`${swatch.reason} · ${swatch.count} product${swatch.count === 1 ? '' : 's'} available`}
                onClick={() => s.set({ palette_colour: on ? null : swatch.name })}
                style={{ cursor: 'pointer', font: 'inherit', width: '100%', outline: on ? '2px solid #6b4bb0' : undefined, outlineOffset: 2 }}
              >
                <div className="swatch-color" style={{ background: swatch.hex }} />
                <div className="swatch-name">
                  {swatch.name} {on ? '✓' : ''}
                </div>
                <div className="muted" style={{ fontSize: '0.68rem' }}>
                  {swatch.count} available
                </div>
              </button>
            )
          })}
        </Columns>
        {pickedColour && (
          <div className="caption" style={{ marginTop: '0.5rem' }}>
            Prioritising <strong>{pickedColour}</strong>
            {palette.length > 0 && !paletteNames.includes(pickedColour) && ' (no longer available for your filters)'} ·{' '}
            <button
              type="button"
              className="inline-link"
              style={{ background: 'none', border: 0, padding: 0, cursor: 'pointer', font: 'inherit', color: '#6b4bb0', fontWeight: 700 }}
              onClick={() => s.set({ palette_colour: null })}
            >
              clear colour
            </button>
          </div>
        )}

        <div className="spacer" />
        <SectionHeading title="Fashion Marketplace Product Grid" icon="🛍️" />

        {loading && outfits.length === 0 && <Loading label="Generating your recommended outfits…" />}
        {error && <Alert kind="error">{error}</Alert>}
        {!loading && !error && outfits.length === 0 && <Alert kind="warning">No outfits found for this criteria.</Alert>}
        {!error &&
          notes.map((note) => (
            <Alert key={note} kind="warning">
              {note}
            </Alert>
          ))}

        <div style={{ opacity: loading && outfits.length > 0 ? 0.55 : 1, transition: 'opacity 0.2s' }}>
          {outfits.map((outfit, idx) => (
            <div key={(outfit.signature ?? [idx]).join('-')}>
              <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#1d1528', margin: '1.5rem 0 0.5rem' }}>Recommended Outfit {idx + 1}</div>
              <div style={{ fontSize: '0.9rem', color: '#625b6e', marginBottom: '1rem' }}>
                Total: {money(outfit.total_price)} | Compatibility Score: {pyFloat(outfit.score)}/100
                {outfit.over_budget && <span style={{ color: '#dc2626', fontWeight: 700 }}> | Over your {money(s.budget)} budget</span>}
              </div>
              {outfit.reasons && outfit.reasons.length > 0 && (
                <div className="caption" style={{ marginTop: '-0.6rem', marginBottom: '0.8rem' }}>
                  Why: {outfit.reasons.join(' · ')}
                </div>
              )}
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
      <ManualOutfitBuilder />

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
