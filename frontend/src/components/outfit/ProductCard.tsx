import { resolveImageUrl } from '../../services/api'
import type { OutfitItem } from '../../types'
import { money } from '../../utils/format'

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
        </div>
      </div>
    </div>
  )
}
