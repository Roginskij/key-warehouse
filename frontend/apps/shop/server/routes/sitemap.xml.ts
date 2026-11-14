/** Every published key page in every language, with hreflang alternates. */
const LANGS = ['uk', 'en', 'pl', 'de', 'fr', 'es', 'it']

export default defineEventHandler(async (event) => {
  const { apiBase, public: pub } = useRuntimeConfig(event)
  const site = pub.siteUrl
  const data = await $fetch<{ keys: { slug: string; updated_at: string }[] }>(`${apiBase}/api/v1/public/sitemap`)
  const pages: { path: string; lastmod?: string }[] = [
    { path: '' },
    { path: '/keys' },
    { path: '/workshops' },
    ...data.keys.map((k) => ({ path: `/keys/${k.slug}`, lastmod: k.updated_at.slice(0, 10) })),
  ]
  const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;')
  const urls = pages.flatMap((p) =>
    LANGS.map((l) => {
      const alts = LANGS.map((a) => `<xhtml:link rel="alternate" hreflang="${a}" href="${esc(`${site}/${a}${p.path}`)}"/>`).join('')
      return `<url><loc>${esc(`${site}/${l}${p.path}`)}</loc>${p.lastmod ? `<lastmod>${p.lastmod}</lastmod>` : ''}${alts}</url>`
    }),
  )
  setHeader(event, 'content-type', 'application/xml; charset=utf-8')
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n${urls.join('\n')}\n</urlset>\n`
})
