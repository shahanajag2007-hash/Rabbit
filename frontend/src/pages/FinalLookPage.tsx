import { useNavigate } from 'react-router-dom'
import { AvatarViewer } from '../components/avatar/AvatarViewer'
import { Button, Columns, EmptyPanel } from '../components/common/Widgets'
import { PageHeader } from '../components/layout/PageHeader'
import { CATEGORY_ICONS } from '../constants/options'
import { useAvatarView } from '../hooks/useAvatar'
import { useStyleStore } from '../hooks/useStyleStore'
import { CATEGORIES, type OutfitItem } from '../types'
import { money } from '../utils/format'

/** Page 6 — Final Look & Order Summary (12_Final_Look.py). */
export default function FinalLookPage() {
  const s = useStyleStore()
  const navigate = useNavigate()
  const avatarView = useAvatarView('outfit')
  const items = s.selected_outfit?.items ?? {}
  const itemList = CATEGORIES.map((c) => items[c]).filter(Boolean) as OutfitItem[]
  const totalCost = itemList.reduce((sum, item) => sum + Number(item.price ?? 0), 0)

  return (
    <>
      <PageHeader title="Final Look & Order Summary" subtitle="Congratulations! Your personalized outfit styling is complete and ready to wear." />

      {!itemList.length ? (
        <EmptyPanel icon="🪞" title="Your final look is not ready yet" text="Select a recommended outfit first, then review it on the Complete Look page.">
          <Button primary onClick={() => navigate('/recommendations')}>
            Go to Recommendations →
          </Button>
        </EmptyPanel>
      ) : (
        <div className="panel">
          <div className="cols gap-lg final-look">
            <AvatarViewer view={avatarView} outfitItems={items} height={600} />
            <div className="hero-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <div className="page-kicker">STYLING READY</div>
              <div style={{ fontSize: '2rem', fontWeight: 900, color: '#1f162d', marginTop: '0.2rem' }}>
                {s.user_name}'s {s.occasion} Style
              </div>
              <div style={{ color: '#5f5a6d', fontSize: '0.9rem', marginTop: '0.4rem', lineHeight: 1.55 }}>
                Your complete look is optimized for <strong>{s.occasion}</strong> propriety, complements your <strong>{s.skin_tone}</strong> skin tone, and
                totals <strong>{money(totalCost)}</strong>.
              </div>
              <div style={{ marginTop: '1.5rem' }} className="stat-card">
                <div className="stat-label">Total Outfitted Spend</div>
                <div className="stat-value">{money(totalCost)}</div>
                <div className="stat-detail">Budget Target: {money(s.budget)}</div>
              </div>
              <div style={{ marginTop: '1.2rem' }} className="gap-sm">
                {itemList.map((item) => (
                  <div key={String(item.item_id)} className="row between" style={{ fontSize: '0.88rem' }}>
                    <span>
                      {CATEGORY_ICONS[String(item.category)]} {item.item_name}
                      {s.locked_items[item.category as keyof typeof s.locked_items] ? ' 🔒' : ''}
                    </span>
                    <strong>{money(item.price)}</strong>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="spacer" />
      <Columns n={2}>
        <Button
          full
          onClick={() => {
            s.restartJourney()
            navigate('/profile')
          }}
        >
          🔄 Restart Styling Journey
        </Button>
        <Button primary full onClick={() => navigate('/complete-look')}>
          ✨ Modify Complete Look
        </Button>
      </Columns>
    </>
  )
}
