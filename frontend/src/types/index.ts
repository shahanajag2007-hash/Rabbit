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
  [key: string]: unknown
}

export type ScoreBreakdown = Record<'colour' | 'style' | 'occasion' | 'compatibility' | 'budget', number>

export interface Outfit {
  signature?: (string | number)[]
  items: Partial<Record<Category, OutfitItem>>
  score?: number
  total_price?: number
  breakdown?: ScoreBreakdown
  palette?: string[]
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
