<template>
  <div class="flex flex-1 flex-col gap-5">
    <template v-if="info">
      <div class="flex flex-col gap-1">
        <h1 class="m-0 text-[24px] font-bold">{{ t('invite.title', { workshop: info.workshop_name }) }}</h1>
        <p class="m-0 text-muted">{{ t('invite.subtitle', { email: info.email, role: t(`roles.${info.role}`) }) }}</p>
      </div>

      <template v-if="info.account_exists">
        <UIButton v-if="signedInAsInvitee" size="lg" block :loading="busy" @click="accept">{{ t('invite.accept') }}</UIButton>
        <template v-else>
          <p class="m-0">{{ t('invite.loginFirst', { email: info.email }) }}</p>
          <RouterLink :to="{ name: 'login', query: { next: route.fullPath } }" class="no-underline">
            <UIButton size="lg" block>{{ t('auth.loginButton') }}</UIButton>
          </RouterLink>
        </template>
      </template>

      <form v-else class="flex flex-col gap-4" novalidate @submit.prevent="accept">
        <UIField v-model="form.full_name" :label="t('auth.name')" autocomplete="name" :error="errors.full_name" />
        <UIField
          v-model="form.password"
          :label="t('auth.password')"
          type="password"
          autocomplete="new-password"
          :hint="t('auth.passwordHint')"
          :show-password-label="t('auth.showPassword')"
          :error="errors.password"
        />
        <label class="flex items-start gap-3 text-[15px]">
          <input v-model="form.accept_terms" type="checkbox" class="mt-0.5 size-6 shrink-0 accent-ink" />
          <span>{{ t('auth.terms') }}</span>
        </label>
        <UIButton type="submit" size="lg" block :loading="busy">{{ t('invite.join') }}</UIButton>
      </form>
    </template>
    <div v-if="error" role="alert" class="rounded-control bg-danger-bg px-4 py-3 text-danger">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import type { Schemas } from '@kv/api'
import { UIButton, UIField } from '@kv/ui'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { call, client } from '@/lib/api'
import { errorText, fieldErrors } from '@/lib/errors'
import { useSession } from '@/stores/session'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSession()
const token = String(route.query.token ?? '')

const info = ref<Schemas['InvitationPublicOut'] | null>(null)
const error = ref('')
const errors = ref<Record<string, string>>({})
const busy = ref(false)
const form = ref({ full_name: '', password: '', accept_terms: false })

const signedInAsInvitee = computed(() => session.me?.user.email === info.value?.email)

onMounted(async () => {
  try {
    info.value = await call(client.POST('/api/v1/invitations/preview', { body: { token } }))
  } catch (e) {
    error.value = errorText(e)
  }
})

async function accept() {
  busy.value = true
  error.value = ''
  errors.value = {}
  try {
    const body = info.value?.account_exists
      ? { token, accept_terms: true }
      : { token, ...form.value, locale: locale.value }
    const res = await call(client.POST('/api/v1/invitations/accept', { body }))
    if (res.tokens) await session.signInWith(res.tokens)
    else await session.load()
    session.selectWorkshop(res.workshop_id)
    router.replace({ name: 'stock' })
  } catch (e) {
    errors.value = fieldErrors(e)
    if (!Object.keys(errors.value).length) error.value = errorText(e)
  } finally {
    busy.value = false
  }
}
</script>
