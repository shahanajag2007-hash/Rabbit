import type { Category, OutfitItem } from '../../types'
import type { AccessoryId } from './avatarCatalog'
import type { WornGarment } from './RealisticAvatar'

/**
 * Maps the backend's recommended items onto the avatar's real 3D garments.
 * Item types are classified with the keyword rules from avatar_engine.py (extended to every item
 * in data/fashion_dataset.csv); the closest available garment asset is chosen and tinted with the
 * item's colour. The viewer only *displays* the backend's outfit — it never picks items itself.
 */

export type TopKind = 'tee' | 'polo' | 'henley' | 'shirt' | 'overshirt' | 'blazer' | 'blouse' | 'kurta'
export type BottomKind = 'jeans' | 'chinos' | 'trousers' | 'joggers' | 'cargo' | 'shorts' | 'wide' | 'dhoti' | 'flare'
export type ShoeKind = 'sneakers' | 'canvas' | 'slipons' | 'trainers' | 'loafers' | 'derby' | 'formal' | 'boots' | 'sandals' | 'juttis' | 'heels'
export type AccessoryKind =
  | 'watch' | 'bracelet' | 'tote' | 'handbag' | 'backpack' | 'tie' | 'scarf' | 'stole' | 'earrings'
  | 'cap' | 'belt' | 'wallet' | 'chain' | 'sunglasses' | 'glasses' | 'pocket-square'

export interface GarmentSpec<K extends string = string> {
  kind: K
  colour: string
  itemName: string
}

const RULES: Record<Category, [RegExp, string][]> = {
  Top: [
    [/blazer|jacket/, 'blazer'],
    [/overshirt/, 'overshirt'],
    [/kurta|kurti|tunic/, 'kurta'],
    [/blouse|wrap|top\b/, 'blouse'],
    [/polo/, 'polo'],
    [/henley/, 'henley'],
    [/t-shirt|tee|crewneck/, 'tee'],
    [/shirt|oxford/, 'shirt'],
  ],
  Bottom: [
    [/dhoti/, 'dhoti'],
    [/palazzo|wide/, 'wide'],
    [/flare/, 'flare'],
    [/short/, 'shorts'],
    [/jogger/, 'joggers'],
    [/cargo/, 'cargo'],
    [/jean|denim/, 'jeans'],
    [/chino/, 'chinos'],
    [/trouser|pant/, 'trousers'],
  ],
  Shoes: [
    [/boot/, 'boots'],
    [/sandal/, 'sandals'],
    [/jutti|mojari/, 'juttis'],
    [/heel|stiletto/, 'heels'],
    [/loafer/, 'loafers'],
    [/derby/, 'derby'],
    [/formal|oxford/, 'formal'],
    [/slip/, 'slipons'],
    [/trainer/, 'trainers'],
    [/canvas/, 'canvas'],
    [/sneaker/, 'sneakers'],
  ],
  Accessory: [
    [/watch/, 'watch'],
    [/bracelet|bangle/, 'bracelet'],
    [/tote/, 'tote'],
    [/handbag|purse/, 'handbag'],
    [/backpack/, 'backpack'],
    [/\btie\b/, 'tie'],
    [/stole|dupatta/, 'stole'],
    [/scarf/, 'scarf'],
    [/earring/, 'earrings'],
    [/\bcap\b|hat/, 'cap'],
    [/belt/, 'belt'],
    [/wallet/, 'wallet'],
    [/chain|necklace/, 'chain'],
    [/sunglass/, 'sunglasses'],
    [/glasses/, 'glasses'],
    [/pocket square/, 'pocket-square'],
  ],
}

const DEFAULT_KIND: Record<Category, string> = { Top: 'tee', Bottom: 'jeans', Shoes: 'sneakers', Accessory: 'watch' }

export function garmentKind(category: Category, itemName: string): string {
  const name = itemName.toLowerCase()
  return RULES[category].find(([re]) => re.test(name))?.[1] ?? DEFAULT_KIND[category]
}

const COLOUR_HEX: Record<string, string> = {
  white: '#f4f4f1', 'off-white': '#efe9dc', ivory: '#f3eedf', cream: '#efe4cc', beige: '#d8c3a0', khaki: '#b8a07a',
  sand: '#d6c19a', tan: '#b98a5c', camel: '#c19a6b', brown: '#6b4428', 'tan brown': '#8a5a35', 'dark brown': '#4a2c1a',
  chocolate: '#3e251a', black: '#1c1c1f', 'deep black': '#141416', charcoal: '#36383d', grey: '#7d8086', gray: '#7d8086',
  silver: '#c9ccd2', gold: '#c9a54a', 'rose gold': '#c98f7a', navy: '#1f2a44', 'navy blue': '#1b2a47', blue: '#3b5fa8',
  'classic blue': '#3c5f96', denim: '#3c5a86', 'cobalt blue': '#1f4bb0', cobalt: '#1f4bb0', teal: '#11605f',
  green: '#2f6b3a', 'forest green': '#1e4731', olive: '#5b6234', 'olive green': '#55602f', sage: '#8a9a78',
  emerald: '#0d6646', mustard: '#c9971f', 'mustard yellow': '#c9971f', yellow: '#e2c044', rust: '#a84b26',
  orange: '#d9772b', coral: '#e2735e', red: '#b3282d', maroon: '#6b1d27', burgundy: '#6b1d2f', pink: '#e48aa6',
  'nude pink': '#d9a59a', blush: '#e7b7ae', lavender: '#b5a7d8', purple: '#5b3f8c',
}

