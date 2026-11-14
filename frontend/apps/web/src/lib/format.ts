import { i18n } from '@/i18n'

const INTL: Record<string, string> = { uk: 'uk-UA', en: 'en-GB', pl: 'pl-PL', de: 'de-DE', fr: 'fr-FR', es: 'es-ES', it: 'it-IT' }
const loc = () => INTL[i18n.global.locale.value] ?? 'en-GB'

export function money(amount: string | number | null | undefined, currency: string | null | undefined) {
  if (amount === null || amount === undefined || amount === '' || !currency) return '—'
  const n = typeof amount === 'string' ? Number(amount) : amount
  return new Intl.NumberFormat(loc(), {
    style: 'currency',
    currency,
    maximumFractionDigits: n % 1 === 0 ? 0 : 2,
  }).format(n)
}

export function num(n: number) {
  return new Intl.NumberFormat(loc()).format(n)
}

export function dateTime(iso: string | null | undefined) {
  if (!iso) return ''
  const d = new Date(iso)
  const today = new Date()
  const sameDay = d.toDateString() === today.toDateString()
  const time = new Intl.DateTimeFormat(loc(), { hour: '2-digit', minute: '2-digit' }).format(d)
  if (sameDay) return `${i18n.global.t('common.today')} ${time}`
  return `${new Intl.DateTimeFormat(loc(), { day: 'numeric', month: 'short' }).format(d)} ${time}`
}
