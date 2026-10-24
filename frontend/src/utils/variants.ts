import type { OutfitItem } from '../types'

/** The item with a size chosen: price, MRP and link follow that size's real variant. */
export function withSize(item: OutfitItem, size: string | null): OutfitItem {
  if (!size) return { ...item, selected_size: null }
  const variant = item.variants?.find((v) => v.size === size && v.available)
  if (!variant) return item
  return { ...item, selected_size: size, price: variant.price, mrp: variant.mrp ?? null, product_url: variant.url ?? item.product_url }
}

/** Carry a size over to another colour of the same product when that colour has it in stock. */
export function carrySize(next: OutfitItem, size: string | null | undefined): { item: OutfitItem; lost: boolean } {
  if (!size) return { item: next, lost: false }
  if (next.available_sizes?.includes(size)) return { item: withSize(next, size), lost: false }
  return { item: { ...next, selected_size: null }, lost: true }
}

/** "Prices checked 24 Oct, 5:10 pm" for live items; null for items without a check time. */
export function priceCheckedLabel(items: OutfitItem[]): string | null {
  const stamps = items.map((i) => i.price_checked_at).filter((t): t is string => Boolean(t))
  if (!stamps.length) return null
  const oldest = new Date(stamps.sort()[0])
  if (Number.isNaN(oldest.getTime())) return null
  return oldest.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
}
