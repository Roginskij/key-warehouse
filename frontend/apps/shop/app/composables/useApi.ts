import type { Schemas } from '@kv/api'

export type PublicKey = Schemas['PublicKey']
export type PublicKeyBrief = Schemas['PublicKeyBrief']
export type PublicWorkshop = Schemas['PublicWorkshop']

/**
 * Backend calls. On the server: straight to the API (apiBase).
 * In the browser: same host, /api/** is proxied (server/routes/api).
 */
export function apiFetch<T>(path: string, opts: Parameters<typeof $fetch>[1] = {}): Promise<T> {
  const base = import.meta.server ? useRuntimeConfig().apiBase : ''
  return $fetch<T>(`${base}/api/v1/public${path}`, opts as never) as Promise<T>
}

/** Image URLs from the API are relative (/api/v1/...). Returns a maker of absolute ones
 *  (og:image, JSON-LD). Call it in setup: it reads the runtime config once. */
export function useAbsoluteUrl() {
  const { siteUrl } = useRuntimeConfig().public
  return (url: string) => `${siteUrl}${url}`
}

export function trackClick(workshopId: string, channel: 'phone' | 'viber' | 'telegram' | 'route', keySlug?: string) {
  // Fire and forget: never block the visitor's call.
  apiFetch(`/workshops/${workshopId}/click`, { method: 'POST', body: { channel, key_slug: keySlug ?? null } }).catch(() => {})
}
