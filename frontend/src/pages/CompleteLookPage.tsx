import { useNavigate } from 'react-router-dom'
import { AvatarViewer } from '../components/avatar/AvatarViewer'
import { GarmentColourPreview } from '../components/avatar/GarmentColourPreview'
import { Alert, Button, Columns, EmptyPanel, Loading } from '../components/common/Widgets'
import { PageHeader, StepProgress } from '../components/layout/PageHeader'
import { CustomizePanel } from '../components/outfit/CustomizePanel'
import { FabricPanel, WhyPanel } from '../components/outfit/InsightPanels'
import { OutfitBreakdown } from '../components/outfit/OutfitBreakdown'
import { useAvatarView } from '../hooks/useAvatar'
import { useMeta } from '../hooks/useMeta'
import { useOutfitScore } from '../hooks/useOutfitScore'
import { useStyleStore } from '../hooks/useStyleStore'
import { CATEGORIES, type OutfitItem } from '../types'
import { money } from '../utils/format'

function paletteKeyFor(skin: string): string {
  if (['Porcelain', 'Light Beige', 'Light'].includes(skin)) return 'Light'
  if (['Golden Tan', 'Tan'].includes(skin)) return 'Tan'
  if (['Deep Cocoa', 'Espresso', 'Deep'].includes(skin)) return 'Deep'
  return 'Medium'
}

/**
 * Page 5 — "Your Complete Look" (05_Outfit_Details.py), with the functionality of
 * 06 Customize, 07 Budget Stylist, 08 Interactive Pairing, 09 Why This Outfit and
 * 10 Virtual Styling Preview consolidated into it.
 */
export default function CompleteLookPage() {
  const s = useStyleStore()
  const navigate = useNavigate()
  const avatarView = useAvatarView('outfit')
  const { meta } = useMeta()
  const { score, error, loading } = useOutfitScore()
  const items = s.selected_outfit?.items ?? {}
  const itemList = CATEGORIES.map((c) => items[c]).filter(Boolean) as OutfitItem[]
  const palette = meta?.demo_palettes[paletteKeyFor(s.skin_tone)] ?? []

  return (
    <>
      <PageHeader title="Your Complete Look" subtitle="Complete outfit styling dashboard with virtual preview, breakdown, and textile insights." />
      <StepProgress step={5} title="Complete Outfit & Virtual Styling" />

      {!itemList.length ? (
        <EmptyPanel icon="🛍️" title="No outfit selected" text="No outfit selected. Please return to the Marketplace.">
          <Button primary onClick={() => navigate('/recommendations')}>
            ← Back to Marketplace
          </Button>
        </EmptyPanel>
      ) : (
        <>
          <div className="panel">
            <div className="cols gap-lg showcase">
              <div>
                <AvatarViewer view={avatarView} outfitItems={items} />
                <GarmentColourPreview palette={palette} />
              </div>
              <div className="hero-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                <div className="page-kicker">STYLING SUMMARY</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 900, color: '#1f162d', marginTop: '0.2rem' }}>Curated {s.occasion} Outfit</div>
                <div style={{ color: '#5f5a6d', fontSize: '0.9rem', marginTop: '0.4rem', lineHeight: 1.55 }}>
                  This complete look coordinates your selected <strong>{s.skin_tone}</strong> skin tone palette, <strong>{s.style}</strong> preference, and
                  stays within your <strong>{money(s.budget)}</strong> budget.
                </div>
                <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                  <div className="stat-card" style={{ flex: 1 }}>
                    <div className="stat-label">Total Look Cost</div>
                    <div className="stat-value">{score ? money(score.total_price) : '…'}</div>
                  </div>
                  <div className="stat-card" style={{ flex: 1 }}>
                    <div className="stat-label">Match Score</div>
                    <div className="stat-value" style={{ color: '#6b4bb0' }}>
                      {score ? `${Math.trunc(score.score)}/100` : '…'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {error && (
            <>
              <div className="spacer" />
              <Alert kind="error">{error}</Alert>
            </>
          )}
          {loading && !score && (
            <>
              <div className="spacer" />
              <Loading label="Scoring your outfit…" />
            </>
          )}

          <OutfitBreakdown total={score?.total_price ?? itemList.reduce((sum, i) => sum + Number(i.price), 0)} />

          {score && <CustomizePanel score={score} id="customize" />}

          <div className="spacer" />
          {score && (
            <Columns n={2} gapLg>
              <WhyPanel score={score} style={s.style} skinTone={s.skin_tone} occasion={s.occasion} budget={s.budget} />
              <FabricPanel items={itemList} notes={meta?.fabric_notes} />
            </Columns>
          )}
        </>
      )}

      <div className="spacer" />
      <Columns n={3}>
        <Button full onClick={() => navigate('/recommendations')}>
          ← Back to Marketplace
        </Button>
        <Button full disabled={!itemList.length} onClick={() => document.getElementById('customize')?.scrollIntoView({ behavior: 'smooth' })}>
          ✨ Customize Outfit
        </Button>
        <Button primary full disabled={!itemList.length} onClick={() => navigate('/final-look')}>
          VIEW FINAL LOOK →
        </Button>
      </Columns>
    </>
  )
}
