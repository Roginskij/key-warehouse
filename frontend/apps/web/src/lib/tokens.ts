import type { TokenPair } from '@kv/api'

const KEY = 'kv.session'

/** Tokens live in localStorage so the PWA survives restarts. */
export const tokenStore = {
  get(): TokenPair | null {
    try {
      const raw = localStorage.getItem(KEY)
      return raw ? (JSON.parse(raw) as TokenPair) : null
    } catch {
      return null
    }
  },
  set(tokens: TokenPair | null) {
    try {
      if (tokens) localStorage.setItem(KEY, JSON.stringify(tokens))
      else localStorage.removeItem(KEY)
    } catch {
      /* private mode: session lives only in memory for this tab */
    }
    listeners.forEach((fn) => fn(tokens))
  },
}

const listeners = new Set<(t: TokenPair | null) => void>()
export function onTokensChange(fn: (t: TokenPair | null) => void) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
