import { createApi } from '@kv/api'
import { i18n } from '@/i18n'
import { tokenStore } from './tokens'

export const api = createApi({
  baseUrl: import.meta.env.VITE_API_URL ?? '',
  tokens: tokenStore,
  locale: () => i18n.global.locale.value,
  onSessionExpired: () => {
    // Router guard sends the user to /login on the next navigation.
    window.dispatchEvent(new CustomEvent('kv:session-expired'))
  },
})

export const { client, call, raw } = api
