import { useNavigate } from 'react-router-dom'
import { Button, Columns, Slider } from '../components/common/Widgets'
import { HeroPanel, PageHeader, SectionHeading, StepProgress } from '../components/layout/PageHeader'
import { GENDERS } from '../constants/options'
import { useStyleStore } from '../hooks/useStyleStore'
import { money } from '../utils/format'

const BUDGET_MIN = 500
const BUDGET_MAX = 10000

export default function ProfilePage() {
  const s = useStyleStore()
  const navigate = useNavigate()
  const pct = Math.max(0, Math.min(100, Math.trunc(((s.budget - BUDGET_MIN) / (BUDGET_MAX - BUDGET_MIN)) * 100)))

  return (
    <>
      <PageHeader title="Welcome to STYLEAI" subtitle="Let's build your personalized fashion profile to get started." />
      <StepProgress step={1} title="Basic Profile Input" />

      <div style={{ marginBottom: '1.2rem' }}>
        <HeroPanel kicker="ONBOARDING STAGE 1" title="Tell Us About Yourself">
          Your height, weight, gender and budget allow our virtual styling engine to tailor proportions, fits and recommendations.
        </HeroPanel>
      </div>

      <Columns n={2} gapLg>
        <div className="stack">
          <SectionHeading title="Personal Identity" icon="👤" />
          <div className="field">
            <label htmlFor="full-name">Full Name</label>
            <input id="full-name" className="st-input" value={s.user_name} onChange={(e) => s.set({ user_name: e.target.value })} />
          </div>
          <Columns n={2}>
            <div className="field">
              <label htmlFor="age">Age</label>
              <input
                id="age"
                className="st-input"
                type="number"
                min={14}
                max={90}
                value={s.age}
                onChange={(e) => {
                  const age = Number(e.target.value)
                  if (!Number.isNaN(age)) s.set({ age: Math.max(14, Math.min(90, age)) })
                }}
              />
            </div>
            <div className="field">
              <label htmlFor="gender">Gender Identity</label>
              <select id="gender" className="st-select" value={s.gender} onChange={(e) => s.set({ gender: e.target.value })}>
                {GENDERS.map((g) => (
                  <option key={g}>{g}</option>
                ))}
              </select>
            </div>
          </Columns>

          <SectionHeading title="Body Proportions" icon="📏" />
          <Columns n={2}>
            <Slider label="Height (cm)" min={140} max={210} value={s.height} onChange={(height) => s.set({ height })} />
            <Slider label="Weight (kg)" min={35} max={140} value={s.weight} onChange={(weight) => s.set({ weight })} />
          </Columns>
        </div>

        <div className="stack">
          <SectionHeading title="Style Budget" icon="💳" />
          <Slider
            label="Select your preferred outfit budget limit"
            min={BUDGET_MIN}
            max={BUDGET_MAX}
            step={250}
            value={s.budget}
            onChange={(budget) => s.set({ budget })}
            format={(v) => `₹${v}`}
          />
          <div className="budget-display-card">
            <div className="budget-label">YOUR STYLE BUDGET</div>
            <div className="budget-value">{money(s.budget)}</div>
            <div className="budget-slider-visual">
              <span>₹500</span>
              <div className="budget-track">
                <div className="budget-track-fill" style={{ width: `${pct}%` }} />
              </div>
              <span>₹10,000</span>
            </div>
          </div>
          <div className="md-list">
            <div className="page-kicker" style={{ marginBottom: '0.4rem' }}>
              Profile Summary
            </div>
            <p>• <strong>Name</strong>: {s.user_name}</p>
            <p>• <strong>Gender</strong>: {s.gender} ({s.age} yrs)</p>
            <p>• <strong>Height &amp; Weight</strong>: {s.height} cm · {s.weight} kg</p>
            <p>• <strong>Budget</strong>: {money(s.budget)}</p>
          </div>
        </div>
      </Columns>

      <div className="spacer" />
      <Columns n={2}>
        <div />
        <Button primary full onClick={() => navigate('/appearance')}>
          CONTINUE TO APPEARANCE →
        </Button>
      </Columns>
    </>
  )
}
