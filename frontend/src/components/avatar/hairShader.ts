import * as THREE from 'three'
import type { HairShaderMod } from './ProceduralHair'

/**
 * Shader modifications that turn the 10 real MakeHuman hair meshes into further styles (see HairMod
 * in hairStyles.ts). Everything works in the mesh's object space *after* the morph targets, so the
 * cuts and displacements follow every body, face and age morph. All features are driven by uniforms,
 * so switching between styles built on the same mesh only updates values (no shader recompile).
 */

interface HairUniforms {
  uHairKeep: { value: number }
  uHairTrimY: { value: number }
  uHairFade: { value: THREE.Vector2 }
  uHairWave: { value: THREE.Vector2 }
  uHairVolume: { value: number }
  /** amount, centre focus (0 = all over the top, 1 = a central strip: faux hawk) */
  uHairSpike: { value: THREE.Vector2 }
  /** highlight colour (rgb) and strength (a, 0 = none) */
  uHairStreak: { value: THREE.Vector4 }
  uHairLift: { value: number }
  uHairCrop: { value: number }
  uHairPart: { value: number }
  uHairMirror: { value: number }
  /** earY, topY, headY, headZ */
  uHairFrame: { value: THREE.Vector4 }
  /** eyeY, eyeZ, neckY, (unused) */
  uHairFace: { value: THREE.Vector4 }
  /** rx, R (head centre -> crown) */
  uHairRadii: { value: THREE.Vector2 }
}

const OFF = -1000

const VERT_PARS = /* glsl */ `
uniform float uHairLift;
uniform float uHairCrop;
uniform float uHairPart;
uniform float uHairMirror;
uniform vec2 uHairRadii;
uniform vec2 uHairWave;
uniform float uHairVolume;
uniform vec2 uHairSpike;
uniform vec4 uHairFrame;
uniform vec4 uHairFace;
varying vec3 vHairPos;
`

const VERT_MAIN = /* glsl */ `
{
  vec3 hp = transformed;
  if (uHairMirror > 0.5) hp.x = -hp.x;
  float headZ = uHairFrame.w;
  if (uHairPart != 0.0) {
    // Side parting: rotate the top of the hair around the forward axis, in the scalp ellipsoid's
    // normalised space (so it stays on the head), fading out towards the ears.
    vec2 c = vec2(0.0, uHairFrame.z);
    vec2 s = vec2(uHairRadii.x + 0.02, uHairRadii.y + 0.02);
    vec2 q = (hp.xy - c) / s;
    float a = -uHairPart * smoothstep(uHairFrame.x - 0.02, uHairFace.x + 0.05, hp.y);
    q = vec2(q.x * cos(a) - q.y * sin(a), q.x * sin(a) + q.y * cos(a));
    hp.xy = c + q * s;
  }
  if (uHairLift > 0.0) {
    // Raise and push forward the front-top section (quiff / pompadour).
    float front = smoothstep(headZ - 0.01, headZ + 0.07, hp.z);
    float top = smoothstep(uHairFace.x + 0.015, uHairFace.x + 0.07, hp.y);
    float k = front * top;
    hp.y += uHairLift * k;
    hp.z += uHairLift * 0.45 * k;
  }
  if (uHairWave.x > 0.0) {
    // Waves grow below the ears; the scalp stays smooth. Also adds volume to the lengths.
    float below = smoothstep(uHairFrame.x + 0.03, uHairFrame.x - 0.08, hp.y);
    vec2 radial = vec2(hp.x, hp.z - headZ);
    float rl = max(length(radial), 1e-4);
    radial /= rl;
    float phase = atan(hp.x, hp.z - headZ);
    float wv = sin(hp.y * uHairWave.y + phase * 5.0) * 0.7 + sin(hp.y * uHairWave.y * 0.53 - phase * 3.0) * 0.3;
    float amp = uHairWave.x * (0.35 + 0.65 * below);
    hp.xz += radial * (wv * amp + uHairWave.x * 0.9 * below);
  }
  if (uHairVolume > 0.0) {
    // Body and bounce: the lengths spread out more the further they fall below the ears (A-line),
    // the sides more than the back, so open hair frames the face instead of hanging flat.
    float drop = clamp((uHairFrame.x + 0.02 - hp.y) / 0.25, 0.0, 1.0);
    float crown = smoothstep(uHairFrame.y - 0.02, uHairFrame.x, hp.y) * smoothstep(uHairFrame.x - 0.06, uHairFrame.x + 0.02, hp.y);
    vec2 radial = vec2(hp.x * 1.35, hp.z - headZ);
    radial /= max(length(radial), 1e-4);
    hp.xz += radial * uHairVolume * (drop * (0.55 + 0.45 * drop) + 0.25 * crown);
  }
  if (uHairSpike.x > 0.0) {
    // Textured spikes on the top: clumps pushed up and out (gel / wax look).
    vec3 c = vec3(0.0, uHairFrame.z, headZ);
    vec3 n = normalize(hp - c);
    float top = smoothstep(uHairFace.x + 0.06, uHairFrame.y - 0.02, hp.y);
    float strip = mix(1.0, exp(-hp.x * hp.x / 0.0012), uHairSpike.y);
    float clump = pow(max(0.0, sin(hp.x * 140.0 + 1.3) * sin(hp.z * 120.0 + hp.y * 40.0)), 2.0);
    hp += (n + vec3(0.0, 0.6, 0.25)) * uHairSpike.x * top * strip * (0.35 + 0.65 * clump);
  }
  if (uHairCrop > 0.0) {
    // Clipper cut: pull each strand towards the scalp ellipsoid (3 mm above it).
    vec3 c = vec3(0.0, uHairFrame.z, headZ - 0.008);
    vec3 radii = vec3(uHairRadii.x - 0.006, uHairRadii.y, uHairRadii.y * 0.97);
    vec3 d = (hp - c) / radii;
    float r = length(d);
    vec3 onScalp = c + d / max(r, 1e-4) * radii;
    vec3 target = onScalp + normalize(hp - c) * 0.003;
    hp = mix(hp, target, uHairCrop * step(1.0, r));
  }
  transformed = hp;
  vHairPos = hp;
}
`

