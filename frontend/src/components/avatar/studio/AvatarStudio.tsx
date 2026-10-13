import { useState, type ReactNode } from 'react'
import { useShallow } from 'zustand/react/shallow'
import {
  ACCESSORIES,
  ACCESSORY_CONFLICTS,
  AVATAR_ASSET_ROOT,
  AVATAR_MODELS,
  BODY_TYPES,
  EYE_COLORS,
  EYE_SHAPES,
  EYEBROWS,
  FACE_SHAPES,
  FACIAL_HAIR,
  garment,
  GARMENT_COLORS,
  GARMENTS,
  HAIR_COLORS,
  HAIR_HIGHLIGHTS,
  inCollection,
  LIPS,
  NOSES,
  SKIN_TONES,
  suggestBodyType,
  thumbUrl,
  type AccessoryId,
  type AvatarConfig,
  type GarmentOption,
  type GarmentSlot,
  type Presentation,
} from '../avatarCatalog'
import { HAIR_GROUPS, hairMeshes, HAIRSTYLES, type HairStyle } from '../hairStyles'
import { useAvatarMeta, type AvatarMeta } from '../avatarAssets'
import { useStyleStore } from '../../../hooks/useStyleStore'
import type { AvatarView } from '../../../hooks/useAvatar'
import { OptionCard, OptionSection } from './OptionCard'

const STUDIO_CATEGORIES = [
  { id: 'appearance', label: 'Appearance', icon: '🧍' },
  { id: 'face', label: 'Face', icon: '🙂' },
  { id: 'hair', label: 'Hairstyle', icon: '💇' },
  { id: 'skin', label: 'Skin Tone', icon: '🎨' },
  { id: 'body', label: 'Body Type', icon: '📐' },
  { id: 'clothing', label: 'Clothing', icon: '👕' },
  { id: 'footwear', label: 'Footwear', icon: '👟' },
  { id: 'accessories', label: 'Accessories', icon: '💍' },
] as const

type ColorField = 'topColor' | 'outerwearColor' | 'bottomColor' | 'fullColor' | 'footwearColor'

function ColourRow({ slot, field, config, update, item }: { slot: string; field: ColorField; config: AvatarConfig; update: (p: Partial<AvatarConfig>) => void; item: string | null }) {
  const current = config[field]
  // Some garments (suits) print shirt, tie and jacket in one texture: re-colouring would tint them all.
  if (!garment(item)?.tintable) return <p className="caption">{slot} is shown in its original colours.</p>
  return (
    <div className="colour-row" role="group" aria-label={`${slot} colour`}>
      <span className="field-label">{slot} colour</span>
      <button type="button" className={`colour-chip original${current === null ? ' on' : ''}`} aria-pressed={current === null} onClick={() => update({ [field]: null })}>
        Original
      </button>
      {GARMENT_COLORS.map((c) => (
        <button
          key={c.id}
          type="button"
          title={c.label}
          aria-label={c.label}
          aria-pressed={current === c.hex}
          className={`colour-dot${current === c.hex ? ' on' : ''}`}
          style={{ background: c.hex }}
          onClick={() => update({ [field]: c.hex })}
        />
      ))}
    </div>
  )
}

/** "For this model" first; other collections behind a disclosure (always selectable). */
function CollectionSplit<T extends { collections: ReadonlyArray<string> }>({ p, items, render, moreLabel }: { p: Presentation; items: T[]; render: (items: T[]) => ReactNode; moreLabel: string }) {
  const primary = items.filter((i) => inCollection(p, i.collections))
  const more = items.filter((i) => !inCollection(p, i.collections))
  return (
    <>
      {render(primary)}
      {more.length > 0 && (
        <details className="more-styles">
          <summary>
            {moreLabel} ({more.length})
          </summary>
          {render(more)}
        </details>
      )}
    </>
  )
}

/** A style works when every real hair mesh it is built on was built for this model. */
function hairState(meta: AvatarMeta | null, h: HairStyle): { disabled: boolean; note?: string } {
  if (h.available === false) return { disabled: true, note: h.note }
  if (meta && !hairMeshes(h).every((m) => meta.hair.includes(m))) return { disabled: true, note: 'Not built for this model' }
  return { disabled: false }
}

