import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AvatarViewer } from '../components/avatar/AvatarViewer'
import { Alert, Button, Columns, Loading } from '../components/common/Widgets'
import { HeroPanel, PageHeader, SectionHeading, StepProgress } from '../components/layout/PageHeader'
import { AvatarStudio } from '../components/avatar/studio/AvatarStudio'
import { IDENTITIES } from '../constants/options'
import { useAvatarView } from '../hooks/useAvatar'
import { useStyleStore } from '../hooks/useStyleStore'
import { api } from '../services/api'
import type { SkinToneAnalysis } from '../types'

function PhotoUpload() {
  const set = useStyleStore((s) => s.set)
  const setSkinTone = useStyleStore((s) => s.setSkinTone)
  const [preview, setPreview] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<SkinToneAnalysis | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [applied, setApplied] = useState(false)

  useEffect(() => () => void (preview && URL.revokeObjectURL(preview)), [preview])

  async function onFile(file: File | undefined) {
    setError(null)
    setAnalysis(null)
    setApplied(false)
    if (!file) return
    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      setError('Please upload a JPG or PNG image.')
      return
    }
    setPreview(URL.createObjectURL(file))
    setBusy(true)
    try {
      const result = await api.analyzeSkinTone(file)
      setAnalysis(result)
      // Keep the detection result separately from the user's manual choice; applying it is explicit.
      set({ skin_tone_detected: result.skin_tone })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="stack">
      <div className="field">
        <label htmlFor="photo">Upload full-body picture (JPG, PNG)</label>
        <input id="photo" className="st-input" type="file" accept="image/jpeg,image/png" onChange={(e) => onFile(e.target.files?.[0])} />
      </div>
      {preview && <img src={preview} alt="Uploaded full-body photo" width={280} style={{ borderRadius: 12 }} />}
      {preview && !error && <Alert kind="success">Photo uploaded successfully! Your styling engine will use this photo.</Alert>}
      {busy && <Loading label="Analysing skin tone from your photo…" />}
      {error && <Alert kind="error">{error}</Alert>}
      {analysis && (
        <div className="mini-card row between">
          <div className="row">
            <div style={{ width: 36, height: 36, borderRadius: '50%', background: `rgb(${analysis.dominant_rgb.join(',')})`, border: '2px solid #fff', boxShadow: '0 0 0 1px rgba(0,0,0,.15)' }} />
            <div>
              <div style={{ fontWeight: 800 }}>Detected skin tone: {analysis.skin_tone}</div>
              <div className="muted">Suggested palette: {analysis.palette.join(', ')} · approximate estimate from the upper-centre of the photo</div>
            </div>
          </div>
          <Button
            onClick={() => {
              setSkinTone(analysis.skin_tone)
              setApplied(true)
            }}
            disabled={applied}
          >
            {applied ? '✓ Applied to profile' : 'Use detected skin tone'}
          </Button>
        </div>
      )}
    </div>
  )
}

