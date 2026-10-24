import type {
  AvatarBuilder,
  BuilderStep,
  Category,
  Meta,
  Outfit,
  OutfitItem,
  PaletteSwatch,
  PhotoValidation,
  RecommendResponse,
  TryOnJob,
  TryOnProvider,
  ScoreResult,
  SizeHint,
  ShoppingResponse,
  SkinToneAnalysis,
  UserProfile,
} from '../types'

/**
 * Base URL of the FastAPI backend. Empty by default so requests go to /api on the same
 * origin (the Vite dev server proxies /api to the backend, see vite.config.ts).
 */
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  readonly status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, credentials: 'include' })
  } catch {
    throw new ApiError(
      'Cannot reach the STYLEAI backend. Make sure the API server is running (uvicorn api.main:app --port 8000).',
      0,
    )
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: { msg?: string }) => d.msg).join('; ')
    } catch {
      // keep generic message
    }
    if (response.status >= 500 || response.status === 404) {
      detail = `${detail}. The backend may be unavailable.`
    }
    throw new ApiError(detail, response.status)
  }
  return (await response.json()) as T
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export const api = {
  health: () => request<{ status: string; dataset_items: number }>('/api/health'),
  meta: () => request<Meta>('/api/meta'),

  recommend: (profile: UserProfile, limit = 3, lockedItems?: Partial<Record<Category, OutfitItem>>) =>
    post<RecommendResponse>('/api/recommendations', { profile, limit, locked_items: lockedItems }),

  palette: (profile: UserProfile) => post<{ swatches: PaletteSwatch[]; unavailable: PaletteSwatch[] }>('/api/palette', { profile }),

  builderOptions: (profile: UserProfile, category: Category, selected: Partial<Record<Category, OutfitItem>>, offset = 0, limit = 8) =>
    post<BuilderStep>('/api/builder/options', { profile, category, selected, offset, limit }),

  product: (itemId: string) => request<{ item: OutfitItem }>(`/api/products/${encodeURIComponent(itemId)}`),

  sizeHint: (gender: string, height: number, weight: number) =>
    request<{ hint: SizeHint | null }>(`/api/size-hint?${new URLSearchParams({ gender, height: String(height), weight: String(weight) })}`),

  score: (outfit: Outfit, profile: UserProfile) =>
    post<ScoreResult>('/api/outfits/score', { outfit: { items: outfit.items }, profile }),

  replacements: (category: Category, outfit: Outfit, profile: UserProfile) =>
    post<{ candidates: OutfitItem[] }>('/api/outfits/replacements', { category, outfit: { items: outfit.items }, profile }),

  cheaper: (item: OutfitItem, profile?: UserProfile, outfit?: Outfit) =>
    post<{ item: OutfitItem | null }>('/api/outfits/cheaper', { item, profile, outfit: outfit ? { items: outfit.items } : undefined }),

  regenerate: (outfit: Outfit, profile: UserProfile, lockedCategories: Category[]) =>
    post<{ outfit: Outfit | null; notes?: string[] }>('/api/outfits/regenerate', {
      outfit: { items: outfit.items },
      profile,
      locked_categories: lockedCategories,
    }),

  shoppingAlternatives: (outfit: Outfit, budget: number, lockedCategories: Category[]) =>
    post<ShoppingResponse>('/api/shopping/alternatives', {
      outfit: { items: outfit.items },
      budget,
      locked_categories: lockedCategories,
    }),

  analyzeSkinTone: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<SkinToneAnalysis>('/api/skin-tone/analyze', { method: 'POST', body: form })
  },

  // Private photo + virtual try-on (session cookie; the photo never goes into browser storage).
  uploadPhoto: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<PhotoValidation>('/api/photos', { method: 'POST', body: form })
  },
  photoStatus: (photoId: string) => request<PhotoValidation>(`/api/photos/${photoId}`),
  deletePhoto: (photoId: string) => request<{ deleted: boolean }>(`/api/photos/${photoId}`, { method: 'DELETE' }),
  photoImageUrl: (photoId: string) => `${API_BASE}/api/photos/${photoId}/image`,
  tryOnProvider: () => request<TryOnProvider>('/api/tryon/provider'),
  startTryOn: (photoId: string, items: Outfit['items'], consent: boolean) => post<TryOnJob>('/api/tryon', { photo_id: photoId, items, consent }),
  tryOnStatus: (photoId: string, jobId: string) => request<TryOnJob>(`/api/tryon/${photoId}/${jobId}`),
  cancelTryOn: (photoId: string, jobId: string) => request<TryOnJob>(`/api/tryon/${photoId}/${jobId}`, { method: 'DELETE' }),
  tryOnImageUrl: (photoId: string, jobId: string) => `${API_BASE}/api/tryon/${photoId}/${jobId}/image`,

  avatarSvg: (params: AvatarBuilder, outfitItems?: Outfit['items']) =>
    post<{ svg: string }>('/api/avatar/svg', { params, outfit_items: outfitItems }),
}

export function resolveImageUrl(url: string | undefined): string | undefined {
  if (!url) return undefined
  return url.startsWith('/api/') ? `${API_BASE}${url}` : url
}