function garmentState(meta: AvatarMeta | null, g: GarmentOption): { disabled: boolean; note?: string } {
  if (g.available === false) return { disabled: true, note: g.note }
  if (meta && !meta.garments[g.id]) return { disabled: true, note: 'Not built for this model' }
  return { disabled: false }
}

function GarmentGrid({ p, meta, slot, value, onPick, allowNone }: { p: Presentation; meta: AvatarMeta | null; slot: GarmentSlot; value: string | null; onPick: (id: string | null) => void; allowNone?: boolean }) {
  const grid = (options: GarmentOption[]) =>
    Array.from(new Set(options.map((g) => g.group))).map((group) => (
      <OptionSection key={group} title={group}>
        {options
          .filter((g) => g.group === group)
          .map((g) => {
            const st = garmentState(meta, g)
            return (
              <OptionCard
                key={g.id}
                label={g.label}
                image={st.disabled ? undefined : thumbUrl(p, g.id)}
                selected={value === g.id}
                disabled={st.disabled}
                note={st.note}
                onSelect={() => onPick(allowNone && value === g.id ? null : g.id)}
              />
            )
          })}
      </OptionSection>
    ))
  return <CollectionSplit p={p} items={GARMENTS.filter((g) => g.slot === slot)} render={grid} moreLabel="More styles from other collections" />
}