export default function AvatarPage() {
  const s = useStyleStore()
  const view = useAvatarView('studio')
  const navigate = useNavigate()
  const [saved, setSaved] = useState<string | null>(null)

  return (
    <>
      <PageHeader title="Virtual Stylist & Avatar Studio" subtitle="Create your personalized visual styling model or upload a photo." />
      <StepProgress step={3} title="Photo or Avatar Profile Creation" />

      <aside className="info-banner" aria-label="About avatar customization">
        <div className="info-banner-icon" aria-hidden="true">ℹ</div>
        <div>
          <div className="info-banner-title">About avatar customization</div>
          <p>
            Customize your virtual appearance using the options below. These settings personalize your avatar for visualization and styling previews, and it starts from your
            profile (gender, height, weight, age and skin tone).
          </p>
          <p>
            <strong>Clothing chosen in the Avatar Studio is for the avatar's appearance only.</strong> It does not change your AI-recommended outfit, product selections,
            recommendation ranking or shopping results. Your recommended outfit is shown on the avatar on the Complete Look and Final Look pages.
          </p>
          <p>
            Your <strong>skin tone stays synchronized</strong> with your profile: changing it here updates the profile value used for colour recommendations. To change your
            actual recommended outfit, use the Recommendations page and its existing controls.
          </p>
        </div>
      </aside>

      <div style={{ marginBottom: '1.5rem' }}>
        <HeroPanel kicker="ONBOARDING STAGE 3" title="How Would You Like To Create Your Look?">
          Choose between building a personalized virtual model or uploading your own photo for styling.
        </HeroPanel>
      </div>

      <Columns n={2} gapLg>
        <div className="gap-sm">
          <div className={`choice-card${s.visual_mode === 'photo' ? ' active' : ''}`}>
            <div className="choice-icon">📷</div>
            <div className="choice-title">OPTION 1: UPLOAD YOUR PHOTO</div>
            <div className="choice-desc">Use your own full-body photo for personalized outfit recommendations and visual analysis.</div>
          </div>
          <Button full onClick={() => s.set({ visual_mode: 'photo' })}>
            Choose Photo Upload 📷
          </Button>
        </div>
        <div className="gap-sm">
          <div className={`choice-card${s.visual_mode === 'avatar' ? ' active' : ''}`}>
            <div className="choice-icon">🧑‍🎨</div>
            <div className="choice-title">OPTION 2: CREATE YOUR AVATAR</div>
            <div className="choice-desc">Build a personalized high-fidelity virtual fashion model based on your profile proportions and skin tone.</div>
          </div>
          <Button primary full onClick={() => s.set({ visual_mode: 'avatar' })}>
            Choose Avatar Builder 🧑‍🎨
          </Button>
        </div>
      </Columns>
      <div className="spacer" />

      {s.visual_mode === 'photo' ? (
        <div className="panel stack">
          <SectionHeading title="Full-Body Photo Upload" icon="📷" />
          <PhotoUpload />
          <Columns n={2}>
            <div />
            <Button primary full onClick={() => navigate('/recommendations')}>
              PROCEED TO PREFERENCE ANALYSIS →
            </Button>
          </Columns>
        </div>
      ) : (
        <div className="panel" style={{ marginTop: '1rem' }}>
          <SectionHeading title="Professional Fashion Avatar Studio" icon="🎨" />
          <div className="cols gap-lg avatar-studio">
            <div className="studio-viewer">
              <AvatarViewer view={view} height={620} />
            </div>
            <AvatarStudio view={view} />
          </div>
        </div>
      )}

      <div className="spacer" />
      <Columns n={4}>
        <Button full onClick={() => navigate('/appearance')}>
          ← Back to Appearance
        </Button>
        <Button full onClick={() => s.resetAvatarAppearance()} title="Restores the default look and casual outfit; your profile is not changed">
          ↺ Reset Avatar
        </Button>
        <Button
          full
          onClick={() => {
            s.saveAvatarLook(s.occasion)
            setSaved(s.occasion)
          }}
        >
          💾 Save Avatar Look
        </Button>
        <Button primary full onClick={() => navigate('/recommendations')}>
          CONTINUE TO PREFERENCE ANALYSIS →
        </Button>
      </Columns>
      {saved && (
        <>
          <div className="spacer" />
          <Alert kind="success">Avatar saved to your '{saved}' style collection!</Alert>
        </>
      )}

      {/* Former "11 Multi Identity" page: saved looks + identity switcher. */}
      <div className="spacer" />
      <div className="panel stack">
        <SectionHeading title="Style Me For Every Version Of Me" icon="🪞" />
        <div className="caption">Switch between different identities and moods, or reload an avatar look you saved for an occasion.</div>
        <Columns n={4}>
          {IDENTITIES.map(([name, style, vibe, detail, emoji]) => (
            <div key={name} className="mini-card gap-sm">
              <div style={{ fontSize: '2rem' }}>{emoji}</div>
              <div style={{ fontWeight: 800, color: '#1d1528' }}>{name}</div>
              <div className="chip-select">
                {[style, vibe, detail].map((chip) => (
                  <span key={chip} className="chip-toggle" style={{ cursor: 'default' }}>
                    {chip}
                  </span>
                ))}
              </div>
              <Button
                full
                onClick={() => {
                  s.set({ style })
                  navigate('/recommendations')
                }}
              >
                Select
              </Button>
            </div>
          ))}
        </Columns>
        <div className="row">
          <span className="field-label">Saved avatar looks:</span>
          {Object.keys(s.saved_avatar_looks).length === 0 && <span className="muted">None yet — use “Save Avatar Look”.</span>}
          {Object.keys(s.saved_avatar_looks).map((name) => (
            <Button key={name} primary={s.selected_avatar_key === name} onClick={() => s.loadAvatarLook(name)}>
              {name}
            </Button>
          ))}
        </div>
      </div>
    </>
  )
}
