import { SectionHeading } from '../layout/PageHeader'
import type { Meta, OutfitItem, ScoreResult } from '../../types'
import { money } from '../../utils/format'

interface WhyProps {
  score: ScoreResult
  style: string
  skinTone: string
  occasion: string
  budget: number
}

/** "Why We Chose This Look For You" (05_Outfit_Details.py) + the full breakdown from 09_Why_This_Outfit.py. */
export function WhyPanel({ score, style, skinTone, occasion, budget }: WhyProps) {
  const b = score.breakdown
  const stylePct = (b.style / 20) * 100
  const colourPct = (b.colour / 30) * 100
  const occasionPct = (b.occasion / 20) * 100
  const budgetPct = (b.budget / 15) * 100
  const compatPct = (b.compatibility / 15) * 100

  const reasons: React.ReactNode[] = []
  if (stylePct >= 70) reasons.push(<>✓ Strong match for your preferred <strong>{style}</strong> aesthetic</>)
  if (colourPct >= 60) reasons.push(<>✓ Aligns well with your <strong>{skinTone}</strong> skin tone palette and colour preferences</>)
  if (occasionPct >= 80) reasons.push(<>✓ Highly appropriate for <strong>{occasion}</strong> settings</>)
  if (budgetPct === 100) reasons.push(<>✓ Comfortably fits within your <strong>{money(budget)}</strong> budget limit</>)
  else if (budgetPct > 0) reasons.push(<>✓ Close to your target budget</>)
  if (compatPct >= 75) reasons.push(<>✓ High visual harmony and coordination between pieces</>)
  if (!reasons.length) reasons.push(<>✓ Selected from available marketplace items based on your criteria</>)

  const bars: [string, number, number][] = [
    ['🎨 Colour Match', b.colour, 30],
    ['👗 Style Match', b.style, 20],
    ['📍 Occasion Match', b.occasion, 20],
    ['🔗 Outfit Compatibility', b.compatibility, 15],
    ['💰 Budget Fit', b.budget, 15],
  ]

  return (
    <div className="panel">
      <SectionHeading title="Why We Chose This Look For You" icon="💡" />
      <div className="md-list">
        {reasons.map((r, i) => (
          <p key={i}>{r}</p>
        ))}
      </div>
      <div className="spacer" />
      <div className="page-kicker">MATCH SCORE BREAKDOWN · {Math.round(score.score)} / 100</div>
      {bars.map(([label, value, max]) => {
        const pct = Math.min(100, Math.max(0, Math.trunc((value / max) * 100)))
        return (
          <div key={label} style={{ margin: '0.6rem 0' }}>
            <div className="row between" style={{ fontSize: '0.78rem', fontWeight: 700, color: '#20192d' }}>
              <span>{label}</span>
              <span>
                {value.toFixed(1)} / {max} · {pct}%
              </span>
            </div>
            <div className="progress-bar">
              <span className="progress-fill" style={{ width: `${pct}%` }} />
            </div>
          </div>
        )
      })}
      <div className="spacer" />
      <div className="mini-card" style={{ background: 'linear-gradient(135deg, rgba(110,83,170,0.08), rgba(239,125,143,0.08))' }}>
        <div className="page-kicker">AI stylist summary</div>
        <div style={{ fontWeight: 700, color: '#20192d', lineHeight: 1.6 }}>
          “This combination balances your selected style, occasion and budget while keeping the outfit visually coordinated.”
        </div>
      </div>
    </div>
  )
}

/** "Fabric & Textile Details" (05_Outfit_Details.py). */
export function FabricPanel({ items, notes }: { items: OutfitItem[]; notes: Meta['fabric_notes'] | undefined }) {
  return (
    <div className="panel">
      <SectionHeading title="Fabric & Textile Details" icon="🧵" />
      {items.map((item) => {
        const fabric = item.fabric ?? 'Cotton Blend'
        const note = notes?.[fabric] ?? 'Comfortable textile tailored for daily wear.'
        return (
          <div key={String(item.item_id)} className="explain-card" style={{ marginBottom: '0.75rem' }}>
            <h4>
              {String(item.category)}: {item.item_name}
            </h4>
            <p>
              <strong>Fabric:</strong> {fabric} ({item.fabric_tag ?? 'N/A'})
            </p>
            <p style={{ fontSize: '0.76rem', color: '#625b6e', marginTop: '0.2rem' }}>{note}</p>
          </div>
        )
      })}
    </div>
  )
}