export function AvatarStudio({ view, children }: { view: AvatarView; children?: ReactNode }) {
  const tab = useStyleStore((s) => s.active_avatar_tab)
  const config = useStyleStore((s) => s.avatar_config)
  const profile = useStyleStore(useShallow((s) => ({ gender: s.gender, height: s.height, weight: s.weight, age: s.age, skin: s.skin_tone, detected: s.skin_tone_detected })))
  const set = useStyleStore((s) => s.set)
  const setSkinShade = useStyleStore((s) => s.setSkinShade)
  const update = useStyleStore((s) => s.updateAvatar)
  const p = view.resolved.presentation
  const model = AVATAR_MODELS[p]
  const { meta } = useAvatarMeta(p)
  const active = STUDIO_CATEGORIES.some((c) => c.id === tab) ? tab : 'appearance'
  const shade = SKIN_TONES.find((t) => t.id === view.resolved.skinTone)
  const suggested = suggestBodyType(p, profile.height, profile.weight)
  const bodyLabel = (id: string) => BODY_TYPES.find((b) => b.id === id)?.label ?? id

  const [indianOnly, setIndianOnly] = useState(false)
  const hairItems = indianOnly ? HAIRSTYLES.filter((h) => h.indian) : HAIRSTYLES

  const toggleAccessory = (id: AccessoryId) => {
    const has = config.accessories.includes(id)
    const others = config.accessories.filter((a) => a !== id && !(ACCESSORY_CONFLICTS[id] ?? []).includes(a))
    update({ accessories: has ? others : [...others, id] })
  }

  return (
    <div className="studio">
      <div className="studio-tabs" role="tablist" aria-label="Customisation categories">
        {STUDIO_CATEGORIES.map((c) => (
          <button key={c.id} type="button" role="tab" aria-selected={active === c.id} className={`studio-tab${active === c.id ? ' on' : ''}`} onClick={() => set({ active_avatar_tab: c.id })}>
            <span aria-hidden="true">{c.icon}</span> {c.label}
          </button>
        ))}
      </div>

      <div className="studio-panel" role="tabpanel">
        {active === 'appearance' && (
          <>
            <div className="profile-summary" aria-label="Avatar initialised from your profile">
              <div className="page-kicker">Initialised from your profile</div>
              <div className="profile-chips">
                <span>{profile.gender}</span>
                <span>{profile.height} cm</span>
                <span>{profile.weight} kg</span>
                <span>
                  Skin: {profile.skin}
                  {shade ? ` · ${shade.label}` : ''}
                </span>
                <span>{profile.age} yrs</span>
              </div>
              <div className="muted">
                Model <strong>{model.label}</strong> · stature calibrated to {profile.height} cm ·{' '}
                {view.bodySuggested ? (
                  <>
                    build <strong>{view.build.label.toLowerCase()}</strong> (blended from height &amp; weight; choose a body type to override)
                  </>
                ) : (
                  <>
                    body type <strong>{bodyLabel(view.resolved.bodyType)}</strong> (your choice)
                  </>
                )}{' '}
                · {view.age.status}
              </div>
              <label className="st-check" style={{ marginTop: '0.45rem' }}>
                <input type="checkbox" checked={config.useProfileAge} onChange={(e) => update({ useProfileAge: e.target.checked })} />
                Apply my profile age (gradual MakeHuman face/body shaping and skin ageing; your profile is not changed)
              </label>
            </div>
            {view.needsPresentationChoice && (
              <div className="alert info">
                Your profile gender is <strong>{profile.gender}</strong>. The avatar starts on the androgynous model. You can choose any body model below, and every hairstyle and
                garment stays available on it.
              </div>
            )}
            <p className="caption">
              Switching the body model (here or through your profile gender) loads that model's default hairstyle, body and casual outfit. Your profile, skin tone, eye and
              hair colour, accessories and recommendations are kept.
            </p>
            <OptionSection title="Body model" hint={`Profile gender: ${profile.gender}`}>
              <OptionCard label="Follow profile" selected={config.presentation === null} image={thumbUrl(p, 'body_average')} onSelect={() => update({ presentation: null })} />
              {Object.values(AVATAR_MODELS).map((m) => (
                <OptionCard key={m.id} label={m.label} selected={config.presentation === m.id} image={thumbUrl(m.id, 'body_average')} onSelect={() => update({ presentation: m.id })} />
              ))}
            </OptionSection>
            <OptionSection title="Pose">
              <OptionCard label="Front (Model A)" selected={config.pose === 'front'} image={thumbUrl(p, 'pose_front')} onSelect={() => update({ pose: 'front' })} />
              <OptionCard label="3/4 fashion pose (Model B)" selected={config.pose === 'three_quarter'} image={thumbUrl(p, 'pose_three_quarter')} onSelect={() => update({ pose: 'three_quarter' })} />
            </OptionSection>
            <OptionSection title="Eye colour" hint="Real iris textures">
              {EYE_COLORS.map((e) => (
                <OptionCard key={e.id} size="sm" label={e.label} image={`${AVATAR_ASSET_ROOT}/tex/${e.id}_eye.png`} selected={config.eyeColor === e.id} onSelect={() => update({ eyeColor: e.id })} />
              ))}
            </OptionSection>
          </>
        )}

        {active === 'face' && (
          <>
            {(
              [
                ['Face shape', FACE_SHAPES, 'facePreset'],
                ['Eye shape', EYE_SHAPES, 'eyeShape'],
                ['Nose', NOSES, 'nose'],
                ['Lips', LIPS, 'lips'],
              ] as const
            ).map(([title, options, field]) => (
              <OptionSection key={field} title={title}>
                {options.map((o) => (
                  <OptionCard key={o.id} label={o.label} image={thumbUrl(p, `morph_${o.id}`)} selected={config[field] === o.id} onSelect={() => update({ [field]: o.id })} />
                ))}
              </OptionSection>
            ))}
            <OptionSection title="Eyebrows">
              {EYEBROWS.map((b) => (
                <OptionCard key={b.id} size="sm" label={b.label} image={thumbUrl(p, b.id)} selected={view.resolved.eyebrows === b.id} onSelect={() => update({ eyebrows: b.id })} />
              ))}
            </OptionSection>
            {p !== 'female' && (
              <OptionSection title="Facial hair" hint="CC0 beard meshes, fitted to the face and tinted with the hair colour">
                {FACIAL_HAIR.map((f) => {
                  const missing = f.available === false || (!!f.mesh && !!meta && !meta.facialHair?.includes(f.mesh))
                  return (
                    <OptionCard
                      key={f.id}
                      label={f.label}
                      image={missing ? undefined : thumbUrl(p, f.mesh ?? 'morph_natural')}
                      selected={(view.resolved.facialHair ?? null) === (f.mesh ?? null)}
                      disabled={missing}
                      note={f.note ?? (missing ? 'Not built for this model' : undefined)}
                      onSelect={() => update({ facialHair: f.id })}
                    />
                  )
                })}
              </OptionSection>
            )}
          </>
        )}

        {active === 'hair' && (
          <>
            <div className="chip-select" role="group" aria-label="Hairstyle collection">
              <button type="button" className={`chip-toggle${!indianOnly ? ' on' : ''}`} aria-pressed={!indianOnly} onClick={() => setIndianOnly(false)}>
                All hairstyles
              </button>
              <button type="button" className={`chip-toggle${indianOnly ? ' on' : ''}`} aria-pressed={indianOnly} onClick={() => setIndianOnly(true)}>
                Indian hairstyles
              </button>
            </div>
            <p className="caption">
              Built from the 10 real MakeHuman hair meshes (cut, faded, waved or combined) plus braids, ponytails and buns modelled on the head. Every style follows your body,
              face and age, and keeps the hair colour you choose.
            </p>
            <CollectionSplit
              p={p}
              items={hairItems}
              moreLabel="More hairstyles"
              render={(items) =>
                HAIR_GROUPS.filter((g) => items.some((h) => h.group === g)).map((group) => (
                  <OptionSection key={group} title={group}>
                    {items
                      .filter((h) => h.group === group)
                      .map((h) => {
                        const st = hairState(meta, h)
                        return (
                          <OptionCard
                            key={h.id}
                            label={h.label}
                            image={st.disabled ? undefined : thumbUrl(p, `hair_${h.id.replace(/^hair_/, '')}`)}
                            selected={view.resolved.hairstyle === h.id}
                            disabled={st.disabled}
                            note={st.note}
                            onSelect={() => update({ hairstyle: h.id })}
                          />
                        )
                      })}
                  </OptionSection>
                ))
              }
            />
            <OptionSection title="Hair colour" hint="Also tints the eyebrows">
              {HAIR_COLORS.map((c) => (
                <OptionCard key={c.id} size="sm" label={c.label} image={thumbUrl(p, `haircolor_${c.id}`)} swatch={c.hex} selected={config.hairColor === c.id} onSelect={() => update({ hairColor: c.id })} />
              ))}
            </OptionSection>
            <OptionSection title="Highlights" hint="Streaks and face-framing pieces over the hair colour; roots stay natural">
              <OptionCard size="sm" label="None" image={thumbUrl(p, `haircolor_${config.hairColor}`)} selected={!config.hairHighlight} onSelect={() => update({ hairHighlight: null })} />
              {HAIR_HIGHLIGHTS.map((c) => (
                <OptionCard key={c.id} size="sm" label={c.label} image={thumbUrl(p, `hairhl_${c.id}`)} swatch={c.hex} selected={config.hairHighlight === c.id} onSelect={() => update({ hairHighlight: c.id })} />
              ))}
            </OptionSection>
          </>
        )}

        {active === 'skin' && (
          <>
            <div className="alert info">
              Skin tone is part of your <strong>profile</strong>. Choosing a shade here updates your profile skin tone (now <strong>{profile.skin}</strong>), which the outfit
              recommendations use for colour matching. Changing it on the Appearance page updates the avatar too.
            </div>
            <OptionSection title="Skin tone" hint="Real skin textures, tinted: texture detail is preserved">
              {SKIN_TONES.map((t) => (
                <OptionCard key={t.id} size="sm" label={`${t.label} · ${t.recommenderTone}`} swatch={t.swatch} selected={view.resolved.skinTone === t.id} onSelect={() => setSkinShade(t.id)} />
              ))}
            </OptionSection>
            {profile.detected && (
              <p className="caption">
                Detected from your photo: <strong>{profile.detected}</strong>
                {profile.detected !== profile.skin ? '. You have since chosen a different tone manually.' : ' (matches your current choice).'}
              </p>
            )}
          </>
        )}

        {active === 'body' && (
          <>
            <p className="caption">
              Appearance presets for the {model.label.toLowerCase()} model, not health classifications. Each is a body-shape morph built into the model; clothes and hair were
              re-fitted for every preset. Height comes from your profile.
            </p>
            {view.bodyNote && <div className="alert warning">{view.bodyNote}</div>}
            <OptionSection title="Body type" hint={`Suggested from ${profile.height} cm / ${profile.weight} kg: ${bodyLabel(suggested)}`}>
              <OptionCard label={`Suggested (${bodyLabel(suggested)})`} image={thumbUrl(p, `body_${suggested}`)} selected={config.bodyType === null} onSelect={() => update({ bodyType: null })} />
              {model.bodyPresets.map((b) => (
                <OptionCard key={b} label={bodyLabel(b)} image={thumbUrl(p, `body_${b}`)} selected={config.bodyType === b} onSelect={() => update({ bodyType: b })} />
              ))}
            </OptionSection>
          </>
        )}

        {active === 'clothing' && (
          <>
            <p className="caption">
              Avatar clothing is for visualisation only. It does not change your recommended outfit. {model.label} styles are listed first; the rest are under
              “More styles”. Every item is a real 3D garment fitted to this body.
            </p>
            <h3 className="studio-subhead">Tops</h3>
            {/* Choosing a separate piece takes off a one-piece outfit. */}
            <GarmentGrid p={p} meta={meta} slot="top" value={config.full ? null : config.top} onPick={(id) => update({ top: id, full: null })} />
            {config.top && !config.full && <ColourRow slot="Top" field="topColor" config={config} update={update} item={config.top} />}
            <h3 className="studio-subhead">Bottoms</h3>
            <GarmentGrid p={p} meta={meta} slot="bottom" value={config.full ? null : config.bottom} onPick={(id) => update({ bottom: id, full: null })} />
            {config.bottom && !config.full && <ColourRow slot="Bottom" field="bottomColor" config={config} update={update} item={config.bottom} />}
            <h3 className="studio-subhead">Dresses, suits &amp; traditional one-piece outfits</h3>
            <p className="caption">Worn instead of top and bottom. Click the selected outfit again to go back to your separates.</p>
            <GarmentGrid p={p} meta={meta} slot="full" value={config.full} onPick={(id) => update({ full: id })} allowNone />
            {config.full && <ColourRow slot="Outfit" field="fullColor" config={config} update={update} item={config.full} />}
            <h3 className="studio-subhead">Outerwear</h3>
            <p className="caption">Outerwear includes its own shirt front, so it is worn instead of the top. Click the selected piece again to remove it.</p>
            <GarmentGrid p={p} meta={meta} slot="outerwear" value={config.full ? null : config.outerwear} onPick={(id) => update({ outerwear: id, full: null })} allowNone />
            {config.outerwear && !config.full && <ColourRow slot="Outerwear" field="outerwearColor" config={config} update={update} item={config.outerwear} />}
          </>
        )}

        {active === 'footwear' && (
          <>
            <GarmentGrid p={p} meta={meta} slot="footwear" value={config.footwear} onPick={(id) => update({ footwear: id })} />
            {config.footwear && <ColourRow slot="Footwear" field="footwearColor" config={config} update={update} item={config.footwear} />}
          </>
        )}

        {active === 'accessories' && (
          <>
            {(['Jewellery', 'Eyewear', 'Other'] as const).map((group) => (
              <OptionSection key={group} title={group} hint={group === 'Eyewear' ? 'One pair at a time' : 'Select several: click again to remove'}>
                {ACCESSORIES.filter((a) => a.group === group).map((a) => (
                  <OptionCard key={a.id} toggle label={a.label} image={thumbUrl(p, `acc_${a.id}`)} selected={config.accessories.includes(a.id)} onSelect={() => toggleAccessory(a.id)} />
                ))}
                {group === 'Other' && (
                  <OptionCard toggle label="Fedora hat" image={thumbUrl(p, 'hat_fedora')} selected={config.hat === 'hat_fedora'} onSelect={() => update({ hat: config.hat ? null : 'hat_fedora' })} />
                )}
              </OptionSection>
            ))}
          </>
        )}
      </div>
      {children}
    </div>
  )
}