const FRAG_PARS = /* glsl */ `
uniform float uHairKeep;
uniform float uHairTrimY;
uniform vec2 uHairFade;
uniform vec4 uHairFrame;
uniform vec4 uHairFace;
uniform vec2 uHairRadii;
uniform vec4 uHairStreak;
varying vec3 vHairPos;
float hairHash(vec3 p) { return fract(sin(dot(floor(p * 900.0), vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
`

const FRAG_STREAK = /* glsl */ `
if (uHairStreak.a > 0.0) {
  // Highlights (balayage): a few soft ribbons around the head plus two face-framing front pieces.
  // They start at forehead height, so the top and the parting keep the base colour, and grow
  // stronger towards the ends.
  vec3 hp = vHairPos;
  float phase = atan(hp.x, hp.z - uHairFrame.w);
  float ribbons = smoothstep(0.45, 0.85, sin(phase * 9.0 + 0.8 * sin(hp.y * 6.0)));
  float front = smoothstep(0.32, 0.06, abs(abs(phase) - 0.62));
  float k = max(ribbons * 0.85, front);
  float eyeY = uHairFace.x;
  k *= smoothstep(eyeY + 0.08, eyeY + 0.02, hp.y);
  k *= 0.55 + 0.45 * clamp((eyeY - hp.y) / 0.25, 0.0, 1.0);
  vec3 tex = diffuseColor.rgb / max(diffuse, vec3(1e-3));
  diffuseColor.rgb = mix(diffuseColor.rgb, tex * uHairStreak.rgb, k * uHairStreak.a);
}
`

const FRAG_MAIN = /* glsl */ `
{
  vec3 hp = vHairPos;
  float earY = uHairFrame.x;
  float headY = uHairFrame.z;
  float headZ = uHairFrame.w;
  if (uHairKeep > 0.5 && uHairKeep < 1.5) {
    // Scalp only: keep what lies on the head shell, drop the hanging tail.
    vec3 d = (hp - vec3(0.0, headY, headZ - 0.008)) / vec3(uHairRadii.x + 0.022, uHairRadii.y + 0.03, uHairRadii.y + 0.004);
    if (dot(d, d) > 1.0 || hp.y < earY - 0.03) discard;
    // Soften the lower edge (dithered over 2 cm) instead of a hard horizontal cut behind the ears.
    float edge = (hp.y - (earY - 0.03)) / 0.02;
    if (edge < 1.0 && hairHash(hp) > edge) discard;
  } else if (uHairKeep > 1.5) {
    // Fringe only: the front section, ending above the brow line so it never covers the eyes.
    if (hp.z < headZ + 0.035 || hp.y < uHairFace.x + 0.03) discard;
  }
  if (uHairTrimY > ${OFF + 1}.0 && hp.y < uHairTrimY) discard;
  if (uHairFade.y > uHairFade.x) {
    if (hp.y < uHairFade.x) discard;
    float t = (hp.y - uHairFade.x) / (uHairFade.y - uHairFade.x);
    if (t < 1.0 && hairHash(hp) > t) discard;
  }
}
`

