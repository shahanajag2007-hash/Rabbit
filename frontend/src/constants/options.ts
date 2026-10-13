// UI option lists carried over verbatim from the Streamlit pages.

export const GENDERS = ['Female', 'Male', 'Non-binary']

export const SKIN_TONES: [name: string, hex: string, description: string][] = [
  ['Light', '#f6d7c5', 'Cool/Fair undertones. Pairs best with Navy, Burgundy, Emerald, White.'],
  ['Medium', '#c9906d', 'Warm Almond undertones. Pairs best with Teal, Olive, Mustard, Maroon, Cream.'],
  ['Tan', '#ad704f', 'Golden Olive undertones. Pairs best with Rust, Sage, Camel, Chocolate, Cream.'],
  ['Deep', '#794936', 'Rich Cocoa undertones. Pairs best with Pure White, Cobalt, Emerald, Coral, Lavender.'],
]

export const FAVOURITE_COLOURS: [name: string, hex: string][] = [
  ['Black', '#1a1a1a'],
  ['White', '#f8f9fa'],
  ['Navy', '#1B2A47'],
  ['Blue', '#2563eb'],
  ['Green', '#166534'],
  ['Pink', '#ec4899'],
  ['Red', '#dc2626'],
  ['Brown', '#78350f'],
  ['Beige', '#d97706'],
  ['Lavender', '#a855f7'],
  ['Olive', '#65a30d'],
  ['Mustard', '#eab308'],
  ['Burgundy', '#831843'],
]

export const STYLES: [name: string, icon: string, description: string][] = [
  ['Minimal', '✨', 'Clean lines, solid neutrals, effortless cuts.'],
  ['Casual', '👟', 'Relaxed everyday denim, comfortable tees, sneakers.'],
  ['Formal', '👔', 'Crisp blazers, tailored trousers, polished footwear.'],
  ['Smart Casual', '🧥', 'Elevated everyday look blending structure and comfort.'],
  ['Trendy', '🔥', 'Fashion-forward statement cuts and current silhouettes.'],
  ['Traditional', '🌸', 'Heritage ethnic wear, kurtas, sarees and classic drapes.'],
  ['Elegant', '💎', 'Refined evening dresses, graceful drapes and subtle luxury.'],
  ['Streetwear', '🧢', 'Oversized silhouettes, graphic details and urban aesthetics.'],
]

export const OCCASIONS: [name: string, icon: string, description: string][] = [
  ['College', '🎓', 'Expressive, easy dressing for campus life and lectures.'],
  ['Office', '💼', 'Professional, workday-ready tailoring and polished layers.'],
  ['Interview', '📄', 'Formal, confident dressing designed to make a strong impression.'],
  ['Party', '🎉', 'Statement night-out styling, festive fits and evening flair.'],
  ['Casual Outing', '☕', 'Weekend brunches, relaxed meetups and coffee runs.'],
  ['Traditional Event', '🪔', 'Festivals, weddings, family celebrations and ceremonies.'],
  ['Special Event', '✨', 'Gala dinners, award events and high-fashion moments.'],
]

// Former "03 Preferences" page.
export const FITS = ['Loose / Oversized', 'Regular Fit', 'Slim / Fitted']
export const FABRICS = ['Breathable Linen', 'Crisp Cotton Blend', 'Classic Denim', 'Silk & Satin', 'Soft Supima Cotton', 'Handloom Khadi']
export const AVOID_OPTIONS = ['Neon / Flashy', 'Overly Bright', 'Dense Layering', 'Clashing Tones', 'Pastels']
export const BRANDS = ['ZARA', 'UNIQLO', 'H&M', 'FabIndia', 'Mango', "Levi's", 'Adidas', 'Aldo', 'Myntra']

// Avatar studio.
export const AVATAR_TABS = ['Preset Model', 'Hair & Style', 'Body Shape', 'Skin Tone', 'Accessories']
export const HAIR_STYLES = ['Long Straight', 'Wavy', 'Curly', 'Bob', 'Ponytail', 'Bun']
export const HAIR_COLOURS = ['Black', 'Dark Brown', 'Brown', 'Light Brown', 'Blonde', 'Auburn', 'Red']
export const BODY_SHAPES = ['Balanced', 'Slim', 'Athletic', 'Curvy']
export const AVATAR_SKIN_TONES = ['Porcelain', 'Light Beige', 'Warm Almond', 'Golden Tan', 'Deep Cocoa', 'Espresso']
export const AVATAR_ACCESSORIES = ['Minimal Watch', 'Glasses', 'Sunglasses', 'Earrings', 'Canvas Tote']

// Former "11 Multi Identity" page.
export const IDENTITIES: [name: string, style: string, vibe: string, detail: string, emoji: string][] = [
  ['College Me', 'Casual', 'Comfortable', 'Sneakers', '👩'],
  ['Office Me', 'Professional', 'Minimal', 'Formal', '💼'],
  ['Party Me', 'Trendy', 'Stylish', 'Accessorized', '✨'],
  ['Traditional Me', 'Elegant', 'Ethnic', 'Traditional', '🌸'],
]

export const CATEGORY_ICONS: Record<string, string> = { Top: '👕', Bottom: '👖', Shoes: '👟', Accessory: '⌚' }
