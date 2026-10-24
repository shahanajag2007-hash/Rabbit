import { resolveImageUrl } from '../../services/api'
import type { OutfitItem } from '../../types'
import { money } from '../../utils/format'

/**
 * Link to the product (or the chosen size's variant) on the brand's own site. The backend only
 * returns https links on a scraped brand's domain; items without one (the original CSV) show nothing.
 */
export function ProductLink({ item, label }: { item: OutfitItem; label?: string }) {
  const sized = item.selected_size ? item.variants?.find((v) => v.size === item.selected_size && v.available)?.url : null
  const url = sized ?? item.product_url
  if (!url) return null
  return (
    <a className="inline-link" href={url} target="_blank" rel="noreferrer noopener" style={{ fontSize: '0.78rem' }}>
      {label ?? (item.link_type === 'search' ? `Search on ${item.brand ?? 'store'}` : `View on ${item.brand ?? 'store'}`)} ↗
    </a>
  )
}

/** Product card from the Recommended Outfit page (unchanged markup/classes from the Streamlit version). */
export function ProductCard({ item }: { item: OutfitItem }) {
  const placeholder = `https://placehold.co/400x500/e6e4eb/1d1528?text=${encodeURIComponent(item.item_name)}`
  return (
    <div className="product-card" style={{ marginBottom: '1.1rem' }}>
      <div className="product-image-container">
        <img
          src={resolveImageUrl(item.image_url) ?? placeholder}
          alt={item.item_name}
          loading="lazy"
          onError={(e) => {
            if (e.currentTarget.src !== placeholder) e.currentTarget.src = placeholder
          }}
        />
        <div className="platform-badge">{String(item.category ?? '')}</div>
      </div>
      <div className="product-info">
        <div className="product-name">{item.item_name}</div>
        <div className="product-meta">
          {item.colour} · {item.style}
        </div>
        <div className="product-price-row">
          <div className="product-price">{money(item.price)}</div>
          <ProductLink item={item} />
        </div>
      </div>
    </div>
  )
}
