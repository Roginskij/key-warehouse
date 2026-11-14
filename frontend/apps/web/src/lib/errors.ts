import { ApiError } from '@kv/api'
import { i18n } from '@/i18n'

/** Human message for any error, in the current language. */
export function errorText(e: unknown): string {
  const t = i18n.global.t
  const te = i18n.global.te
  if (e instanceof ApiError) {
    const key = `errors.${e.code.replaceAll('.', '_')}`
    if (te(key)) return t(key, e.params as Record<string, unknown>)
    if (e.status === 429) return t('errors.rate_limited', e.params as Record<string, unknown>)
    if (e.status >= 500) return t('errors.server')
    return t('errors.unknown')
  }
  if (e instanceof TypeError) return t('errors.network')
  return t('errors.unknown')
}

/** Per-field messages for a 422 validation error: { email: '...', password: '...' }. */
export function fieldErrors(e: unknown): Record<string, string> {
  if (!(e instanceof ApiError) || e.code !== 'validation_error') return {}
  const t = i18n.global.t
  const out: Record<string, string> = {}
  for (const f of e.fields) {
    const key = `validation.${f.code}`
    out[f.field.split('.').pop() || f.field] = i18n.global.te(key) ? t(key) : t('validation.invalid')
  }
  return out
}
