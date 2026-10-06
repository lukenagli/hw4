import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { formatPrice } from '../api'
import { useAuth } from '../auth/AuthContext'
import { StitchAvatar } from '../components/Brand'
import {
  ChatError,
  fetchChatHistory,
  MAX_MESSAGE_CHARS,
  pageContextFor,
  sendChatMessage,
  type ChatMessage,
  type FactCheckSummary,
  type SearchResults,
} from './chatClient'
import { useChatResults } from './ChatResults'

// isGreeting / isError mark UI-only bubbles that are never sent as history.
// search holds the products a reply put on the page, so they can be reopened.
// factCheck is what the backend verified in this reply (shown as a badge).
type PanelMessage = ChatMessage & {
  isGreeting?: boolean
  isError?: boolean
  search?: SearchResults
  factCheck?: FactCheckSummary
}

const RESULTS_PATH = '/products'
const CARDS_IN_BUBBLE = 3

// Starter questions: show shoppers what the assistant can do.
const GENERAL_SUGGESTIONS = [
  'What hoodies do you have?',
  "What's in stock in XL?",
  'Anything under $40?',
  'Show me Yale Dad gear',
]
const PRODUCT_SUGGESTIONS = [
  'Is this in stock in my size?',
  'What sizes are left?',
  'Do you have this in another color?',
  'Show me similar items',
]

function FactCheckBadge({ check }: { check: FactCheckSummary }) {
  if (check.status === 'no_figures') return null
  const figures = [...check.prices, ...check.stock].join(' · ')
  const text =
    check.status === 'verified'
      ? 'Checked against store data'
      : check.status === 'corrected'
        ? `Corrected ${check.retries === 1 ? 'once' : `${check.retries} times`} before sending, then checked`
        : "Couldn't verify the numbers, so none were sent"
  return (
    <div className={`fact-badge ${check.status}`} title={figures ? `Verified: ${figures}` : undefined}>
      <span aria-hidden>{check.status === 'unverified' ? '!' : '✓'}</span> {text}
      {figures && <span className="fact-figures">{figures}</span>}
    </div>
  )
}

function greeting(firstName: string | null, returning: boolean): PanelMessage {
  const content = !firstName
    ? "Hi, I'm Stitch, at the Campus Customs counter. Ask me about sizes, colors or what's on the shelves."
    : returning
      ? `Welcome back, ${firstName}! Your earlier chat is below. What can I find for you today?`
      : `Hi ${firstName}! I'm Stitch, at the Campus Customs counter. Ask me about sizes, colors or what's on the shelves.`
  return { role: 'assistant', content, isGreeting: true }
}

