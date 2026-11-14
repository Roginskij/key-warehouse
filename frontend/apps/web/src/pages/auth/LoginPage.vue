<template>
  <form class="flex flex-1 flex-col gap-5" novalidate @submit.prevent="submit">
    <div class="flex flex-col gap-1">
      <h1 class="m-0 text-[26px] font-bold tracking-tight">{{ t('auth.loginTitle') }}</h1>
      <p class="m-0 text-muted">{{ t('auth.loginSubtitle') }}</p>
    </div>
    <UIField v-model="email" :label="t('auth.email')" type="email" autocomplete="email" inputmode="email" required />
    <UIField
      v-model="password"
      :label="t('auth.password')"
      type="password"
      autocomplete="current-password"
      :show-password-label="t('auth.showPassword')"
      required
    />
    <div v-if="error" role="alert" class="rounded-control bg-danger-bg px-4 py-3 text-[15px] text-danger">
      {{ error }}
      <button v-if="notVerified && !resent" type="button" class="ml-1 font-bold underline" @click="resend">
        {{ t('auth.resendLink') }}
      </button>
      <span v-if="resent" class="ml-1 font-semibold">{{ t('auth.resent') }}</span>
    </div>
    <RouterLink :to="{ name: 'forgot' }" class="self-start text-[15px] font-semibold text-ink">
      {{ t('auth.forgot') }}
    </RouterLink>
    <div class="mt-auto flex flex-col gap-3 pt-4">
      <UIButton type="submit" size="lg" block :loading="busy">{{ t('auth.loginButton') }}</UIButton>
      <p class="m-0 text-center text-[15px] text-muted">
        {{ t('auth.noAccount') }}
        <RouterLink :to="{ name: 'register' }" class="font-semibold text-ink">{{ t('auth.createAccount') }}</RouterLink>
      </p>
    </div>
  </form>
</template>

<script setup lang="ts">
import { ApiError } from '@kv/api'
import { UIButton, UIField } from '@kv/ui'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { useSession } from '@/stores/session'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSession()

const email = ref('')
const password = ref('')
const error = ref('')
const notVerified = ref(false)
const busy = ref(false)
const resent = ref(false)

async function submit() {
  busy.value = true
  error.value = ''
  notVerified.value = false
  try {
    await session.login(email.value, password.value)
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/') ? route.query.next : '/stock'
    router.replace(next)
  } catch (e) {
    notVerified.value = e instanceof ApiError && e.code === 'auth.email_not_verified'
    error.value = errorText(e)
  } finally {
    busy.value = false
  }
}

async function resend() {
  await call(client.POST('/api/v1/auth/resend-verification', { body: { email: email.value } })).catch(() => {})
  resent.value = true
}
</script>
