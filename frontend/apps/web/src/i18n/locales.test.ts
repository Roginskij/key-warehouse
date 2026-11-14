import { createI18n } from 'vue-i18n'
import { describe, expect, it } from 'vitest'
import de from './locales/de'
import en from './locales/en'
import es from './locales/es'
import fr from './locales/fr'
import itLocale from './locales/it'
import pl from './locales/pl'
import uk from './locales/uk'

const LOCALES = { uk, en, pl, de, fr, es, it: itLocale }

function keys(obj: Record<string, unknown>, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    typeof v === 'object' && v !== null ? keys(v as Record<string, unknown>, `${prefix}${k}.`) : [`${prefix}${k}`],
  )
}

describe('translations', () => {
  const all = keys(uk)

  for (const [code, messages] of Object.entries(LOCALES)) {
    it(`${code}: every key exists and every message compiles`, () => {
      const i18n = createI18n({ legacy: false, locale: code, messages: { [code]: messages }, missingWarn: false })
      const t = i18n.global.t
      for (const key of all) {
        expect(i18n.global.te(key), `${code} is missing ${key}`).toBe(true)
        // Throws on broken message syntax ({, |, @ …).
        const out = t(key, { n: 1, email: 'a@b.c', name: 'X', min: 1, place: 'P', cars: 'C', items: 1, pieces: 1,
          workshop: 'W', role: 'R', cur: 'UAH', have: 1, list: 'USD', base: 'UAH', available: 1, retry_after: 5,
          date: 'D', a: 'A', b: 'B', sub: 'S', item: 'I', code: 'C', dup: 'D', main: 'M', created: 1, codes: 1 })
        expect(out, `${code}:${key}`).not.toBe('')
        expect(out, `${code}:${key} has unfilled placeholder`).not.toMatch(/\{[a-z_]+\}/)
      }
    })
  }
})
