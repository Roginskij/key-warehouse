import { createI18n } from 'vue-i18n'
import de from './locales/de'
import en from './locales/en'
import es from './locales/es'
import fr from './locales/fr'
import it from './locales/it'
import pl from './locales/pl'
import uk from './locales/uk'

/** Launch languages (plan). Anything missing falls back to English. */
export const LOCALES = [
  { code: 'uk', name: 'Українська' },
  { code: 'en', name: 'English' },
  { code: 'pl', name: 'Polski' },
  { code: 'de', name: 'Deutsch' },
  { code: 'fr', name: 'Français' },
  { code: 'es', name: 'Español' },
  { code: 'it', name: 'Italiano' },
] as const
export type Locale = (typeof LOCALES)[number]['code']

const STORAGE = 'kv.locale'

function detect(): Locale {
  try {
    const saved = localStorage.getItem(STORAGE)
    if (saved && LOCALES.some((l) => l.code === saved)) return saved as Locale
  } catch {
    /* ignore */
  }
  const nav = (navigator.language || 'en').slice(0, 2).toLowerCase()
  if (nav === 'ru') return 'uk'
  return (LOCALES.some((l) => l.code === nav) ? nav : 'en') as Locale
}

export const i18n = createI18n({
  legacy: false,
  locale: detect(),
  fallbackLocale: 'en',
  // pl/de/fr/es/it are machine translations — native speakers should review them (plan).
  messages: { uk, en, pl, de, fr, es, it } as Record<string, typeof uk>,
  missingWarn: false,
  fallbackWarn: false,
})

export function setLocale(code: string) {
  const l = (LOCALES.some((x) => x.code === code) ? code : 'en') as Locale
  ;(i18n.global.locale as unknown as { value: string }).value = l
  document.documentElement.lang = l
  try {
    localStorage.setItem(STORAGE, l)
  } catch {
    /* ignore */
  }
}
