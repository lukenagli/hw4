import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import ChatPanel from '../chat/ChatPanel'
import { ShopPatch, openChat } from './Brand'

const NAV = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

const GUEST_NAV = [
  { to: '/login', label: 'Log in' },
  { to: '/signup', label: 'Create account' },
]

function AccountNav() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()

  if (loading) return null
  if (!user) {
    return GUEST_NAV.map((item) => (
      <NavLink key={item.to} to={item.to}>
        {item.label}
      </NavLink>
    ))
  }
  return (
    <>
      <span className="nav-user">Hi, {user.first_name}</span>
      <button
        className="nav-logout"
        onClick={async () => {
          await logout()
          navigate('/')
        }}
      >
        Log out
      </button>
    </>
  )
}

export default function Layout() {
  const { pathname } = useLocation()
  const { user } = useAuth()

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="announcement">
        <span>Officially licensed Yale apparel</span>
        <span className="dot" aria-hidden>
          ✦
        </span>
        <span>Pressed &amp; stitched at 57 Broadway, New Haven</span>
      </div>
      <header className="site-header">
        <div className="container header-inner">
          <Link to="/" className="brand" aria-label="Campus Customs home">
            <ShopPatch />
            <span className="brand-text">
              Campus Customs
              <small>Varsity print shop · New Haven</small>
            </span>
          </Link>
          <nav className="nav" aria-label="Main">
            {NAV.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end}>
                {item.label}
              </NavLink>
            ))}
            <AccountNav />
          </nav>
        </div>
        <div className="cuff-stripe" aria-hidden />
      </header>

      {/* Keyed on the path so each page fades in. */}
      <main id="main" key={pathname} className="page-enter">
        <Outlet />
      </main>

      <footer className="site-footer">
        <div className="container footer-inner">
          <div className="footer-brand">
            <ShopPatch size={60} />
            <div>
              <strong>Campus Customs</strong>
              <p>57 Broadway, New Haven, CT 06511</p>
              <button className="footer-ask" onClick={() => openChat()}>
                Questions? Ask Stitch at the counter →
              </button>
            </div>
          </div>
          <div>
            <strong>Shop</strong>
            <p>
              <Link to="/products">All products</Link>
              <br />
              <Link to="/products?category=hoodie">Hoodies</Link>
              <br />
              <Link to="/about">About us</Link>
            </p>
          </div>
          <div>
            <strong>Account</strong>
            <p>
              {user ? (
                <span>Signed in as {user.first_name}</span>
              ) : (
                <>
                  <Link to="/login">Log in</Link>
                  <br />
                  <Link to="/signup">Create account</Link>
                </>
              )}
            </p>
          </div>
        </div>
        <p className="container footer-fine">
          © {new Date().getFullYear()} Campus Customs. Class project demo, not a live store. Decorative art is original
          and not affiliated with Yale's official marks.
        </p>
      </footer>

      <ChatPanel />
    </>
  )
}