function uniforms(mat: THREE.Material): HairUniforms {
  let u = mat.userData.hairUniforms as HairUniforms | undefined
  if (!u) {
    u = {
      uHairKeep: { value: 0 },
      uHairTrimY: { value: OFF },
      uHairFade: { value: new THREE.Vector2(0, 0) },
      uHairWave: { value: new THREE.Vector2(0, 0) },
      uHairVolume: { value: 0 },
      uHairSpike: { value: new THREE.Vector2(0, 0) },
      uHairStreak: { value: new THREE.Vector4(1, 1, 1, 0) },
      uHairLift: { value: 0 },
      uHairCrop: { value: 0 },
      uHairPart: { value: 0 },
      uHairMirror: { value: 0 },
      uHairFrame: { value: new THREE.Vector4() },
      uHairFace: { value: new THREE.Vector4() },
      uHairRadii: { value: new THREE.Vector2() },
    }
    mat.userData.hairUniforms = u
    const uni = u
    mat.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, uni)
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', `#include <common>\n${VERT_PARS}`)
        .replace('#include <morphtarget_vertex>', `#include <morphtarget_vertex>\n${VERT_MAIN}`)
        .replace('#include <defaultnormal_vertex>', 'if (uHairMirror > 0.5) objectNormal.x = -objectNormal.x;\n#include <defaultnormal_vertex>')
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', `#include <common>\n${FRAG_PARS}`)
        .replace('#include <clipping_planes_fragment>', `#include <clipping_planes_fragment>\n${FRAG_MAIN}`)
        .replace('#include <map_fragment>', `#include <map_fragment>\n${FRAG_STREAK}`)
    }
    mat.customProgramCacheKey = () => 'styleai-hair-v4'
  }
  return u
}

/** Install (once) and update the hair modifications on a hair-mesh material. `null` = unmodified mesh. */
export function applyHairMod(mat: THREE.Material, mod: HairShaderMod | null) {
  const u = uniforms(mat)
  const f = mod?.frame
  u.uHairKeep.value = mod?.keep ?? 0
  u.uHairTrimY.value = mod?.trimY ?? OFF
  u.uHairFade.value.set(mod?.fade?.[0] ?? 0, mod?.fade?.[1] ?? 0)
  u.uHairWave.value.set(mod?.wave?.[0] ?? 0, mod?.wave?.[1] ?? 0)
  u.uHairVolume.value = mod?.volume ?? 0
  u.uHairSpike.value.set(mod?.spike?.[0] ?? 0, mod?.spike?.[1] ?? 0)
  u.uHairLift.value = mod?.lift ?? 0
  u.uHairCrop.value = mod?.crop ?? 0
  u.uHairPart.value = mod?.part ?? 0
  u.uHairMirror.value = mod?.mirror ? 1 : 0
  if (f) {
    u.uHairFrame.value.set(f.earY, f.topY, f.headY, f.headZ)
    u.uHairFace.value.set(f.eyeY, f.eyeZ, f.neckY, 0)
    u.uHairRadii.value.set(f.rx, f.R)
  }
}

/** Highlight streaks in `hex` (null = none). Works on hair meshes and procedural parts alike. */
export function applyHairHighlight(mat: THREE.Material, hex: string | null) {
  const u = uniforms(mat)
  if (!hex) {
    u.uHairStreak.value.w = 0
    return
  }
  // Boosted: the strand texture it multiplies is mid-grey.
  const c = new THREE.Color(hex).multiplyScalar(1.6)
  u.uHairStreak.value.set(c.r, c.g, c.b, 0.85)
}

/** Does this modification remove parts of the mesh? (Then the mesh should not cast the full shadow.) */
export function hairModCuts(mod: HairShaderMod | null): boolean {
  return !!mod && (mod.keep !== 0 || mod.trimY !== null || mod.fade !== null)
}
