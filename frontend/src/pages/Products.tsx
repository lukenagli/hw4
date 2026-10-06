import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CATEGORIES, COLOR_FAMILIES, SIZES, fetchProducts, type ProductSummary } from '../api'
import { useChatResults } from '../chat/ChatResults'
import { StitchAvatar } from '../components/Brand'
import ProductCard from '../components/ProductCard'

const SORTS = [
  { key: 'name', label: 'Name A–Z' },
  { key: 'price-asc', label: 'Price: low to high' },
  { key: 'price-desc', label: 'Price: high to low' },
] as const
type SortKey = (typeof SORTS)[number]['key']

// Filters live in the URL (?category=hoodie&color=Navy&size=XL&sort=price-asc),
// so they survive opening a product and coming back, and can be shared.
function useFilters() {
  const [params, setParams] = useSearchParams()
  const filters = {
    category: params.get('category'),
    color: params.get('color'),
    size: params.get('size'),
    sort: (params.get('sort') as SortKey | null) ?? 'name',
  }
  const set = (key: keyof typeof filters, value: string | null) => {
    const next = new URLSearchParams(params)
    if (value === null || (key === 'sort' && value === 'name')) next.delete(key)
    else next.set(key, value)
    setParams(next, { replace: true })
  }
  const clear = () => setParams({}, { replace: true })
  const active = Boolean(filters.category || filters.color || filters.size)
  return { filters, set, clear, active }
}

function applyFilters(products: ProductSummary[], f: ReturnType<typeof useFilters>['filters']) {
  const list = products.filter(
    (p) =>
      (!f.category || p.category === f.category) &&
      (!f.color || p.color_families.includes(f.color)) &&
      (!f.size || p.sizes_in_stock.includes(f.size)),
  )
  const byName = (a: ProductSummary, b: ProductSummary) => a.name.localeCompare(b.name)
  if (f.sort === 'price-asc') list.sort((a, b) => a.price - b.price || byName(a, b))
  else if (f.sort === 'price-desc') list.sort((a, b) => b.price - a.price || byName(a, b))
  else list.sort(byName)
  return list
}

export default function Products() {
  const [products, setProducts] = useState<ProductSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { filters, set, clear, active } = useFilters()
  const { results, clearResults } = useChatResults()

  useEffect(() => {
    fetchProducts().then(setProducts).catch((e: Error) => setError(e.message))
  }, [])

  // New chat results: bring the heading into view (instantly if the shopper prefers reduced motion).
  useEffect(() => {
    if (!results) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' })
  }, [results])

  const visible = useMemo(() => applyFilters(products ?? [], filters), [products, filters])
  const total = products?.length ?? 0

  // Choosing a filter means the shopper wants the catalogue, not the chat's picks.
  const choose = (key: 'category' | 'color' | 'size', value: string | null) => {
    clearResults()
    set(key, filters[key] === value ? null : value)
  }

  return (
    <>
      <section className={results ? 'page-hero felt from-chat' : 'page-hero felt'}>
        <div className="container page-hero-inner">
          {results && <StitchAvatar size={52} />}
          <div>
            <p className="eyebrow">{results ? 'Pulled from the shelves by Stitch' : 'The full rack'}</p>
            <h1>{results ? `Results for ${results.label}` : 'All products'}</h1>
          </div>
        </div>
      </section>

      <section className="container section">
        {results ? (
          <>
            <div className="results-bar" role="status">
              <span>
                {results.total_matches && results.total_matches > results.products.length
                  ? `Showing the first ${results.products.length} of ${results.total_matches} matches. Ask Stitch to narrow it down`
                  : `${results.products.length} ${results.products.length === 1 ? 'product' : 'products'} picked by the shop assistant`}
              </span>
              <button className="btn btn-outline-dark" onClick={clearResults}>
                Clear results · show all products
              </button>
            </div>
            {/* Keyed on the search so every new chat result set deals in again, card by card. */}
            <div
              key={`${results.label}|${results.products.length}`}
              className="product-grid"
              aria-label={`Results for ${results.label}`}
            >
              {results.products.map((p, i) => (
                <ProductCard key={p.product_id} product={p} index={i} animate />
              ))}
            </div>
          </>
        ) : (
          <>
            <div className="filter-panel" aria-label="Filter and sort products">
              <div className="filter-row">
                <span className="filter-label">Category</span>
                <div className="filters" role="group" aria-label="Category">
                  <button className={!filters.category ? 'chip active' : 'chip'} onClick={() => choose('category', null)}>
                    All
                  </button>
                  {CATEGORIES.map((c) => (
                    <button
                      key={c.key}
                      className={filters.category === c.key ? 'chip active' : 'chip'}
                      onClick={() => choose('category', c.key)}
                      aria-pressed={filters.category === c.key}
                    >
                      {c.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="filter-row">
                <span className="filter-label">Color</span>
                <div className="filters" role="group" aria-label="Color">
                  {COLOR_FAMILIES.map((c) => (
                    <button
                      key={c.name}
                      className={filters.color === c.name ? 'chip swatch-chip active' : 'chip swatch-chip'}
                      onClick={() => choose('color', c.name)}
                      aria-pressed={filters.color === c.name}
                    >
                      <span className="swatch" style={{ background: c.swatch }} aria-hidden />
                      {c.name}
                    </button>
                  ))}
                </div>
              </div>

              <div className="filter-row">
                <span className="filter-label">In stock in</span>
                <div className="filters" role="group" aria-label="Size in stock">
                  {SIZES.map((s) => (
                    <button
                      key={s}
                      className={filters.size === s ? 'chip size-chip active' : 'chip size-chip'}
                      onClick={() => choose('size', s)}
                      aria-pressed={filters.size === s}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              <div className="filter-footer">
                <p className="result-count" role="status" aria-live="polite">
                  {products ? (
                    <>
                      <strong>{visible.length}</strong> of {total} products
                    </>
                  ) : (
                    'Loading…'
                  )}
                </p>
                <div className="filter-actions">
                  {active && (
                    <button className="link-button" onClick={clear}>
                      Clear filters
                    </button>
                  )}
                  <label className="sort">
                    Sort by
                    <select value={filters.sort} onChange={(e) => set('sort', e.target.value)}>
                      {SORTS.map((s) => (
                        <option key={s.key} value={s.key}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </div>
            </div>

            {error && <p className="notice error">Couldn't load products: {error}</p>}
            {!products && !error && <p className="notice">Loading products…</p>}
            {products && visible.length === 0 && (
              <div className="notice empty-state">
                No products match all of these filters.{' '}
                <button className="link-button" onClick={clear}>
                  Clear filters
                </button>
              </div>
            )}
            <div className="product-grid">
              {visible.map((p) => (
                <ProductCard key={p.product_id} product={p} />
              ))}
            </div>
          </>
        )}
      </section>
    </>
  )
}
