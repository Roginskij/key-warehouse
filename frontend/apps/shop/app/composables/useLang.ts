import de from '~/i18n/de'
import en from '~/i18n/en'
import es from '~/i18n/es'
import fr from '~/i18n/fr'
import it from '~/i18n/it'
import pl from '~/i18n/pl'
import uk from '~/i18n/uk'

export const LANGS = ['uk', 'en', 'pl', 'de', 'fr', 'es', 'it'] as const
export type Lang = (typeof LANGS)[number]
const DICTS: Record<Lang, typeof uk> = { uk, en, pl, de, fr, es, it }

export const isLang = (v: unknown): v is Lang => typeof v === 'string' && (LANGS as readonly string[]).includes(v)

/** Current language from the URL (/uk/..., /de/...) and a tiny t('a.b', {n}) helper. */
export function useLang() {
  const route = useRoute()
  const lang = computed<Lang>(() => (isLang(route.params.lang) ? route.params.lang : 'en'))
  const dict = computed(() => DICTS[lang.value])
  function t(key: string, params: Record<string, string | number> = {}): string {
    let v: unknown = dict.value
    for (const k of key.split('.')) v = (v as Record<string, unknown> | undefined)?.[k]
    if (typeof v !== 'string') return key
    return v.replace(/\{(\w+)\}/g, (_, p) => String(params[p] ?? `{${p}}`))
  }
  const path = (p = '') => `/${lang.value}${p}`
  return { lang, t, path, dict }
}

/** canonical + hreflang for every language + og:url. `p` is the path after /<lang>. */
export function useSeoLinks(p: MaybeRefOrGetter<string>) {
  const { siteUrl } = useRuntimeConfig().public
  const { lang } = useLang()
  useHead(() => {
    const rest = toValue(p)
    return {
      htmlAttrs: { lang: lang.value },
      link: [
        { rel: 'canonical', href: `${siteUrl}/${lang.value}${rest}` },
        ...LANGS.map((l) => ({ rel: 'alternate' as const, hreflang: l, href: `${siteUrl}/${l}${rest}` })),
        { rel: 'alternate', hreflang: 'x-default', href: `${siteUrl}/en${rest}` },
      ],
      meta: [
        { property: 'og:url', content: `${siteUrl}/${lang.value}${rest}` },
        { property: 'og:site_name', content: 'KeyVerhaus' },
        { property: 'og:locale', content: lang.value },
      ],
    }
  })
}
