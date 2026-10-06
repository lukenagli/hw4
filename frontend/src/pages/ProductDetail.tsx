import { useEffect, useState, type MouseEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CATEGORIES, fetchProduct, type ProductDetail as Product, type SizeStock } from '../api'
import { openChat } from '../components/Brand'
import { HangTag } from '../components/ProductCard'
import { useChatResults } from '../chat/ChatResults'

const LOW_STOCK = 5

type SizeState = 'in' | 'low' | 'out'
const sizeState = (s: SizeStock): SizeState => (!s.in_stock ? 'out' : s.quantity <= LOW_STOCK ? 'low' : 'in')
const SIZE_TEXT: Record<SizeState, (s: SizeStock) => string> = {
  in: () => 'In stock',
  low: (s) => `Only ${s.quantity} left`,
  out: () => 'Sold out',
}

/** Large product photo that zooms 2.2x where you point (hover), or on tap. */
function ZoomImage({ src, alt }: { src: string; alt: string }) {
  const [zoomed, setZoomed] = useState(false)
  const [origin, setOrigin] = useState('50% 50%')

  const track = (e: MouseEvent<HTMLButtonElement>) => {
    // Keyboard "clicks" have no pointer position: zoom into the center instead.
    if (e.clientX === 0 && e.clientY === 0) return setOrigin('50% 50%')
    const r = e.currentTarget.getBoundingClientRect()
    const pct = (v: number) => Math.min(100, Math.max(0, v * 100))
    setOrigin(`${pct((e.clientX - r.left) / r.width)}% ${pct((e.clientY - r.top) / r.height)}%`)
  }

  return (
    <button
      type="button"
      className={zoomed ? 'zoom-frame zoomed' : 'zoom-frame'}
      onMouseMove={track}
      onMouseEnter={() => setZoomed(true)}
      onMouseLeave={() => setZoomed(false)}
      onClick={(e) => {
        track(e)
        setZoomed((z) => !z)
      }}
      aria-label={zoomed ? `Zoom out of ${alt}` : `Zoom into ${alt}`}
      aria-pressed={zoomed}
    >
      <img src={src} alt={alt} style={{ transformOrigin: origin }} />
      <span className="zoom-hint" aria-hidden>
        {zoomed ? 'Move to look around' : 'Hover or tap to zoom'}
      </span>
    </button>
  )
}

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { results } = useChatResults()
  const backLabel = results ? `← Back to results for ${results.label}` : '← All products'

  useEffect(() => {
    setProduct(null)
    setError(null)
    fetchProduct(productId).then(setProduct).catch((e: Error) => setError(e.message))
  }, [productId])

  if (error) {
    return (
      <section className="container section">
        <p className="notice error">Couldn't load this product ({error}).</p>
        <Link to="/products">← Back to all products</Link>
      </section>
    )
  }
  if (!product) return <p className="container section notice">Loading…</p>

  const available = product.inventory.filter((s) => s.in_stock)
  const low = product.inventory.filter((s) => sizeState(s) === 'low')
  const category = CATEGORIES.find((c) => c.key === product.category)?.label ?? product.garment_type

  return (
    <section className="container section">
      <Link to="/products" className="back-link">
        {backLabel}
      </Link>

      <div className="detail">
        <div className="detail-media">
          <ZoomImage src={product.image_url} alt={product.name} />
        </div>

        <div className="detail-info">
          <p className="eyebrow">{category}</p>
          <h1>{product.name}</h1>

          <div className="buy-box">
            <HangTag price={product.price} large />
            <p className={available.length ? 'stock-line ok' : 'stock-line out'} role="status">
              {available.length === 0
                ? 'Sold out in every size'
                : available.length === product.inventory.length
                  ? 'In stock in every size'
                  : `In stock in ${available.length} of ${product.inventory.length} sizes`}
              {low.length > 0 && (
                <span className="stock-low"> · Hurry: {low.map((s) => `${s.size} (${s.quantity})`).join(', ')} almost gone</span>
              )}
            </p>

            <h2 className="detail-label" id="sizes-label">
              Sizes
            </h2>
            <ul className="size-chips" aria-labelledby="sizes-label">
              {product.inventory.map((s) => {
                const state = sizeState(s)
                return (
                  <li key={s.size} className={`size-chip-lg ${state}`}>
                    <span className="size">{s.size}</span>
                    <span className="stock">{SIZE_TEXT[state](s)}</span>
                  </li>
                )
              })}
            </ul>
            <ul className="size-legend" aria-label="Size legend">
              <li className="in">In stock</li>
              <li className="low">5 or fewer left</li>
              <li className="out">Sold out</li>
            </ul>

            <button className="btn btn-primary btn-block" onClick={() => openChat('Is this in stock in my size?')}>
              Ask Stitch about this item
            </button>
          </div>

          <h2 className="detail-label">About this piece</h2>
          <p className="detail-desc">{product.description}</p>

          <h2 className="detail-label">Colors on this item</h2>
          {product.colors.length > 0 ? (
            <ul className="color-list">
              {product.colors.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          ) : (
            <p className="muted">Color details aren't listed for this item.</p>
          )}
        </div>
      </div>
    </section>
  )
}
