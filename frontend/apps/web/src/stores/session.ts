import type { Schemas } from '@kv/api'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { setLocale } from '@/i18n'
import { call, client } from '@/lib/api'
import { tokenStore } from '@/lib/tokens'

type Me = Schemas['MeOut']
const WS_KEY = 'kv.workshop'

export const useSession = defineStore('session', () => {
  const me = ref<Me | null>(null)
  const loaded = ref(false)
  const workshopId = ref<string | null>(localStorage.getItem(WS_KEY))

  const isLoggedIn = computed(() => !!me.value)
  const workshops = computed(() => me.value?.workshops ?? [])
  const workshop = computed(
    () => workshops.value.find((w) => w.workshop_id === workshopId.value) ?? workshops.value[0] ?? null,
  )
  const wid = computed(() => workshop.value?.workshop_id ?? '')
  const isOwner = computed(() => workshop.value?.role === 'owner')
  const isAdmin = computed(() => !!me.value && (me.value.user.is_superadmin || me.value.user.permissions.length > 0))
  const isSuperadmin = computed(() => !!me.value?.user.is_superadmin)
  /** Admin-panel right check: superadmin has all of them. */
  function can(...perms: string[]) {
    const u = me.value?.user
    return !!u && (u.is_superadmin || perms.some((p) => u.permissions.includes(p)))
  }

  async function load() {
    if (!tokenStore.get()) {
      me.value = null
      loaded.value = true
      return
    }
    try {
      me.value = await call(client.GET('/api/v1/users/me'))
      setLocale(me.value.user.locale)
    } catch {
      me.value = null
    } finally {
      loaded.value = true
    }
  }

  async function login(email: string, password: string) {
    tokenStore.set(await call(client.POST('/api/v1/auth/login', { body: { email, password } })))
    await load()
  }

  async function signInWith(tokens: { access_token: string; refresh_token: string; expires_in: number }) {
    tokenStore.set(tokens)
    await load()
  }

  async function logout() {
    const t = tokenStore.get()
    if (t) {
      try {
        await client.POST('/api/v1/auth/logout', { body: { refresh_token: t.refresh_token } })
      } catch {
        /* offline: forget locally anyway */
      }
    }
    tokenStore.set(null)
    me.value = null
  }

  function selectWorkshop(id: string) {
    workshopId.value = id
    localStorage.setItem(WS_KEY, id)
  }

  async function updateMe(body: { full_name?: string; locale?: string }) {
    me.value = await call(client.PATCH('/api/v1/users/me', { body }))
    if (body.locale) setLocale(body.locale)
  }

  return {
    me, loaded, isLoggedIn, workshops, workshop, wid, isOwner, isAdmin, isSuperadmin, can,
    load, login, signInWith, logout, selectWorkshop, updateMe,
  }
})
