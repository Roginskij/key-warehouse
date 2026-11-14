/**
 * Typed client for the KeyVerhaus API.
 *
 * Types come from the backend's OpenAPI schema: run `pnpm api:gen` after every
 * backend change. All paths, bodies and responses are then checked by TypeScript.
 */
import createClient, { type Middleware } from 'openapi-fetch'
import type { components, paths } from './schema'

export type { components, paths }
export type Schemas = components['schemas']

export interface TokenPair {
  access_token: string
  refresh_token: string
  expires_in: number
}

/** Error body every endpoint returns: translate by `code`. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public params: Record<string, unknown> = {},
    public fields: { field: string; code: string; message: string }[] = [],
  ) {
    super(message)
  }
}

export interface TokenStore {
  get(): TokenPair | null
  set(tokens: TokenPair | null): void
}

export interface ClientOptions {
  baseUrl?: string
  tokens: TokenStore
  /** Called when the session cannot be refreshed (go to login). */
  onSessionExpired?: () => void
  locale?: () => string
}

async function toApiError(res: Response): Promise<ApiError> {
  let body: any = null
  try {
    body = await res.clone().json()
  } catch {
    /* not JSON */
  }
  const e = body?.error ?? {}
  return new ApiError(res.status, e.code ?? 'http_error', e.message ?? res.statusText, e.params, e.fields)
}

export function createApi(opts: ClientOptions) {
  const baseUrl = opts.baseUrl ?? ''
  const client = createClient<paths>({ baseUrl })

  // One refresh at a time: parallel 401s wait for the same promise.
  let refreshing: Promise<boolean> | null = null
  async function refresh(): Promise<boolean> {
    const current = opts.tokens.get()
    if (!current) return false
    if (!refreshing) {
      refreshing = (async () => {
        try {
          const res = await fetch(`${baseUrl}/api/v1/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: current.refresh_token }),
          })
          if (!res.ok) {
            opts.tokens.set(null)
            return false
          }
          opts.tokens.set((await res.json()) as TokenPair)
          return true
        } catch {
          return false
        } finally {
          setTimeout(() => (refreshing = null), 0)
        }
      })()
    }
    return refreshing
  }

  // Body of a sent request can't be read again, so keep a copy for the retry.
  const copies = new WeakMap<Request, Request>()

  const auth: Middleware = {
    async onRequest({ request }) {
      const t = opts.tokens.get()
      if (t && !request.headers.has('Authorization')) {
        request.headers.set('Authorization', `Bearer ${t.access_token}`)
      }
      if (opts.locale) request.headers.set('Accept-Language', opts.locale())
      copies.set(request, request.clone())
      return request
    },
    async onResponse({ request, response }) {
      if (response.ok) return response
      const err = await toApiError(response)
      const retriable = response.status === 401 && err.code === 'auth.invalid_token'
      if (retriable && !request.headers.has('X-Retried') && (await refresh())) {
        const t = opts.tokens.get()!
        const retry = copies.get(request) ?? new Request(request)
        retry.headers.set('Authorization', `Bearer ${t.access_token}`)
        retry.headers.set('X-Retried', '1')
        return fetch(retry)
      }
      if (retriable) {
        opts.tokens.set(null)
        opts.onSessionExpired?.()
      }
      return response
    },
  }
  client.use(auth)

  /** Unwraps `{data, error, response}` → data, or throws ApiError. */
  async function call<T>(p: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
    const { data, response } = await p
    if (!response.ok) throw await toApiError(response)
    return data as T
  }

  /** For multipart uploads and file downloads, which openapi-fetch does not type well. */
  async function raw(path: string, init: RequestInit = {}, retried = false): Promise<Response> {
    const t = opts.tokens.get()
    const headers = new Headers(init.headers)
    if (t) headers.set('Authorization', `Bearer ${t.access_token}`)
    const res = await fetch(`${baseUrl}${path}`, { ...init, headers })
    if (res.status === 401 && !retried && (await refresh())) return raw(path, init, true)
    if (!res.ok) throw await toApiError(res)
    return res
  }

  return { client, call, raw, refresh }
}

export type Api = ReturnType<typeof createApi>