export function colourToHex(colour: string | undefined): string {
  const key = String(colour ?? '').trim().toLowerCase()
  if (COLOUR_HEX[key]) return COLOUR_HEX[key]
  // "Gold & Maroon" -> first recognised word group.
  for (const part of key.split(/[&/,]| and /)) {
    const p = part.trim()
    if (COLOUR_HEX[p]) return COLOUR_HEX[p]
  }
  const word = Object.keys(COLOUR_HEX).find((name) => key.includes(name))
  return word ? COLOUR_HEX[word] : '#8b8794'
}

export interface RecommendedOnAvatar {
  worn: Partial<Record<'top' | 'outerwear' | 'bottom' | 'footwear', WornGarment>>
  accessories: AccessoryId[]
  /** Human-readable notes about approximations (shown under the viewer). */
  notes: string[]
}

const TOP_ASSET: Record<TopKind, { id: string; slot: 'top' | 'outerwear'; exact: boolean }> = {
  tee: { id: 'top_white_tee', slot: 'top', exact: true },
  polo: { id: 'top_polo', slot: 'top', exact: true },
  henley: { id: 'top_longsleeve_tee', slot: 'top', exact: false },
  shirt: { id: 'top_formal_shirt', slot: 'top', exact: true },
  overshirt: { id: 'outer_casual_jacket', slot: 'outerwear', exact: false },
  blazer: { id: 'outer_suit_blazer', slot: 'outerwear', exact: true },
  blouse: { id: 'top_striped_blouse', slot: 'top', exact: true },
  kurta: { id: 'top_tunic', slot: 'top', exact: false },
}
const BOTTOM_ASSET: Record<BottomKind, { id: string; exact: boolean }> = {
  jeans: { id: 'bottom_jeans_light', exact: true },
  chinos: { id: 'bottom_suit_trousers', exact: false },
  trousers: { id: 'bottom_suit_trousers', exact: true },
  joggers: { id: 'bottom_leggings', exact: false },
  cargo: { id: 'bottom_cargo', exact: true },
  // Shorts are shown as relaxed cargo trousers (the shorts mesh is not offered: too revealing).
  shorts: { id: 'bottom_cargo', exact: false },
  wide: { id: 'bottom_harem', exact: false },
  dhoti: { id: 'bottom_harem', exact: false },
  flare: { id: 'bottom_suit_trousers', exact: false },
}
const SHOE_ASSET: Record<ShoeKind, { id: string; exact: boolean }> = {
  sneakers: { id: 'shoes_white_sneakers', exact: true },
  canvas: { id: 'shoes_navy_sneakers', exact: false },
  slipons: { id: 'shoes_white_sneakers', exact: false },
  trainers: { id: 'shoes_grey_trainers', exact: true },
  loafers: { id: 'shoes_brown_leather', exact: false },
  derby: { id: 'shoes_brown_leather', exact: true },
  formal: { id: 'shoes_black_formal', exact: true },
  boots: { id: 'shoes_black_boots', exact: true },
  sandals: { id: 'shoes_flats', exact: false },
  juttis: { id: 'shoes_flats', exact: false },
  heels: { id: 'shoes_black_formal', exact: false },
}
const ACCESSORY_ASSET: Partial<Record<AccessoryKind, AccessoryId>> = {
  watch: 'watch',
  bracelet: 'bracelet',
  tote: 'tote',
  handbag: 'handbag',
  earrings: 'earrings',
  chain: 'necklace',
  belt: 'belt',
  sunglasses: 'sunglasses',
  glasses: 'glasses',
}

/** Translate the recommended outfit into avatar garments (closest real asset + item colour). */
export function recommendedOnAvatar(items: Partial<Record<Category, OutfitItem>> | undefined): RecommendedOnAvatar {
  const result: RecommendedOnAvatar = { worn: {}, accessories: [], notes: [] }
  if (!items) return result
  const approx = (item: OutfitItem, label: string) => result.notes.push(`${item.item_name} is shown as the closest available 3D garment (${label}) in ${item.colour}.`)

  const top = items.Top
  if (top) {
    const a = TOP_ASSET[garmentKind('Top', top.item_name) as TopKind]
    result.worn[a.slot] = { id: a.id, color: colourToHex(top.colour) }
    if (!a.exact) approx(top, a.id.replace(/^(top|outer)_/, '').replace(/_/g, ' '))
  }
  const bottom = items.Bottom
  if (bottom) {
    const a = BOTTOM_ASSET[garmentKind('Bottom', bottom.item_name) as BottomKind]
    result.worn.bottom = { id: a.id, color: colourToHex(bottom.colour) }
    if (!a.exact) approx(bottom, a.id.replace(/^bottom_/, '').replace(/_/g, ' '))
  }
  const shoes = items.Shoes
  if (shoes) {
    const a = SHOE_ASSET[garmentKind('Shoes', shoes.item_name) as ShoeKind]
    result.worn.footwear = { id: a.id, color: colourToHex(shoes.colour) }
    if (!a.exact) approx(shoes, a.id.replace(/^shoes_/, '').replace(/_/g, ' '))
  }
  const acc = items.Accessory
  if (acc) {
    const id = ACCESSORY_ASSET[garmentKind('Accessory', acc.item_name) as AccessoryKind]
    if (id) result.accessories.push(id)
    else result.notes.push(`${acc.item_name} is not shown on the avatar (no 3D model for this accessory type yet).`)
  }
  return result
}
