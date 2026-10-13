import * as THREE from 'three'

/**
 * Body-skin material additions (installed once per body material, then driven by uniforms):
 *
 *  1. Scalp / hair roots: skin under the hairstyle (vertex attribute `aScalp`, from scalpCoverage.ts)
 *     is shaded towards a darker root tone of the hair colour, so gaps between hair cards and the
 *     hairline read as hair growing from the scalp instead of bare skin under a wig.
 *
 *  2. Age detail: luminance-ratio maps derived from MakeHuman's own middle-aged and old skin textures
 *     (tools/avatar-pipeline/age_detail.py). They share the body UV layout, so forehead lines, crow's
 *     feet and nasolabial folds sit exactly where the face geometry has them. Applied multiplicatively,
 *     so the user's chosen skin tone (texture + tint) is preserved. Weights blend continuously with age.
 */

export interface SkinUniforms {
  uScalpColor: { value: THREE.Color }
  uScalpAmount: { value: number }
  uAgeMap: { value: THREE.Texture | null }
  /** x = middle-aged detail weight, y = old detail weight */
  uAgeWeights: { value: THREE.Vector2 }
}

const VERT_PARS = /* glsl */ `
attribute float aScalp;
varying float vScalp;
`
const FRAG_PARS = /* glsl */ `
uniform vec3 uScalpColor;
uniform float uScalpAmount;
uniform sampler2D uAgeMap;
uniform vec2 uAgeWeights;
varying float vScalp;
`
const FRAG_MAIN = /* glsl */ `
#ifdef USE_MAP
if (uAgeWeights.x + uAgeWeights.y > 0.001) {
  // Stored ratio r in [0.6, 1.4] as (r - 0.6) / 0.8; 0.5 = no change.
  vec2 ratio = texture2D(uAgeMap, vMapUv).rg * 0.8 + 0.6;
  diffuseColor.rgb *= 1.0 + (ratio.x - 1.0) * uAgeWeights.x + (ratio.y - 1.0) * uAgeWeights.y;
}
#endif
float scalp = clamp(vScalp, 0.0, 1.0) * uScalpAmount;
diffuseColor.rgb = mix(diffuseColor.rgb, uScalpColor, scalp);
`

export function skinUniforms(mat: THREE.Material): SkinUniforms {
  let u = mat.userData.skinUniforms as SkinUniforms | undefined
  if (!u) {
    u = {
      uScalpColor: { value: new THREE.Color('#2a1d16') },
      uScalpAmount: { value: 0.88 },
      uAgeMap: { value: null },
      uAgeWeights: { value: new THREE.Vector2() },
    }
    mat.userData.skinUniforms = u
    const uni = u
    mat.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, uni)
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', `#include <common>\n${VERT_PARS}`)
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvScalp = aScalp;')
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', `#include <common>\n${FRAG_PARS}`)
        .replace('#include <map_fragment>', `#include <map_fragment>\n${FRAG_MAIN}`)
    }
    mat.customProgramCacheKey = () => 'styleai-skin-v1'
  }
  return u
}

/** Root tone seen through the hair: the hair colour, darker and slightly desaturated. */
export function scalpColor(hairHex: string): THREE.Color {
  const c = new THREE.Color(hairHex)
  const hsl = { h: 0, s: 0, l: 0 }
  c.getHSL(hsl)
  return c.setHSL(hsl.h, hsl.s * 0.85, Math.max(0.03, hsl.l * 0.72))
}

/**
 * Continuous age-detail weights. Under 30 the young texture is used as is; middle-aged detail fades
 * in from 30 to 50, old detail takes over from 50 to 75 (both kept subtle: at most 0.85).
 */
export function ageDetailWeights(age: number): [number, number] {
  const a = Number(age) || 0
  const s = (x: number, lo: number, hi: number) => THREE.MathUtils.smoothstep(x, lo, hi)
  const old = s(a, 50, 75)
  const mid = s(a, 30, 50) * (1 - old)
  return [0.85 * mid, 0.85 * old]
}
