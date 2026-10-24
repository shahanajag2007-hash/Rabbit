export type Category = 'Top' | 'Bottom' | 'Shoes' | 'Accessory'

export const CATEGORIES: Category[] = ['Top', 'Bottom', 'Shoes', 'Accessory']

/** A row of data/fashion_dataset.csv as returned by the API (plus a resolved image_url). */
export interface OutfitItem {
  item_id: number | string
  category: Category | string
  item_name: string
  colour: string
  shade?: string
  style: string
  occasion: string
  price: number
  image?: string
  image_url?: string
  fabric?: string
  fabric_tag?: string
  // Live brand-store products (absent on the original CSV items).
  brand?: string
  product_url?: string | null
  product_id?: string
  colour_label?: string
  mrp?: number | null
  sizes?: string[]
  available_sizes?: string[]
  variants?: ProductVariant[]
  colour_options?: ColourOption[]
  price_checked_at?: string | null
  /** Garment type (kurta, palazzo, sneakers, ethnic_set, saree, dress, ...). */
  subcategory?: string | null
  /** A set, saree, dress or suit that fills the Top slot and replaces bottom wear. */
  covers_bottom?: boolean
  /** "product" = the product's own page; "search" = a retailer search page (imported feeds only). */
  link_type?: 'product' | 'search'
  /** Size the user picked on Complete Look (one of available_sizes). */
  selected_size?: string | null
  [key: string]: unknown
}

/** One purchasable variant (colour + size) of a live product. */
export interface ProductVariant {
  variant_id: number | string
  size: string | null
  available: boolean
  price: number
  mrp?: number | null
  url: string | null
  image?: string
}

/** Another in-stock colour of the same product (a separate catalogue item). */
export interface ColourOption {
  item_id: string
  colour: string
  colour_label: string
  image: string
  price: number
}

export type ScoreBreakdown = Record<'colour' | 'style' | 'occasion' | 'compatibility' | 'budget', number>

export interface Outfit {
  signature?: (string | number)[]
  items: Partial<Record<Category, OutfitItem>>
  score?: number
  total_price?: number
  breakdown?: ScoreBreakdown
  palette?: string[]
  reasons?: string[]
  over_budget?: boolean
}

export interface ScoreResult {
  score: number
  breakdown: ScoreBreakdown
  total_price: number
}

/** Same keys the Streamlit app sent to recommender.recommend_outfits(). */
export interface UserProfile {
  gender: string
  height: number
  weight: number
  skin_tone: string
  style: string
  occasion: string
  budget: number
  favorite_colours: string[]
  avoid_colours: string[]
  age?: number
  preferred_fit?: string
  preferred_fabrics?: string[]
  preferred_brands?: string[]
  /** Free-text request, sent once the user presses "Analyze my style". */
  preference_text?: string
  /** Colour picked from the Recommended Colour Palette. */
  palette_colour?: string | null
}

export interface RecommendResponse {
  outfits: Outfit[]
  notes: string[]
  understood: string[]
  /** Style / occasion / budget actually used once the text request is applied. */
  context?: { style: string; styles: string[]; occasion: string; budget: number }
}

export interface PaletteSwatch {
  name: string
  hex: string
  count: number
  reason: string
}

export interface BuilderStep {
  category: Category
  items: OutfitItem[]
  total: number
  remaining_budget: number
  notes: string[]
}

export interface SizeHint {
  size: string
  note: string
}

export interface ShoppingAlternative {
  platform: string
  product_name: string
  price: number
  original_price?: number
  savings: number
  url: string
  image: string
  match_type: string
}

export interface ShoppingResponse {
  alternatives: Partial<Record<Category, ShoppingAlternative>>
  configured_providers: string[]
  mock_mode: boolean
}

export interface Swatch {
  name: string
  hex: string
}

export interface Meta {
  categories: Category[]
  score_weights: Record<string, number>
  skin_tone_palettes: Record<string, string[]>
  demo_palettes: Record<string, Swatch[]>
  suggestion_chips: string[]
  fabric_notes: Record<string, string>
}

export interface AvatarBuilder {
  gender: string
  model_preset: string
  body_shape: string
  height: number
  weight: number
  skin_tone: string
  hair_style: string
  hair_colour: string
  hair_type?: string
  occasion: string
  outfit?: string
  accessory: string
}

export interface SkinToneAnalysis {
  skin_tone: string
  dominant_rgb: [number, number, number]
  palette: string[]
}

/** Result of validating an uploaded photo on the server (see api/photos.py). */
export interface PhotoValidation {
  photo_id: string
  accepted: boolean
  /** Checks that passed / failed, in plain words. */
  checks: { name: string; ok: boolean | null; message: string }[]
  /** Problems that make the photo unusable for a full-body try-on. */
  problems: string[]
  width: number
  height: number
  skin_tone?: string | null
  skin_rgb?: [number, number, number] | null
  palette?: string[]
}

export interface TryOnProvider {
  provider: string
  configured: boolean
  label: string
  /** Outfit categories this provider renders on the photo. */
  garments: string[]
  missing: string | null
  /** Earlier providers in the fallback chain that could not run, and why. */
  skipped?: string[]
}

export interface TryOnJob {
  job_id: string
  photo_id: string
  status: 'queued' | 'running' | 'done' | 'failed' | 'cancelled'
  /** True when an earlier identical result was reused instead of running the model again. */
  cached?: boolean
  provider: string
  label: string
  garments: Record<string, { item_id: string | number; item_name: string }>
  rendered: string[]
  not_rendered: string[]
  error: string | null
}
