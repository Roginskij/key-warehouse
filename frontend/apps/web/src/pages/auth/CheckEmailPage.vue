<template>
  <div class="flex flex-1 flex-col items-center gap-4 pt-6 text-center">
    <span class="flex size-16 items-center justify-center rounded-full bg-primary-soft"><UIIcon name="check" :size="32" :stroke="2.6" /></span>
    <h1 class="m-0 text-[24px] font-bold">{{ t('auth.checkEmailTitle') }}</h1>
    <p class="m-0 text-[16px] text-muted">{{ t('auth.checkEmailText', { email }) }}</p>
    <p class="m-0 text-[15px] text-muted">{{ t('auth.checkSpam') }}</p>
    <UIButton v-if="email && !sent" variant="outline" @click="resend">{{ t('auth.resendLink') }}</UIButton>
    <p v-if="sent" class="m-0 font-semibold">{{ t('auth.resent') }}</p>
    <RouterLink :to="{ name: 'login' }" class="mt-auto font-semibold text-ink">{{ t('auth.backToLogin') }}</RouterLink>
  </div>
</template>

<script setup lang="ts">
import { UIButton, UIIcon } from '@kv/ui'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { call, client } from '@/lib/api'

const { t } = useI18n()
const email = String(useRoute().query.email ?? '')
const sent = ref(false)

async function resend() {
  if (!email) return
  await call(client.POST('/api/v1/auth/resend-verification', { body: { email } })).catch(() => {})
  sent.value = true
}
</script>
