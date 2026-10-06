// Typed client for the FastAPI backend (backend/main.py).

export interface ProductSummary {
  product_id: string
  name: string
  garment_type: string
  description: string
  price: number
  image_url: string
  in_stock: boolean
  category: string
  color_families: string[]
  sizes_in_stock: string[]
}

export interface SizeStock {
  size: string
  quantity: number
  in_stock: boolean
}

export interface ProductDetail extends ProductSummary {
  colors: string[]
  search_tags: string[]
  inventory: SizeStock[]
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const fetchProducts = () => getJson<ProductSummary[]>('/api/products')

export const fetchProduct = (id: string) =>
  getJson<ProductDetail>(`/api/products/${encodeURIComponent(id)}`)

export const formatPrice = (price: number) =>
  price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

// The backend groups the catalogue's 22 inconsistent garment_type labels into
// clean categories (backend/catalogue.py) and sends each product's category,
// color families and in-stock sizes. These are the labels shoppers see.
export const CATEGORIES = [
  { key: 'hoodie', label: 'Hoodies' },
  { key: 'crewneck', label: 'Crewnecks' },
  { key: 't-shirt', label: 'T-Shirts' },
  { key: 'quarter-zip', label: 'Quarter-Zips' },
  { key: 'jacket', label: 'Jackets & Fleece' },
  { key: 'long-sleeve shirt', label: 'Long Sleeves' },
] as const

// Swatch colors for the color families (backend/catalogue.py COLOR_RULES).
export const COLOR_FAMILIES: { name: string; swatch: string }[] = [
  { name: 'Navy', swatch: '#1f2f5c' },
  { name: 'Gray', swatch: '#9aa0a6' },
  { name: 'White & Cream', swatch: '#f7f3e8' },
  { name: 'Blue', swatch: '#3b73c4' },
  { name: 'Black', swatch: '#111111' },
  { name: 'Red & Coral', swatch: '#c8473f' },
  { name: 'Gold & Yellow', swatch: '#e2b33c' },
  { name: 'Green', swatch: '#3f7d4f' },
  { name: 'Multicolor', swatch: 'conic-gradient(#c8473f, #e2b33c, #3f7d4f, #3b73c4, #c8473f)' },
]

export const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL'] as const
