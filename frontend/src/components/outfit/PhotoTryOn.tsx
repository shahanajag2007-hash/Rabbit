import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Loading } from '../common/Widgets'
import { useStyleStore } from '../../hooks/useStyleStore'
import { api } from '../../services/api'
import { CATEGORIES, type TryOnJob, type TryOnProvider } from '../../types'

/**
 * Photo mode of Complete Look / Final Look: the selected outfit tried on the user's own photo by the
 * configured try-on service (see api/tryon.py). Shown instead of the 3D avatar, never next to it.
 * Generation starts only when the user asks (and has consented); results are cached per outfit.
 */
export function PhotoTryOn({ height = 560, compact = false }: { height?: number; compact?: boolean }) {
  const navigate = useNavigate()
  const s = useStyleStore()
  const items = s.selected_outfit?.items ?? {}
  const signature = JSON.stringify(
    CATEGORIES.map((c) => {
      const item = items[c]
      return item
        ? [item.item_id, item.image, item.image_url, item.item_name, item.colour, item.covers_bottom]
        : null
    }),
  )
  const [provider, setProvider] = useState<TryOnProvider | null>(null)
  const [job, setJob] = useState<TryOnJob | null>(null)
  const [error, setError] = useState<string | null>(null)
  const current = s.tryon_job && s.tryon_job.signature === signature ? s.tryon_job : null

  useEffect(() => {
    api
      .tryOnProvider()
      .then(setProvider)
      .catch((e: Error) => {
        setProvider(null)
        setError(e.message)
      })
  }, [])

  // Poll the job for this outfit until it finishes.
  useEffect(() => {
    if (!current || !s.photo_id) {
      setJob(null)
      return
    }
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    const poll = () =>
      api
        .tryOnStatus(s.photo_id!, current.id)
        .then((j) => {
          if (!alive) return
          setJob(j)
          if (j.status === 'queued' || j.status === 'running') timer = setTimeout(poll, 4000)
        })
        .catch((e: Error) => alive && setError(e.message))
    poll()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [current?.id, s.photo_id]) // eslint-disable-line react-hooks/exhaustive-deps

  async function start() {
    if (!s.photo_id) return
    setError(null)
    try {
      const j = await api.startTryOn(s.photo_id, items, s.tryon_consent)
      setJob(j)
      s.set({ tryon_job: { id: j.job_id, signature } })
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const box = { minHeight: compact ? undefined : height, display: 'flex', flexDirection: 'column' as const, justifyContent: 'center' }

  if (!s.photo_id || !s.photo_validation) {
    return (
      <div className="mini-card gap-sm" style={box}>
        <strong>Photo mode is selected, but no photo is uploaded.</strong>
        <div className="muted">Upload a full-body photo on the Avatar page to try this outfit on yourself, or switch to the avatar there.</div>
        <Button primary onClick={() => navigate('/avatar')}>
          Upload my photo →
        </Button>
      </div>
    )
  }
  if (!s.photo_validation.accepted) {
    return (
      <div className="mini-card gap-sm" style={box}>
        <Alert kind="error">Your photo did not pass the full-body checks: {s.photo_validation.problems.join(' ')}</Alert>
        <Button primary onClick={() => navigate('/avatar')}>
          Upload another photo →
        </Button>
      </div>
    )
  }

  const done = job?.status === 'done'
  const running = job?.status === 'queued' || job?.status === 'running'
  const notRendered = (job?.not_rendered ?? []).filter((c) => items[c as keyof typeof items])

  return (
    <div className="gap-sm" style={box}>
      <img
        src={done ? api.tryOnImageUrl(s.photo_id, job!.job_id) : api.photoImageUrl(s.photo_id)}
        alt={done ? 'Your selected outfit tried on your photo' : 'Your uploaded photo'}
        crossOrigin="use-credentials"
        style={{ width: '100%', maxHeight: height, objectFit: 'contain', borderRadius: 16, background: '#f3f1f6' }}
      />
      {running && (
        <div className="row between">
          <Loading label={`Generating your try-on with ${job!.label}… this can take a minute or more.`} />
          <Button onClick={() => api.cancelTryOn(s.photo_id!, job!.job_id).then(setJob).catch((e: Error) => setError(e.message))}>Cancel</Button>
        </div>
      )}
      {job?.status === 'failed' && <Alert kind="error">{job.error}</Alert>}
      {job?.status === 'cancelled' && <Alert kind="warning">Try-on cancelled. Your outfit is unchanged.</Alert>}
      {provider?.skipped && provider.skipped.length > 0 && !done && (
        <div className="caption">Using {provider.label} because: {provider.skipped.join(' ')}</div>
      )}
      {error && <Alert kind="error">{error}</Alert>}
      {done && (
        <div className="caption">
          AI try-on of your {job!.rendered.join(' and ').toLowerCase()} by {job!.label}
          {job!.cached ? ' (saved result for this photo and outfit, no new generation)' : ''}.
          {notRendered.length > 0 && ` Not drawn on the photo: ${notRendered.join(', ').toLowerCase()} — this model only renders ${(provider?.garments ?? job!.rendered).join(' and ').toLowerCase()}.`}{' '}
          The model approximates fabric and fit; it does not simulate the chosen size.
        </div>
      )}
      {!done && !running && (
        <>
          {!provider?.configured ? (
            <Alert kind="warning">Virtual try-on is not available on this server{provider?.missing ? `: ${provider.missing}` : '.'} Your photo is shown without the outfit.</Alert>
          ) : !s.tryon_consent ? (
            <label className="st-check mini-card" style={{ alignItems: 'flex-start' }}>
              <input type="checkbox" checked={false} onChange={() => s.set({ tryon_consent: true })} />
              <span>
                I agree to send my photo and the selected product images to <strong>{provider.label}</strong> to generate the try-on.
              </span>
            </label>
          ) : null}
          <Button primary disabled={!provider?.configured || !s.tryon_consent} onClick={start}>
            ✨ {job?.status === 'failed' ? 'Try again' : 'Try this outfit on my photo'}
          </Button>
        </>
      )}
    </div>
  )
}