export default function ChatPanel() {
  const { user, loading: authLoading } = useAuth()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<PanelMessage[]>([greeting(null, false)])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const { results, showResults, clearResults } = useChatResults()
  const navigate = useNavigate()
  // Refs, so a reply that arrives later sees the current page and account.
  const { pathname } = useLocation()
  const pathRef = useRef(pathname)
  const accountRef = useRef<number | null>(null)
  useEffect(() => {
    pathRef.current = pathname
  }, [pathname])

  const userId = user?.id ?? null
  const firstName = user?.first_name ?? null

  // "Ask Stitch" buttons elsewhere on the site dispatch cc:open-chat.
  const [queued, setQueued] = useState<string | null>(null)
  useEffect(() => {
    const onOpen = (e: Event) => {
      setOpen(true)
      const q = (e as CustomEvent<{ question?: string }>).detail?.question
      if (q) setQueued(q)
    }
    window.addEventListener('cc:open-chat', onOpen)
    return () => window.removeEventListener('cc:open-chat', onOpen)
  }, [])

  // Whenever the account changes (page load, log in, log out, switch user),
  // start a fresh panel for that account. A guest's chat is dropped on login,
  // so it never mixes into the account; a customer's saved chat is loaded.
  useEffect(() => {
    if (authLoading) return
    accountRef.current = userId
    clearResults()
    setPending(false)
    if (userId === null) {
      setMessages([greeting(null, false)])
      return
    }
    setMessages([greeting(firstName, false)])
    setHistoryLoading(true)
    fetchChatHistory()
      .then((saved) => {
        if (accountRef.current !== userId) return // account changed while loading
        const restored: PanelMessage[] = saved.map((m) => ({
          role: m.role,
          content: m.content,
          search: m.search ?? undefined,
        }))
        setMessages([greeting(firstName, restored.length > 0), ...restored])
      })
      .catch(() => {
        if (accountRef.current === userId) {
          setMessages((m) => [...m, { role: 'assistant', content: "I couldn't load your earlier chat.", isError: true }])
        }
      })
      .finally(() => setHistoryLoading(false))
    // clearResults is stable enough for this purpose; re-run only on account change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, userId])

  // Put search results on the page, taking the shopper to Products if needed.
  // The panel lives in the shared layout, so it stays open with its history.
  function openResults(search: SearchResults) {
    showResults(search)
    if (pathRef.current !== RESULTS_PATH) navigate(RESULTS_PATH)
  }

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
  }, [messages, pending, open])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  async function send(e?: FormEvent, preset?: string) {
    e?.preventDefault()
    const text = (preset ?? draft).trim()
    if (!text || pending || historyLoading) return

    // Guests: earlier turns go with the message so the bot remembers them.
    // Logged in: the backend reads saved history itself, so nothing is sent.
    const history =
      userId === null
        ? messages.filter((m) => !m.isGreeting && !m.isError).map(({ role, content }) => ({ role, content }))
        : []
    const page = pageContextFor(pathRef.current, results?.label ?? null)
    const account = userId
    setMessages([...messages, { role: 'user', content: text }])
    setDraft('')
    setPending(true)
    try {
      const reply = await sendChatMessage({ message: text, history, page })
      if (accountRef.current !== account) return // logged in/out while waiting
      const search = reply.search ?? undefined
      const factCheck = reply.fact_check ?? undefined
      setMessages((m) => [...m, { role: 'assistant', content: reply.message, search, factCheck }])
      // Search results go on the Products page. Alternatives stay as cards in
      // the chat, so the shopper isn't pulled away from the product they're on.
      if (search && search.kind !== 'alternatives') openResults(search)
    } catch (err) {
      if (accountRef.current !== account) return
      const content = err instanceof ChatError ? err.message : 'Sorry, something went wrong. Please try again.'
      setMessages((m) => [...m, { role: 'assistant', content, isError: true }])
    } finally {
      setPending(false)
    }
  }

  // Send a question queued by an "Ask Stitch" button once the panel is ready.
  useEffect(() => {
    if (open && queued && !pending && !historyLoading && !authLoading) {
      const q = queued
      setQueued(null)
      void send(undefined, q)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, queued, pending, historyLoading, authLoading])

  const onProductPage = /^\/products\/[^/]+\/?$/.test(pathname)
  const askedSomething = messages.some((m) => m.role === 'user')
  const suggestions = onProductPage ? PRODUCT_SUGGESTIONS : askedSomething ? [] : GENERAL_SUGGESTIONS

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" role="dialog" aria-label="Shop assistant chat">
          <div className="awning" aria-hidden />
          <header className="chat-header">
            <StitchAvatar size={42} />
            <div className="chat-title">
              <strong>Stitch</strong>
              <span>At the Campus Customs counter</span>
              <span className="chat-status">
                {firstName ? `Chatting as ${firstName} · saved to your account` : 'Guest chat · not saved'}
              </span>
            </div>
            <button className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">
              ×
            </button>
          </header>

          <div className="chat-messages" ref={listRef} aria-live="polite">
            {messages.map((m, i) => (
              <div key={i} className={`msg-row ${m.role}`}>
                {m.role === 'assistant' && <StitchAvatar size={26} />}
              <div className={`chat-bubble ${m.role}${m.isError ? ' error' : ''}`}>
                {m.content}
                {m.search?.kind === 'alternatives' && <div className="chat-cards-title">In stock instead:</div>}
                {m.search && (
                  <div className="chat-cards">
                    {m.search.products.slice(0, CARDS_IN_BUBBLE).map((p, j) => (
                      <Link
                        key={p.product_id}
                        to={`/products/${p.product_id}`}
                        className="chat-card"
                        style={{ '--i': j } as CSSProperties}
                      >
                        <img src={p.image_url} alt="" loading="lazy" />
                        <span className="chat-card-name">{p.name}</span>
                        <span className="chat-card-price">{formatPrice(p.price)}</span>
                      </Link>
                    ))}
                    <button className="chat-results-link" onClick={() => openResults(m.search!)}>
                      {m.search.products.length > CARDS_IN_BUBBLE
                        ? `View all ${m.search.products.length} on the page →`
                        : 'Show on the page →'}
                    </button>
                  </div>
                )}
                {m.factCheck && <FactCheckBadge check={m.factCheck} />}
              </div>
              </div>
            ))}
            {historyLoading && (
              <div className="msg-row assistant">
                <StitchAvatar size={26} />
                <div className="chat-bubble assistant typing">Finding your earlier chat…</div>
              </div>
            )}
            {pending && (
              <div className="msg-row assistant" aria-label="Stitch is typing">
                <StitchAvatar size={26} />
                <div className="chat-bubble assistant typing">
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                  <span className="typing-label">Stitch is checking the shelves</span>
                </div>
              </div>
            )}
          </div>

          {suggestions.length > 0 && !pending && !historyLoading && (
            <div className="chat-suggestions" aria-label="Suggested questions">
              {suggestions.map((q) => (
                <button key={q} className="suggestion" onClick={() => send(undefined, q)}>
                  {q}
                </button>
              ))}
            </div>
          )}

          <form className="chat-input" onSubmit={(e) => send(e)}>
            <textarea
              ref={inputRef}
              rows={1}
              value={draft}
              maxLength={MAX_MESSAGE_CHARS}
              placeholder="Ask Stitch anything about our gear…"
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) send(e)
              }}
              aria-label="Message"
            />
            <button type="submit" disabled={!draft.trim() || pending || historyLoading}>
              {pending ? '…' : 'Send'}
            </button>
          </form>
        </section>
      )}

      <button
        className={open ? 'chat-toggle is-open' : 'chat-toggle'}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={open ? 'Close chat' : 'Open chat with Stitch'}
      >
        {open ? (
          <span aria-hidden>×</span>
        ) : (
          <>
            <StitchAvatar size={30} />
            <span>Ask Stitch</span>
          </>
        )}
      </button>
    </div>
  )
}
