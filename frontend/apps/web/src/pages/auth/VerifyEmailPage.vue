<template>
  <div class="flex flex-1 flex-col items-center gap-4 pt-6 text-center">
    <template v-if="!error">
      <span class="size-10 animate-spin rounded-full border-4 border-primary border-t-transparent" aria-hidden="true" />
      <p class="m-0 text-[16px]">{{ t('auth.verifying') }}</p>
    </template>
    <template v-else>
      <h1 class="m-0 text-[24px] font-bold">{{ t('auth.linkProblem') }}</h1>
      <p class="m-0 text-muted">{{ error }}</p>
      <RouterLink :to="{ name: 'login' }" class="no-underline"><UIButton>{{ t('auth.backToLogin') }}</UIButton></RouterLink>
    </template>
  </div>
</template>

<script setup lang="ts">
import { UIButton } from '@kv/ui'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { useSession } from '@/stores/session'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSession()
const error = ref('')

onMounted(async () => {
  try {
    const tokens = await call(client.POST('/api/v1/auth/verify-email', { body: { token: String(route.query.token ?? '') } }))
    await session.signInWith(tokens)
    router.replace({ name: 'stock', query: { welcome: '1' } })
  } catch (e) {
    error.value = errorText(e)
  }
})
</script>
