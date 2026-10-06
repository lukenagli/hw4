import type { ProductSummary } from '../api'

// Chat transport. The panel only talks to this module.
// Backend route: POST /api/chat (backend/main.py). Override with
// VITE_CHAT_ENDPOINT in frontend/.env if the route ever moves.

export type ChatRole = 'user' | 'assistant'

export interface ChatMessage {
  role: ChatRole
  content: string
}

export type PageType = 'home' | 'products' | 'product' | 'about' | 'login' | 'signup' | 'other'

// What the shopper is looking at, sent with every message so "this" works.
export interface PageContext {
  path: string
  page_type: PageType
  product_id: string | null
  results_label: string | null
}

export function pageContextFor(pathname: string, resultsLabel: string | null): PageContext {
  const product = pathname.match(/^\/products\/([^/]+)\/?$/)
  const fixed: Record<string, PageType> = {
    '/': 'home',
    '/products': 'products',
    '/about': 'about',
    '/login': 'login',
    '/signup': 'signup',
  }
  const page_type: PageType = product ? 'product' : (fixed[pathname] ?? 'other')
  return {
    path: pathname,
    page_type,
    product_id: product ? decodeURIComponent(product[1]) : null,
    results_label: page_type === 'products' ? resultsLabel : null,
  }
}

// Same limit as the backend (models.MAX_MESSAGE_CHARS); longer messages are rejected.
export const MAX_MESSAGE_CHARS = 1000

export interface ChatRequest {
  message: string
  // Only used for guests; for logged-in customers the backend reads saved history.
  history: ChatMessage[]
  page: PageContext
}

// Products to show on the page. Card fields come from the database on the
// backend (same shape as GET /api/products), never from the model.
export interface SearchResults {
  label: string
  // search: shown on the Products page; alternatives: shown as cards in the chat
  kind: 'search' | 'alternatives'
  products: ProductSummary[]
  // Matches before the backend's 30-product cap (0 = all of them are shown).
  total_matches?: number
}

// What the backend's fact check verified in this reply (backend/factcheck.py).
export interface FactCheckSummary {
  status: 'verified' | 'corrected' | 'no_figures' | 'unverified'
  prices: string[]
  stock: string[]
  retries: number
}

export interface ChatReply {
  message: string
  search: SearchResults | null
  fact_check: FactCheckSummary | null
}

const CHAT_ENDPOINT: string = import.meta.env.VITE_CHAT_ENDPOINT || '/api/chat'

export class ChatError extends Error {}

export async function sendChatMessage(request: ChatRequest): Promise<ChatReply> {
  let res: Response
  try {
    res = await fetch(CHAT_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
  } catch {
    throw new ChatError("I can't reach the shop right now. Please check your connection and try again in a moment.")
  }

  // The Vite proxy answers 502/503/504 when the backend isn't running.
  if (res.status >= 502 && res.status <= 504 && !res.headers.get('content-type')?.includes('json')) {
    throw new ChatError("The shop assistant is offline right now. Please try again in a moment.")
  }
  if (!res.ok) {
    throw new ChatError('Sorry, something went wrong on our end. Please try asking again.')
  }
  return res.json() as Promise<ChatReply>
}

// Saved conversation for the logged-in customer (the backend picks the user
// from the session cookie). Guests get 401, so they just start fresh.
export interface HistoryMessage extends ChatMessage {
  id: number
  search: SearchResults | null
  created_at: string
}

export async function fetchChatHistory(): Promise<HistoryMessage[]> {
  const res = await fetch('/api/chat/history')
  if (res.status === 401) return []
  if (!res.ok) throw new ChatError("Couldn't load your earlier chat.")
  const data = (await res.json()) as { messages: HistoryMessage[] }
  return data.messages
}
