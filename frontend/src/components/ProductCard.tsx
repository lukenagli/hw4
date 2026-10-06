import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { CATEGORIES, formatPrice, type ProductSummary } from '../api'

const categoryLabel = (key: string) => CATEGORIES.find((c) => c.key === key)?.label.replace(/s$/, '') ?? key

/** Price styled as a manila hang tag on a string. */
export function HangTag({ price, large = false }: { price: number; large?: boolean }) {
  return (
    <span className={large ? 'hang-tag hang-tag-lg' : 'hang-tag'}>
      <span className="tag-hole" aria-hidden />
      <span className="sr-only">Price: </span>
      {formatPrice(price)}
    </span>
  )
}

/**
 * Product card used on the Products page, Home and for chat search results.
 * `index` + `animate` stagger the entrance so chat results "deal" onto the page.
 */
export default function ProductCard({
  product,
  index = 0,
  animate = false,
}: {
  product: ProductSummary
  index?: number
  animate?: boolean
}) {
  return (
    <Link
      to={`/products/${product.product_id}`}
      className={animate ? 'card card-deal' : 'card'}
      style={{ '--i': index } as CSSProperties}
    >
      <div className="card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {!product.in_stock && <span className="stamp">Sold out</span>}
      </div>
      <HangTag price={product.price} />
      <div className="card-body">
        {product.category && <p className="card-kicker">{categoryLabel(product.category)}</p>}
        <h3>{product.name}</h3>
        <p className="card-desc">{product.description}</p>
      </div>
    </Link>
  )
}
