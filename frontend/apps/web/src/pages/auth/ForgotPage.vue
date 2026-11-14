<template>
  <form v-if="!done" class="flex flex-1 flex-col gap-5" novalidate @submit.prevent="submit">
    <div class="flex flex-col gap-1">
      <h1 class="m-0 text-[26px] font-bold tracking-tight">{{ t('auth.forgotTitle') }}</h1>
      <p class="m-0 text-muted">{{ t('auth.forgotText') }}</p>
    </div>
    <UIField v-model="email" :label="t('auth.email')" type="email" autocomplete="email" inputmode="email" />
    <div v-if="error" role="alert" class="rounded-control bg-danger-bg px-4 py-3 text-danger">{{ error }}</div>
    <div class="mt-auto flex flex-col gap-3 pt-4">
      <UIButton type="submit" size="lg" block :loading="busy">{{ t('auth.sendLink') }}</UIButton>
      <RouterLink :to="{ name: 'login' }" class="text-center font-semibold text-ink">{{ t('auth.backToLogin') }}</RouterLink>
    </div>
  </form>
  <div v-else class="flex flex-1 flex-col items-center gap-4 pt-6 text-center">
    <h1 class="m-0 text-[24px] font-bold">{{ t('auth.checkEmailTitle') }}</h1>
    <p class="m-0 text-muted">{{ t('auth.forgotSent', { email }) }}</p>
    <RouterLink :to="{ name: 'login' }" class="mt-auto font-semibold text-ink">{{ t('auth.backToLogin') }}</RouterLink>
  </div>
</template>

<script setup lang="ts">
import { UIButton, UIField } from '@kv/ui'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'

const { t } = useI18n()
const email = ref('')
const done = ref(false)
const error = ref('')
const busy = ref(false)

async function submit() {
  busy.value = true
  error.value = ''
  try {
    await call(client.POST('/api/v1/auth/forgot-password', { body: { email: email.value } }))
    done.value = true
  } catch (e) {
    error.value = errorText(e)
  } finally {
    busy.value = false
  }
}
</script>
