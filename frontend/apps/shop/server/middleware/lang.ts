/**
 * "/" → the visitor's language. Runs before the page cache, so every visitor
 * gets their own answer (a cached page would send everyone to the same language).
 */
const LANGS = ['uk', 'en', 'pl', 'de', 'fr', 'es', 'it']

export default defineEventHandler((event) => {
  if (event.path !== '/' && !event.path.startsWith('/?')) return
  let lang = 'en'
  for (const part of (getHeader(event, 'accept-language') ?? '').split(',')) {
    const code = part.trim().slice(0, 2).toLowerCase()
    if (LANGS.includes(code)) {
      lang = code
      break
    }
    if (code === 'ru') {
      lang = 'uk'
      break
    }
  }
  setHeader(event, 'vary', 'Accept-Language')
  return sendRedirect(event, `/${lang}`, 302)
})
