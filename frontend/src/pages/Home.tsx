import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CATEGORIES, fetchProducts, type ProductSummary } from '../api'
import { openChat, Pennant, StitchAvatar } from '../components/Brand'
import ProductCard, { HangTag } from '../components/ProductCard'

const HERO_ID = 'basic-hoodie-big-yale'
const FEATURED_IDS = [
  'champion-reverse-weave-crewneck',
  'benjamin-franklin-1-4-zip',
  'yale-bowl-t-shirt',
  'district-vit-hoodie-vintage-sailor-bulldog',
]

const STEPS = [
  { n: '1', title: 'Pick your corner of Yale', body: 'College crests, grad schools, varsity teams and family designs.' },
  { n: '2', title: 'Check live sizes', body: 'Every size shows what is on the shelf right now, XS to XXL.' },
  { n: '3', title: 'Ask at the counter', body: 'Stitch, our shop assistant, finds styles, sizes and swaps in seconds.' },
]

export default function Home() {
  const [products, setProducts] = useState<ProductSummary[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchProducts().then(setProducts).catch((e: Error) => setError(e.message))
  }, [])

  const byId = (id: string) => products.find((p) => p.product_id === id)
  const hero = byId(HERO_ID)
  const featured = FEATURED_IDS.map(byId).filter((p): p is ProductSummary => p !== undefined)
  const coverFor = (key: string) => products.find((p) => p.category === key)

  return (
    <>
      <section className="hero felt">
        <div className="container hero-inner">
          <div className="hero-copy">
            <Pennant label="The print shop on Broadway" />
            <h1>
              Varsity gear,
              <br />
              pressed with pride.
            </h1>
            <p className="hero-lede">
              Hoodies, crewnecks, tees and quarter-zips for every college, team and proud Yale family, stocked
              and ready on our shelves in New Haven.
            </p>
            <div className="hero-actions">
              <Link to="/products" className="btn btn-primary btn-lg">
                Shop the collection
              </Link>
              <button className="hero-ask" onClick={() => openChat()}>
                or ask Stitch at the counter
              </button>
            </div>
          </div>

          {hero && (
            <Link to={`/products/${hero.product_id}`} className="hero-display" aria-label={`${hero.name}, featured`}>
              <span className="hanger" aria-hidden />
              <span className="hero-patch">
                <img src={hero.image_url} alt={hero.name} />
              </span>
              <span className="hero-tag">
                <HangTag price={hero.price} large />
                <span className="hero-tag-name">{hero.name}</span>
              </span>
            </Link>
          )}
        </div>
      </section>

      <section className="steps" aria-label="How the shop works">
        <div className="container steps-inner">
          {STEPS.map((s) => (
            <div key={s.n} className="step">
              <span className="step-num" aria-hidden>
                {s.n}
              </span>
              <div>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="container section">
        <div className="section-head">
          <h2 className="section-title">Shop by category</h2>
        </div>
        <div className="category-grid">
          {CATEGORIES.map((c) => {
            const cover = coverFor(c.key)
            return (
              <Link key={c.key} to={`/products?category=${encodeURIComponent(c.key)}`} className="category-patch">
                <span className="category-photo">{cover && <img src={cover.image_url} alt="" loading="lazy" />}</span>
                <span className="category-name">{c.label}</span>
              </Link>
            )
          })}
        </div>
      </section>

      <section className="container section">
        <div className="section-head">
          <h2 className="section-title">Fresh off the press</h2>
          <Link to="/products" className="text-link">
            View all 102 →
          </Link>
        </div>
        {error && <p className="notice error">Couldn't load products: {error}</p>}
        <div className="product-grid">
          {featured.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </section>

      <section className="counter-band">
        <div className="awning" aria-hidden />
        <div className="container counter-inner">
          <StitchAvatar size={64} />
          <div>
            <h2>Can't find it on the rack?</h2>
            <p>
              Tell Stitch what you're after ("navy crewneck in XL under $60") and the matching gear lands right on
              the page.
            </p>
          </div>
          <button className="btn btn-primary" onClick={() => openChat()}>
            Ask Stitch
          </button>
        </div>
      </section>
    </>
  )
}
