import tailwindcss from '@tailwindcss/vite'

/**
 * Public site (SEO): key pages for Google, "find a workshop", waitlist.
 * Pages are rendered on the server and cached (swr), so Google gets full HTML fast.
 * API calls go to the FastAPI backend: on the server directly (apiBase),
 * from the browser through /api/** on this same host (server/routes/api).
 */
export default defineNuxtConfig({
  compatibilityDate: '2026-11-01',
  devtools: { enabled: false },
  css: ['~/assets/main.css'],
  vite: { plugins: [tailwindcss()] },
  build: { transpile: ['@kv/ui'] },
  runtimeConfig: {
    apiBase: 'http://localhost:8000', // NUXT_API_BASE
    public: {
      siteUrl: 'http://localhost:3000', // NUXT_PUBLIC_SITE_URL (canonical, sitemap, hreflang)
      appUrl: 'http://localhost:5173', // NUXT_PUBLIC_APP_URL (the workshop app)
    },
  },
  // Production only: cache rendered HTML for 10 min, then refresh in the background
  // (stale-while-revalidate). In development every request renders fresh.
  $production: {
    routeRules: {
      '/*/keys/**': { swr: 600 },
      '/*/workshops': { swr: 300 },
      '/*': { swr: 600 },
      '/sitemap.xml': { swr: 3600 },
    },
  },
  app: {
    head: {
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' },
        { name: 'theme-color', content: '#3a3a3f' },
      ],
      link: [{ rel: 'icon', href: '/favicon.svg', type: 'image/svg+xml' }],
    },
  },
})
