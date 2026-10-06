import { createContext, useContext, useState, type ReactNode } from 'react'
import type { SearchResults } from './chatClient'

// Products the chat assistant put on the page. Lives above the routes, so it
// survives navigating to a product page and back.

interface ChatResultsState {
  results: SearchResults | null
  showResults: (results: SearchResults) => void
  clearResults: () => void
}

const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<SearchResults | null>(null)
  return (
    <ChatResultsContext.Provider
      value={{ results, showResults: setResults, clearResults: () => setResults(null) }}
    >
      {children}
    </ChatResultsContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
