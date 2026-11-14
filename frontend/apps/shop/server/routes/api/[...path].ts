/** Browser → this host → backend. Keeps one origin for the site (no CORS, cookies untouched). */
export default defineEventHandler((event) => {
  const { apiBase } = useRuntimeConfig(event)
  return proxyRequest(event, `${apiBase}${event.path}`)
})
